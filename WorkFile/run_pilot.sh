#!/bin/bash
# Pilot run: one species through upload, to verify legacy annotation IDs match
# the sequence IDs produced by this workflow.
cd /data/web/CottonOGD/OGD/WorkFile || exit 1

SNAKE=/data/wbliu/soft/home/.conda/envs/snakemake/bin/snakemake
SPECIES=G.arboreumA2_DC086_HAU_v1

"$SNAKE" --use-conda --cores 8 \
  --configfile config.yaml \
  --rerun-incomplete \
  --config species_filter="$SPECIES" \
  --until upload_to_db
echo "SNAKEMAKE_EXIT=$?"
