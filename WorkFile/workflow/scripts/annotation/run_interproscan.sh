#!/usr/bin/env bash
# InterProScan 5 run (TSV + InterPro + GO + pathway annotations).
set -euo pipefail

PROTEINS="$1"
OUTDIR="$2"
PREFIX="$3"
THREADS="$4"
INTERPROSCAN="${5:-interproscan.sh}"

mkdir -p "$OUTDIR"
"$INTERPROSCAN" -i "$PROTEINS" -f TSV -dp -goterms -pa \
    -cpu "$THREADS" -b "$OUTDIR/$PREFIX"

if [ ! -f "$OUTDIR/$PREFIX.tsv" ]; then
    echo "[WARN] InterProScan produced no TSV (no hits); creating empty file" >&2
    : > "$OUTDIR/$PREFIX.tsv"
fi

echo "[OK] InterProScan finished"