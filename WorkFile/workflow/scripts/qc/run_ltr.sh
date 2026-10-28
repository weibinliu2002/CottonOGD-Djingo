#!/usr/bin/env bash
# LTR discovery + LTR_retriever, parameterised from Script/CottonOGD/LAI/LAI.sh.
# The caller must provide a genome whose sequence IDs are seq1..seqN so that
# LTR_retriever/LAI output is deterministic and traceable via id_map.tsv.
set -euo pipefail

GENOME="$1"
OUTDIR="$2"
PREFIX="$3"
THREADS_FINDER="$4"
THREADS_RETRIEVER="$5"
SIZE="$6"
TIME="$7"
LTR_FINDER="${8:-LTR_FINDER_parallel}"
GT="${9:-gt}"
LTR_RETRIEVER="${10:-LTR_retriever}"

mkdir -p "$OUTDIR"
cd "$OUTDIR"
GENOME_BASE="$(basename "$GENOME")"

"$LTR_FINDER" -seq "$GENOME_BASE" -threads "$THREADS_FINDER" \
    -harvest_out -size "$SIZE" -time "$TIME" &
PID_FINDER=$!

(
    "$GT" suffixerator -db "$GENOME_BASE" -indexname "$GENOME_BASE" \
        -tis -suf -lcp -des -ssp -sds -dna &&
    "$GT" ltrharvest -index "$GENOME_BASE" \
        -minlenltr 100 -maxlenltr 7000 -mintsd 4 -maxtsd 6 \
        -motif TGCA -motifmis 1 -similar 85 -vic 10 -seed 20 -seqids yes \
        > "${GENOME_BASE}.harvest.scn"
) &
PID_HARVEST=$!

STATUS=0
wait "$PID_FINDER" || STATUS=$?
wait "$PID_HARVEST" || STATUS=$?
if [ "$STATUS" -ne 0 ]; then
    echo "[ERROR] LTR_FINDER_parallel or gt ltrharvest failed" >&2
    exit "$STATUS"
fi

if [ -f "${GENOME_BASE}.finder.combine.scn" ]; then
    cat "${GENOME_BASE}.harvest.scn" "${GENOME_BASE}.finder.combine.scn" > "${PREFIX}.rawLTR.scn"
else
    cp "${GENOME_BASE}.harvest.scn" "${PREFIX}.rawLTR.scn"
fi

"$LTR_RETRIEVER" -genome "$GENOME_BASE" -inharvest "${PREFIX}.rawLTR.scn" \
    -threads "$THREADS_RETRIEVER"

echo "[OK] LTR_retriever finished: ${GENOME_BASE}.pass.list, ${GENOME_BASE}.out"