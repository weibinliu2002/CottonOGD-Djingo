#!/usr/bin/env bash
# EDTA transposable-element annotation.
# Legacy behaviour preserved: EDTA.pl with --anno 1, optional --cds and
# --sensitive, single run over the genome. Outputs are renamed to the names
# used by the rest of the workflow.
set -euo pipefail

GENOME="$1"
CDS="$2"
OUTDIR="$3"
PREFIX="$4"
THREADS="$5"
SENSITIVE="${6:-1}"
SPECIES_NAME="${7:-others}"
EDTA_BIN="${8:-EDTA.pl}"

mkdir -p "$OUTDIR"
cd "$OUTDIR"

# EDTA derives output names from the input file name. Work on a stable
# per-species copy so parallel species never collide in a shared directory.
GENOME_LOCAL="${PREFIX}.fa"
if [ ! -e "$GENOME_LOCAL" ] || [ "$(readlink -f "$GENOME")" != "$(readlink -f "$GENOME_LOCAL")" ]; then
    cp -f "$GENOME" "$GENOME_LOCAL"
fi

ARGS=(--genome "$GENOME_LOCAL" --species "$SPECIES_NAME" --step all
      --anno 1 --sensitive "$SENSITIVE" --threads "$THREADS")
if [ -n "$CDS" ] && [ -f "$CDS" ]; then
    ARGS+=(--cds "$CDS")
fi

"$EDTA_BIN" "${ARGS[@]}"

# Normalise output names: <prefix>.fa.mod.EDTA.* -> <prefix>.EDTA.*
for suffix in TEanno.gff3 TEanno.sum TElib.fa; do
    src="${GENOME_LOCAL}.mod.EDTA.${suffix}"
    dst="${PREFIX}.EDTA.${suffix}"
    if [ -f "$src" ]; then
        mv -f "$src" "$dst"
    elif [ -f "${OUTDIR}/${src}" ]; then
        mv -f "${OUTDIR}/${src}" "${OUTDIR}/${dst}"
    else
        echo "[WARN] EDTA output not found: $src" >&2
    fi
done

if [ ! -f "${PREFIX}.EDTA.TEanno.gff3" ]; then
    echo "[ERROR] EDTA did not produce ${PREFIX}.EDTA.TEanno.gff3" >&2
    exit 3
fi

echo "[OK] EDTA finished"