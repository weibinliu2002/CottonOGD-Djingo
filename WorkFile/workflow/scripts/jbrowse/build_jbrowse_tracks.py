#!/usr/bin/env python3
"""Build GO / KEGG / TE JBrowse tracks from workflow annotation outputs.

This adapts `backend/scripts/build_gokegg_tracks.py` (same GFF attribute format,
sorting, bgzip/tabix and config registration) to consume the files produced by
`workflow/scripts/annotation/parse_eggnog.py` and `workflow/scripts/te/parse_te.py`.

GO/KEGG attribute conventions (matching the legacy SoybeanGDB R code):
  GO:   ID=<gene>;Gene ontology:0004615=<name>;...
  KEGG: ID=<gene>;Annotation=K12345:<description>,...
TE: original EDTA attributes are preserved; only coordinate sorting/compression.
"""
import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict

NAMESPACES = ("molecular_function", "biological_process", "cellular_component")
TRACK_NAMES = {
    "molecular_function": "GO: Molecular Function",
    "biological_process": "GO: Biological Process",
    "cellular_component": "GO: Cellular Component",
    "kegg": "KEGG Annotation",
    "te": "TE Annotation",
}
FINAL_NAMES = {
    "molecular_function": "{s}_molecular_function.sorted.gff.gz",
    "biological_process": "{s}_biological_process.sorted.gff.gz",
    "cellular_component": "{s}_cellular_component.sorted.gff.gz",
    "kegg": "{s}KO.sorted.gff.gz",
    "te": "{s}_TE.sorted.gff.gz",
}
SUFFIX_RE = re.compile(r"\.(mRNA|t|p)\d+$")
NUM_SUFFIX_RE = re.compile(r"\.\d+$")


def log(msg):
    print(msg, flush=True)


def sanitize(text):
    # Match the legacy R track preparation: commas, spaces and GFF metacharacters
    # are replaced with underscores so descriptions cannot break attributes.
    return re.sub(r"[;=,\s]+", "_", str(text))


def open_text(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def load_go_obo(path):
    go_map = {}
    go_id = name = namespace = None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line == "[Term]":
                go_id = name = namespace = None
            elif line.startswith("id: GO:") and go_id is None:
                go_id = line[4:].strip()
            elif line.startswith("name: ") and go_id:
                name = line[6:].strip()
            elif line.startswith("namespace: ") and go_id:
                namespace = line[11:].strip()
            elif line == "" and go_id:
                if name and namespace:
                    go_map[go_id] = (name, namespace)
                go_id = name = namespace = None
    if go_id and name and namespace:
        go_map[go_id] = (name, namespace)
    return go_map


def load_kegg_desc(path):
    desc = {}
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2:
                    desc[parts[0].strip()] = parts[1].strip()
    return desc


def parse_gff_genes(path):
    genes, tx2gene = {}, {}
    with open_text(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9:
                continue
            attrs = parts[8]
            ftype = parts[2].lower()
            if ftype in ("gene", "pseudogene"):
                m = re.search(r"(?:^|;)ID=([^;]+)", attrs + ";")
                if m:
                    genes[m.group(1).strip()] = (parts[0], int(parts[3]), int(parts[4]), parts[6])
            else:
                mid = re.search(r"(?:^|;)ID=([^;]+)", attrs + ";")
                mparent = re.search(r"(?:^|;)Parent=([^;]+)", attrs + ";")
                # gffread's GTF conversion puts the gene id in `geneID=`.
                if not mparent:
                    mparent = re.search(r"(?:^|;)geneID=([^;]+)", attrs + ";")
                if not mparent:
                    mparent = re.search(r"(?:^|;)gene_id=([^;]+)", attrs + ";")
                if mid and mparent:
                    parent = mparent.group(1).strip().split(",")[0]
                    if parent in genes:
                        tx2gene[mid.group(1).strip()] = parent
    return genes, tx2gene


def resolve_gene(gene_id, genes, tx2gene):
    if gene_id in genes:
        return gene_id
    if gene_id in tx2gene:
        return tx2gene[gene_id]
    base = SUFFIX_RE.sub("", gene_id)
    if base != gene_id and base in genes:
        return base
    base = NUM_SUFFIX_RE.sub("", gene_id)
    if base != gene_id:
        if base in genes:
            return base
        if base in tx2gene:
            return tx2gene[base]
    return None


def parse_fai_order(path):
    order = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            name = line.split("\t", 1)[0].strip()
            if name:
                order.append(name)
    return {name: i for i, name in enumerate(order)}


def write_gff(rows, rank, path):
    rows.sort(key=lambda r: (rank.get(r[0], len(rank)), r[1], r[2], r[4]))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("##gff-version 3\n")
        for chr_, start, end, strand, gene_id, attrs in rows:
            fh.write(f"{chr_}\tworkflow\tgene\t{start}\t{end}\t.\t{strand}\t.\t{attrs}\n")


def bgzip_and_index(plain, bgzip, tabix):
    gz = plain + ".gz"
    with open(plain, "rb") as inp, open(gz, "wb") as out:
        subprocess.run([bgzip, "-c"], stdin=inp, stdout=out, check=True)
    subprocess.run([tabix, "-p", "gff", gz], check=True)
    os.remove(plain)
    return gz


def read_tsv(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        header = None
        rows = []
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = [p.lstrip("#") for p in parts]
                continue
            if len(parts) < len(header):
                parts += [""] * (len(header) - len(parts))
            rows.append(dict(zip(header, parts)))
    return rows


def build_go_rows(go_rows, go_annotation, genes, tx2gene, go_map):
    go_by_gene = defaultdict(lambda: defaultdict(dict))
    for row in go_annotation:
        go_id = (row.get("GO") or "").strip()
        gene = (row.get("gene") or row.get("Query") or "").strip()
        if not go_id or not gene:
            continue
        info = go_map.get(go_id)
        if not info:
            continue
        name, namespace = info
        if namespace not in NAMESPACES:
            continue
        if "=" in name:  # legacy R code drops names containing '='
            continue
        gid = resolve_gene(gene, genes, tx2gene)
        if gid is None:
            continue
        go_by_gene[gid][namespace][go_id] = name

    for gid, ns_map in go_by_gene.items():
        if gid not in genes:
            continue
        chr_, start, end, strand = genes[gid]
        for namespace, terms in ns_map.items():
            parts = [f"ID={gid}"]
            for go_id in sorted(terms):
                parts.append(f"Gene ontology:{go_id[3:]}={sanitize(terms[go_id])}")
            go_rows[namespace].append((chr_, start, end, strand, gid, ";".join(parts)))


def build_kegg_rows(kegg_annotation, genes, tx2gene, kegg_desc):
    ko_by_gene = defaultdict(set)
    pw_by_gene = defaultdict(set)
    pw_desc = {}
    for row in kegg_annotation:
        gene = (row.get("gene") or row.get("Query") or "").strip()
        ko = (row.get("KO") or "").strip()
        pw = (row.get("pathway") or row.get("pathway_id") or "").strip()
        if pw and not pw.startswith("map") and pw.isdigit():
            pw = "map" + pw
        gid = resolve_gene(gene, genes, tx2gene)
        if gid is None:
            continue
        if ko:
            ko_by_gene[gid].add(ko)
        if pw:
            pw_by_gene[gid].add(pw)
            if row.get("description"):
                pw_desc.setdefault(pw, row["description"])

    rows = []
    for gid in set(ko_by_gene) | set(pw_by_gene):
        if gid not in genes:
            continue
        chr_, start, end, strand = genes[gid]
        kos = sorted(ko_by_gene.get(gid, ()))
        anns = []
        for pw in sorted(pw_by_gene.get(gid, ())):
            desc = kegg_desc.get(pw) or pw_desc.get(pw)
            if not desc:
                continue
            desc = sanitize(desc)
            anns.append(f"{kos[0]}:{desc}" if len(kos) == 1 else desc)
        if not anns:
            continue
        rows.append((chr_, start, end, strand, gid,
                     f"ID={gid};Annotation={','.join(anns)}"))
    return rows


def sort_te_gff(src, dst, rank):
    """External sort keeps memory bounded for large EDTA outputs."""
    body = tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(dst), suffix=".te.body")
    try:
        with open_text(src) as fh, body:
            for line in fh:
                if line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 9:
                    continue
                key = rank.get(parts[0], len(rank))
                body.write(f"{key:09d}\t{int(parts[3]):012d}\t{line}")
        sort_key = ["-k1,1n", "-k2,2n"]
        sorted_body = body.name + ".sorted"
        with open(body.name, "rb") as inp, open(sorted_body, "wb") as out:
            subprocess.run(["sort", *sort_key], stdin=inp, stdout=out, check=True)
        with open(sorted_body, "r", encoding="utf-8", errors="replace") as inp, \
                open(dst, "w", encoding="utf-8") as out:
            out.write("##gff-version 3\n")
            for line in inp:
                out.write(line.split("\t", 2)[2])
    finally:
        for path in (body.name, body.name + ".sorted"):
            if os.path.exists(path):
                os.remove(path)


def link_file(src, jb_dir):
    os.makedirs(jb_dir, exist_ok=True)
    for suffix in ("", ".tbi"):
        s = src + suffix
        if not os.path.exists(s):
            continue
        dst = os.path.join(jb_dir, os.path.basename(s))
        if os.path.islink(dst):
            os.remove(dst)
        elif os.path.exists(dst):
            continue  # never replace a real file
        os.symlink(os.path.relpath(s, jb_dir), dst)


def update_config(config_path, species, files, enable_te):
    with open(config_path, "r", encoding="utf-8") as fh:
        config = json.load(fh)
    by_id = {t.get("trackId"): t for t in config.get("tracks", []) if t.get("trackId")}

    mapping = {key: f"{key}_annotation" for key in
               ("molecular_function", "biological_process", "cellular_component", "kegg", "te")}
    mapping["te"] = "TE_annotation"
    for key, track_id in mapping.items():
        if key not in files:
            continue
        if key == "te" and not enable_te:
            continue
        fname = files[key]
        track = by_id.get(track_id) or {
            "type": "FeatureTrack",
            "trackId": track_id,
            "name": TRACK_NAMES[key],
            "assemblyNames": [species],
        }
        track["name"] = TRACK_NAMES[key]
        track["adapter"] = {
            "type": "Gff3TabixAdapter",
            "gffGzLocation": {"uri": f"/jbrowse/large/{species}/{fname}", "locationType": "UriLocation"},
            "index": {
                "location": {"uri": f"/jbrowse/large/{species}/{fname}.tbi", "locationType": "UriLocation"},
                "indexType": "TBI",
            },
        }
        track["assemblyNames"] = [species]
        if track_id not in by_id:
            config.setdefault("tracks", []).append(track)
            by_id[track_id] = track

    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Build GO/KEGG/TE JBrowse tracks")
    ap.add_argument("--species", required=True)
    ap.add_argument("--gff", required=True, help="JBrowse GFF (.gff.gz or plain)")
    ap.add_argument("--fai", required=True)
    ap.add_argument("--go-annotation", default="")
    ap.add_argument("--ko-annotation", default="")
    ap.add_argument("--te-gff", default="")
    ap.add_argument("--go-obo", required=True)
    ap.add_argument("--kegg-desc", default="")
    ap.add_argument("--out-dir", required=True, help="backend/data/gokegg_track")
    ap.add_argument("--jbrowse-dir", required=True, help="backend/static/jbrowse/data/<species>")
    ap.add_argument("--bgzip", default="bgzip")
    ap.add_argument("--tabix", default="tabix")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--te-track", action="store_true")
    ap.add_argument("--summary", default="")
    args = ap.parse_args()

    if not os.path.exists(args.gff) or not os.path.exists(args.fai):
        log(f"[ERROR] GFF or FAI missing for {args.species}")
        return 3
    if not os.path.exists(args.go_obo):
        log(f"[ERROR] GO OBO missing: {args.go_obo}")
        return 3

    out_dir = os.path.join(args.out_dir, args.species)
    os.makedirs(out_dir, exist_ok=True)
    genes, tx2gene = parse_gff_genes(args.gff)
    rank = parse_fai_order(args.fai)
    go_map = load_go_obo(args.go_obo)
    kegg_desc = load_kegg_desc(args.kegg_desc)
    log(f"[INFO] {args.species}: {len(genes)} genes, {len(go_map)} GO terms")

    produced = {}
    files = {}

    go_rows = {ns: [] for ns in NAMESPACES}
    go_annotation = read_tsv(args.go_annotation)
    if go_annotation:
        build_go_rows(go_rows, go_annotation, genes, tx2gene, go_map)
    else:
        log(f"[WARN] no GO annotation for {args.species}")

    kegg_rows = []
    ko_annotation = read_tsv(args.ko_annotation)
    if ko_annotation:
        kegg_rows = build_kegg_rows(ko_annotation, genes, tx2gene, kegg_desc)
    else:
        log(f"[WARN] no KEGG annotation for {args.species}")

    for key, rows in list(go_rows.items()) + [("kegg", kegg_rows)]:
        if not rows:
            log(f"[WARN] {args.species}: empty {key} track")
            continue
        fname = FINAL_NAMES[key].format(s=args.species)
        final = os.path.join(out_dir, fname)
        if os.path.exists(final) and not args.force:
            files[key] = fname
        else:
            tmp = os.path.join(out_dir, f".tmp_{args.species}_{key}.gff")
            write_gff(rows, rank, tmp)
            gz = bgzip_and_index(tmp, args.bgzip, args.tabix)
            os.replace(gz, final)
            os.replace(gz + ".tbi", final + ".tbi")
            files[key] = fname
        link_file(final, args.jbrowse_dir)

    if args.te_gff and os.path.exists(args.te_gff):
        fname = FINAL_NAMES["te"].format(s=args.species)
        final = os.path.join(out_dir, fname)
        if not os.path.exists(final) or args.force:
            tmp = os.path.join(out_dir, f".tmp_{args.species}_te.gff")
            sort_te_gff(args.te_gff, tmp, rank)
            gz = bgzip_and_index(tmp, args.bgzip, args.tabix)
            os.replace(gz, final)
            os.replace(gz + ".tbi", final + ".tbi")
        link_file(final, args.jbrowse_dir)
        files["te"] = fname
    elif args.te_track:
        log(f"[WARN] TE track requested but no TE GFF for {args.species}")

    config_path = os.path.join(args.jbrowse_dir, "config.json")
    if os.path.exists(config_path):
        update_config(config_path, args.species, files, args.te_track)
    else:
        log(f"[WARN] JBrowse config not found: {config_path}")

    summary = {"species": args.species, "files": files, "gene_count": len(genes)}
    if args.summary:
        os.makedirs(os.path.dirname(os.path.abspath(args.summary)), exist_ok=True)
        with open(args.summary, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
    log(f"[OK] tracks: {files}")
    return 0


if __name__ == "__main__":
    sys.exit(main())