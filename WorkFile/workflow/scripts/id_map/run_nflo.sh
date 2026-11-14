#!/usr/bin/env bash
# Run nf-LO to generate a Chain file for one source->target pair.
#
# Usage:
#   run_nflo.sh <nflo_dir> <source.fa> <target.fa> <work_dir> <out_chain> <out_net> <out_log>
#
# nf-LO sampled outputs are copied into `work_dir`. On success this script
# copies `chainnet/liftover.chain` to `out_chain` and `chainnet/netfile.net`
# to `out_net`. An empty/missing chain causes failure.
#
# Environment variables:
#   NEXTFLOW_BIN    - path to nextflow launcher (default: nextflow)
#   NFLO_ALIGNER    - aligner to use (default: lastz)
#   NFLO_DISTANCE   - alignment distance preset (default: medium)
#   NFLO_MAX_CPUS   - max CPUs per nf-LO task (default: 16)
#   NFLO_MAX_MEM    - max memory per nf-LO task (default: 64.GB)
#   NFLO_MAX_FORKS  - max concurrent nextflow tasks (default: 16). Caps the
#                     number of simultaneous LASTZ jobs so the run cannot
#                     exhaust RAM (an earlier run hit 72 concurrent / 501 GB).
#   NFLO_CHAIN_NAME - chain file name (default: liftover)
#   NFLO_CWD        - CWD for nextflow (must contain work/conda/ with cached envs)
set -euo pipefail

NFLO_DIR="$1"
SOURCE="$2"
TARGET="$3"
WORK_DIR="$4"
OUT_CHAIN="$5"
OUT_NET="$6"
OUT_LOG="$7"

# Parameters (kept as in validated nf-LO test config; do not change aligner/core params)
DISTANCE="${NFLO_DISTANCE:-medium}"
ALIGNER="${NFLO_ALIGNER:-lastz}"
MAX_CPUS="${NFLO_MAX_CPUS:-16}"
MAX_MEM="${NFLO_MAX_MEM:-64.GB}"
MAX_FORKS="${NFLO_MAX_FORKS:-16}"
CHAIN_NAME="${NFLO_CHAIN_NAME:-liftover}"

MKDIR=$(command -v mkdir)
CP=$(command -v cp)
NEXTFLOW="${NEXTFLOW_BIN:-nextflow}"

# nf-LO always writes into its own OUTPUTS dir; we give it an outdir under work_dir
RUN_OUTDIR="$WORK_DIR/nflo_out"

# CWD for nextflow: must contain work/conda/ with cached conda envs.
# When called from Snakemake, NFLO_CWD is set to the WorkFile root.
NFLO_CWD="${NFLO_CWD:-$(pwd)}"

mkdir -p "$WORK_DIR"
# Do NOT wipe RUN_OUTDIR: a resumed run needs the already-published singlechains
# and the nextflow work cache. A clean rerun can set NFLO_FRESH=1.
if [ "${NFLO_FRESH:-0}" = "1" ]; then
    rm -rf "$RUN_OUTDIR"
fi

{
    echo "=== nf-LO run ==="
    echo "cmd: nextflow run $NFLO_DIR/main.nf -profile conda \\"
    echo "      --source $SOURCE --target $TARGET \\"
    echo "      --aligner $ALIGNER --distance $DISTANCE \\"
    echo "      --chain_name $CHAIN_NAME --outdir $RUN_OUTDIR \\"
    echo "      --max_cpus $MAX_CPUS --max_memory $MAX_MEM"
    echo "source : $(realpath "$SOURCE")"
    echo "target : $(realpath "$TARGET")"
    echo "start  : $(date -Is)"
} >> "$OUT_LOG"

# -resume lets an interrupted run continue from the nextflow task cache
# (work/ + .nextflow/cache) instead of redoing finished LASTZ chunks.
NXF_OFFLINE=true \
cd "$NFLO_CWD" && \
"$NEXTFLOW" run "$NFLO_DIR/main.nf" \
    -resume \
    -profile conda \
    --source "$SOURCE" \
    --target "$TARGET" \
    --aligner "$ALIGNER" \
    --distance "$DISTANCE" \
    --chain_name "$CHAIN_NAME" \
    --outdir "$RUN_OUTDIR" \
    --max_cpus "$MAX_CPUS" \
    --max_memory "$MAX_MEM" \
    -process.maxForks "$MAX_FORKS" \
    >> "$OUT_LOG" 2>&1

echo "end    : $(date -Is)" >> "$OUT_LOG"

# Locate chain/net outputs
CHAIN_SRC="$RUN_OUTDIR/chainnet/${CHAIN_NAME}.chain"
CHAIN_NET="$RUN_OUTDIR/chainnet/netfile.net"

if [ ! -s "$CHAIN_SRC" ]; then
    echo "ERROR: expected chain file not found: $CHAIN_SRC" >> "$OUT_LOG"
    exit 1
fi
if [ ! -s "$CHAIN_NET" ]; then
    echo "ERROR: expected net file not found: $CHAIN_NET" >> "$OUT_LOG"
    exit 1
fi

"$CP" "$CHAIN_SRC" "$OUT_CHAIN"
"$CP" "$CHAIN_NET" "$OUT_NET"

# Symlink whole run outdir for traceability
if [ ! -d "$WORK_DIR/nflo_outputs" ]; then
    ln -s "$RUN_OUTDIR" "$WORK_DIR/nflo_outputs"
fi

echo "Chain OK: $(wc -l < "$OUT_CHAIN") blocks -> $OUT_CHAIN"