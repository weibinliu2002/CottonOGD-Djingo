#!/usr/bin/env python3
"""Genome size = sum of all FASTA sequence lengths (legacy Genome_size.R)."""
import argparse
import gzip
import json
import os
import sys


def open_text(path):
    with open(path, "rb") as fh:
        magic = fh.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description="Calculate genome size")
    ap.add_argument("--genome", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    total = 0
    count = 0
    with open_text(args.genome) as fh:
        for line in fh:
            if line.startswith(">"):
                count += 1
            elif line.strip():
                total += len(line.strip())
    if count == 0:
        print("[ERROR] no sequences in genome", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"genome_size": total, "sequence_count": count}, fh, indent=2)
    print(f"[OK] genome_size={total} sequence_count={count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())