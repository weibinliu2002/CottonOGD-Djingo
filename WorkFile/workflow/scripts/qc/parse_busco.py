#!/usr/bin/env python3
"""Parse BUSCO short_summary.specific.*.txt (legacy busco_summary.R semantics)."""
import argparse
import glob
import json
import os
import re
import sys

KEYS = {
    "Complete BUSCOs": "complete",
    "Complete and single-copy BUSCOs": "single",
    "Complete and duplicated BUSCOs": "duplicated",
    "Fragmented BUSCOs": "fragmented",
    "Missing BUSCOs": "missing",
    "Total BUSCO groups searched": "total",
}


def main():
    ap = argparse.ArgumentParser(description="Parse BUSCO summary")
    ap.add_argument("--input", required=True, help="short_summary file or directory")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lineage", default="", help="BUSCO lineage name (for upload)")
    args = ap.parse_args()

    path = args.input
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "short_summary*.txt")))
        if not files:
            print(f"[ERROR] no short_summary*.txt in {path}", file=sys.stderr)
            return 3
        path = files[0]

    counts = {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.match(r"\s*(\d+)\s+(.+?)\s*$", line)
            if not m:
                continue
            value, label = int(m.group(1)), m.group(2).strip()
            for key, name in KEYS.items():
                if label.startswith(key):
                    counts[name] = value
                    break
    n = counts.get("total", 0)
    if not n:
        print(f"[ERROR] could not parse Total BUSCO groups from {path}", file=sys.stderr)
        return 3
    pct = {f"pc_{k}": round(counts.get(k, 0) / n * 100, 1) for k in
           ("complete", "single", "duplicated", "fragmented", "missing")}
    report = {
        "source": os.path.abspath(path),
        "lineage": args.lineage or None,
        **counts,
        **pct,
        "busco_fraction": round(counts.get("complete", 0) / n, 4),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())