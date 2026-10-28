#!/usr/bin/env bash
# eggNOG-mapper run, parameterised from Script/CottonOGD/eggnog_annoation/emapper.sh.
# The mapper directory must be on PYTHONPATH because upstream emapper.py imports
# the sibling eggnogmapper package.
set -euo pipefail

PROTEINS="$1"
OUTDIR="$2"
PREFIX="$3"
THREADS="$4"
MAPPER="$5"
DATA_DIR="$6"
TEMP_DIR="$7"
PYTHON_BIN="${8:-python3}"

mkdir -p "$OUTDIR" "$TEMP_DIR"
MAPPER_DIR="$(cd "$(dirname "$MAPPER")" && pwd)"
export PYTHONPATH="${MAPPER_DIR}${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON_BIN" "$MAPPER" \
    --cpu "$THREADS" --mp_start_method forkserver \
    --data_dir "$DATA_DIR" --temp_dir "$TEMP_DIR" --override \
    --evalue 0.001 --score 60 --pident 40 --query_cover 20 --subject_cover 20 \
    --tax_scope auto --target_orthologs all --go_evidence non-electronic \
    --pfam_realign realign --report_orthologs --decorate_gff yes --excel \
    -m mmseqs --output_dir "$OUTDIR" -i "$PROTEINS" -o "$PREFIX" --itype proteins

for suffix in emapper.annotations emapper.hits emapper.seed_orthologs; do
    if [ ! -s "$OUTDIR/${PREFIX}.${suffix}" ]; then
        echo "[ERROR] eggNOG-mapper did not produce ${PREFIX}.${suffix}" >&2
        exit 3
    fi
done

echo "[OK] eggNOG-mapper finished"