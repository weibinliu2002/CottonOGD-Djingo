#!/usr/bin/env bash
# UniProt protein alignment using the legacy BLAST database.
# Input database is a BLASTP database (`uniprot.psq`), matching the pipeline
# that produced best_hits.m8 for unipro_annotation.py.
set -euo pipefail

PROTEINS="$1"
DB="$2"
OUT="$3"
TMP="$4"
THREADS="$5"
EVALUE="${6:-1e-5}"
BLASTP="${7:-blastp}"

mkdir -p "$(dirname "$OUT")" "$TMP"
"$BLASTP" -query "$PROTEINS" -db "$DB" -out "$OUT" \
    -outfmt 6 -evalue "$EVALUE" -max_target_seqs 1 -max_hsps 1 \
    -num_threads "$THREADS"

if [ ! -s "$OUT" ]; then
    echo "[WARN] BLASTP produced no hits: $OUT" >&2
   : > "$OUT"
fi

echo "[OK] UniProt BLASTP finished"