#!/usr/bin/env python3
"""Aggregate QC results and build the batch summary report.

Modes
-----
qc:      merge validation/genome size/LAI/BUSCO/TE JSON into qc_report.yaml.
summary: scan results/*/ and write summary.tsv + summary.html.

Computed values always win over user metadata; conflicts are recorded as
warnings, never silently accepted.
"""
import argparse
import glob
import html
import json
import os
import sys
from datetime import datetime, timezone

import yaml


def read_json(path):
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return None


def count_fasta(path):
    n = 0
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith(">"):
                n += 1
    return n


def conflict_warnings(meta, computed):
    warnings = []
    aliases = {
        "genome_size": ["genome_size", "Genome_size"],
        "lai": ["lai", "LAI", "LAI_value"],
        "busco": ["busco", "BUSCO", "Busco"],
    }
    for key, names in aliases.items():
        if computed.get(key) is None:
            continue
        for name in names:
            if name in meta and meta[name] not in (None, ""):
                warnings.append(
                    f"metadata field {name}={meta[name]!r} conflicts with computed "
                    f"{key}={computed[key]!r}; computed value used"
                )
    return warnings


def existing_qc_value(meta, metric, completed):
    """Return a MySQL-backed QC value for a metric marked as completed."""
    if metric not in completed:
        return None
    existing = meta.get("existing_qc") or {}
    value = existing.get(metric)
    return value if value not in (None, "") else None


def qc_mode(args):
    meta = {}
    if args.metadata and os.path.exists(args.metadata):
        with open(args.metadata, "r", encoding="utf-8") as fh:
            meta = yaml.safe_load(fh) or {}
    completed = {str(x) for x in (meta.get("qc_completed") or [])}
    qc_sources = meta.get("qc_sources") or {}
    validation = read_json(args.validation) or {}
    genome_size = read_json(args.genome_size)
    lai = read_json(args.lai)
    busco = read_json(args.busco)
    te = read_json(args.te)

    # Metrics already present in MySQL are not recomputed. Reconstruct the same
    # JSON shape used by the parsers so qc_report and db_upload stay unchanged.
    if genome_size is None:
        value = existing_qc_value(meta, "genome_size", completed)
        if value is not None:
            genome_size = {
                "genome_size": int(value),
                "sequence_count": None,
                "source": qc_sources.get("genome_size", "existing_mysql"),
            }
    if lai is None:
        value = existing_qc_value(meta, "lai", completed)
        if value is not None:
            lai = {
                "lai": float(value),
                "raw_value": str(value),
                "source": qc_sources.get("lai", "existing_mysql"),
            }
    if busco is None:
        value = existing_qc_value(meta, "busco", completed)
        if value is not None:
            busco = {
                "busco_fraction": float(value),
                "lineage": meta.get("busco_lineage"),
                "source": qc_sources.get("busco", "existing_mysql"),
            }

    computed = {
        "genome_size": genome_size.get("genome_size") if genome_size else None,
        "lai": lai.get("lai") if lai else None,
        "busco": busco.get("busco_fraction") if busco else None,
    }
    warnings = conflict_warnings(meta, computed)
    warnings.extend(validation.get("warnings", []))
    for item in meta.get("legacy_qc_conflicts") or []:
        action = item.get("action", "conflict_kept_mysql")
        if action == "invalid_mysql_replaced_by_legacy":
            warnings.append(
                f"{item.get('metric')}: invalid MySQL value {item.get('database')!r} "
                f"replaced by legacy value {item.get('legacy')!r} "
                f"from {item.get('source')}"
            )
        else:
            warnings.append(
                f"{item.get('metric')}: MySQL value {item.get('database')!r} "
                f"differs from legacy value {item.get('legacy')!r} "
                f"({item.get('source')}); MySQL value kept"
            )

    report = {
        "species": args.species,
        "species_name": meta.get("species_name", args.species),
        "annotation_version": meta.get("annotation_version"),
        "assembly_version": meta.get("assembly_version"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gene_count": (validation.get("gff") or {}).get("gene_count"),
        "transcript_count": (validation.get("gff") or {}).get("transcript_count"),
        "genome_size": computed["genome_size"],
        "sequence_count": (genome_size or {}).get("sequence_count"),
        "lai": lai,
        "busco": busco,
        "te": te,
        "qc_completed": sorted(completed),
        "qc_sources": qc_sources,
        "metadata": meta,
        "warnings": warnings,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out_yaml)), exist_ok=True)
    with open(args.out_yaml, "w", encoding="utf-8") as fh:
        yaml.safe_dump(report, fh, allow_unicode=True, sort_keys=False)
    with open(args.out_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    for warning in warnings:
        print(f"[WARNING] {warning}", file=sys.stderr)
    print(f"[OK] QC report for {args.species}")
    return 0


def summary_row(species_dir):
    species = os.path.basename(species_dir.rstrip("/"))
    qc = {}
    qc_yaml = os.path.join(species_dir, "qc", "qc_report.yaml")
    if os.path.exists(qc_yaml):
        with open(qc_yaml, "r", encoding="utf-8") as fh:
            qc = yaml.safe_load(fh) or {}
    upload = read_json(os.path.join(species_dir, "upload", "upload_report.json")) or {}
    row = {
        "species": species,
        "ploidy": (qc.get("metadata") or {}).get("ploidy"),
        "genome_size": qc.get("genome_size"),
        "LAI": qc.get("lai", {}).get("lai") if isinstance(qc.get("lai"), dict) else None,
        "BUSCO": qc.get("busco", {}).get("busco_fraction") if isinstance(qc.get("busco"), dict) else None,
        "gene_count": qc.get("gene_count"),
        "longest_transcript_count": count_fasta(
            os.path.join(species_dir, "longest", "mrna_longest.fasta")
        ),
        "upload_status": upload.get("status", "pending"),
        "jbrowse": os.path.exists(os.path.join(species_dir, "jbrowse", "jbrowse.done")),
        "blast": os.path.exists(os.path.join(species_dir, "blast", "blast.done")),
    }
    return row


def summary_mode(args):
    species_dirs = sorted(
        d for d in glob.glob(os.path.join(args.results_dir, "*"))
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "qc", "qc_report.yaml"))
    )
    rows = [summary_row(d) for d in species_dirs]
    columns = [
        "species", "ploidy", "genome_size", "LAI", "BUSCO", "gene_count",
        "longest_transcript_count", "upload_status", "jbrowse", "blast",
    ]
    os.makedirs(os.path.dirname(os.path.abspath(args.out_tsv)), exist_ok=True)
    with open(args.out_tsv, "w", encoding="utf-8") as fh:
        fh.write("\t".join(columns) + "\n")
        for row in rows:
            fh.write("\t".join("" if row.get(c) is None else str(row.get(c)) for c in columns) + "\n")

    head = "".join(f"<th>{html.escape(c)}</th>" for c in columns)
    body = []
    for row in rows:
        cells = "".join(
            f"<td>{html.escape('' if row.get(c) is None else str(row.get(c)))}</td>"
            for c in columns
        )
        body.append(f"<tr>{cells}</tr>")
    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>CottonOGD batch summary</title>
<style>body{{font-family:sans-serif;margin:2rem}}table{{border-collapse:collapse}}
th,td{{border:1px solid #ccc;padding:.35rem .6rem;font-size:13px}}
th{{background:#f3f3f3;position:sticky;top:0}}tr:nth-child(even){{background:#fafafa}}</style>
</head><body><h1>CottonOGD batch summary</h1>
<p>Generated {html.escape(datetime.now(timezone.utc).isoformat())} · {len(rows)} species</p>
<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>
</body></html>
"""
    with open(args.out_html, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"[OK] summary: {len(rows)} species -> {args.out_tsv}, {args.out_html}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Aggregate QC/summary reports")
    ap.add_argument("--mode", choices=["qc", "summary"], required=True)
    ap.add_argument("--species", default="")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--metadata", default="")
    ap.add_argument("--validation", default="")
    ap.add_argument("--genome-size", default="")
    ap.add_argument("--lai", default="")
    ap.add_argument("--busco", default="")
    ap.add_argument("--te", default="")
    ap.add_argument("--out-yaml", default="")
    ap.add_argument("--out-json", default="")
    ap.add_argument("--out-tsv", default="")
    ap.add_argument("--out-html", default="")
    args = ap.parse_args()

    if args.mode == "qc":
        if not args.species or not args.out_yaml or not args.out_json:
            print("[ERROR] qc mode requires --species/--out-yaml/--out-json", file=sys.stderr)
            return 2
        return qc_mode(args)
    if not args.out_tsv or not args.out_html:
        print("[ERROR] summary mode requires --out-tsv/--out-html", file=sys.stderr)
        return 2
    return summary_mode(args)


if __name__ == "__main__":
    sys.exit(main())