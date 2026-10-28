#!/usr/bin/env bash
# Add a JBrowse assembly and the canonical GFF track, then normalise URIs.
# Parameterised version of backend/static/jbrowse/add_jbrowes.sh.
set -euo pipefail

SPECIES="$1"
OUTDIR="$2"
GENOME_GZ="$3"
GFF_GZ="$4"
JBROWSE="${5:-jbrowse}"
PYTHON_BIN="${6:-python3}"
CONFIG_SCRIPT="${7:-update_jbrowse_config.py}"

for f in "$GENOME_GZ" "$GFF_GZ"; do
    if [ ! -s "$f" ]; then
        echo "[ERROR] required file missing: $f" >&2
        exit 3
    fi
done

mkdir -p "$OUTDIR"
"$JBROWSE" add-assembly "$GENOME_GZ" --load symlink \
    --name "$SPECIES" --out "$OUTDIR" --force
"$JBROWSE" add-track "$GFF_GZ" --load symlink \
    --name "$SPECIES" --out "$OUTDIR" --trackId GFF --force

"$PYTHON_BIN" "$CONFIG_SCRIPT" --config "$OUTDIR/config.json" --species "$SPECIES"

echo "[OK] JBrowse assembly/track added for $SPECIES"