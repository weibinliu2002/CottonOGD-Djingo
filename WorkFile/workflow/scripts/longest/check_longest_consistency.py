#!/usr/bin/env python3
"""Check that protein/CDS/mRNA longest-sequence runs selected compatible IDs.

The external longest script runs independently on each FASTA. This check is
advisory: it reports IDs that appear in one output but not another, and fails
only when a mapping-rate threshold is violated (handled by run_longest.py).
"""
import argparse
import json
import os
import sys


def ids(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith(">"):
                out.append(line[1:].split()[0])
    return out


def main():
    ap = argparse.ArgumentParser(description="Longest-ID consistency check")
    ap.add_argument("--pro", required=True)
    ap.add_argument("--cds", required=True)
    ap.add_argument("--mrna", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pro, cds, mrna = ids(args.pro), ids(args.cds), ids(args.mrna)
    sets = {"pro": set(pro), "cds": set(cds), "mrna": set(mrna)}
    common = set.intersection(*sets.values()) if sets else set()
    only = {k: sorted(v - common)[:50] for k, v in sets.items()}
    report = {
        "counts": {k: len(v) for k, v in sets.items()},
        "common": len(common),
        "only_first_50": only,
        "consistent": len(common) == max((len(v) for v in sets.values()), default=0),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))
    if not report["consistent"]:
        print(
            "[WARNING] pro/cds/mrna selected different IDs; protein result is "
            "authoritative for downstream annotation.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())