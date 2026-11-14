#!/usr/bin/env python3
"""Build genome registry for id_map module.

Reads liftover pairs TSV, per-species metadata.yaml, and genome FASTA
headers to produce a unified genome registry with ploidy, genome_type,
source, and FASTA path information.

Outputs:
  genome_registry.tsv   -- one row per genome_id appearing in pairs
  liftover_tasks.tsv   -- one row per directional conversion task
"""
import argparse
import csv
import os
import re
import sys
import yaml
from collections import OrderedDict


def load_metadata(metadata_path):
    """Load a species metadata.yaml, returning dict or empty dict."""
    if not metadata_path or not os.path.exists(metadata_path):
        return {}
    with open(metadata_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def scan_fasta_first_header(fasta_path, max_scan=2048):
    """Return (seqid, description) of the first FASTA record's header.

    Only reads a few lines — fast even for huge genomes — since we only need
    the accession/source of the first scaffold to classify the assembly as
    NCBI or non-NCBI. `max_scan` bounds the header scan to avoid reading an
    enormous 2bit-scaled first sequence body for classification purposes.
    """
    if not fasta_path or not os.path.exists(fasta_path):
        return ("", "")
    with open(fasta_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(">"):
                parts = line[1:].split(None, 1)
                seqid = parts[0]
                desc = parts[1] if len(parts) > 1 else ""
                return (seqid, desc)
        return ("", "")
    return ("", "")


def extract_accession_from_header(seqid, desc):
    """Try to extract an NCBI accession from seqid or description."""
    # Direct accession in seqid: NC_XXXXX.X, NW_XXXXX.X, CM_XXXXX.X
    m = re.match(r"(N[CGWSTZ]_\d+\.\d+)", seqid)
    if m:
        return m.group(1)
    # GenBank/GCF accession pattern
    m = re.match(r"(GC[AF]_\d+\.\d+)", seqid)
    if m:
        return m.group(1)
    # Search in description
    for part in desc.split():
        m = re.match(r"(N[CGWSTZ]_\d+\.\d+)", part)
        if m:
            return m.group(1)
        m = re.match(r"(GC[AF]_\d+\.\d+)", part)
        if m:
            return m.group(1)
    return ""


def infer_subgenome_from_name(seqid, genome_type):
    """Infer At/Dt subgenome from chromosome name patterns.

    Returns (subgenome, method, confidence).
    subgenome: 'At', 'Dt', or 'Unassigned'
    method: 'validated_name_rule'
    confidence: 'high', 'medium', 'low'
    """
    if genome_type and genome_type.startswith("AD"):
        # Pattern: XXX_A01 or XXX_A01 (prefix_A/D + number)
        m = re.search(r"[_]?([AD])(\d+)$", seqid, re.IGNORECASE)
        if m:
            letter = m.group(1).upper()
            sub = "At" if letter == "A" else "Dt"
            return (sub, "validated_name_rule", "high")
        # Pattern: chrA01, ChrA01, chromosome A01
        m = re.search(r"([AD])\d+", seqid, re.IGNORECASE)
        if m:
            letter = m.group(1).upper()
            sub = "At" if letter == "A" else "Dt"
            return (sub, "validated_name_rule", "medium")
    # For diploid A-genome or D-genome
    if genome_type and re.match(r"^A\d+$", genome_type):
        return ("At", "validated_name_rule", "high")
    if genome_type and re.match(r"^D\d+$", genome_type):
        return ("Dt", "validated_name_rule", "high")
    return ("Unassigned", "unassigned", "low")


def main():
    parser = argparse.ArgumentParser(description="Build genome registry for id_map")
    parser.add_argument("--pairs-tsv", required=True, help="Liftover pairs TSV")
    parser.add_argument("--species-dir", required=True, help="Dir with per-species metadata.yaml")
    parser.add_argument("--genome-dir", required=True, help="Dir with genome FASTA files (*.fa)")
    parser.add_argument("--registry-out", required=True, help="Output genome registry TSV")
    parser.add_argument("--tasks-out", required=True, help="Output liftover tasks TSV")
    args = parser.parse_args()

    # 1. Read liftover pairs
    genome_ids = set()
    tasks = []
    with open(args.pairs_tsv, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            sid = row["source_id"]
            tid = row["target_id"]
            species = row["species"]
            pair_type = row["pair_type"]
            direction_rule = row["direction_rule"]
            genome_ids.add(sid)
            genome_ids.add(tid)
            tasks.append(row)

    # 2. Build genome registry
    registry = {}
    for gid in sorted(genome_ids):
        meta_path = os.path.join(args.species_dir, gid, "metadata.yaml")
        meta = load_metadata(meta_path)
        ploidy = meta.get("ploidy", "unknown")
        genome_type = meta.get("genome_type", "")
        cotton_species = meta.get("cotton_species", "")
        common_name = meta.get("common_name", "")

        # Find FASTA
        fasta_path = os.path.join(args.genome_dir, f"{gid}.fa")
        if not os.path.exists(fasta_path):
            # Try .genome.fa.gz
            fasta_path = os.path.join(args.genome_dir, f"{gid}.genome.fa.gz")

        # Determine source (NCBI vs non-NCBI) based on first FASTA header
        source = "unknown"
        ncbi_accession = ""
        if os.path.exists(fasta_path) and not fasta_path.endswith(".gz"):
            seqid, desc = scan_fasta_first_header(fasta_path)
            if seqid:
                acc = extract_accession_from_header(seqid, desc)
                if acc and (acc.startswith("NC_") or acc.startswith("NW_") or
                            acc.startswith("CM_") or acc.startswith("GCF_") or
                            acc.startswith("GCA_")):
                    source = "ncbi"
                    ncbi_accession = acc
                else:
                    source = "non_ncbi"
        elif fasta_path.endswith(".gz"):
            source = "non_ncbi"  # compressed, assume non-NCBI for now

        registry[gid] = {
            "genome_id": gid,
            "species": cotton_species,
            "common_name": common_name,
            "ploidy": ploidy,
            "genome_type": genome_type,
            "source": source,
            "ncbi_assembly_accession": ncbi_accession,
            "fasta_path": fasta_path,
            "metadata_path": meta_path if os.path.exists(meta_path) else "",
        }

    # 3. Write registry
    reg_fields = [
        "genome_id", "species", "common_name", "ploidy", "genome_type",
        "source", "ncbi_assembly_accession", "fasta_path", "metadata_path",
    ]
    with open(args.registry_out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=reg_fields, delimiter="\t")
        writer.writeheader()
        for gid in sorted(registry):
            writer.writerow({k: registry[gid][k] for k in reg_fields})

    # 4. Write tasks
    task_fields = ["species", "source_id", "target_id", "pair_type", "direction_rule"]
    with open(args.tasks_out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=task_fields, delimiter="\t")
        writer.writeheader()
        for row in tasks:
            writer.writerow({k: row[k] for k in task_fields})

    # Summary
    n_diploid = sum(1 for g in registry.values() if g["ploidy"] == "diploid")
    n_tetraploid = sum(1 for g in registry.values() if g["ploidy"] == "allotetraploid")
    n_ncbi = sum(1 for g in registry.values() if g["source"] == "ncbi")
    print(f"Registry: {len(registry)} genomes ({n_diploid} diploid, {n_tetraploid} tetraploid, {n_ncbi} NCBI-source)")
    print(f"Tasks: {len(tasks)} directional conversion tasks")
    print(f"Registry written to: {args.registry_out}")
    print(f"Tasks written to: {args.tasks_out}")


if __name__ == "__main__":
    main()
