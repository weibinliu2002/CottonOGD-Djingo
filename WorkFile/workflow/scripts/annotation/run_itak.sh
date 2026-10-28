#!/usr/bin/env bash
# iTAK transcription-factor / kinase identification.
# Legacy invocation: python iTAK.py <proteins.fa> -o <outdir> -p <threads>.
# iTAK names result files inside a sub-directory that depends on the input file
# name, so copy the three files we consume to stable paths afterwards.
set -euo pipefail

PROTEINS="$1"
OUTDIR="$2"
PREFIX="$3"
THREADS="$4"
PYTHON_BIN="${5:-python3}"
ITAK="${6:-iTAK.py}"

mkdir -p "$OUTDIR"
STAGE="$OUTDIR/${PREFIX}.pro.fa"
if [ "$(readlink -f "$PROTEINS")" != "$(readlink -f "$STAGE" 2>/dev/null || true)" ]; then
    cp -f "$PROTEINS" "$STAGE"
fi

RAW="$OUTDIR/raw"
rm -rf "$RAW"
mkdir -p "$RAW"

"$PYTHON_BIN" "$ITAK" "$STAGE" -o "$RAW" -p "$THREADS"

copied=0
for name in tf_classification.txt shiu_classification.txt tf_tr_kinase_with_uniprot.txt; do
    src="$(find "$RAW" -type f -name "$name" -print -quit)"
    if [ -n "$src" ]; then
        cp -f "$src" "$OUTDIR/$name"
        copied=$((copied + 1))
    else
        echo "[WARN] iTAK output not found: $name" >&2
        : > "$OUTDIR/$name"
    fi
done

if [ "$copied" -eq 0 ]; then
    echo "[ERROR] iTAK produced no classification files" >&2
    exit 3
fi

echo "[OK] iTAK finished ($copied/3 files)"