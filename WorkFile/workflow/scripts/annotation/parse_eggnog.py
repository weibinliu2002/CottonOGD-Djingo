#!/usr/bin/env python3
"""Run the legacy eggNOG-mapper parser with a cached, offline-capable KEGG client.

The GO/KEGG extraction itself is delegated to the vendored
`vendor/parse_eggNOG.py` and `vendor/parse_go_obofile.py` scripts, so the
annotation semantics are identical to the legacy pipeline. This wrapper only:

* builds the GO name/namespace table from go-basic.obo once per run,
* adds timeouts, retries and an on-disk cache to KEGG REST calls,
* normalises `mapXXXXX` to the 5-digit pathway id used by the database,
* emits a combined `eggnog.tsv` for `db_upload.py`.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import os
import sys
import time

import pandas as pd
import requests

NF = "NA"
LEVEL_NAMESPACE = {"MF": "molecular_function", "BP": "biological_process", "CC": "cellular_component"}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_cached_get_html(cache_dir, offline, timeout=60, retries=3, retry_wait=2):
    os.makedirs(cache_dir, exist_ok=True)

    def _get(url):
        # The vendored parser uses http://; normalise to https so the cache key
        # is stable and redirects cannot double the download time.
        original_url = url
        if url.startswith("http://rest.kegg.jp"):
            url = "https://" + url[len("http://"):]
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        cache_file = os.path.join(cache_dir, key + ".txt")
        meta_file = os.path.join(cache_dir, key + ".url")
        old_cache = None
        if original_url != url:
            old_key = hashlib.sha256(original_url.encode("utf-8")).hexdigest()
            old_cache = os.path.join(cache_dir, old_key + ".txt")

        def read_cache(path):
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()

        # Batch runs parse several species in parallel. Lock per cache key so
        # only one process downloads an endpoint while the others wait, and
        # publish the result atomically to avoid reading a partial file.
        lock_file = cache_file + ".lock"
        with open(lock_file, "w", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if os.path.exists(cache_file):
                return read_cache(cache_file)
            # Accept caches seeded by older runs that used the http:// URL, so
            # an existing offline cache keeps working after https normalisation.
            if old_cache and os.path.exists(old_cache):
                return read_cache(old_cache)
            if offline:
                raise RuntimeError(
                    f"offline mode but no cached KEGG response for {url} ({cache_file})"
                )
            # `link/pathway/ko` is a large endpoint (~2.3 MB, several minutes on
            # a cold connection); all other endpoints respond quickly.
            request_timeout = 900 if "link/pathway/ko" in url else timeout
            last_error = None
            for attempt in range(1, retries + 1):
                try:
                    resp = requests.get(
                        url,
                        timeout=request_timeout,
                        headers={"User-Agent": "CottonOGD-workflow/1.0"},
                    )
                    resp.raise_for_status()
                    text = resp.text
                    tmp_file = f"{cache_file}.tmp.{os.getpid()}"
                    tmp_meta = f"{meta_file}.tmp.{os.getpid()}"
                    try:
                        with open(tmp_file, "w", encoding="utf-8") as fh:
                            fh.write(text)
                        with open(tmp_meta, "w", encoding="utf-8") as fh:
                            fh.write(url + "\n")
                        os.replace(tmp_file, cache_file)
                        os.replace(tmp_meta, meta_file)
                    finally:
                        for tmp in (tmp_file, tmp_meta):
                            if os.path.exists(tmp):
                                os.remove(tmp)
                    return text
                except Exception as exc:  # network errors, HTTP errors
                    last_error = exc
                    if attempt < retries:
                        time.sleep(retry_wait * attempt)
            raise RuntimeError(
                f"KEGG request failed after {retries} attempts: {url}: {last_error}"
            )

    return _get


def read_emapper(path):
    """Read emapper.annotations whose header line begins with '#query'."""
    header = None
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("##"):
                continue
            if line.startswith("#"):
                header = line.lstrip("#").split("\t")
                continue
            if header is None:
                continue
            parts = line.split("\t")
            if len(parts) < len(header):
                parts += [""] * (len(header) - len(parts))
            rows.append(parts[: len(header)])
    if header is None:
        raise ValueError(f"no emapper header found in {path}")
    return pd.DataFrame(rows, columns=header)


def normalise_go(go_path, go_table=None):
    """The legacy GO parser emits MF/BP/CC; add full namespace names and names."""
    df = pd.read_table(go_path) if os.path.getsize(go_path) else pd.DataFrame()
    if df.empty:
        return pd.DataFrame(columns=["gene", "GO", "name", "namespace", "level"])
    # The legacy table carries the GO description; use it to fill missing names
    # without changing the legacy annotation selection.
    go_names = {}
    if go_table and os.path.exists(go_table):
        names = pd.read_table(go_table)
        if {"GO", "Description"}.issubset(names.columns):
            go_names = dict(zip(names["GO"], names["Description"]))

    if "level" in df.columns:
        df["namespace"] = df["level"].map(lambda x: LEVEL_NAMESPACE.get(str(x).strip(), x))
    elif "namespace" in df.columns:
        df["level"] = df["namespace"].map(
            {v: k for k, v in LEVEL_NAMESPACE.items()}
        )
    else:
        df["level"] = None
        df["namespace"] = None
    if "name" not in df.columns:
        df["name"] = None
    df["name"] = df["name"].where(df["name"].notna(), df["GO"].map(go_names))
    ordered = ["gene", "GO", "name", "namespace", "level"] + [
        c for c in df.columns if c not in {"gene", "GO", "name", "namespace", "level"}
    ]
    return df[ordered].drop_duplicates(subset=["gene", "GO"])


def normalise_ko(ko_path, kegg_desc_path):
    if not os.path.exists(ko_path) or not os.path.getsize(ko_path):
        return pd.DataFrame(columns=["gene", "KO", "pathway", "pathway_id", "description"])
    df = pd.read_table(ko_path)
    if "pathway" not in df.columns:
        df["pathway"] = NF
    desc_map = {}
    if kegg_desc_path and os.path.exists(kegg_desc_path):
        with open(kegg_desc_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2:
                    desc_map[parts[0].strip()] = parts[1].strip()
    # Keep mapXXXXX for JBrowse, add the 5-digit id used by metabolic_pathway.
    df["pathway"] = df["pathway"].fillna(NF).astype(str)
    df["pathway_id"] = df["pathway"].str.replace(r"^map", "", regex=True)
    df["pathway_id"] = df["pathway_id"].where(df["pathway_id"].str.fullmatch(r"\d{5}"), None)
    if "description" not in df.columns:
        df["description"] = None
    desc_series = df["pathway"].map(desc_map)
    df["description"] = df["description"].where(df["description"].notna(), desc_series)
    return df[["gene", "KO", "pathway", "pathway_id", "description"]].drop_duplicates(
        subset=["gene", "KO", "pathway"]
    )


def write_detail(annotations, out_path):
    wanted = [
        "query", "seed_ortholog", "evalue", "score", "eggNOG_OGs",
        "max_annot_lvl", "COG_category", "Description", "Preferred_name",
        "GOs", "EC", "KEGG_ko", "KEGG_Pathway",
    ]
    present = [c for c in wanted if c in annotations.columns]
    annotations[present].to_csv(out_path, sep="\t", index=False)
    return len(annotations)


def main():
    ap = argparse.ArgumentParser(description="Parse eggNOG-mapper annotations")
    ap.add_argument("--input", required=True, help="*.emapper.annotations")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--vendor", required=True, help="vendor/parse_eggNOG.py")
    ap.add_argument("--go-obo", required=True)
    ap.add_argument("--kegg-desc", default="")
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--orgs", default="all", help="comma-separated KEGG org codes, or 'all'")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    legacy = load_module(args.vendor, "legacy_parse_eggnog")
    go_parser = load_module(
        os.path.join(os.path.dirname(args.vendor), "parse_go_obofile.py"),
        "legacy_parse_go_obo",
    )

    go_table = os.path.join(args.outdir, "go.tb")
    if not os.path.exists(go_table) or os.path.getmtime(go_table) < os.path.getmtime(args.go_obo):
        go_parser.main(args.go_obo, go_table)
    if not os.path.exists(go_table) or os.path.getsize(go_table) == 0:
        print("[ERROR] GO table is empty; check go-basic.obo", file=sys.stderr)
        return 3

    orgs = [x.strip() for x in args.orgs.split(",") if x.strip()] or ["all"]
    legacy.get_html = make_cached_get_html(args.cache_dir, args.offline)
    try:
        legacy.main(args.input, args.outdir, go_table, orgs)
    except Exception as exc:
        print(f"[ERROR] legacy parse_eggNOG failed: {exc}", file=sys.stderr)
        return 3

    go_path = os.path.join(args.outdir, "GOannotation.tsv")
    ko_path = os.path.join(args.outdir, "KOannotation.tsv")
    if os.path.exists(go_path):
        normalise_go(go_path, go_table).to_csv(go_path, sep="\t", index=False)
    if os.path.exists(ko_path):
        normalise_ko(ko_path, args.kegg_desc).to_csv(ko_path, sep="\t", index=False)

    annotations = read_emapper(args.input)
    n = write_detail(annotations, os.path.join(args.outdir, "eggnog.tsv"))
    print(f"[OK] eggNOG parsed: {n} queries")
    return 0


if __name__ == "__main__":
    sys.exit(main())