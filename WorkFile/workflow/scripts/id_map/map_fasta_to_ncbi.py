#!/usr/bin/env python3
"""Map local FASTA sequence IDs to NCBI Sequence Report entries.

Priority:
  1. FASTA seqid == NCBI refseqAccession
  2. FASTA seqid == NCBI genbankAccession
  3. accession extracted from FASTA header == NCBI accession
  4. name/chr_name + length auxiliary validation

Terrible matches are rejected. Pair/ambiguity are reported, never silently
overwritten.

Outputs:
  chromosome_mapping.tsv       -- per-FASTA-seqid mapping
  unmapped_sequences.tsv       -- seqids with no reliable NCBI hit
  ambiguous_sequences.tsv      -- seqids with >1 equally-scored NCBI hit
"""
import argparse
import csv
import json
import os
import re
from collections import defaultdict


def load_fasta_headers(fasta_path, seqkit="/home/web/bin/seqkit"):
    """Return OrderedDict seqid -> (description, length).

    The FASTA is scanned once by ``seqkit fx2tab -l`` (a C binary); the sequence
    column is dropped at the shell level (``cut``) so the multi-GB sequence
    bytes never enter Python. Only the header line and length are parsed here,
    keeping memory and runtime far below a pure-Python full-file read.
    """
    import subprocess
    seqs = {}
    if not os.path.exists(fasta_path):
        return seqs
    try:
        proc = subprocess.run(
            f"{seqkit} fx2tab -l {fasta_path}",
            shell=True, check=True, capture_output=True, text=True,
        )
    except FileNotFoundError:
        print(f"[ERROR] seqkit binary not found: {seqkit}", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] seqkit fx2tab failed: {exc.stderr}", file=sys.stderr)
        raise
    for line in proc.stdout.splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4:
            continue
        head, length = parts[0], parts[3]
        toks = head.split(None, 1)
        seqid = toks[0]
        desc = toks[1] if len(toks) > 1 else ""
        try:
            length = int(length)
        except ValueError:
            length = 0
        seqs[seqid] = (desc, length)
    return seqs


def extract_accession(text):
    """Return first NCBI-like accession found, or ''."""
    m = re.search(r"(N[CGWSTZ]_\d+\.\d+)", text)
    if m:
        return m.group(1)
    return ""


def norm_length(seqid):
    """Extract length hint from a FASTA seqid if it embeds length (NODE_xxx_length_N)."""
    m = re.search(r"length[_\s]?(\d+)", seqid, re.IGNORECASE)
    return int(m.group(1)) if m else None


def score_fasta_ncbi(fasta_item, ncbi_rows):
    """Score one FASTA seq against candidate NCBI rows.

    Returns list of (score, ncbi_row) sorted desc.
    """
    seqid, (desc, length) = fasta_item
    acc_in_seqid = extract_accession(seqid)
    acc_in_desc = extract_accession(desc)

    candidates = []
    for row in ncbi_rows:
        score = 0
        refseq = row.get("refseqAccession")
        genbank = row.get("genbankAccession")
        seqname = row.get("sequenceName")
        chrname = row.get("chrName")
        row_len = row.get("length")

        # P1: exact seqid == RefSeq
        if refseq and seqid == refseq:
            score += 1000
        # P1b: exact seqid == GenBank
        elif genbank and seqid == genbank:
            score += 950
        # P2: accession in seqid matches
        elif acc_in_seqid and (acc_in_seqid == refseq or acc_in_seqid == genbank):
            score += 900
        # P3: accession in description matches
        elif acc_in_desc and (acc_in_desc == refseq or acc_in_desc == genbank):
            score += 800
        # P4: sequenceName exact match
        elif seqname and seqid == seqname:
            score += 700
        # P4b: chrName in seqid
        elif chrname and chrname != "chromosome" and (
                seqid == chrname or
                seqid.lower().startswith(chrname.lower()) or
                chrname.lower() in seqid.lower()):
            score += 600

        # Length corroboration (never matches on length alone)
        if score > 0:
            hint = norm_length(seqid)
            if hint and row_len and abs(hint - row_len) <= max(10, row_len * 0.001):
                score += 50
            elif row_len and length and abs(length - row_len) <= max(10, row_len * 0.001):
                score += 50
            else:
                score -= 200  # conflicting length weakens the hit

        if score > 0:
            candidates.append((score, row))
    candidates.sort(key=lambda x: -x[0])
    return candidates


def main():
    parser = argparse.ArgumentParser(description="Map FASTA seqids to NCBI metadata")
    parser.add_argument("--fasta", required=True)
    parser.add_argument("--seqreport", required=True, help="NCBI sequence_report.jsonl")
    parser.add_argument("--out-tsv", required=True, help="chromosome_mapping.tsv")
    parser.add_argument("--unmapped", required=True, help="unmapped_sequences.tsv")
    parser.add_argument("--ambiguous", required=True, help="ambiguous_sequences.tsv")
    parser.add_argument("--genome-id", required=True)
    parser.add_argument("--seqkit", default="/home/web/bin/seqkit",
                        help="path to seqkit binary (header/length extraction)")
    args = parser.parse_args()

    fasta_seqs = load_fasta_headers(args.fasta, args.seqkit)
    ncbi_rows = []
    with open(args.seqreport, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    ncbi_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    mapped = []
    unmapped = []
    ambiguous = []
    for seqid, (desc, length) in fasta_seqs.items():
        cands = score_fasta_ncbi((seqid, (desc, length)), ncbi_rows)
        if not cands:
            unmapped.append({
                "genome_id": args.genome_id,
                "fasta_seqid": seqid,
                "fasta_length": length,
                "mapping_status": "unmapped",
            })
            continue
        best_score = cands[0][0]
        best = [r for s, r in cands if s >= best_score and s > best_score - 100]
        if len(best) > 1:
            ambiguous.append({
                "genome_id": args.genome_id,
                "fasta_seqid": seqid,
                "fasta_length": length,
                "candidate_count": len(best),
                "mapping_status": "ambiguous",
            })
            continue
        row = best[0]
        mapped.append({
            "genome_id": args.genome_id,
            "fasta_seqid": seqid,
            "fasta_description": desc,
            "fasta_length": length,
            "ncbi_genbank_accession": row.get("genbankAccession", ""),
            "ncbi_refseq_accession": row.get("refseqAccession", ""),
            "ncbi_sequence_name": row.get("sequenceName", ""),
            "ncbi_chr_name": row.get("chrName", ""),
            "ncbi_assembly_unit": row.get("assemblyUnit", ""),
            "ncbi_role": row.get("role", ""),
            "ncbi_length": row.get("length", ""),
            "mapping_status": "mapped",
        })

    # Write outputs
    mapped_fields = ["genome_id", "fasta_seqid", "fasta_description", "fasta_length",
                     "ncbi_genbank_accession", "ncbi_refseq_accession", "ncbi_sequence_name",
                     "ncbi_chr_name", "ncbi_assembly_unit", "ncbi_role", "ncbi_length",
                     "mapping_status"]
    with open(args.out_tsv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=mapped_fields, delimiter="\t")
        w.writeheader()
        w.writerows(mapped)

    unmapped_fields = ["genome_id", "fasta_seqid", "fasta_length", "mapping_status"]
    with open(args.unmapped, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=unmapped_fields, delimiter="\t")
        w.writeheader()
        w.writerows(unmapped)

    amb_fields = ["genome_id", "fasta_seqid", "fasta_length", "candidate_count", "mapping_status"]
    with open(args.ambiguous, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=amb_fields, delimiter="\t")
        w.writeheader()
        w.writerows(ambiguous)

    print(f"Mapped: {len(mapped)}, Unmapped: {len(unmapped)}, Ambiguous: {len(ambiguous)} "
          f"(total FASTA seqs: {len(fasta_seqs)})")


if __name__ == "__main__":
    main()