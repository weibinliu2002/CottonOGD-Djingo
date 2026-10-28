#!/usr/bin/env python3
"""Upload one or more species into CottonOGD MySQL (DML only).

Design notes
------------
* Schema is owned by Django (`backend/CottonOGD/models.py`). This script never
  executes DDL; if a column/table added by a planned migration is absent it
  reports `migration not applied` and skips that write.
* `--dry-run` is the default. Nothing is written and no cache is touched.
* Each species is uploaded in one transaction under a file lock plus a MySQL
  `GET_LOCK`, so two concurrent uploads for the same species cannot interleave.
* Conflict policies: `skip` (default), `overwrite`, `version`.
* Gene/GO/KEGG links always use `genemaster.id`, never a transcript id.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import pymysql
import yaml

try:
    import redis
except ImportError:  # cache invalidation is optional
    redis = None

BATCH_DEFAULT = 5000
NUM_SUFFIX = re.compile(r"\.\d+$")
ID_SUFFIX = re.compile(r"[-_](?:R[AB]|mRNA\d+|t\d+|p\d+)$")
GENE_ANNOT = [
    "uniprot", "interproscan", "pfam", "smart", "eggnog", "prosite", "prints",
    "funfam", "superfamily", "cdd", "gene3d", "hamap", "panther", "pirsf",
    "sfld", "tigrfams",
]


def db_now():
    """Timestamp for Django `auto_now_add`/`auto_now` columns.

    Raw SQL bypasses the ORM, so NOT NULL timestamp columns must be supplied
    explicitly or MySQL strict mode rejects the insert.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def log(msg, verbose_only=False, verbose=False):
    if verbose_only and not verbose:
        return
    print(msg, flush=True)


def read_yaml(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def read_json(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_env(path):
    env = {}
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip("'\"")
    return env


def env_value(env, *names, default=None):
    for name in names:
        if os.environ.get(name):
            return os.environ[name]
        if env.get(name):
            return env[name]
    return default


def open_text(path):
    import gzip
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        magic = fh.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def fasta_records(path):
    fh = open_text(path)
    if fh is None:
        return
    header = None
    chunks = []
    with fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(chunks)
                header = line[1:].split()[0] if line[1:].strip() else ""
                chunks = []
            elif header is not None:
                chunks.append(line.strip())
        if header is not None:
            yield header, "".join(chunks)


def parse_attrs(attrs):
    out = {}
    if "=" in attrs:
        for item in attrs.split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                out[key.strip()] = value.strip()
    else:  # GTF fallback
        for item in attrs.split(";"):
            item = item.strip()
            if not item or " " not in item:
                continue
            key, value = item.split(" ", 1)
            out[key] = value.strip().strip('"')
    return out


def parse_gff(path):
    genes, transcripts, tx2gene = {}, {}, {}
    fh = open_text(path)
    if fh is None:
        raise FileNotFoundError(path)
    with fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9:
                continue
            attrs = parse_attrs(parts[8])
            ftype = parts[2].lower()
            if ftype in ("gene", "pseudogene"):
                gid = attrs.get("ID") or attrs.get("gene_id")
                if gid:
                    genes[gid] = (parts[0], int(parts[3]), int(parts[4]), parts[6])
            elif ftype in ("mrna", "transcript"):
                tid = attrs.get("ID") or attrs.get("transcript_id")
                # gffread's GTF conversion stores the gene on the transcript
                # as `geneID`, while native GFF3 uses `Parent`.
                parent = (attrs.get("Parent") or attrs.get("gene_id")
                          or attrs.get("geneID"))
                if tid:
                    transcripts[tid] = parent
                    if parent:
                        tx2gene[tid] = parent.split(",")[0]
    return genes, transcripts, tx2gene


def resolve_gene(query, genes, tx2gene):
    if not query:
        return None
    if query in genes:
        return query
    if query in tx2gene:
        return tx2gene[query]
    for regex in (NUM_SUFFIX, ID_SUFFIX):
        base = regex.sub("", query)
        if base != query:
            if base in genes:
                return base
            if base in tx2gene:
                return tx2gene[base]
    if "|" in query:
        base = query.split("|")[-1]
        if base in genes:
            return base
        if base in tx2gene:
            return tx2gene[base]
    return None


def read_dicts(path):
    fh = open_text(path)
    if fh is None:
        return []
    rows = []
    header = None
    with fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = [p.strip() for p in parts]
                continue
            if len(parts) < len(header):
                parts += [""] * (len(header) - len(parts))
            rows.append(dict(zip(header, parts)))
    return rows


def chunked(items, size):
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


class Uploader:
    def __init__(self, args, sample):
        self.args = args
        self.sample = sample
        self.species = sample["id"]
        self.results = os.path.join(args.results_dir, self.species)
        self.metadata = read_yaml(sample.get("metadata"))
        self.qc = read_yaml(os.path.join(self.results, "qc", "qc_report.yaml"))
        self.report = {
            "species": self.species,
            "dry_run": not args.apply,
            "policy": args.policy,
            "status": "pending",
            "tables": {},
            "warnings": [],
            "errors": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        self.conn = None
        self.cursor = None
        self.species_id = None
        self.annotation_version = str(
            self.metadata.get("annotation_version")
            or self.metadata.get("assembly_version")
            or "unversioned"
        )[:100]
        self.source_cache = {}
        self.detail_cache = {}
        self.table_columns = {}
        self.batch = args.batch_size

    # ------------------------------------------------------------------ db
    def connect(self):
        cfg = self.args.db_config
        self.conn = pymysql.connect(
            host=cfg["host"], port=int(cfg["port"]), user=cfg["user"],
            password=cfg["password"], database=cfg["database"],
            charset="utf8mb4", autocommit=False,
        )
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def columns(self, table):
        if table not in self.table_columns:
            try:
                self.cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                self.table_columns[table] = {row[0] for row in self.cursor.fetchall()}
            except Exception:
                self.table_columns[table] = set()
        return self.table_columns[table]

    def has_table(self, table):
        return bool(self.columns(table))

    def count(self, table, where="", params=()):
        if not self.has_table(table):
            return 0
        self.cursor.execute(f"SELECT COUNT(*) FROM `{table}` {where}", params)
        return int(self.cursor.fetchone()[0])

    def bump(self, table, key="inserted", n=1):
        entry = self.report["tables"].setdefault(table, {"inserted": 0, "skipped": 0, "warned": 0})
        entry[key] += n

    def warn(self, msg):
        if msg not in self.report["warnings"]:
            self.report["warnings"].append(msg)

    def error(self, msg):
        self.report["errors"].append(msg)

    def insert(self, table, columns, rows, update=None):
        """Insert rows in batches. Returns (attempted, inserted_or_affected)."""
        attempted = len(rows)
        if not rows:
            return 0, 0
        if not self.args.apply:
            self.bump(table, "inserted", attempted)
            return attempted, 0
        existing = self.columns(table)
        columns = [c for c in columns if c in existing]
        if not columns:
            self.warn(f"{table}: no target columns exist (migration not applied?)")
            self.bump(table, "skipped", attempted)
            return attempted, 0
        placeholders = ", ".join(["%s"] * len(columns))
        sql = f"INSERT INTO `{table}` ({', '.join('`%s`' % c for c in columns)}) VALUES ({placeholders})"
        if update:
            updates = [c for c in update if c in columns]
            if updates:
                sql += " ON DUPLICATE KEY UPDATE " + ", ".join(f"`{c}`=VALUES(`{c}`)" for c in updates)
            else:
                sql = sql.replace("INSERT INTO", "INSERT IGNORE INTO", 1)
        affected = 0
        for batch in chunked(rows, self.batch):
            self.cursor.executemany(sql, batch)
            affected += max(self.cursor.rowcount, 0)
        self.bump(table, "inserted", affected)
        self.bump(table, "skipped", max(attempted - affected, 0))
        return attempted, affected

    # ------------------------------------------------------------- helpers
    def get_source_id(self, name):
        name = name.lower()
        if name in self.source_cache:
            return self.source_cache[name]
        self.cursor.execute("SELECT id FROM annotation_source WHERE name=%s", (name,))
        row = self.cursor.fetchone()
        if row:
            self.source_cache[name] = row[0]
            return row[0]
        if not self.args.apply:
            self.source_cache[name] = -1
            return -1
        self.cursor.execute(
            "INSERT INTO annotation_source (name, description) VALUES (%s, %s)",
            (name, f"Added by unified workflow ({name})"),
        )
        self.source_cache[name] = self.cursor.lastrowid
        return self.cursor.lastrowid

    def get_detail_id(self, source_id, annotation_id, fields):
        key = (source_id, annotation_id)
        if key in self.detail_cache:
            return self.detail_cache[key]
        self.cursor.execute(
            "SELECT id FROM annotation_detail WHERE source_id=%s AND annotation_id=%s LIMIT 1",
            (source_id, annotation_id),
        )
        row = self.cursor.fetchone()
        if row:
            self.detail_cache[key] = row[0]
            return row[0]
        if not self.args.apply:
            self.detail_cache[key] = -1
            return -1
        cols = ["source_id", "annotation_id"] + [c for c in fields if c in self.columns("annotation_detail")]
        placeholders = ", ".join(["%s"] * len(cols))
        values = [source_id, annotation_id] + [fields[c] for c in cols[2:]]
        self.cursor.execute(
            f"INSERT INTO annotation_detail ({', '.join('`%s`' % c for c in cols)}) "
            f"VALUES ({placeholders})", values,
        )
        self.detail_cache[key] = self.cursor.lastrowid
        return self.cursor.lastrowid

    def link_annotation(self, rows):
        if not rows:
            return
        seen = set()
        unique = []
        for row in rows:
            if row not in seen:
                seen.add(row)
                unique.append(row)
        self.insert("gene_annotation",
                    ["id_id", "genome_id", "source_id", "annotation_detail_id"],
                    unique, update=None)

    # ------------------------------------------------------------ species
    def upsert_species(self):
        meta = self.metadata
        cols = self.columns("species")
        payload = {
            "name": self.species,
            "alias": str(meta.get("alias") or self.species)[:255],
            "Cotton_Species": meta.get("cotton_species") or meta.get("species_name"),
            "Genome_type": meta.get("genome_type"),
            "Category": meta.get("category"),
            "Accession": meta.get("accession"),
            "Ploidy": meta.get("ploidy"),
            "Assembling_institution": meta.get("assembling_institution"),
            "Website": meta.get("website"),
            "Article": meta.get("article"),
            "description": meta.get("description"),
            "common_name": meta.get("common_name"),
            "assembly_version": meta.get("assembly_version"),
            "annotation_version": meta.get("annotation_version"),
            "submitter": meta.get("submitter"),
        }
        genome_size = self.qc.get("genome_size")
        lai = (self.qc.get("lai") or {}).get("lai")
        busco = (self.qc.get("busco") or {}).get("busco_fraction")
        payload.update({
            "Genome_size": int(genome_size) if genome_size else None,
            "LAI_value": str(lai) if lai is not None else None,
            "Busco": str(busco) if busco is not None else None,
        })

        # alias must be unique across other species
        if self.has_table("species"):
            self.cursor.execute(
                "SELECT name FROM species WHERE alias=%s AND name<>%s LIMIT 1",
                (payload["alias"], self.species),
            )
            conflict = self.cursor.fetchone()
            if conflict:
                raise RuntimeError(
                    f"alias {payload['alias']!r} already belongs to species {conflict[0]!r}"
                )

        writable = [c for c in payload if c in cols]
        if not self.args.apply:
            self.cursor.execute("SELECT id FROM species WHERE name=%s", (self.species,))
            row = self.cursor.fetchone()
            self.species_id = row[0] if row else -1
            self.bump("species", "inserted", 1)
            return
        sql = (
            f"INSERT INTO species ({', '.join('`%s`' % c for c in writable)}) "
            f"VALUES ({', '.join(['%s'] * len(writable))}) "
            "ON DUPLICATE KEY UPDATE "
            + ", ".join(f"`{c}`=COALESCE(VALUES(`{c}`), `{c}`)" for c in writable if c != "name")
        )
        self.cursor.execute(sql, [payload[c] for c in writable])
        self.cursor.execute("SELECT id FROM species WHERE name=%s", (self.species,))
        self.species_id = self.cursor.fetchone()[0]
        self.bump("species", "inserted", 1)

    # ----------------------------------------------------------- conflicts
    def existing_state(self):
        if not self.has_table("species_upload_state"):
            return None
        cols = self.columns("species_upload_state")
        if "annotation_version" not in cols:
            return None
        self.cursor.execute(
            "SELECT status FROM species_upload_state WHERE species_id=%s AND annotation_version=%s",
            (self.species, self.annotation_version),
        )
        row = self.cursor.fetchone()
        return row[0] if row else None

    def existing_gene_count(self):
        if self.species_id in (None, -1) or not self.has_table("genemaster"):
            return 0
        return self.count("genemaster", "WHERE genome_id=%s", (self.species,))

    def clear_species_genes(self):
        """Delete only this species' gene-linked rows, in FK-safe order."""
        if not self.args.apply or self.species_id in (None, -1):
            return
        gid = self.species_id
        # genemaster.genome_id stores species.name (FK to_field='name'); the
        # other gene-linked tables store the numeric species id.
        genome_name = self.species
        if self.has_table("gene_annotation"):
            self.cursor.execute("DELETE FROM gene_annotation WHERE genome_id=%s", (gid,))
        if self.has_table("gene_go") and self.has_table("genemaster"):
            self.cursor.execute(
                "DELETE FROM gene_go WHERE id_id IN (SELECT id FROM genemaster WHERE genome_id=%s)",
                (genome_name,),
            )
        if self.has_table("gene_kegg") and self.has_table("genemaster"):
            self.cursor.execute(
                "DELETE FROM gene_kegg WHERE id_id IN (SELECT id FROM genemaster WHERE genome_id=%s)",
                (genome_name,),
            )
        if self.has_table("genefamily"):
            self.cursor.execute("DELETE FROM genefamily WHERE genome_id=%s", (gid,))
        if self.has_table("gene_seq"):
            self.cursor.execute("DELETE FROM gene_seq WHERE genome_id=%s", (gid,))
        if self.has_table("transcriptmaster"):
            self.cursor.execute("DELETE FROM transcriptmaster WHERE genome_id=%s", (gid,))
        if self.has_table("genemaster"):
            self.cursor.execute("DELETE FROM genemaster WHERE genome_id=%s", (genome_name,))
        log(f"[INFO] cleared existing gene data for {self.species}")

    # -------------------------------------------------------------- genes
    def upload_genes(self, gff_path):
        genes, transcripts, tx2gene = parse_gff(gff_path)
        self.report["gff"] = {
            "gene_count": len(genes),
            "transcript_count": len(transcripts),
        }
        if not self.args.apply:
            self.insert("genemaster", [], [])
            self.bump("genemaster", "inserted", len(genes))
            self.bump("transcriptmaster", "inserted", len(transcripts))
            return genes, transcripts, tx2gene, {}, {}

        now = db_now()
        rows = [(gid, self.species, f"{self.species}::{gid}"[:200], now) for gid in genes]
        self.insert("genemaster", ["geneid", "genome_id", "alias", "created_at"], rows,
                    update=["geneid"])
        # genemaster.genome_id is species.name, not the numeric species id.
        self.cursor.execute("SELECT geneid, id FROM genemaster WHERE genome_id=%s", (self.species,))
        gene_db = {row[0]: row[1] for row in self.cursor.fetchall()}

        tx_rows = [
            (gene_db.get(tx2gene.get(tid), 0), tid, self.species_id)
            for tid in transcripts if tx2gene.get(tid) in gene_db
        ]
        self.insert("transcriptmaster", ["id_id", "transcriptid", "genome_id"], tx_rows,
                    update=["id_id"])
        self.cursor.execute(
            "SELECT transcriptid, id FROM transcriptmaster WHERE genome_id=%s",
            (self.species_id,),
        )
        tx_db = {row[0]: row[1] for row in self.cursor.fetchall()}
        return genes, transcripts, tx2gene, gene_db, tx_db

    # ---------------------------------------------------------- sequences
    def upload_sequences(self, genes, gene_db, tx_db, tx2gene):
        mapping = {
            "mrna": "mrna.fa",
            "cdna": "cdna.fa",
            "cds": "cds.fa",
            "pro": "pro.fa",
            "gene_genome": "gene_genome.fa",
            "upstream": "upstream20000.fa",
            "downstream": "downstream20000.fa",
        }
        wanted = self.args.sequence_types
        for gene_type in wanted:
            name = mapping.get(gene_type)
            if not name:
                continue
            path = os.path.join(self.results, "sequences", name)
            if not os.path.exists(path):
                self.warn(f"sequence file missing: {path}")
                continue
            rows = []
            skipped = 0
            for header, seq in fasta_records(path):
                if not seq:
                    skipped += 1
                    continue
                if header in tx_db:
                    tid = header
                    gid = tx2gene.get(tid)
                    tr_id = str(tx_db[tid])
                else:
                    gid = header if header in genes else resolve_gene(header, genes, tx2gene)
                    tid = header
                    tr_id = None
                db_gene = gene_db.get(gid)
                if gid is None or (self.args.apply and db_gene is None):
                    skipped += 1
                    continue
                rows.append((tid, seq, self.species_id, gene_type,
                             db_gene if self.args.apply else 0, tr_id))
            if not self.args.apply:
                self.bump("gene_seq", "inserted", len(rows))
                self.bump("gene_seq", "skipped", skipped)
                continue
            self.insert("gene_seq",
                        ["mrna_id", "sequence", "genome_id", "gene_type", "id_id", "tr_id"],
                        rows)
            if skipped:
                self.bump("gene_seq", "skipped", skipped)

    # ------------------------------------------------------------- GO/KEGG
    def upload_go_kegg(self, gene_db, tx2gene, genes):
        ann_dir = os.path.join(self.results, "annotation", "eggnog")
        go_path = os.path.join(ann_dir, "GOannotation.tsv")
        ko_path = os.path.join(ann_dir, "KOannotation.tsv")

        if os.path.exists(go_path) and self.has_table("go_term"):
            self.cursor.execute("SELECT id FROM go_term")
            valid_go = {row[0] for row in self.cursor.fetchall()}
            go_rows, skipped = [], 0
            for row in read_dicts(go_path):
                gid = resolve_gene(row.get("gene") or row.get("Query"), genes, tx2gene)
                go_id = (row.get("GO") or "").strip()
                db_gene = gene_db.get(gid) if self.args.apply else None
                if not gid or not go_id or go_id not in valid_go:
                    skipped += 1
                    continue
                if self.args.apply and db_gene is None:
                    skipped += 1
                    continue
                go_rows.append((db_gene if self.args.apply else 0, go_id))
            self.insert("gene_go", ["id_id", "go_id"], go_rows)
            if skipped:
                self.bump("gene_go", "skipped", skipped)
                self.warn(f"gene_go: {skipped} rows skipped (unmapped gene or unknown GO)")
        elif os.path.exists(go_path):
            self.warn("gene_go skipped: go_term table missing")

        if os.path.exists(ko_path) and self.has_table("ko_term") and self.has_table("metabolic_pathway"):
            self.cursor.execute("SELECT ko_id FROM ko_term")
            valid_ko = {row[0] for row in self.cursor.fetchall()}
            self.cursor.execute("SELECT pathway_id FROM metabolic_pathway")
            valid_pathway = {row[0] for row in self.cursor.fetchall()}
            ko_rows, skipped = [], 0
            for row in read_dicts(ko_path):
                gid = resolve_gene(row.get("gene") or row.get("Query"), genes, tx2gene)
                ko = (row.get("KO") or "").strip()
                pw = (row.get("pathway_id") or row.get("pathway") or "").strip()
                pw = re.sub(r"^map", "", pw)
                db_gene = gene_db.get(gid) if self.args.apply else None
                if not gid or ko not in valid_ko or pw not in valid_pathway:
                    skipped += 1
                    continue
                if self.args.apply and db_gene is None:
                    skipped += 1
                    continue
                ko_rows.append((db_gene if self.args.apply else 0, ko, pw))
            self.insert("gene_kegg", ["id_id", "kegg_id", "pathway_id"], ko_rows)
            if skipped:
                self.bump("gene_kegg", "skipped", skipped)
                self.warn(f"gene_kegg: {skipped} rows skipped (unmapped gene/unknown KO/pathway)")
        elif os.path.exists(ko_path):
            self.warn("gene_kegg skipped: ko_term or metabolic_pathway table missing")

    # ---------------------------------------------------------- iTAK/others
    def upload_itak(self, gene_db, tx2gene, genes):
        path = os.path.join(self.results, "annotation", "itak", "itak.tsv")
        if not os.path.exists(path):
            return
        rows, skipped = [], 0
        for row in read_dicts(path):
            gid = resolve_gene(row.get("gene_id"), genes, tx2gene)
            db_gene = gene_db.get(gid) if self.args.apply else None
            if not gid or (self.args.apply and db_gene is None):
                skipped += 1
                continue
            rows.append((
                db_gene if self.args.apply else 0,
                self.species_id if self.args.apply else 0,
                gid,
                row.get("TF_class") or "",
                row.get("class_name") or "",
                row.get("TF_name") or "",
            ))
        self.insert("genefamily",
                    ["id_id", "genome_id", "geneid", "TF_class", "class_name", "TF_name"],
                    rows, update=["geneid", "TF_class", "class_name", "TF_name"])
        if skipped:
            self.warn(f"genefamily: {skipped} iTAK rows skipped (unmapped gene)")

    def upload_uniprot(self, gene_db, tx2gene, genes):
        path = os.path.join(self.results, "annotation", "uniprot", "Final_Annotation.tsv")
        if not os.path.exists(path):
            return
        source_id = self.get_source_id("uniprot")
        links, skipped = [], 0
        for row in read_dicts(path):
            gid = resolve_gene(row.get("Query_ID"), genes, tx2gene)
            db_gene = gene_db.get(gid) if self.args.apply else None
            if not gid or (self.args.apply and db_gene is None):
                skipped += 1
                continue
            fields = {
                "description": row.get("Protein_Name"),
                "protein_name": row.get("Protein_Name"),
                "gene_name": row.get("Gene_Name"),
                "species": row.get("Species"),
                "ox": int(row["OX"]) if str(row.get("OX", "")).isdigit() else None,
                "pe": int(row["PE"]) if str(row.get("PE", "")).isdigit() else None,
                "sv": int(row["SV"]) if str(row.get("SV", "")).isdigit() else None,
                "full_header": row.get("Full_Header"),
                "other_info": json.dumps({
                    "identity": row.get("Identity"), "evalue": row.get("E-value"),
                }),
            }
            detail_id = self.get_detail_id(source_id, row.get("UniProt_ID"), fields)
            links.append((db_gene if self.args.apply else 0,
                          self.species_id if self.args.apply else 0,
                          source_id if source_id != -1 else 0,
                          detail_id if detail_id != -1 else 0))
        self.link_annotation(links)
        if skipped:
            self.warn(f"uniprot: {skipped} rows skipped (unmapped gene)")

    def upload_interproscan(self, gene_db, tx2gene, genes):
        path = os.path.join(self.results, "annotation", "interproscan", "interproscan.tsv")
        if not os.path.exists(path):
            return
        links, skipped = [], 0
        for row in read_dicts(path):
            gid = resolve_gene(row.get("protein_id"), genes, tx2gene)
            db_gene = gene_db.get(gid) if self.args.apply else None
            if not gid or (self.args.apply and db_gene is None):
                skipped += 1
                continue
            source_id = self.get_source_id(row.get("annotation_source") or "interproscan")
            fields = {
                "description": row.get("signature_desc"),
                "accession": row.get("interpro_acc") or row.get("signature_acc"),
                "pfam_type": "domain" if row.get("member_db", "").lower() == "pfam" else None,
                "other_info": json.dumps({
                    "member_db": row.get("member_db"),
                    "interpro_acc": row.get("interpro_acc"),
                    "start": row.get("start"), "end": row.get("end"),
                    "score": row.get("score"), "status": row.get("status"),
                    "go_terms": row.get("go_terms"),
                }),
            }
            detail_id = self.get_detail_id(source_id, row.get("signature_acc"), fields)
            links.append((db_gene if self.args.apply else 0,
                          self.species_id if self.args.apply else 0,
                          source_id if source_id != -1 else 0,
                          detail_id if detail_id != -1 else 0))
        self.link_annotation(links)
        if skipped:
            self.warn(f"interproscan: {skipped} rows skipped (unmapped gene)")

    def upload_eggnog_detail(self, gene_db, tx2gene, genes):
        path = os.path.join(self.results, "annotation", "eggnog", "eggnog.tsv")
        if not os.path.exists(path):
            return
        source_id = self.get_source_id("eggnog")
        links, skipped = [], 0
        for row in read_dicts(path):
            gid = resolve_gene(row.get("query"), genes, tx2gene)
            db_gene = gene_db.get(gid) if self.args.apply else None
            if not gid or (self.args.apply and db_gene is None):
                skipped += 1
                continue
            ogs = (row.get("eggNOG_OGs") or "").split(",")
            fields = {
                "description": row.get("Description"),
                "eggnog_og": ogs[0][:50] if ogs and ogs[0] else None,
                "cog_category": (row.get("COG_category") or "")[:50] or None,
                "other_info": json.dumps({
                    "evalue": row.get("evalue"), "score": row.get("score"),
                    "preferred_name": row.get("Preferred_name"),
                    "max_annot_lvl": row.get("max_annot_lvl"),
                    "EC": row.get("EC"),
                }),
            }
            annotation_id = (row.get("seed_ortholog") or row.get("query") or "")[:100]
            detail_id = self.get_detail_id(source_id, annotation_id, fields)
            links.append((db_gene if self.args.apply else 0,
                          self.species_id if self.args.apply else 0,
                          source_id if source_id != -1 else 0,
                          detail_id if detail_id != -1 else 0))
        self.link_annotation(links)
        if skipped:
            self.warn(f"eggnog: {skipped} rows skipped (unmapped gene)")

    # ------------------------------------------------------- metadata / QC
    def upload_metadata_tables(self):
        # The new species_* tables reference species.name, unlike gene_seq /
        # genefamily / gene_annotation which use the numeric species id.
        species_key = self.species
        if not species_key:
            return
        qc = self.qc
        if self.has_table("species_qc"):
            busco = qc.get("busco") or {}
            te = qc.get("te") or {}
            fields = {
                "species_id": species_key,
                "annotation_version": self.annotation_version,
                "genome_size": qc.get("genome_size"),
                "lai": (qc.get("lai") or {}).get("lai"),
                "busco_complete": busco.get("complete"),
                "busco_single": busco.get("single"),
                "busco_duplicated": busco.get("duplicated"),
                "busco_fragmented": busco.get("fragmented"),
                "busco_missing": busco.get("missing"),
                "busco_total": busco.get("total"),
                "busco_lineage": busco.get("lineage"),
                "busco_fraction": busco.get("busco_fraction"),
                "te_content_pct": te.get("te_content_pct"),
                "ltr_count": te.get("ltr_count"),
                "intact_ltr_count": te.get("intact_ltr_count"),
                "qc_json": json.dumps(qc, ensure_ascii=False),
                "created_at": db_now(),
            }
            cols = [c for c in fields if c in self.columns("species_qc")]
            if cols:
                if self.args.apply:
                    sql = (
                        f"INSERT INTO species_qc ({', '.join('`%s`' % c for c in cols)}) "
                        f"VALUES ({', '.join(['%s'] * len(cols))}) "
                        "ON DUPLICATE KEY UPDATE "
                        + ", ".join(f"`{c}`=VALUES(`{c}`)" for c in cols
                                    if c not in ("species_id", "annotation_version", "created_at"))
                    )
                    self.cursor.execute(sql, [fields[c] for c in cols])
                self.bump("species_qc", "inserted", 1)
        else:
            self.warn("species_qc table missing: migration not applied; detailed QC skipped")

        literature = self.metadata.get("literature") or []
        if self.has_table("species_literature"):
            if self.args.apply:
                self.cursor.execute("DELETE FROM species_literature WHERE species_id=%s", (species_key,))
                rows = []
                for order, item in enumerate(literature):
                    if isinstance(item, str):
                        item = {"title": item}
                    now = db_now()
                    rows.append((
                        species_key, item.get("title") or "", item.get("authors"),
                        item.get("journal"), item.get("year"), item.get("doi"),
                        item.get("url"), order, now,
                    ))
                self.insert("species_literature",
                            ["species_id", "title", "authors", "journal", "year", "doi", "url", "order", "created_at"],
                            rows)
            else:
                self.bump("species_literature", "inserted", len(literature))
        elif literature:
            self.warn("species_literature table missing: migration not applied; literature skipped")

    def upload_state(self, status):
        if not self.has_table("species_upload_state"):
            return
        if not self.args.apply:
            self.bump("species_upload_state", "inserted", 1)
            return
        blocks = []
        for path in (self.sample.get("genome"), self.sample.get("gff")):
            if path and os.path.exists(path):
                blocks.append(self._sha256(path))
            else:
                blocks.append(None)
        now = db_now()
        fields = {
            "species_id": self.species,
            "annotation_version": self.annotation_version,
            "genome_sha256": blocks[0],
            "gff_sha256": blocks[1],
            "status": status,
            "conflict_policy": self.args.policy,
            "upload_report": json.dumps(self.report, ensure_ascii=False),
            "uploader": os.environ.get("USER", "snakemake"),
            "uploaded_at": now,
            "updated_at": now,
        }
        cols = [c for c in fields if c in self.columns("species_upload_state")]
        sql = (
            f"INSERT INTO species_upload_state ({', '.join('`%s`' % c for c in cols)}) "
            f"VALUES ({', '.join(['%s'] * len(cols))}) "
            "ON DUPLICATE KEY UPDATE "
            + ", ".join(f"`{c}`=VALUES(`{c}`)" for c in cols
                        if c not in ("species_id", "annotation_version"))
        )
        self.cursor.execute(sql, [fields[c] for c in cols])
        self.bump("species_upload_state", "inserted", 1)

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    # --------------------------------------------------------------- cache
    def invalidate_cache(self):
        if not self.args.apply or not self.args.cache_enabled or redis is None:
            return
        cfg = self.args.redis_config
        try:
            client = redis.Redis(
                host=cfg["host"], port=int(cfg["port"]), db=int(cfg["db"]),
                password=cfg.get("password") or None, decode_responses=True,
                socket_timeout=5,
            )
        except Exception as exc:
            self.warn(f"Redis connection failed: {exc}")
            return
        patterns = [
            f"tissues:{self.species_id}", f"tissues:{self.species}",
            "tissues:all", "genomes_with_tissue",
            f"geneset:*{self.species}*", f"*:{self.species_id}:*",
        ]
        deleted = 0
        try:
            for pattern in patterns:
                for key in client.scan_iter(match=pattern, count=500):
                    client.delete(key)
                    deleted += 1
        except Exception as exc:
            self.warn(f"Redis invalidation failed: {exc}")
        self.report["redis_deleted"] = deleted

    # ----------------------------------------------------------------- run
    def run(self):
        gff_path = self.sample.get("gff")
        if not gff_path or not os.path.exists(gff_path):
            raise FileNotFoundError(f"GFF not found: {gff_path}")

        self.connect()
        lock_acquired = False
        try:
            timeout = int(self.args.upload_cfg.get("lock_timeout_sec", 300))
            mysql_lock(self.cursor, self.species, timeout)
            lock_acquired = True
            self.upsert_species()
            if not self.args.apply:
                for table in ("species_qc", "species_literature", "species_upload_state"):
                    if not self.has_table(table):
                        self.warn(f"{table} table missing: migration 0054 not applied")
                if self.metadata.get("literature") and not self.has_table("species_literature"):
                    self.warn("literature entries will be skipped until migration 0054 is applied")
            state = self.existing_state()
            gene_count = self.existing_gene_count()

            if state in ("success", "skipped_existing") and self.args.policy == "skip":
                self.report["status"] = "skipped"
                self.warn("previous successful upload exists; policy=skip")
                return
            if gene_count and self.args.policy == "skip" and state is None:
                self.report["status"] = "skipped_existing"
                self.warn(f"{gene_count} genes already exist; gene tables left untouched")
                self.upload_metadata_tables()
                self.upload_state("skipped_existing")
                self.conn.commit()
                return
            if gene_count and self.args.policy in ("overwrite", "version"):
                self.clear_species_genes()

            genes, transcripts, tx2gene, gene_db, tx_db = self.upload_genes(
                os.path.join(self.results, "sequences", "genes.fixed.gff")
                if os.path.exists(os.path.join(self.results, "sequences", "genes.fixed.gff"))
                else gff_path
            )
            self.upload_sequences(genes, gene_db, tx_db, tx2gene)
            self.upload_go_kegg(gene_db, tx2gene, genes)
            self.upload_itak(gene_db, tx2gene, genes)
            self.upload_uniprot(gene_db, tx2gene, genes)
            self.upload_interproscan(gene_db, tx2gene, genes)
            self.upload_eggnog_detail(gene_db, tx2gene, genes)
            self.upload_metadata_tables()
            self.report["status"] = "dry_run" if not self.args.apply else "success"
            self.upload_state(self.report["status"])
            if self.args.apply:
                self.conn.commit()
                self.invalidate_cache()
            else:
                self.conn.rollback()
        except Exception as exc:
            self.report["status"] = "error"
            self.error(str(exc))
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            if lock_acquired:
                try:
                    self.cursor.execute("SELECT RELEASE_LOCK(%s)", (f"cottonogd:upload:{self.species}",))
                    self.cursor.fetchall()
                except Exception:
                    pass
            self.report["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.close()


def acquire_locks(results_dir, species, timeout):
    os.makedirs(results_dir, exist_ok=True)
    lock_path = os.path.join(results_dir, f".upload.{species}.lock")
    handle = open(lock_path, "w")
    deadline = time.time() + timeout
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            if time.time() >= deadline:
                handle.close()
                raise RuntimeError(f"another upload is running for {species}")
            time.sleep(1)


def mysql_lock(cursor, species, timeout):
    cursor.execute("SELECT GET_LOCK(%s, %s)", (f"cottonogd:upload:{species}", timeout))
    row = cursor.fetchone()
    if not row or row[0] != 1:
        raise RuntimeError(f"could not acquire MySQL lock for {species}")


def build_samples(args, config):
    samples = []
    if args.samples:
        data = read_yaml(args.samples)
        entries = data.get("samples", []) if isinstance(data, dict) else data
        for item in entries or []:
            if item.get("enabled", True):
                samples.append(item)
    if args.species:
        # Honour the explicit selection even when a species comes from
        # single-species mode and therefore is absent from samples.yaml.
        wanted = [s.strip() for s in args.species.split(",") if s.strip()]
        by_id = {s.get("id"): s for s in samples}
        samples = [by_id.get(sid, {"id": sid}) for sid in wanted]
    elif not samples:
        default_samples = os.path.join(os.path.dirname(args.config), "samples.yaml")
        data = read_yaml(default_samples)
        entries = data.get("samples", []) if isinstance(data, dict) else data
        samples = [s for s in (entries or []) if s.get("enabled", True)]
    return samples


def main():
    ap = argparse.ArgumentParser(description="Upload species to CottonOGD MySQL")
    ap.add_argument("--config", required=True)
    ap.add_argument("--samples", default="")
    ap.add_argument("--species", default="", help="comma-separated species ids")
    ap.add_argument("--results-dir", default="")
    ap.add_argument("--apply", action="store_true", help="write to MySQL (default: dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="explicit dry-run (default)")
    ap.add_argument("--yes", action="store_true", help="required for batch apply")
    ap.add_argument("--policy", choices=["skip", "overwrite", "version"], default="")
    ap.add_argument("--batch-size", type=int, default=0)
    ap.add_argument("--sample-genome", default="", help="override genome path for single-species mode")
    ap.add_argument("--sample-gff", default="", help="override GFF path for single-species mode")
    ap.add_argument("--sample-metadata", default="", help="override metadata path")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--sequence-types", default="")
    args = ap.parse_args()

    config = read_yaml(args.config)
    base_dir = os.path.abspath(config.get("base_dir", os.path.dirname(args.config)))
    args.results_dir = os.path.abspath(args.results_dir or os.path.join(base_dir, config.get("results_dir", "results")))
    upload_cfg = config.get("upload", {})
    args.upload_cfg = upload_cfg
    args.policy = args.policy or upload_cfg.get("conflict_policy", "skip")
    args.batch_size = args.batch_size or int(upload_cfg.get("batch_size", BATCH_DEFAULT))
    args.cache_enabled = bool(upload_cfg.get("sync_cache", True))
    args.sequence_types = (
        [s.strip() for s in args.sequence_types.split(",") if s.strip()]
        if args.sequence_types else upload_cfg.get("sequence_types",
            ["mrna", "cdna", "cds", "pro", "gene_genome", "upstream", "downstream"])
    )
    args.apply = bool(args.apply and not args.dry_run)

    env = read_env(os.path.join(base_dir, "backend", ".env"))
    db_cfg = config.get("db", {})
    args.db_config = {
        "host": env_value(env, "MYSQL_DB_HOST", "MYSQL_HOST", default=db_cfg.get("host", "localhost")),
        "port": env_value(env, "MYSQL_DB_PORT", "MYSQL_PORT", default=db_cfg.get("port", 3306)),
        "user": env_value(env, "MYSQL_DB_USER", "MYSQL_USER", default="root"),
        "password": env_value(env, "MYSQL_DB_PASSWORD", "MYSQL_PASSWORD", default=""),
        "database": env_value(env, "MYSQL_DB_NAME", "MYSQL_DB", default=db_cfg.get("database", "cottonogd-ortho")),
    }
    redis_cfg = config.get("redis", {})
    args.redis_config = {
        "host": env_value(env, "REDIS_HOST", default=redis_cfg.get("host", "localhost")),
        "port": env_value(env, "REDIS_PORT", default=redis_cfg.get("port", 6379)),
        "db": env_value(env, "REDIS_DB", default=redis_cfg.get("db", 1)),
        "password": env_value(env, "REDIS_PASSWORD", default=""),
    }

    samples = build_samples(args, config)
    if not samples:
        print("[ERROR] no samples selected", file=sys.stderr)
        return 2
    if args.apply and len(samples) > 1 and not args.yes:
        print("[ERROR] batch apply requires --yes", file=sys.stderr)
        return 2

    overall = 0
    for sample in samples:
        sid = sample.get("id")
        if not sid:
            print("[ERROR] sample without id", file=sys.stderr)
            overall = 4
            continue
        if len(sid) > 255:
            print(f"[ERROR] species id exceeds 255 characters: {sid}", file=sys.stderr)
            overall = 4
            continue
        # Fill paths from samples.yaml defaults.
        root = os.path.dirname(os.path.abspath(args.samples)) if args.samples else base_dir
        sample.setdefault("metadata", os.path.join(root, "data", sid, "metadata.yaml"))
        sample.setdefault("genome", os.path.join(root, "data", sid, "genome.fasta"))
        sample.setdefault("gff", os.path.join(root, "data", sid, "genes.gff3"))
        for key in ("metadata", "genome", "gff"):
            if sample.get(key) and not os.path.isabs(sample[key]):
                sample[key] = os.path.join(root, sample[key])
        for key, override in (
            ("genome", args.sample_genome),
            ("gff", args.sample_gff),
            ("metadata", args.sample_metadata),
        ):
            if override:
                sample[key] = os.path.abspath(override)

        lock = acquire_locks(args.results_dir, sid, int(upload_cfg.get("lock_timeout_sec", 300)))
        uploader = Uploader(args, sample)
        try:
            uploader.run()
            status = uploader.report["status"]
            if status == "error":
                overall = 4
            log(f"[{status}] {sid}: {json.dumps(uploader.report['tables'], ensure_ascii=False)}",
                verbose_only=True, verbose=args.verbose)
        except Exception as exc:
            print(f"[ERROR] {sid}: {exc}", file=sys.stderr)
            uploader.report["status"] = "error"
            if str(exc) not in uploader.report["errors"]:
                uploader.report["errors"].append(str(exc))
            overall = 4 if overall == 0 else overall
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
            os.makedirs(os.path.join(args.results_dir, sid, "upload"), exist_ok=True)
            report_path = os.path.join(args.results_dir, sid, "upload", "upload_report.json")
            with open(report_path, "w", encoding="utf-8") as fh:
                json.dump(uploader.report, fh, ensure_ascii=False, indent=2)
            print(f"[REPORT] {report_path}")
    return overall


if __name__ == "__main__":
    sys.exit(main())