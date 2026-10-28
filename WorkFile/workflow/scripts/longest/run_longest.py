#!/usr/bin/env python3
"""Run the user-provided longest_protein_by_gene.py and record statistics.

The external script is intentionally not copied or modified. It accepts a
protein/nucleotide FASTA plus GFF and keeps one record per gene (longest
sequence, then lowest isoform number, then first in file).
"""
import argparse
import json
import os
import subprocess
import sys


def count_fasta(path):
    n = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith(">"):
                n += 1
    return n


def count_lines(path, header=True):
    if not os.path.exists(path):
        return 0
    n = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return max(0, n - (1 if header else 0))


def main():
    ap = argparse.ArgumentParser(description="Longest sequence per gene")
    ap.add_argument("--input", required=True)
    ap.add_argument("--gff", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--unmapped-tsv", required=True)
    ap.add_argument("--unmapped-fasta", required=True)
    ap.add_argument("--stats", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--min-mapping-rate", type=float, default=0.0)
    args = ap.parse_args()

    if not os.path.exists(args.tool):
        print(f"[ERROR] longest script not found: {args.tool}", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    cmd = [
        sys.executable, args.tool,
        "-i", args.input,
        "-g", args.gff,
        "-o", args.out,
        "--unmapped-tsv", args.unmapped_tsv,
        "--unmapped-fasta", args.unmapped_fasta,
        "-v",
    ]
    print("[CMD] " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print(f"[ERROR] longest script failed with exit {proc.returncode}", file=sys.stderr)
        return proc.returncode or 3

    total = count_fasta(args.input)
    selected = count_fasta(args.out)
    unmapped = count_lines(args.unmapped_tsv)
    mapped = max(0, total - unmapped)
    rate = (mapped / total) if total else 0.0
    stats = {
        "input": args.input,
        "gff": args.gff,
        "output": args.out,
        "input_records": total,
        "selected_records": selected,
        "unmapped_records": unmapped,
        "mapped_records": mapped,
        "mapping_rate": round(rate, 6),
        "min_mapping_rate": args.min_mapping_rate,
    }
    with open(args.stats, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(json.dumps(stats, indent=2))

    if args.min_mapping_rate and rate < args.min_mapping_rate:
        print(
            f"[ERROR] mapping rate {rate:.4f} < {args.min_mapping_rate:.4f}",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())