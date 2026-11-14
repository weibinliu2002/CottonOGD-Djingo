#!/usr/bin/env python3
"""Genome size = sum of all FASTA sequence lengths (legacy Genome_size.R).

To avoid a second full-genome scan, the values are taken from the
precomputed ``assembly_stats.json`` (--stats) when present: assembly-stats
already reports ``total_length`` (= genome_size) and ``number`` (=
sequence_count). The FASTA is only scanned as a fallback for standalone use
or when the stats file is missing.
"""
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


def read_stats(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (ValueError, OSError):
        return None
    size = data.get("total_length")
    count = data.get("number")
    if size is None or count is None:
        return None
    return int(size), int(count)


def scan_fasta(genome):
    total = 0
    count = 0
    with open_text(genome) as fh:
        for line in fh:
            if line.startswith(">"):
                count += 1
            elif line.strip():
                total += len(line.strip())
    if count == 0:
        return None
    return total, count


def main():
    ap = argparse.ArgumentParser(description="Calculate genome size")
    ap.add_argument("--genome", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stats", default="",
                    help="precomputed assembly_stats.json (preferred source)")
    args = ap.parse_args()

    result = read_stats(args.stats)
    source = "assembly_stats"
    if result is None:
        result = scan_fasta(args.genome)
        source = "fasta_scan"
    if result is None:
        print("[ERROR] no sequences found and no valid stats file", file=sys.stderr)
        return 2

    total, count = result
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"genome_size": total, "sequence_count": count}, fh, indent=2)
    print(f"[OK] genome_size={total} sequence_count={count} (source={source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
