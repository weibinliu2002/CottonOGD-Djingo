#!/usr/bin/env python3
"""Run `assembly-stats` on a genome FASTA and emit the result as JSON.

assembly-stats (https://github.com/sanger-pathogens/assembly-stats) reports
per-assembly statistics: total size, sequence count, mean/shortest/longest and
the N10/N50/.../N90 contiguity metrics. We call it with `-s` (grep-friendly
output: one `key<TAB>value` line per metric) and write a compact JSON so the
values can be merged into qc_report.yaml.
"""
import argparse
import json
import os
import re
import subprocess
import sys


def parse_assembly_stats(stdout):
    """Parse `assembly-stats -s` output into a flat dict of numbers.

    `-s` prints one line per metric, each `filename<TAB>key<TAB>value`.
    """
    data = {}
    for line in stdout.splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        key = parts[1].strip()
        raw = parts[2].strip()
        m = re.match(r"^-?\d+(?:\.\d+)?$", raw)
        if not m:
            continue
        value = float(raw)
        if value.is_integer():
            value = int(value)
        data[key] = value
    return data


def main():
    ap = argparse.ArgumentParser(description="Run assembly-stats and emit JSON")
    ap.add_argument("--genome", required=True, help="genome FASTA")
    ap.add_argument("--assembly-stats", default="assembly-stats",
                    help="path to assembly-stats binary")
    ap.add_argument("--out", required=True, help="output JSON path")
    args = ap.parse_args()

    try:
        proc = subprocess.run(
            [args.assembly_stats, "-s", args.genome],
            check=True, capture_output=True, text=True,
        )
    except FileNotFoundError:
        print(f"[ERROR] assembly-stats binary not found: {args.assembly_stats}",
              file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] assembly-stats failed: {exc.stderr}", file=sys.stderr)
        return exc.returncode

    data = parse_assembly_stats(proc.stdout)
    if not data:
        print(f"[ERROR] no statistics parsed from assembly-stats output:\n{proc.stdout}",
              file=sys.stderr)
        return 2

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    keys = ", ".join(f"{k}={data[k]}" for k in ("total_length", "number", "N50", "longest") if k in data)
    print(f"[OK] assembly_stats: {keys}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
