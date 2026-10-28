#!/usr/bin/env bash
# BUSCO in protein mode, matching Script/CottonOGD/busco/busco.sh.
set -euo pipefail

PROTEINS="$1"
OUTDIR="$2"
PREFIX="$3"
LINEAGE="$4"
AUGUSTUS_SPECIES="$5"
THREADS="$6"
BUSCO_BIN="${7:-busco}"

mkdir -p "$OUTDIR"
"$BUSCO_BIN" -i "$PROTEINS" \
    --out_path "$OUTDIR" -o "$PREFIX" \
    --lineage_dataset "$LINEAGE" \
    -f -m proteins --augustus -c "$THREADS" \
    --augustus_species "$AUGUSTUS_SPECIES" --long --offline

echo "[OK] BUSCO finished"