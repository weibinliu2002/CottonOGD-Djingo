#!/usr/bin/env python3
"""Publish workflow results into the backend data trees.

Canonical files live under `backend/data/Genome/{type}/`; per-species entry
points under `backend/data/genome/{species}/` are relative symlinks. Existing
regular files are never deleted or overwritten unless `--overwrite` is given.

Download endpoint compatibility (`DownloadGenome.py`) requires these species
symlinks: `{s}.genome.fa.gz`, `{s}.gene_genome.fa.gz`, `{s}.cds.fa.gz`,
`{s}.pro.fa.gz`, `{s}.upstream.fa.gz`, `{s}.gff.gz`.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_symlinks import (  # noqa: E402
    ensure_bgzip,
    ensure_copy,
    ensure_fai,
    ensure_symlink,
    record,
)


def _add(manifest, role, status, message, canonical=None, link=None, base_dir=None):
    entry = {"role": role, "status": status, "message": message}
    if canonical:
        entry["canonical"] = record(canonical, base_dir, manifest["hash_max_bytes"])
    if link:
        entry["link"] = record(link, base_dir, manifest["hash_max_bytes"])
    manifest["files"].append(entry)
    if status not in ("created", "updated"):
        manifest["warnings"].append(f"{role}: {message}")


def publish_file(manifest, role, src, canonical, link, overwrite):
    status, message = ensure_copy(src, canonical, overwrite=overwrite)
    _add(manifest, role, status, message, canonical, None, manifest["type_dir"])
    # Ensure the species-level link even when the canonical file already
    # existed from an earlier run (incremental repair of missing symlinks).
    if os.path.exists(canonical):
        lst, msg = ensure_symlink(canonical, link, overwrite=overwrite)
        _add(manifest, role + "_link", lst, msg, None, link, manifest["species_dir"])


def publish_gz(manifest, role, src, canonical, link, overwrite, bgzip, samtools):
    status, message = ensure_bgzip(src, canonical, bgzip=bgzip, overwrite=overwrite)
    _add(manifest, role, status, message, canonical, None, manifest["type_dir"])
    if os.path.exists(canonical):
        fstatus, fmsg = ensure_fai(canonical, samtools=samtools, bgzip_index=True)
        _add(manifest, role + "_fai", fstatus, fmsg, canonical + ".fai", None, manifest["type_dir"])
        for suffix in ("", ".fai", ".gzi"):
            target = canonical + suffix
            if os.path.exists(target):
                lst, msg = ensure_symlink(target, link + suffix, overwrite=overwrite)
                _add(manifest, role + "_link" + suffix, lst, msg, None, link + suffix,
                     manifest["species_dir"])


def main():
    ap = argparse.ArgumentParser(description="Publish results into backend data trees")
    ap.add_argument("--species", required=True)
    ap.add_argument("--genome", required=True)
    ap.add_argument("--gff", required=True, help="fixed GFF3 (plain)")
    ap.add_argument("--gff-gz", required=True)
    ap.add_argument("--gff-tbi", required=True)
    ap.add_argument("--sequences-dir", required=True)
    ap.add_argument("--longest-dir", required=True)
    ap.add_argument("--metadata", default="")
    ap.add_argument("--type-dir", required=True)
    ap.add_argument("--species-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--bgzip", default="bgzip")
    ap.add_argument("--tabix", default="tabix")
    ap.add_argument("--samtools", default="samtools")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--hash-max-bytes", type=int, default=2 * 1024 ** 3)
    args = ap.parse_args()

    species = args.species
    type_dir = os.path.abspath(args.type_dir)
    species_dir = os.path.abspath(args.species_dir)
    manifest = {
        "species": species,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "type_dir": type_dir,
        "species_dir": species_dir,
        "overwrite": args.overwrite,
        "hash_max_bytes": args.hash_max_bytes,
        "files": [],
        "warnings": [],
    }

    if args.dry_run:
        print(f"[DRY-RUN] would publish {species} to {type_dir} and {species_dir}")
        return 0

    # --- genome -----------------------------------------------------------
    genome = os.path.abspath(args.genome)
    gz = os.path.join(type_dir, "genome", f"{species}.genome.fa.gz")
    if genome.endswith(".gz"):
        # Accept ordinary gzip as well as bgzip; ensure_bgzip decompresses and
        # recompresses when needed so `.fai`/`.gzi` indexing is reliable.
        status, message = ensure_bgzip(genome, gz, bgzip=args.bgzip,
                                       overwrite=args.overwrite)
        _add(manifest, "genome_gz", status, message, gz, None, type_dir)
    else:
        plain = os.path.join(type_dir, "genome", f"{species}.fa")
        publish_file(manifest, "genome", genome, plain,
                     os.path.join(species_dir, f"{species}.fa"), args.overwrite)
        status, message = ensure_bgzip(genome, gz, bgzip=args.bgzip, overwrite=args.overwrite)
        _add(manifest, "genome_gz", status, message, gz, None, type_dir)
    if os.path.exists(gz):
        fstatus, fmsg = ensure_fai(gz, samtools=args.samtools, bgzip_index=True)
        _add(manifest, "genome_fai", fstatus, fmsg, gz + ".fai", None, type_dir)
        for suffix in (".fai", ".gzi"):
            target = gz + suffix
            if os.path.exists(target):
                lst, msg = ensure_symlink(target, os.path.join(species_dir, f"{species}.genome.fa.gz{suffix}"),
                                          overwrite=args.overwrite)
                _add(manifest, "genome_link" + suffix, lst, msg, None,
                     os.path.join(species_dir, f"{species}.genome.fa.gz{suffix}"), species_dir)
        lst, msg = ensure_symlink(gz, os.path.join(species_dir, f"{species}.genome.fa.gz"),
                                  overwrite=args.overwrite)
        _add(manifest, "genome_link", lst, msg, None,
             os.path.join(species_dir, f"{species}.genome.fa.gz"), species_dir)

    # --- GFF --------------------------------------------------------------
    gff = os.path.join(type_dir, "gff", f"{species}.gff")
    publish_file(manifest, "gff", args.gff, gff,
                 os.path.join(species_dir, f"{species}.gff"), args.overwrite)
    gff_gz = os.path.join(type_dir, "gff", f"{species}.gff.gz")
    status, message = ensure_copy(args.gff_gz, gff_gz, overwrite=args.overwrite)
    _add(manifest, "gff_gz", status, message, gff_gz, None, type_dir)
    if os.path.exists(gff_gz):
        tbi = gff_gz + ".tbi"
        if os.path.exists(args.gff_tbi):
            status, message = ensure_copy(args.gff_tbi, tbi, overwrite=args.overwrite)
        else:
            subprocess.run([args.tabix, "-p", "gff", gff_gz], check=True)
            status, message = "created", f"tabix index built: {tbi}"
        _add(manifest, "gff_tbi", status, message, tbi, None, type_dir)
        for suffix in ("", ".tbi"):
            target = gff_gz + suffix
            link = os.path.join(species_dir, f"{species}.gff.gz{suffix}")
            if os.path.exists(target):
                lst, msg = ensure_symlink(target, link, overwrite=args.overwrite)
                _add(manifest, "gff_link" + suffix, lst, msg, None, link, species_dir)

    # --- sequence types ---------------------------------------------------
    seq_types = [
        ("cds", "cds.fa", "cds", "cds.fa"),
        ("protein", "pro.fa", "pep", "pro.fa"),
        ("cdna", "cdna.fa", "cdna", "cdna.fa"),
        ("mrna", "mrna.fa", "mrna", "mrna.fa"),
        ("gene", "gene_genome.fa", "gene", "gene_genome.fa"),
        ("upstream", "upstream20000.fa", "upstream", "upstream20000.fa"),
        ("downstream", "downstream20000.fa", "downstream", "downstream20000.fa"),
    ]
    for role, src_name, subdir, canon_name in seq_types:
        src = os.path.join(args.sequences_dir, src_name)
        if not os.path.exists(src):
            manifest["warnings"].append(f"{role}: source missing: {src}")
            continue
        canonical = os.path.join(type_dir, subdir, f"{species}.{canon_name}")
        link = os.path.join(species_dir, f"{species}.{canon_name}")
        publish_file(manifest, role, src, canonical, link, args.overwrite)
        if role in ("cds", "protein", "cdna", "mrna", "gene", "upstream", "downstream"):
            gz_name = {
                "cds": f"{species}.cds.fa.gz",
                "protein": f"{species}.pro.fa.gz",
                "cdna": f"{species}.cdna.fa.gz",
                "mrna": f"{species}.mrna.fa.gz",
                "gene": f"{species}.gene_genome.fa.gz",
                "upstream": f"{species}.upstream.fa.gz",
                "downstream": f"{species}.downstream.fa.gz",
            }[role]
            publish_gz(manifest, role + "_gz", src, os.path.join(type_dir, subdir, gz_name),
                       os.path.join(species_dir, gz_name), args.overwrite,
                       args.bgzip, args.samtools)

    # --- longest sequences ------------------------------------------------
    for role, name, subdir in (
        ("pro_longest", "pro_longest.fasta", "pep"),
        ("cds_longest", "cds_longest.fasta", "cds"),
        ("mrna_longest", "mrna_longest.fasta", "mrna"),
    ):
        src = os.path.join(args.longest_dir, name)
        if not os.path.exists(src):
            manifest["warnings"].append(f"{role}: source missing: {src}")
            continue
        canonical = os.path.join(type_dir, subdir, f"{species}.{name}")
        link = os.path.join(species_dir, f"{species}.{name}")
        publish_file(manifest, role, src, canonical, link, args.overwrite)

    # --- metadata ---------------------------------------------------------
    if args.metadata and os.path.exists(args.metadata):
        meta_out = os.path.join(os.path.dirname(os.path.abspath(args.manifest)), "metadata.yaml")
        ensure_copy(args.metadata, meta_out, overwrite=True, hardlink=False)

    os.makedirs(os.path.dirname(os.path.abspath(args.manifest)), exist_ok=True)
    with open(args.manifest, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print(f"[OK] published {species}: {len(manifest['files'])} entries, "
          f"{len(manifest['warnings'])} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())