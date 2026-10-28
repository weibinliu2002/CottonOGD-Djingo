#!/usr/bin/env bash
# Build the four BLAST databases expected by backend/CottonOGD/views/blast.py:
#   {db_root}/{species}/{genome,mrna,cds,protein}/{species}.*
# Upstream/downstream are not BLAST databases in the legacy pipeline.
set -euo pipefail

SPECIES="$1"
DB_ROOT="$2"
GENOME="$3"
MRNA="$4"
CDS="$5"
PROTEIN="$6"
MAKEBLASTDB="$7"
WORKDIR="$8"

mkdir -p "$WORKDIR/inputs"
mkdir -p "$DB_ROOT/$SPECIES"/{genome,mrna,cds,protein}

decompress() {
    local src="$1"
    local dst="$2"
    if [[ "$src" == *.gz ]]; then
        if [ ! -s "$dst" ] || [ "$src" -nt "$dst" ]; then
            gzip -dc "$src" > "$dst"
        fi
        echo "$dst"
    else
        echo "$src"
    fi
}

GENOME_FA=$(decompress "$GENOME" "$WORKDIR/inputs/${SPECIES}.genome.fa")

"$MAKEBLASTDB" -in "$GENOME_FA" -dbtype nucl -parse_seqids \
    -out "$DB_ROOT/$SPECIES/genome/$SPECIES" -title "${SPECIES}_genome"
"$MAKEBLASTDB" -in "$MRNA" -dbtype nucl -parse_seqids \
    -out "$DB_ROOT/$SPECIES/mrna/$SPECIES" -title "${SPECIES}_mRNA"
"$MAKEBLASTDB" -in "$CDS" -dbtype nucl -parse_seqids \
    -out "$DB_ROOT/$SPECIES/cds/$SPECIES" -title "${SPECIES}_CDS"
"$MAKEBLASTDB" -in "$PROTEIN" -dbtype prot -parse_seqids \
    -out "$DB_ROOT/$SPECIES/protein/$SPECIES" -title "${SPECIES}_protein"

echo "[OK] BLAST databases built under $DB_ROOT/$SPECIES"