#!/usr/bin/env bash
"""Fetch and cache NCBI metadata for a single assembly accession.

Usage:
  fetch_ncbi.sh <accession> <out_dir>

Downloads (if not already cached):
  <out_dir>/sequence_report.jsonl   -- datasets summary genome --report sequence
  <out_dir>/metadata.json           -- datasets summary genome --report genome (summary)
"""
set -euo pipefail

ACC="$1"
OUT_DIR="$2"
DATASETS="${DATASETS_BIN:-/home/web/bin/datasets}"

SEQ_REPORT="$OUT_DIR/sequence_report.jsonl"
GENOME_REPORT="$OUT_DIR/genome_report.jsonl"

mkdir -p "$OUT_DIR"

if [ ! -s "$SEQ_REPORT" ]; then
    "$DATASETS" summary genome accession "$ACC" --report sequence --as-json-lines > "$SEQ_REPORT" \
        || { echo "ERROR: datasets sequence report failed for $ACC" >&2; rm -f "$SEQ_REPORT"; exit 1; }
fi

if [ ! -s "$GENOME_REPORT" ]; then
    "$DATASETS" summary genome accession "$ACC" --report genome --as-json-lines > "$GENOME_REPORT" \
        || { echo "ERROR: datasets genome report failed for $ACC" >&2; rm -f "$GENOME_REPORT"; exit 1; }
fi

echo "NCBI metadata cached for $ACC -> $OUT_DIR"