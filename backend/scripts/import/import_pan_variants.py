#!/usr/bin/env python
"""
导入 1913 份棉花泛基因组的 SNP/InDel 变异位点（仅位点主表，不含逐样本 GT）。

设计依据：docs/Genome_SV_数据库设计说明.md §4.2 / 调查结论 —— 1913 样本 × 26 染色体
约 5000 万位点，逐样本 GT 是千亿级，不可全量进库；本脚本只落"位点主表"
（variant），群体/逐样本基因型按方案 A/B/C 后续决定。

数据：cotton_Pan-genmone/snp/fix/clean_vcf/1913g.{A/D}{01..13}.final.vcf.gz
  - final 文件已含 SNP + InDel（README 说明）
  - 染色体在 VCF 中是 1..13，按文件名前缀 A/D 映射为 A01..A13 / D01..D13
  - svtype 由 REF/ALT 长度判定：两端均单碱基→SNP，否则→INDEL

用法：
  python scripts/import/import_pan_variants.py \
      --vcf-dir <clean_vcf dir> --set-name cotton_pan_sv_v1 \
      --reference-genome 67 [--limit-chrom A01] [--dry-run]
"""
import argparse
import glob
import gzip
import os
import sys
import django

sys.path.insert(0, "/data/web/CottonOGD/OGD/backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from CottonOGD.models import VariationSet, Variant  # noqa: E402


def chrom_from_filename(fname):
    """1913g.A01.final.vcf.gz -> ('A01', 'A', '01')"""
    base = os.path.basename(fname)
    # 1913g.A01.final.vcf.gz
    parts = base.split(".")
    if len(parts) < 3:
        return None
    tag = parts[1]  # e.g. A01
    return tag


def classify_svtype(ref, alt):
    ref = ref or ""
    alt = alt or ""
    if len(ref) == 1 and len(alt) == 1:
        return "SNP"
    return "INDEL"


def load_one_vcf(fname, set_id, chrom):
    # 幂等：先删该 set+chrom 已有位点。大染色体整表 DELETE 会在单条语句上超过
    # MySQL net_read_timeout，故用原生分块 DELETE ... LIMIT（每批独立短事务）。
    # （Django ORM 的 delete() 不支持 LIMIT，故走 cursor 原生 SQL。）
    from django.db import connection
    with connection.cursor() as cur:
        cur.execute("SET SESSION net_read_timeout=600, net_write_timeout=600, wait_timeout=28800")
        deleted = 0
        while True:
            cur.execute(
                "DELETE FROM variant WHERE set_id=%s AND chrom=%s LIMIT 50000",
                (set_id, chrom),
            )
            cnt = cur.rowcount
            deleted += cnt
            if cnt == 0:
                break
    print(f"[pan] {chrom}: deleted existing {deleted}")
    rows = []
    seen = set()  # (pos, svtype) 内存去重，减少冲突
    open_fn = gzip.open if fname.endswith(".gz") else open
    n = 0
    with open_fn(fname, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 5:
                continue
            _, pos, vid, ref, alt = cols[0], cols[1], cols[2], cols[3], cols[4]
            try:
                pos_i = int(pos)
            except ValueError:
                continue
            svtype = classify_svtype(ref, alt)
            key = (pos_i, svtype)
            if key in seen:
                continue
            seen.add(key)
            rows.append(Variant(
                set_id=set_id,
                chrom=chrom,
                pos=pos_i,
                end_pos=pos_i + max(len(ref), len(alt)) - 1 if (ref and alt) else None,
                svtype=svtype,
                ref=ref if len(ref) <= 4 else None,
                alt=alt if len(alt) <= 4 else alt,  # 长插入走 TEXT
                filter="PASS" if (len(cols) > 6 and cols[6] in (".", "PASS")) else None,
            ))
            n += 1
            if len(rows) >= 20000:
                Variant.objects.bulk_create(rows, batch_size=20000, ignore_conflicts=True)
                rows = []
    if rows:
        Variant.objects.bulk_create(rows, batch_size=20000, ignore_conflicts=True)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vcf-dir", required=True, help="clean_vcf 目录")
    ap.add_argument("--set-name", default="cotton_pan_sv_v1")
    ap.add_argument("--reference-genome", type=int, default=67)
    ap.add_argument("--limit-chrom", default=None, help="只导某个染色体，如 A01")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.vcf_dir, "1913g.*.final.vcf.gz")))
    if args.limit_chrom:
        files = [f for f in files if chrom_from_filename(f) == args.limit_chrom]
    if not files:
        print("ERROR: no final vcf found", file=sys.stderr)
        sys.exit(1)

    print(f"[pan] {len(files)} vcf files to load")

    if args.dry_run:
        total = 0
        for f in files:
            with gzip.open(f, "rt") as fh:
                total += sum(1 for l in fh if not l.startswith("#"))
        print(f"[pan] dry-run total variant lines ~ {total}")
        return

    vset, _ = VariationSet.objects.update_or_create(
        name=args.set_name,
        defaults={"reference_genome": args.reference_genome, "caller": "pan-genome calling",
                  "sample_count": 1913},
    )
    print(f"[pan] variation_set id={vset.id} name={vset.name}")

    total = 0
    for f in files:
        chrom = chrom_from_filename(f)
        cnt = load_one_vcf(f, vset.id, chrom)
        total += cnt
        print(f"[pan] {chrom}: {cnt} variants")
    print(f"[pan] DONE total={total}")


if __name__ == "__main__":
    main()
