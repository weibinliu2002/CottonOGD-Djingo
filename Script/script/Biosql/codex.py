#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import gzip
import argparse
from Bio import SeqIO
from BioSQL import BioSeqDatabase
from BCBio import GFF

# 你的目录结构根路径
DEFAULT_GENOMES_DIR = "/data/web/CottonOGD/OGD/backend/data/genome"


def open_maybe_gzip(path, mode="rt"):
    if path.endswith(".gz"):
        return gzip.open(path, mode, encoding="utf-8")
    return open(path, mode, encoding="utf-8")


def load_fasta_to_biosql(db, fasta_path, fmt="fasta"):
    with open_maybe_gzip(fasta_path, "rt") as handle:
        count = db.load(SeqIO.parse(handle, fmt))
    return count


def build_bioseq_lookup(db):
    lookup = {}
    for rec in db.values():
        lookup[rec.id] = rec
        lookup[rec.name] = rec
    return lookup


def load_gff_features(db, gff_path):
    base_dict = build_bioseq_lookup(db)
    updated = 0
    with open_maybe_gzip(gff_path, "rt") as handle:
        for _rec in GFF.parse(handle, base_dict=base_dict):
            updated += 1
    return updated


def import_one_genome(server, db, genomes_dir, genome_name, load_protein=False):
    genome_path = os.path.join(genomes_dir, genome_name)
    gff_file = os.path.join(genome_path, f"{genome_name}.gff.gz")
    genome_fa = os.path.join(genome_path, f"{genome_name}.genome.fa.gz")
    protein_fa = os.path.join(genome_path, f"{genome_name}.pro.fa.gz")

    if not (os.path.isfile(gff_file) and os.path.isfile(genome_fa)):
        print(f"[SKIP] {genome_name}: 缺少 {genome_name}.gff.gz 或 {genome_name}.genome.fa.gz")
        return False

    print(f"\n[INFO] {genome_name}")
    print(f"  genome:  {genome_fa}")
    print(f"  gff:     {gff_file}")

    try:
        # 检查是否已存在该基因组的记录（db.keys()返回的是整数ID）
        existing_count = len(list(db.keys()))
        if existing_count > 0:
            print(f"  [WARN] 检测到已存在 {existing_count} 条记录，跳过导入")
            return True

        # 分步导入：先导入fasta序列，再加载GFF注释
        # 避免 GFF.parse 返回的记录包含不可pickle的socket对象
        
        # 1) 先用 BioSQL 导入纯序列
        n_seq = load_fasta_to_biosql(db, genome_fa, 'fasta')
        print(f"  [OK] genome FASTA records: {n_seq}")
        server.commit()
        
        # 2) 获取已导入序列的 lookup（从 BioSQL 获取）
        base_dict = build_bioseq_lookup(db)
        
        # 3) 再挂 GFF 注释
        updated = 0
        with open_maybe_gzip(gff_file, "rt") as gh:
            for rec in GFF.parse(gh, base_dict=base_dict):
                updated += 1
        server.commit()
        print(f"  [OK] GFF attached records: {updated}")

        if load_protein and os.path.isfile(protein_fa):
            n_pro = load_fasta_to_biosql(db, protein_fa, "fasta")
            server.commit()
            print(f"  [OK] protein FASTA records: {n_pro}")
        elif load_protein:
            print(f"  [WARN] protein file not found: {protein_fa}")

        return True
    except Exception as e:
        server.rollback()
        print(f"  [ERROR] {genome_name}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--driver", default="psycopg2", help="如 psycopg2 / pymysql")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5432)
    ap.add_argument("--db", required=True, help="BioSQL数据库名")
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--namespace", required=True, help="BioSQL biodatabase 名")
    ap.add_argument("--genomes-dir", default=DEFAULT_GENOMES_DIR)
    ap.add_argument("--load-protein", action="store_true", help="是否额外导入 .pro.fa.gz")
    ap.add_argument("--only-genome", default=None)

    args = ap.parse_args()

    server = BioSeqDatabase.open_database(
    driver="pymysql",
    user="root",
    passwd="1234",   # 改这里
    host="localhost",
    db="cottonogd-ortho",
    port=3306,
    )

    conn = server.adaptor.conn
    cur = conn.cursor()
    cur.execute("SET SESSION sql_mode = CONCAT(@@sql_mode, ',ANSI_QUOTES')")
    conn.commit()
    cur.close()  # 加这一行

    if args.namespace in server:
        db = server[args.namespace]
        print(f"[INFO] 使用已存在 namespace: {args.namespace}")
    else:
        db = server.new_database(args.namespace)
        server.commit()
        print(f"[INFO] 创建 namespace: {args.namespace}")

    ok, fail = 0, 0
    for genome_name in sorted(os.listdir(args.genomes_dir)):
        genome_path = os.path.join(args.genomes_dir, genome_name)
        if not os.path.isdir(genome_path):
            continue
        if args.only_genome and genome_name != args.only_genome:
            continue
        if import_one_genome(server, db, args.genomes_dir, genome_name, args.load_protein):
            ok += 1
        else:
            fail += 1

    print(f"\n[DONE] success={ok}, failed={fail}")
    conn.close()


if __name__ == "__main__":
    main()
