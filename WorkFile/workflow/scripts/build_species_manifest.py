#!/usr/bin/env python3
"""Build the multi-species manifest from the existing MySQL ``species`` table.

For every species already registered in CottonOGD this script creates a small
input directory::

    data/species/{species}/
        genome.fasta      -> symlink to the existing plain FASTA
        genes.gff3        -> symlink to the existing GFF/GTF
        metadata.yaml     -> generated metadata + existing QC values

It then writes ``samples.yaml`` and ``data/species_manifest.tsv``.

Design notes
------------
* Only symlinks and metadata are created; existing genome/GFF files are never
  copied, moved, or deleted.
* ``qc_completed`` is filled per metric from the legacy ``species`` columns
  (``Genome_size``, ``LAI_value``, ``Busco``) and from the old
  ``Script/CottonOGD/{busco,LAI}`` summary files.  The workflow uses it to skip
  those heavy QC rules, while longest-protein/transcript extraction always
  runs because it is not listed there.
* MySQL values win when both sources exist; differences are written to
  ``data/legacy_qc_report.tsv`` for review.  Values missing from MySQL are
  filled from the legacy summary and marked with their source.
* The script is idempotent: metadata is rewritten, and only symlinks previously
  created by this script are replaced.  A regular file at the link path is an
  error rather than silently overwritten.
"""
import argparse
import csv
import gzip
import os
import re
import sys
import tempfile

import pymysql
import yaml

REQUIRED_META = (
    "species_name", "common_name", "ploidy", "assembly_version",
    "annotation_version", "literature", "submitter", "description",
)
SPECIES_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
GENOME_SUFFIXES = (".fa", ".fasta", ".fna")
EXCLUDE_GENOME_TOKENS = (
    "cds", "cdna", "pep", "pro", "protein", "mrna", "transcript",
    "gene_genome", "tbtools", "repeat",
)
# A ``{species}.fa`` symlink sometimes points at a gene/CDS/peptide FASTA in
# the legacy layout (for example ``AD2-NBI_v1.0.gene.fa``).  Reject those by
# inspecting the resolved basename, not just the symlink name.
EXCLUDE_GENOME_RE = re.compile(
    r"(^|[._-])(gene|genes|cds|cdna|pep|pro|protein|transcript|mrna|tbtools|repeat)([._-]|$)",
    re.IGNORECASE,
)
# Legacy summary files produced by the old Script/CottonOGD pipeline.  These
# values were computed but may never have been uploaded to MySQL.
LEGACY_FILES = {
    "busco": ("busco/Busco_summary.txt", "nam"),
    "lai": ("LAI/result/LAI_summary.txt", "sam"),
    "genome_size": ("LAI/Genome_size/Genome_size.txt", "name"),
}


def read_env(path):
    """Read simple KEY=VALUE pairs from backend/.env without exporting them."""
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def connect(env):
    """Connect using the same variables as the Django backend."""
    return pymysql.connect(
        host=env.get("MYSQL_DB_HOST", "localhost"),
        port=int(env.get("MYSQL_DB_PORT", "3306")),
        user=env.get("MYSQL_DB_USER"),
        password=env.get("MYSQL_DB_PASSWORD"),
        database=env.get("MYSQL_DB_NAME", "cottonogd-ortho"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _valid_file(path):
    try:
        return os.path.exists(path) and os.path.getsize(path) > 0
    except OSError:
        return False


def _is_plain_fasta(path):
    """True for a non-gzipped file that looks like genomic sequence."""
    if not _valid_file(path) or os.path.realpath(path).endswith(".gz"):
        return False
    real_name = os.path.basename(os.path.realpath(path))
    return not EXCLUDE_GENOME_RE.search(real_name)


def pick_genome(species_dir, species):
    """Return a plain (uncompressed) genome FASTA.

    gffread 0.12.8 in this environment does not reliably read gzipped FASTA,
    so a plain file is required.  The legacy layout exposes one through a
    ``{species}.fa`` symlink for most species; a few use a versioned name or an
    original file with a different basename.  Gene/CDS/peptide FASTA files are
    rejected even when a legacy ``.fa`` symlink points at one.
    """
    candidates = [
        f"{species}.genome.fa",
        f"{species}.fa",
        f"{species}.1.fa",
        f"{species}.genome.fasta",
        f"{species}.fasta",
    ]
    for name in candidates:
        path = os.path.join(species_dir, name)
        if _is_plain_fasta(path):
            return path

    # Fallback: largest plain FASTA that is not an extracted sequence type.
    found = []
    for name in os.listdir(species_dir):
        lower = name.lower()
        if not lower.endswith(GENOME_SUFFIXES):
            continue
        if any(token in lower for token in EXCLUDE_GENOME_TOKENS):
            continue
        path = os.path.join(species_dir, name)
        if _is_plain_fasta(path):
            found.append((os.path.getsize(path), path))
    return max(found)[1] if found else None


def _gff_has_features(path, max_lines=20000):
    """Return True when a plain/gzip GFF contains at least one real feature.

    Several legacy ``{species}.gff`` files are 16-byte placeholders that only
    contain ``##gff-version 3``; the usable annotation is in the companion
    ``.gff.gz``.  Checking the content (not just the file size) prevents the
    manifest from selecting such a placeholder and failing validation later.
    """
    try:
        with open(path, "rb") as fh:
            magic = fh.read(2)
        opener = gzip.open if magic == b"\x1f\x8b" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
            seen = 0
            for line in fh:
                if not line.strip() or line.startswith("#"):
                    continue
                seen += 1
                fields = line.rstrip("\r\n").split("\t")
                if len(fields) >= 9 and fields[2] not in ("", "."):
                    return True
                if seen >= max_lines:
                    break
    except (OSError, EOFError):
        return False
    return False


def pick_gff(species_dir, species):
    """Return the first non-empty GFF/GTF used as annotation input.

    Plain files are preferred for tool compatibility, but a plain placeholder
    is skipped in favour of a gzipped file with actual features.
    """
    for name in (f"{species}.gff", f"{species}.gff3", f"{species}.gtf",
                 f"{species}.gff.gz", f"{species}.gtf.gz"):
        path = os.path.join(species_dir, name)
        if _valid_file(path) and _gff_has_features(path):
            return path
    return None


def derive_assembly_version(species):
    """Best-effort version label from names such as ..._HAU_v1.1."""
    parts = species.split("_")
    if len(parts) >= 2:
        return "_".join(parts[-2:])
    return "unknown"


def read_tsv(path):
    """Read a tab-separated summary, returning an empty list if absent."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def normalise_legacy_name(raw):
    """Map old BUSCO/LAI labels onto the current ``species.name`` values.

    The BUSCO summary used the GFF filename (``N200.gff3``) and sometimes a
    ``N200_gene`` alias for the 107 resequenced G. hirsutum accessions.  The
    old LAI/genome-size summaries already use the full species name.
    """
    name = (raw or "").strip()
    match = re.fullmatch(r"(N\d+)(?:\.gff3|_gene)", name)
    if match:
        return f"G.hirsutumAD1_{match.group(1)}_CRI_v1"
    if name == "Ghirsutum_genome_HAU_v1.0":
        return "G.hirsutumAD1_TM-1_HAU_v1"
    return name


def legacy_busco_value(row):
    """Convert legacy BUSCO counts to the Complete/Total fraction used by DB."""
    try:
        complete = float(row.get("C") or 0)
        total = float(row.get("n") or 0)
        if total:
            return f"{complete / total:.4f}"
    except (TypeError, ValueError):
        pass
    try:
        return f"{float(row.get('pc_C')) / 100:.4f}"
    except (TypeError, ValueError):
        return None


def legacy_value(metric, row):
    """Extract a normalised QC value from one legacy summary row."""
    if metric == "busco":
        return legacy_busco_value(row)
    if metric == "lai":
        value = (row.get("LAI_value") or "").strip()
        return value or None
    if metric == "genome_size":
        try:
            return int(float(row.get("size")))
        except (TypeError, ValueError):
            return None
    return None


def load_legacy_qc(legacy_dir):
    """Load BUSCO/LAI/genome-size summaries keyed by current species name.

    ``.gff3`` BUSCO rows take precedence over the ``_gene`` alias when both
    exist.  Values are kept as strings/ints so metadata.yaml remains readable.
    """
    legacy = {metric: {} for metric in LEGACY_FILES}
    for metric, (rel_path, name_field) in LEGACY_FILES.items():
        path = os.path.join(legacy_dir, rel_path)
        for row in read_tsv(path):
            raw_name = (row.get(name_field) or "").strip()
            species = normalise_legacy_name(raw_name)
            value = legacy_value(metric, row)
            if not species or value is None:
                continue
            # Prefer an exact species name, then .gff3, then the _gene alias.
            priority = 3 if raw_name == species else (2 if raw_name.endswith(".gff3") else 1)
            previous = legacy[metric].get(species)
            if previous is None or priority >= previous["priority"]:
                legacy[metric][species] = {
                    "value": value,
                    "source": os.path.join("Script", "CottonOGD", rel_path),
                    "priority": priority,
                }
    return legacy


def same_value(left, right):
    """Compare numeric QC values without being fooled by string formatting."""
    try:
        return abs(float(left) - float(right)) < 1e-9
    except (TypeError, ValueError):
        return str(left).strip() == str(right).strip()


def valid_metric(metric, value):
    """Reject obviously corrupt legacy/MySQL values before reusing them."""
    if value in (None, ""):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    if metric == "busco":
        return 0.0 <= number <= 1.0
    if metric == "lai":
        return 0.0 <= number <= 100.0
    if metric == "genome_size":
        return number > 0
    return True


def merge_qc(row, legacy):
    """Merge MySQL values with legacy summaries, keeping MySQL on conflict.

    Returns (existing_qc, qc_completed, qc_sources, conflicts, actions).  A
    corrupt MySQL value (e.g. Busco=9.62 or LAI=89093) is replaced by a valid
    legacy value; otherwise MySQL is kept and the difference is reported.
    """
    species = row["name"]
    db_values, _ = qc_values(row)
    existing, completed, sources, conflicts, actions = {}, [], {}, [], {}
    for metric in ("genome_size", "lai", "busco"):
        db_value = db_values.get(metric)
        item = (legacy.get(metric) or {}).get(species)
        legacy_val = item["value"] if item else None
        db_ok = valid_metric(metric, db_value)
        legacy_ok = valid_metric(metric, legacy_val)

        if db_value is not None and not db_ok:
            if legacy_ok:
                existing[metric] = legacy_val
                completed.append(metric)
                sources[metric] = item["source"]
                actions[metric] = "invalid_mysql_replaced_by_legacy"
                conflicts.append({
                    "metric": metric,
                    "database": db_value,
                    "legacy": legacy_val,
                    "source": item["source"],
                    "action": "invalid_mysql_replaced_by_legacy",
                })
            else:
                actions[metric] = "invalid_mysql_ignored"
            continue

        if db_ok:
            existing[metric] = db_value
            completed.append(metric)
            sources[metric] = "mysql"
            if legacy_ok and not same_value(db_value, legacy_val):
                actions[metric] = "conflict_kept_mysql"
                conflicts.append({
                    "metric": metric,
                    "database": db_value,
                    "legacy": legacy_val,
                    "source": item["source"],
                    "action": "conflict_kept_mysql",
                })
            else:
                actions[metric] = "confirmed" if legacy_ok else "mysql_only"
        elif legacy_ok:
            existing[metric] = legacy_val
            completed.append(metric)
            sources[metric] = item["source"]
            actions[metric] = "filled_from_legacy"
        else:
            actions[metric] = "missing"
    return existing, completed, sources, conflicts, actions


def qc_values(row):
    """Extract MySQL QC values and the list of completed metrics."""
    existing = {}
    completed = []
    if row.get("Genome_size") is not None:
        existing["genome_size"] = int(row["Genome_size"])
        completed.append("genome_size")
    if row.get("LAI_value") not in (None, ""):
        existing["lai"] = str(row["LAI_value"])
        completed.append("lai")
    if row.get("Busco") not in (None, ""):
        existing["busco"] = str(row["Busco"])
        completed.append("busco")
    return existing, completed


def build_metadata(row, existing, completed, sources, conflicts):
    """Create a metadata.yaml payload accepted by validate_input.py."""
    species = row["name"]
    cotton_species = row.get("Cotton_Species") or species
    article = (row.get("Article") or "").strip()
    website = (row.get("Website") or "").strip()
    literature = []
    if article:
        item = {"title": article}
        if website:
            item["url"] = website
        literature.append(item)

    description = (row.get("description") or "").strip()
    if not description:
        genome_type = row.get("Genome_type") or "unknown genome type"
        description = f"{cotton_species} ({genome_type})"

    meta = {
        "species_name": species,
        "common_name": row.get("common_name") or cotton_species,
        "ploidy": row.get("Ploidy") or "unknown",
        "assembly_version": row.get("assembly_version") or derive_assembly_version(species),
        "assembly_version_source": (
            "database" if row.get("assembly_version")
            else "derived_from_species_name"
        ),
        "annotation_version": row.get("annotation_version") or "unknown",
        "literature": literature,
        "submitter": row.get("submitter") or "CottonOGD",
        "description": description,
        # Legacy database context, kept for traceability.
        "source_db_id": row.get("id"),
        "alias": row.get("alias"),
        "cotton_species": cotton_species,
        "genome_type": row.get("Genome_type"),
        "category": row.get("Category"),
        "accession": row.get("Accession"),
        "website": website,
        "article": article,
        "existing_qc": existing,
        "qc_completed": completed,
        "qc_sources": sources,
        "legacy_qc_conflicts": conflicts,
    }
    return {key: meta[key] for key in REQUIRED_META} | {
        key: value for key, value in meta.items() if key not in REQUIRED_META
    }


def ensure_symlink(link_path, target, dry_run=False):
    """Create/replace a relative symlink, refusing to overwrite regular files."""
    link_dir = os.path.dirname(link_path)
    rel_target = os.path.relpath(target, link_dir)
    if os.path.lexists(link_path):
        if not os.path.islink(link_path):
            raise RuntimeError(
                f"refusing to overwrite non-symlink path: {link_path}"
            )
        if os.readlink(link_path) == rel_target:
            return
        if dry_run:
            return
        os.unlink(link_path)
    if dry_run:
        return
    os.makedirs(link_dir, exist_ok=True)
    os.symlink(rel_target, link_path)


def write_atomic(path, text):
    """Write text atomically so an interrupted run does not leave half a file."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-dir", default="/data/web/CottonOGD/OGD/WorkFile")
    ap.add_argument("--backend-dir", default="/data/web/CottonOGD/OGD/backend")
    ap.add_argument("--legacy-dir", default="")
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--samples", default="")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--qc-report", default="")
    ap.add_argument("--env-file", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base_dir = os.path.abspath(args.base_dir)
    backend_dir = os.path.abspath(args.backend_dir)
    legacy_qc_dir = os.path.abspath(
        args.legacy_dir
        or os.path.join(os.path.dirname(backend_dir), "Script", "CottonOGD")
    )
    out_dir = os.path.abspath(args.out_dir or os.path.join(base_dir, "data", "species"))
    samples_path = os.path.abspath(args.samples or os.path.join(base_dir, "samples.yaml"))
    manifest_path = os.path.abspath(args.manifest or os.path.join(base_dir, "data", "species_manifest.tsv"))
    qc_report_path = os.path.abspath(
        args.qc_report or os.path.join(base_dir, "data", "legacy_qc_report.tsv")
    )
    env_file = os.path.abspath(args.env_file or os.path.join(backend_dir, ".env"))
    genome_root = os.path.join(backend_dir, "data", "genome")

    env = read_env(env_file)
    missing = [key for key in ("MYSQL_DB_USER", "MYSQL_DB_PASSWORD") if not env.get(key)]
    if missing:
        print(f"[ERROR] missing MySQL settings in {env_file}: {', '.join(missing)}", file=sys.stderr)
        return 2
    if not os.path.isdir(genome_root):
        print(f"[ERROR] genome root not found: {genome_root}", file=sys.stderr)
        return 2

    try:
        conn = connect(env)
    except Exception as exc:  # noqa: BLE001 - surface a useful CLI error
        print(f"[ERROR] cannot connect to MySQL: {exc}", file=sys.stderr)
        return 3

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id,name,alias,Cotton_Species,Genome_type,Category,Accession,"
                "Ploidy,Website,Article,LAI_value,Busco,Genome_size,description,"
                "common_name,assembly_version,annotation_version,submitter "
                "FROM species ORDER BY id"
            )
            rows = cursor.fetchall()
    finally:
        conn.close()

    # Read the old Script/CottonOGD summaries once.  These contain many values
    # that were computed but never uploaded.
    legacy_qc = load_legacy_qc(legacy_qc_dir)
    db_names = {str(row["name"]).strip() for row in rows}

    samples = []
    manifest_rows = []
    qc_report_rows = []
    errors = []
    for row in rows:
        species = str(row["name"]).strip()
        if not species or not SPECIES_RE.fullmatch(species):
            errors.append(f"skip invalid species id: {species!r}")
            continue
        species_data_dir = os.path.join(genome_root, species)
        if not os.path.isdir(species_data_dir):
            errors.append(f"{species}: legacy directory missing: {species_data_dir}")
            continue
        genome = pick_genome(species_data_dir, species)
        gff = pick_gff(species_data_dir, species)
        if not genome:
            errors.append(f"{species}: no plain genome FASTA found in {species_data_dir}")
            continue
        if not gff:
            errors.append(f"{species}: no GFF/GTF found in {species_data_dir}")
            continue

        existing, completed, sources, conflicts, actions = merge_qc(row, legacy_qc)
        db_values, _ = qc_values(row)

        species_out = os.path.join(out_dir, species)
        genome_link = os.path.join(species_out, "genome.fasta")
        gff_link = os.path.join(species_out, "genes.gff3")
        metadata_path = os.path.join(species_out, "metadata.yaml")
        try:
            ensure_symlink(genome_link, genome, args.dry_run)
            ensure_symlink(gff_link, gff, args.dry_run)
            if not args.dry_run:
                meta_text = yaml.safe_dump(
                    build_metadata(row, existing, completed, sources, conflicts),
                    allow_unicode=True, sort_keys=False,
                )
                write_atomic(metadata_path, meta_text)
        except Exception as exc:  # noqa: BLE001 - continue other species
            errors.append(f"{species}: {exc}")
            continue

        entry = {
            "id": species,
            "enabled": True,
            "genome": os.path.relpath(genome_link, base_dir),
            "gff": os.path.relpath(gff_link, base_dir),
            "metadata": os.path.relpath(metadata_path, base_dir),
            "qc_completed": completed,
        }
        samples.append(entry)
        manifest_rows.append({
            "db_id": row.get("id"),
            "species": species,
            "genome_size_db": db_values.get("genome_size", ""),
            "lai_db": db_values.get("lai", ""),
            "busco_db": db_values.get("busco", ""),
            "genome_size_used": existing.get("genome_size", ""),
            "lai_used": existing.get("lai", ""),
            "busco_used": existing.get("busco", ""),
            "qc_completed": ",".join(completed),
            "qc_sources": ";".join(f"{k}={v}" for k, v in sources.items()),
            "legacy_conflicts": len(conflicts),
            "genome_source": genome,
            "gff_source": gff,
            "metadata": metadata_path,
        })

        # One row per species/metric makes the provenance easy to audit.
        for metric in ("genome_size", "lai", "busco"):
            item = (legacy_qc.get(metric) or {}).get(species)
            legacy_val = item["value"] if item else ""
            db_val = db_values.get(metric, "")
            qc_report_rows.append({
                "species": species,
                "metric": metric,
                "database_value": db_val,
                "legacy_value": legacy_val,
                "used_value": existing.get(metric, ""),
                "source": sources.get(metric, ""),
                "action": actions.get(metric, "missing"),
            })

    # Report legacy names that never matched a current species.
    for metric, values in legacy_qc.items():
        for species, item in sorted(values.items()):
            if species in db_names:
                continue
            qc_report_rows.append({
                "species": species,
                "metric": metric,
                "database_value": "",
                "legacy_value": item["value"],
                "used_value": "",
                "source": item["source"],
                "action": "legacy_name_not_in_mysql",
            })

    header = """# Generated from MySQL species + legacy Script/CottonOGD QC summaries.
# Paths are relative to base_dir (config.yaml).
# qc_completed marks metrics already in MySQL or found in a legacy summary;
# those heavy QC rules are skipped, while longest protein/CDS/mRNA extraction
# always runs. See data/legacy_qc_report.tsv for provenance/conflicts.
# Run one or a few species with:
#   snakemake -n --config species_filter=species_A,species_B
"""
    samples_text = header + yaml.safe_dump(
        {"samples": samples}, allow_unicode=True, sort_keys=False
    )
    if not args.dry_run:
        write_atomic(samples_path, samples_text)
        columns = [
            "db_id", "species", "genome_size_db", "lai_db", "busco_db",
            "genome_size_used", "lai_used", "busco_used", "qc_completed",
            "qc_sources", "legacy_conflicts", "genome_source", "gff_source",
            "metadata",
        ]
        lines = ["\t".join(columns)]
        for item in manifest_rows:
            lines.append("\t".join(str(item.get(col, "")) for col in columns))
        write_atomic(manifest_path, "\n".join(lines) + "\n")

        qc_columns = [
            "species", "metric", "database_value", "legacy_value",
            "used_value", "source", "action",
        ]
        qc_lines = ["\t".join(qc_columns)]
        for item in qc_report_rows:
            qc_lines.append("\t".join(str(item.get(col, "")) for col in qc_columns))
        write_atomic(qc_report_path, "\n".join(qc_lines) + "\n")

    stats = {
        "species": len(samples),
        "genome_size_completed": sum("genome_size" in s["qc_completed"] for s in samples),
        "lai_completed": sum("lai" in s["qc_completed"] for s in samples),
        "busco_completed": sum("busco" in s["qc_completed"] for s in samples),
        "all_three_completed": sum(len(s["qc_completed"]) == 3 for s in samples),
        "longest_pending": len(samples),
        "legacy_filled": sum(r["action"] == "filled_from_legacy" for r in qc_report_rows),
        "legacy_conflicts": sum(r["action"] == "conflict_kept_mysql" for r in qc_report_rows),
    }
    print("[OK] " + ", ".join(f"{key}={value}" for key, value in stats.items()))
    print(f"[OK] samples: {samples_path}")
    print(f"[OK] manifest: {manifest_path}")
    print(f"[OK] legacy QC report: {qc_report_path}")
    for error in errors:
        print(f"[WARNING] {error}", file=sys.stderr)
    return 0 if samples else 2


if __name__ == "__main__":
    sys.exit(main())