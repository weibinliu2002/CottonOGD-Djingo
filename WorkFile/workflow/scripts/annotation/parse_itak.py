#!/usr/bin/env python3
"""Normalise iTAK transcription-factor and kinase classifications.

Input layouts (tab-separated, no header), matching the legacy
`import_itak_to_genefamily.py` parser:

* tf_classification.txt: gene_id, class_name, TF_class (TF/TR), TF_name
* shiu_classification.txt: gene_id, kinase_name

The output is a single TSV used by `db_upload.py`; no database writes happen
here and the `genefamily` table is never truncated.
"""
import argparse
import os
import sys

HEADER = ["gene_id", "TF_class", "TF_name", "class_name", "category"]


def parse_tf(path, rows):
    if not path or not os.path.exists(path):
        return 0
    n = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2 or not parts[0].strip():
                continue
            gene_id = parts[0].strip()
            if len(parts) >= 4:
                class_name, tf_class, tf_name = parts[1], parts[2], parts[3]
            elif len(parts) == 3:
                class_name, tf_class, tf_name = parts[1], parts[2], parts[2]
            else:
                class_name, tf_class, tf_name = parts[1], "TF", parts[1]
            rows.append([gene_id, tf_class, tf_name, class_name, tf_class])
            n += 1
    return n


def parse_shiu(path, rows):
    if not path or not os.path.exists(path):
        return 0
    n = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2 or not parts[0].strip():
                continue
            gene_id, gene_name = parts[0].strip(), parts[1].strip()
            class_name = gene_name.split("_")[0] if "_" in gene_name else gene_name
            rows.append([gene_id, "kinase", gene_name, class_name, "kinase"])
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description="Normalise iTAK outputs")
    ap.add_argument("--tf", required=True)
    ap.add_argument("--shiu", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    n_tf = parse_tf(args.tf, rows)
    n_kinase = parse_shiu(args.shiu, rows)
    if not rows:
        print("[ERROR] no iTAK records parsed", file=sys.stderr)
        return 3

    seen = set()
    unique = []
    for row in rows:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            unique.append(row)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\t".join(HEADER) + "\n")
        for row in unique:
            fh.write("\t".join(row) + "\n")
    print(f"[OK] iTAK: {n_tf} TF/TR, {n_kinase} kinase, {len(unique)} unique")
    return 0


if __name__ == "__main__":
    sys.exit(main())