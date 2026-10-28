#!/usr/bin/env python3
"""Summarise EDTA output for QC and database upload.

The EDTA GFF3 is the authoritative source for feature counts by class; the
`.TEanno.sum` file, when parseable, supplies the masked-base count (features in
the GFF can overlap, so summing them would overestimate the masked genome).
"""
import argparse
import json
import os
import re
import sys

import yaml


def parse_gff(path):
    total = 0
    by_class = {}
    ltr_features = 0
    intact_ltr = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9:
                continue
            try:
                start, end = int(parts[3]), int(parts[4])
            except ValueError:
                continue
            length = max(0, end - start + 1)
            total += length

            attrs = {}
            for item in parts[8].split(";"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    attrs[key.strip()] = value.strip()
            classification = attrs.get("Classification") or attrs.get("Name") or parts[2]
            by_class[classification] = by_class.get(classification, 0) + 1

            is_ltr = "LTR" in classification.upper() or "LTR" in parts[2].upper()
            if is_ltr:
                ltr_features += 1
                if "intact" in classification.lower() or "intact" in parts[8].lower():
                    intact_ltr += 1
    return {
        "gff_bp": total,
        "feature_count": sum(by_class.values()),
        "class_counts": by_class,
        "ltr_count": ltr_features,
        "intact_ltr_count": intact_ltr,
    }


def parse_sum(path):
    """Return (masked_bp, rows). Column layout differs between EDTA versions, so
    pick the count and bp columns positionally after the class name."""
    rows = []
    masked_bp = 0
    if not path or not os.path.exists(path):
        return masked_bp, rows
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = re.split(r"\t| {2,}", line.rstrip("\n"))
            parts = [p for p in parts if p != ""]
            if len(parts) < 3:
                continue
            # EDTA versions may append a Total/All summary row; summing it
            # together with the per-class rows would double count the genome.
            if parts[0].strip().lower() in ("total", "all", "sum"):
                continue
            numbers = []
            for token in parts[1:]:
                token = token.replace(",", "").rstrip("%")
                try:
                    numbers.append(float(token))
                except ValueError:
                    numbers = []
                    break
            if len(numbers) < 2:
                continue
            count, bp = int(numbers[0]), int(numbers[1])
            masked_bp += bp
            rows.append({"class": parts[0], "count": count, "bp": bp})
    return masked_bp, rows


def main():
    ap = argparse.ArgumentParser(description="Summarise EDTA TE annotation")
    ap.add_argument("--gff", required=True)
    ap.add_argument("--sum", required=False)
    ap.add_argument("--genome-size", required=False, help="genome_size.json from QC")
    ap.add_argument("--metadata", required=False, help="sample metadata.yaml")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not os.path.exists(args.gff):
        print(f"[ERROR] GFF not found: {args.gff}", file=sys.stderr)
        return 3

    gff_stats = parse_gff(args.gff)
    masked_bp, sum_rows = parse_sum(args.sum)
    if not masked_bp:
        # Fall back to the GFF total and flag the approximation.
        masked_bp = gff_stats["gff_bp"]

    genome_size = None
    if args.genome_size and os.path.exists(args.genome_size):
        with open(args.genome_size, "r", encoding="utf-8") as fh:
            genome_size = json.load(fh).get("genome_size")
    if genome_size is None and args.metadata and os.path.exists(args.metadata):
        # genome_size may have been marked as already-completed in MySQL, in
        # which case no qc/genome_size.json is produced by the workflow.
        with open(args.metadata, "r", encoding="utf-8") as fh:
            meta = yaml.safe_load(fh) or {}
        existing = meta.get("existing_qc") or {}
        if "genome_size" in (meta.get("qc_completed") or []):
            genome_size = existing.get("genome_size")

    pct = round(masked_bp / genome_size * 100, 2) if genome_size else None
    report = {
        "masked_bp": masked_bp,
        "genome_size": genome_size,
        "te_content_pct": pct,
        "gff_bp": gff_stats["gff_bp"],
        "feature_count": gff_stats["feature_count"],
        "class_counts": gff_stats["class_counts"],
        "ltr_count": gff_stats["ltr_count"],
        "intact_ltr_count": gff_stats["intact_ltr_count"],
        "sum_rows": sum_rows,
        "masked_bp_source": "sum" if sum_rows else "gff",
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"[OK] TE {pct}% masked ({report['masked_bp_source']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())