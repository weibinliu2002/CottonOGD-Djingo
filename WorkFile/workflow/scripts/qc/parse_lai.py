#!/usr/bin/env python3
"""Parse LAI .out.LAI and take the first whole_genome row (legacy LAI_summary.R)."""
import argparse
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser(description="Parse LAI output")
    ap.add_argument("--input", required=True, help="*.out.LAI")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    header = None
    row = None
    with open(args.input, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                continue
            if parts[0] == "whole_genome":
                row = parts
                break
    if row is None:
        print(f"[ERROR] no whole_genome row in {args.input}", file=sys.stderr)
        return 3
    try:
        lai = float(row[-1])
    except ValueError:
        print(f"[ERROR] non-numeric LAI value: {row[-1]!r}", file=sys.stderr)
        return 3
    report = {
        "lai": lai,
        "intact": row[3] if len(row) > 3 else None,
        "total": row[4] if len(row) > 4 else None,
        "raw_lai": row[5] if len(row) > 5 else None,
        "raw_line": "\t".join(row),
        "columns": header,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"[OK] LAI={lai}")
    return 0


if __name__ == "__main__":
    sys.exit(main())