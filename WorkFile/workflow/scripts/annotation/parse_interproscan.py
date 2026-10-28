#!/usr/bin/env python3
"""Normalise InterProScan 5 TSV output for JBrowse and database upload.

Standard InterProScan TSV columns:
protein, md5, length, member_db, signature_acc, signature_desc, start, end,
score, status, date, interpro_acc, interpro_desc, go_terms, pathways.

Member database names are mapped to the lowercase values stored in
`annotation_source`; unmapped databases fall back to `interproscan`.
"""
import argparse
import os
import sys

HEADER = [
    "protein_id", "md5", "length", "member_db", "signature_acc",
    "signature_desc", "start", "end", "score", "status", "date",
    "interpro_acc", "interpro_desc", "go_terms", "pathways", "annotation_source",
]

SOURCE_MAP = {
    "pfam": "pfam",
    "smart": "smart",
    "prositeprofiles": "prosite",
    "prositepatterns": "prosite",
    "prints": "prints",
    "superfamily": "superfamily",
    "ssf": "superfamily",
    "cdd": "cdd",
    "gene3d": "gene3d",
    "hamap": "hamap",
    "panther": "panther",
    "pirsf": "pirsf",
    "sfld": "sfld",
    "tigrfam": "tigrfams",
    "tigrfams": "tigrfams",
    "funfam": "funfam",
    "ncbifam": "interproscan",
}


def normalise_source(member_db):
    key = "".join(ch for ch in member_db.lower() if ch.isalnum())
    return SOURCE_MAP.get(key, "interproscan")


def main():
    ap = argparse.ArgumentParser(description="Normalise InterProScan TSV")
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERROR] input not found: {args.input}", file=sys.stderr)
        return 3

    seen = set()
    rows = []
    with open(args.input, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 14:
                continue
            parts += [""] * (15 - len(parts))
            source = normalise_source(parts[3])
            key = (parts[0], parts[4], parts[6], parts[7], parts[11])
            if key in seen:
                continue
            seen.add(key)
            rows.append(parts[:14] + [parts[14], source])

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as out:
        out.write("\t".join(HEADER) + "\n")
        for row in rows:
            out.write("\t".join(row) + "\n")
    if not rows:
        print("[WARN] InterProScan TSV contained no hits", file=sys.stderr)
    print(f"[OK] InterProScan: {len(rows)} unique rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())