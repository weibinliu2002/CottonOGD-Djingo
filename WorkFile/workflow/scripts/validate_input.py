#!/usr/bin/env python3
"""Validate genome FASTA, GFF/GTF and metadata before any heavy step.

Exit codes:
  0  valid (warnings allowed)
  2  validation error
"""
import argparse
import gzip
import json
import os
import re
import sys
from collections import defaultdict

import yaml

from seqid_alias import SeqidResolver

DNA_RE = re.compile(r"^[ACGTNacgtn]+$")
# IUPAC DNA ambiguity codes are common in public assemblies (R/Y/S/W/K/M/B/D/H/V).
ALLOWED_BASES = set("ACGTRYSWKMBDHVNacgtryswkmbdhvnUuXx")
REQUIRED_META = [
    "species_name", "common_name", "ploidy", "assembly_version",
    "annotation_version", "literature", "submitter", "description",
]
AUTO_FIELDS = ("genome_size", "LAI", "lai", "BUSCO", "busco")


def open_text(path):
    """Open plain or gzip FASTA/GFF, following symlinks."""
    real = os.path.realpath(path)
    with open(real, "rb") as fh:
        magic = fh.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(real, "rt", encoding="utf-8", errors="replace")
    return open(real, "rt", encoding="utf-8", errors="replace")


def validate_fasta(path, errors, warnings):
    seq_ids = set()
    lengths = {}
    headers = {}
    total = 0
    count = 0
    current = None
    current_len = 0
    with open_text(path) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\r\n")
            if line.startswith(">"):
                if current is not None:
                    if current_len == 0:
                        errors.append(f"FASTA {current!r}: empty sequence")
                    lengths[current] = current_len
                    total += current_len
                header = line[1:].strip()
                if not header:
                    errors.append(f"FASTA line {lineno}: empty header")
                    current = None
                    continue
                seq_id = header.split()[0]
                if seq_id in seq_ids:
                    errors.append(f"FASTA line {lineno}: duplicate sequence id {seq_id!r}")
                seq_ids.add(seq_id)
                headers[seq_id] = header
                current = seq_id
                current_len = 0
                count += 1
            elif line:
                if current is None:
                    errors.append(f"FASTA line {lineno}: sequence before first header")
                    continue
                bad = set(line) - ALLOWED_BASES
                if bad:
                    errors.append(
                        f"FASTA {current!r} line {lineno}: invalid base(s) "
                        f"{''.join(sorted(bad))!r}"
                    )
                current_len += len(line)
        if current is not None:
            if current_len == 0:
                errors.append(f"FASTA {current!r}: empty sequence")
            lengths[current] = current_len
            total += current_len
    if count == 0:
        errors.append("FASTA contains no sequences")
    return {
        "sequence_count": count,
        "total_length": total,
        "ids": seq_ids,
        "lengths": lengths,
        "headers": headers,
    }


def parse_attrs(text):
    attrs = {}
    for item in text.strip().strip(";").split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            attrs[key.strip()] = value.strip()
        else:
            m = re.match(r"^(\S+)\s+\"?(.+?)\"?$", item)
            if m:
                attrs[m.group(1).strip()] = m.group(2).strip().strip('"')
    return attrs


def validate_gff(path, fasta, errors, warnings):
    genome_ids = fasta.get("ids") or set()
    resolver = SeqidResolver(genome_ids, fasta.get("headers"))
    gene_ids = set()
    inferred_gene_ids = set()
    transcript_ids = set()
    parent_of = {}
    features = defaultdict(int)
    mapped_features = defaultdict(int)
    unmapped_features = defaultdict(int)
    for lineno, line in enumerate(open_text(path), 1):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.rstrip("\r\n").split("\t")
        if len(fields) != 9:
            errors.append(f"GFF line {lineno}: expected 9 columns, got {len(fields)}")
            continue
        seqid, _source, ftype, start, end, _score, _strand, _phase, attrs_text = fields
        features[ftype] += 1
        resolved = resolver.resolve(seqid)
        if resolved is None:
            unmapped_features[seqid] += 1
            continue
        mapped_features[ftype] += 1
        try:
            start_i, end_i = int(start), int(end)
            if start_i < 1 or end_i < start_i:
                errors.append(f"GFF line {lineno}: invalid coordinates {start}-{end}")
        except ValueError:
            errors.append(f"GFF line {lineno}: non-integer coordinates")
        attrs = parse_attrs(attrs_text)
        fid = attrs.get("ID")
        parent = attrs.get("Parent")
        if parent:
            parent_of[fid or f"line{lineno}"] = parent.split(",")[0].strip()
        if ftype in ("gene", "pseudogene"):
            gid = fid or attrs.get("gene_id") or attrs.get("locus_tag")
            if gid:
                gene_ids.add(gid)
        elif ftype.lower() in ("mrna", "transcript"):
            tid = fid or attrs.get("transcript_id")
            if tid:
                transcript_ids.add(tid)
            # GTF (and transcript-only GFF3) may not carry gene rows.
            # Record the gene id so QC can still report a gene count.
            gid = (attrs.get("geneID") or attrs.get("gene_id")
                   or (attrs.get("Parent") or "").split(",")[0].strip())
            if gid:
                inferred_gene_ids.add(gid)
    if not gene_ids and inferred_gene_ids:
        gene_ids = inferred_gene_ids
        warnings.append(
            f"GFF has no explicit gene rows; inferred {len(gene_ids)} genes from transcript attributes"
        )

    if resolver.aliases:
        sample = ", ".join(
            f"{src}->{dst}" for src, dst in sorted(resolver.aliases.items())[:10]
        )
        warnings.append(
            f"mapped {len(resolver.aliases)} GFF seqid(s) to genome aliases: {sample}"
        )
    if unmapped_features:
        total_unmapped = sum(unmapped_features.values())
        sample = ", ".join(sorted(unmapped_features)[:10])
        message = (
            f"GFF has {total_unmapped} feature(s) on {len(unmapped_features)} "
            f"seqid(s) absent from genome FASTA; they will be dropped: {sample}"
        )
        if mapped_features.get("gene", 0) or mapped_features.get("mRNA", 0) or \
                mapped_features.get("transcript", 0):
            warnings.append(message)
        else:
            errors.append(
                "GFF seqid(s) do not match any genome sequence: " + sample
            )
    if not gene_ids and mapped_features.get("mRNA", 0) == 0 and \
            mapped_features.get("transcript", 0) == 0:
        errors.append("GFF has no gene/mRNA/transcript features")
    if not transcript_ids:
        warnings.append("GFF has no mRNA/transcript features with an ID attribute")
    return {
        "gene_count": len(gene_ids),
        "transcript_count": len(transcript_ids),
        "feature_counts": dict(sorted(features.items())),
        "mapped_feature_counts": dict(sorted(mapped_features.items())),
        "unmapped_seqids": sorted(unmapped_features),
        "seqid_aliases": dict(sorted(resolver.aliases.items())),
    }


def validate_metadata(path, species, allow_alias, errors, warnings):
    if not path or not os.path.exists(path):
        errors.append(f"metadata.yaml not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        meta = yaml.safe_load(fh) or {}
    for key in REQUIRED_META:
        value = meta.get(key)
        if key == "literature":
            # Required key, but an empty list is valid (no publications yet).
            if "literature" not in meta or value is None:
                errors.append("metadata.yaml: required field 'literature' is missing")
            continue
        if value in (None, "", [], {}):
            errors.append(f"metadata.yaml: required field {key!r} is missing")
    lit = meta.get("literature")
    if lit is not None and not isinstance(lit, list):
        errors.append("metadata.yaml: literature must be a list")
    if isinstance(lit, list):
        for idx, item in enumerate(lit):
            if not isinstance(item, dict) or not item.get("title"):
                errors.append(f"metadata.yaml: literature[{idx}] must contain a title")
            if isinstance(item, dict) and not (item.get("doi") or item.get("url")):
                warnings.append(f"metadata.yaml: literature[{idx}] has no doi/url")

    meta_species = str(meta.get("species_name", "")).strip()
    if meta_species and meta_species != species and not allow_alias:
        errors.append(
            f"metadata species_name {meta_species!r} does not match sample id {species!r}"
        )
    for key in AUTO_FIELDS:
        if key in meta and meta[key] not in (None, ""):
            warnings.append(
                f"metadata.yaml contains {key}; it will be overwritten by the computed value"
            )
    return meta


def main():
    ap = argparse.ArgumentParser(description="Validate CottonOGD input files")
    ap.add_argument("--species", required=True)
    ap.add_argument("--genome", required=True)
    ap.add_argument("--gff", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-id-alias", action="store_true")
    args = ap.parse_args()

    errors, warnings = [], []
    if not os.path.exists(args.genome):
        errors.append(f"genome not found: {args.genome}")
        fasta = {"sequence_count": 0, "total_length": 0, "ids": set(),
                 "lengths": {}, "headers": {}}
    else:
        fasta = validate_fasta(args.genome, errors, warnings)

    if not os.path.exists(args.gff):
        errors.append(f"GFF not found: {args.gff}")
        gff = {}
    else:
        gff = validate_gff(args.gff, fasta, errors, warnings)

    meta = validate_metadata(
        args.metadata, args.species, args.allow_id_alias, errors, warnings
    )

    report = {
        "species": args.species,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "genome": {
            "path": args.genome,
            "sequence_count": fasta.get("sequence_count", 0),
            "total_length": fasta.get("total_length", 0),
        },
        "gff": {"path": args.gff, **gff},
        "metadata": {
            "path": args.metadata,
            "species_name": meta.get("species_name"),
            "annotation_version": meta.get("annotation_version"),
            "assembly_version": meta.get("assembly_version"),
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    for msg in warnings:
        print(f"[WARNING] {msg}", file=sys.stderr)
    for msg in errors:
        print(f"[ERROR] {msg}", file=sys.stderr)
    if errors:
        return 2
    print(
        f"[OK] {args.species}: {fasta.get('sequence_count', 0)} sequences, "
        f"{fasta.get('total_length', 0)} bp; "
        f"{gff.get('gene_count', 0)} genes, {gff.get('transcript_count', 0)} transcripts"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())