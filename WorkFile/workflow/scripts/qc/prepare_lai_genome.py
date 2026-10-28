#!/usr/bin/env python3
"""Create the deterministic seq1..seqN genome used by the legacy LAI pipeline."""
import argparse
import gzip
import os
import sys


def open_text(path):
    with open(path, "rb") as fh:
        magic = fh.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description="Rename genome IDs for LAI")
    ap.add_argument("--genome", required=True)
    ap.add_argument("--out-fasta", required=True)
    ap.add_argument("--out-map", required=True)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out_fasta)), exist_ok=True)
    mapping = []
    n = 0
    with open_text(args.genome) as fh, \
            open(args.out_fasta, "w", encoding="utf-8") as out:
        for line in fh:
            if line.startswith(">"):
                n += 1
                original = line[1:].strip().split()[0]
                new = f"seq{n}"
                mapping.append((original, new))
                out.write(f">{new}\n")
            else:
                out.write(line)
    with open(args.out_map, "w", encoding="utf-8") as fh:
        for original, new in mapping:
            fh.write(f"{original}\t{new}\n")
    if n == 0:
        print("[ERROR] genome has no sequences", file=sys.stderr)
        return 2
    print(f"[OK] renamed {n} sequences")
    return 0


if __name__ == "__main__":
    sys.exit(main())