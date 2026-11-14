#!/usr/bin/env python3
"""Assign At/Dt subgenome to each chromosome of a tetraploid genome.

Evidence sources (priority order):
  1. configured_mapping        -- user-supplied At/Dt lists from config.yaml
  2. ncbi_metadata            -- NCBI Assembly/Sequence Report organisation
  3. validated_name_rule      -- chromosome-name rules (Ghir_A01, A01, chrA01...)
  4. manual_mapping           -- (reserved) explicit per-chromosome mapping
  5. unassigned               -- no reliable assignment

Design notes:
  - A chromosome is At if its name/locus maps to the A subgenome; Dt for D.
  - Never infer subgenome from a single blind character.
  - Diploid genomes are not split: all chromosomes are "Whole".
  - Unreliably-determined chromosomes are reported as Unassigned, never
    silently merged into At or Dt.

Outputs:
  subgenome_mapping.tsv
  subgenome_summary.tsv
  unmapped_chromosomes.tsv
"""
import argparse
import csv
import json
import os
import re
import sys
import yaml


def load_config_mapping(config_path):
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return cfg.get("id_map", {}).get("subgenome_mapping", {}) or {}


def load_fasta_seqids(fasta_path, seqkit="/home/web/bin/seqkit"):
    """Return FASTA seqids in file order.

    Uses ``seqkit seq -n -i`` (a C binary) for a single streaming pass instead of
    reading the whole (potentially multi-GB) FASTA in Python. Only the id column
    is parsed here; the sequence bytes never enter Python.
    """
    import subprocess
    seqs = []
    if not os.path.exists(fasta_path):
        return seqs
    try:
        proc = subprocess.run([seqkit, "seq", "-n", "-i", fasta_path],
                              check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print(f"[ERROR] seqkit binary not found: {seqkit}", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] seqkit seq failed: {exc.stderr}", file=sys.stderr)
        raise
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            seqs.append(line)
    return seqs


def load_ncbi_report(path):
    rows = []
    if not path or not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def normalize_chr_key(seqid, desc):
    """Canonical chromosome key for configured-mapping lookup."""
    m = re.search(r"([AD]\d{1,2})$", seqid)
    if m:
        return m.group(1)
    m = re.search(r"[Cc]hromosome\s+([AD]\d+)", desc or "")
    if m:
        return m.group(1)
    return seqid


def infer_by_name_rule(seqid, desc):
    """Return (subgenome, method, confidence) or (None, None, None)."""
    joined = seqid + (" " + desc if desc else "")
    m = re.search(r"(?<![A-Za-z])([AD])(\d{1,2})(?![A-Za-z0-9])", joined)
    if m:
        return ("At" if m.group(1).upper() == "A" else "Dt", "validated_name_rule", "high")
    m = re.search(r"[Cc]hromosome\s+([AD])(\d+)", joined)
    if m:
        return ("At" if m.group(1).upper() == "A" else "Dt", "validated_name_rule", "high")
    return (None, None, None)


def is_tetraploid(genome_type, ploidy):
    if ploidy == "allotetraploid":
        return True
    if genome_type and genome_type.startswith("AD"):
        return True
    return False


def match_ncbi(sub, rows, seqid, desc):
    """Best NCBI evidence for this seqid (returns subgenome or None)."""
    acc = ""
    m = re.search(r"(N[CGWSTZ]_\d+\.\d+)", seqid + " " + desc)
    if m:
        acc = m.group(1)
    for r in rows:
        ref = r.get("refseqAccession", "")
        gb = r.get("genbankAccession", "")
        if acc and (acc == ref or acc == gb):
            cn = r.get("chrName", "")
            m2 = re.search(r"([AD])\d+", cn or "")
            if m2:
                return "At" if m2.group(1).upper() == "A" else "Dt"
    return None


def main():
    parser = argparse.ArgumentParser(description="Assign At/Dt subgenomes")
    parser.add_argument("--fasta", required=True, help="source genome FASTA")
    parser.add_argument("--genome-id", required=True)
    parser.add_argument("--genome-type", required=True)
    parser.add_argument("--ploidy", required=True)
    parser.add_argument("--config", required=True, help="config.yaml")
    parser.add_argument("--ncbi-report", default="", help="cached NCBI sequence_report.jsonl (optional)")
    parser.add_argument("--seqkit", default="/home/web/bin/seqkit",
                        help="path to seqkit binary (seqid extraction)")
    parser.add_argument("--out-tsv", required=True)
    parser.add_argument("--out-summary", required=True)
    parser.add_argument("--out-unmapped", required=True)
    args = parser.parse_args()

    config_map = load_config_mapping(args.config)
    seqids = load_fasta_seqids(args.fasta, args.seqkit)
    ncbi_rows = load_ncbi_report(args.ncbi_report)

    genome_cfg = config_map.get(args.genome_id, {})
    cfg_at_keys = [normalize_chr_key(x, "") for x in (genome_cfg.get("At") or [])]
    cfg_dt_keys = [normalize_chr_key(x, "") for x in (genome_cfg.get("Dt") or [])]
    cfg_at_raw = genome_cfg.get("At") or []
    cfg_dt_raw = genome_cfg.get("Dt") or []

    tetra = is_tetraploid(args.genome_type, args.ploidy)

    assignments = []
    unmapped = []
    counts = {"At": set(), "Dt": set(), "Unassigned": set(), "Whole": set()}

    for seqid in seqids:
        desc = ""  # seqid-only for now
        sub = None
        method = None
        conf = None

        if not tetra:
            sub, method, conf = "Whole", "diploid_whole", "high"
        else:
            # 1. configured mapping
            key = normalize_chr_key(seqid, desc)
            if key in cfg_at_keys or seqid in cfg_at_raw or \
               any(seqid.startswith(p) for p in cfg_at_raw):
                sub, method, conf = "At", "configured_mapping", "high"
            elif key in cfg_dt_keys or seqid in cfg_dt_raw or \
                 any(seqid.startswith(p) for p in cfg_dt_raw):
                sub, method, conf = "Dt", "configured_mapping", "high"
            else:
                # 2. ncbi metadata
                if ncbi_rows:
                    nsub = match_ncbi(sub, ncbi_rows, seqid, desc)
                    if nsub:
                        sub, method, conf = nsub, "ncbi_metadata", "medium"
                # 3. name rule
                if sub is None:
                    sub, method, conf = infer_by_name_rule(seqid, desc)
                # 4/5. unassigned
                if sub is None:
                    sub, method, conf = "Unassigned", "unassigned", "low"

        counts[sub].add(seqid)
        assignments.append({
            "genome_id": args.genome_id,
            "genome_type": args.genome_type,
            "ploidy": args.ploidy,
            "fasta_seqid": seqid,
            "subgenome": sub,
            "assignment_method": method,
            "assignment_confidence": conf,
        })
        if tetra and sub == "Unassigned":
            unmapped.append({
                "genome_id": args.genome_id,
                "fasta_seqid": seqid,
                "subgenome": "Unassigned",
                "status": "unassigned",
            })

    fields = ["genome_id", "genome_type", "ploidy", "fasta_seqid",
              "subgenome", "assignment_method", "assignment_confidence"]
    with open(args.out_tsv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(assignments)

    summary = {
        "genome_id": args.genome_id,
        "genome_type": args.genome_type,
        "ploidy": args.ploidy,
        "total_seqids": len(seqids),
        "at_count": len(counts["At"]),
        "dt_count": len(counts["Dt"]),
        "whole_count": len(counts["Whole"]),
        "unassigned_count": len(counts["Unassigned"]),
        "completeness": "complete" if len(counts["Unassigned"]) == 0 else "incomplete",
    }
    with open(args.out_summary, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary.keys()), delimiter="\t")
        w.writeheader()
        w.writerow(summary)

    if unmapped:
        with open(args.out_unmapped, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(unmapped[0].keys()), delimiter="\t")
            w.writeheader()
            w.writerows(unmapped)
    else:
        open(args.out_unmapped, "w", encoding="utf-8").close()

    if tetra and counts["Unassigned"]:
        print(f"WARNING: {args.genome_id}: {len(counts['Unassigned'])} unassigned "
              f"(At={len(counts['At'])}, Dt={len(counts['Dt'])}).", file=sys.stderr)

    print(f"{args.genome_id}: tetra={tetra}, At={len(counts['At'])}, Dt={len(counts['Dt'])}, "
          f"Whole={len(counts['Whole'])}, Unassigned={len(counts['Unassigned'])}")


if __name__ == "__main__":
    main()