"""Shared helpers for the CottonOGD Snakemake workflow.

This file is included by the root Snakefile before any rule file. It only
contains read-only path/sample helpers; all real work lives in workflow/scripts.
"""
import os
import re
import yaml

BASE_DIR = os.path.abspath(config.get("base_dir", os.getcwd()))
RESULTS_DIR = os.path.join(BASE_DIR, config.get("results_dir", "results"))
TOOLS = config.get("tools", {})
PATHS = config.get("paths", {})
PYTHON = TOOLS.get("python", "python3")
try:
    CONFIG_FILE = os.path.abspath(workflow.configfiles[0])
except (AttributeError, IndexError, TypeError):
    CONFIG_FILE = os.path.join(BASE_DIR, "config.yaml")
SAMPLES_FILE = os.path.join(BASE_DIR, config.get("samples_file", "samples.yaml"))


def _abspath(path):
    """Resolve a user path relative to base_dir, without requiring existence."""
    if not path:
        return path
    path = os.path.expanduser(str(path))
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


def _read_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _infer_species_id(genome, metadata, explicit=None):
    if explicit:
        return str(explicit)
    if metadata and os.path.exists(metadata):
        data = _read_yaml(metadata)
        if data.get("species_name"):
            return str(data["species_name"])
    name = os.path.basename(str(genome))
    for suffix in (".fasta.gz", ".fa.gz", ".fna.gz", ".fasta", ".fa", ".fna"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return name


def _normalise_sample(raw):
    sid = str(raw.get("id", "")).strip()
    if not sid:
        raise ValueError("samples.yaml entry is missing a non-empty 'id'")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", sid):
        raise ValueError(f"invalid species id {sid!r}: only [A-Za-z0-9_.-] is allowed")
    if len(sid) > 255:
        raise ValueError(f"species id {sid!r} exceeds the 255-character database limit")
    out = dict(raw)
    out["id"] = sid
    out["enabled"] = bool(raw.get("enabled", True))
    # QC metrics that already exist in MySQL can be listed here so the
    # corresponding heavy rule is not added to the DAG. Values themselves live
    # in metadata.yaml -> existing_qc and are copied into qc_report.yaml.
    out["qc_completed"] = [str(x) for x in (raw.get("qc_completed") or [])]
    for key in ("genome", "gff", "protein", "transcripts", "cds", "metadata"):
        if raw.get(key):
            out[key] = _abspath(raw[key])
    return out


def _load_samples():
    """Return the batch manifest, or a one-element list for --config genome=..."""
    if config.get("genome"):
        genome = _abspath(config["genome"])
        gff = _abspath(config.get("gff"))
        metadata = _abspath(config.get("metadata"))
        sid = _infer_species_id(genome, metadata, config.get("species") or config.get("species_id"))
        raw = {
            "id": sid,
            "enabled": True,
            "genome": genome,
            "gff": gff,
            "metadata": metadata,
        }
        for key in ("protein", "transcripts", "cds"):
            if config.get(key):
                raw[key] = _abspath(config[key])
        return [_normalise_sample(raw)]

    samples_file = _abspath(config.get("samples_file", "samples.yaml"))
    if not os.path.exists(samples_file):
        raise FileNotFoundError(f"samples file not found: {samples_file}")
    data = _read_yaml(samples_file)
    entries = data.get("samples", []) if isinstance(data, dict) else data
    samples = [_normalise_sample(item) for item in (entries or [])]
    samples = [s for s in samples if s.get("enabled", True)]

    # Optional CLI filter: --config species_filter=species_A,species_B
    requested = config.get("species_filter") or config.get("species")
    if requested and not config.get("genome"):
        allowed = [x.strip() for x in str(requested).split(",") if x.strip()]
        selected = [s for s in samples if s["id"] in allowed]
        missing = sorted(set(allowed) - {s["id"] for s in selected})
        if missing:
            raise ValueError(
                "species_filter ids not present/enabled in samples.yaml: "
                + ", ".join(missing)
            )
        samples = selected

    seen = set()
    for sample in samples:
        if sample["id"] in seen:
            raise ValueError(f"duplicate species id in samples.yaml: {sample['id']}")
        seen.add(sample["id"])
        for key in ("genome", "gff", "metadata"):
            if not sample.get(key):
                raise ValueError(f"{sample['id']}: required field {key!r} is missing")
            if not os.path.exists(sample[key]):
                raise FileNotFoundError(f"{sample['id']}: {key} not found: {sample[key]}")
    return samples


SAMPLES = _load_samples()
SAMPLE_MAP = {s["id"]: s for s in SAMPLES}


def get_sample(wildcards):
    sid = wildcards.species
    if sid not in SAMPLE_MAP:
        raise KeyError(f"unknown species wildcard: {sid}")
    return SAMPLE_MAP[sid]


def spath(wildcards, key, default=None):
    return get_sample(wildcards).get(key, default)


def qc_completed(wildcards):
    """QC metrics already present in MySQL for this sample (skip re-running)."""
    return set(get_sample(wildcards).get("qc_completed") or [])


def sdir(wildcards, *parts):
    return os.path.join(RESULTS_DIR, wildcards.species, *parts)


def module_enabled(name):
    return bool(config.get("modules", {}).get(name, {}).get("enabled", False))


def module_opt(name, key, default=None):
    return config.get("modules", {}).get(name, {}).get(key, default)


def resource(name, key):
    return config.get("resources", {}).get(name, {}).get(key)


# All species ids must be usable as path components and Snakemake wildcards.
wildcard_constraints:
    species=r"[A-Za-z0-9_.-]+"