#!/usr/bin/env bash
# LAI calculation, parameterised from Script/CottonOGD/LAI/LAI.sh.
set -euo pipefail

GENOME="$1"          # renamed genome in OUTDIR (basename used)
OUTDIR="$2"
PREFIX="$3"
THREADS="$4"
LAI_BIN="${5:-LAI}"

cd "$OUTDIR"
GENOME_BASE="$(basename "$GENOME")"

"$LAI_BIN" -genome "$GENOME_BASE" \
    -intact "${GENOME_BASE}.pass.list" \
    -all "${GENOME_BASE}.out" \
    -t "$THREADS"

if [ -f "${GENOME_BASE}.out.LAI" ]; then
    cp -f "${GENOME_BASE}.out.LAI" "${PREFIX}.out.LAI"
else
    echo "[ERROR] LAI did not produce ${GENOME_BASE}.out.LAI" >&2
    exit 3
fi

echo "[OK] LAI finished: ${PREFIX}.out.LAI"