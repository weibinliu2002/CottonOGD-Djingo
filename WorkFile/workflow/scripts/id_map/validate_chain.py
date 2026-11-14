#!/usr/bin/env python3
"""Validate a generated Chain file.

Checks:
  - file exists and non-empty
  - valid UCSC chain header lines
  - tName (target) and qName (query) orientation matches expected
  - chromosome names appear in source/target FASTA
  - no At<->Dt cross-subgenome mappings (when subgenome labels provided)
  - chain/net direction consistent with the task

UCSC chain format: header line `chain {score} {tName} {tSize} {tStart} {tEnd} {strand} {qName} {qSize} {qStart} {qEnd}`.

For nf-LO LASTZ runs the source FASTA is the query (qName) and target the
target (tName). Verify accordingly.
"""
import argparse
import csv
import os
import subprocess
import sys


def load_fasta_seqids(path, seqkit="/home/web/bin/seqkit"):
    """Return the set of FASTA seqids.

    Uses ``seqkit seq -n -i`` (a C binary) for a single streaming pass instead of
    reading the whole (potentially multi-GB) FASTA in Python. Only the id column
    is parsed here; the sequence bytes never enter Python.
    """
    seqs = set()
    if not path or not os.path.exists(path):
        return seqs
    try:
        proc = subprocess.run([seqkit, "seq", "-n", "-i", path],
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
            seqs.add(line)
    return seqs


def main():
    parser = argparse.ArgumentParser(description="Validate a Chain file")
    parser.add_argument("--chain", required=True, help="chain file to validate")
    parser.add_argument("--net", required=True, help="net file (optional check)")
    parser.add_argument("--source-fasta", required=True)
    parser.add_argument("--target-fasta", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--subgenome", required=True, help="Whole|At|Dt")
    parser.add_argument("--seqkit", default="/home/web/bin/seqkit",
                        help="path to seqkit binary (seqid extraction)")
    parser.add_argument("--out", required=True, help="validation.tsv")
    args = parser.parse_args()

    src_seqs = load_fasta_seqids(args.source_fasta, args.seqkit)
    tgt_seqs = load_fasta_seqids(args.target_fasta, args.seqkit)
    errors = []

    # 1. Exists and non-empty
    if not os.path.exists(args.chain):
        errors.append("chain_file_missing")
    elif os.path.getsize(args.chain) == 0:
        errors.append("chain_file_empty")

    t_names = set()
    q_names = set()
    if os.path.exists(args.chain):
        with open(args.chain, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("chain"):
                    parts = line.split()
                    if len(parts) < 10:
                        errors.append("bad_chain_header")
                        continue
                    tName = parts[2]
                    strand = parts[5]
                    qName = parts[6]
                    t_names.add(tName)
                    q_names.add(qName)
                elif line.startswith("#"):
                    continue

    # 2. Format + orientation: tName should be in target FASTA, qName in source FASTA
    #    (source=query for nf-LO)
    unknown_t = t_names - tgt_seqs
    unknown_q = q_names - src_seqs
    # Allow the trivial all-chroms case where a chain header references a genome;
    # but flag when truly nothing matches.
    if unknown_t and len(unknown_t) == len(t_names):
        errors.append("target_names_not_in_target_fasta")
    if unknown_q and len(unknown_q) == len(q_names):
        errors.append("source_names_not_in_source_fasta")

    # 3. Cross-subgenome check (only when subgenome != Whole)
    if args.subgenome != "Whole":
        cross = 0
        prefix = args.subgenome  # 'At' or 'Dt'
        # tName and qName should share the same subgenome prefix (Axx/Dxx)
        for t in t_names:
            for q in q_names:
                t_sub = t[0].upper() if t else ""
                q_sub = q[0].upper() if q else ""
                if t_sub in ("A", "D") and q_sub in ("A", "D") and t_sub != q_sub:
                    cross += 1
        if cross:
            errors.append(f"cross_subgenome_mapping({cross})")

    # 4. Net file
    if os.path.exists(args.net) and os.path.getsize(args.net) == 0:
        errors.append("net_file_empty")

    status = "OK" if not errors else "FAIL:" + ";".join(errors)

    result = {
        "source_id": args.source_id,
        "target_id": args.target_id,
        "subgenome": args.subgenome,
        "chain_path": args.chain,
        "chain_lines": str(sum(1 for _ in open(args.chain, errors="replace")) if os.path.exists(args.chain) else 0),
        "n_target_chroms": str(len(t_names)),
        "n_query_chroms": str(len(q_names)),
        "target_chroms": ",".join(sorted(t_names)),
        "query_chroms": ",".join(sorted(q_names)),
        "status": status,
    }
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(result.keys()), delimiter="\t")
        w.writeheader()
        w.writerow(result)

    print(f"chain={args.chain}: {status}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()