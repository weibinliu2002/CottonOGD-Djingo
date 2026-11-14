#!/usr/bin/env python
"""
C 侧（tabix 文件层）注册脚本：为群体 VCF 建立 tabix 索引并登记到 variation_file 台账。

B 域 A+C 混合决策：逐样本基因型不进 MySQL，原始 VCF 经 bgzip+tabix 索引，
查询时后端调 tabix 取回。本脚本是"逐样本基因型导入方案"的执行部分：
  - 1913 泛基因组：final VCF 已自带 .tbi，仅登记台账
  - GWAS SNP/CNV：需先 tabix 建索引（bcftools/bgzip 已就绪），再登记

用法：
  # 仅登记已索引的 1913 泛基因组（--no-index）
  python scripts/import/register_variant_files.py --pan-dir <clean_vcf> --set-id 1

  # 为 GWAS VCF 建索引并登记
  python scripts/import/register_variant_files.py \
      --gwas-snp "/data/.../890.hmp.biallele.vcf .gz" --gwas-cnv /data/.../419.CNV.MAF0.05.vcf.gz \
      --snp-set-id 2 --cnv-set-id 3

  # 同时全做
  python scripts/import/register_variant_files.py \
      --pan-dir <clean_vcf> --set-id 1 \
      --gwas-snp "..." --gwas-cnv ... --snp-set-id 2 --cnv-set-id 3
"""
import argparse
import hashlib
import os
import subprocess
import sys
import django

sys.path.insert(0, "/data/web/CottonOGD/OGD/backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from CottonOGD.models import VariationFile  # noqa: E402


def md5_of(path, limit_mb=50):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        total = 0
        while True:
            chunk = fh.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            total += len(chunk)
            if total > limit_mb * 1024 * 1024:
                break
    return h.hexdigest()


def ensure_tabix(vcf_path):
    """若缺 .tbi 则建索引。返回是否就绪。"""
    tbi = vcf_path + ".tbi"
    if os.path.exists(tbi):
        return True
    print(f"[tabix] indexing {vcf_path} ...")
    # 尝试直接 tabix（要求 bgzip 格式）；若失败先 bgzip 转码
    try:
        subprocess.run(["tabix", "-p", "vcf", vcf_path], check=True, capture_output=True, timeout=600)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"[tabix] direct index failed ({e}); attempting bgzip recompress")
        bgz = vcf_path + ".bgz"
        try:
            subprocess.run(["bgzip", "-c", vcf_path], stdout=open(bgz, "wb"),
                           check=True, timeout=1200)
            os.replace(bgz, vcf_path)
            subprocess.run(["tabix", "-p", "vcf", vcf_path], check=True, timeout=600)
            return True
        except Exception as e2:
            print(f"[tabix] FAILED: {e2}")
            return False


def register(path, category, set_id=None, ref_genome=None, query_genome=None,
             pan_chrom=None, status="indexed", writable_copy=None):
    """登记一个 VCF 到 variation_file 台账。

    path: 源文件（可能为只读目录，仅作来源记录）。
    writable_copy: 可写目录中的副本（在此上建 tabix 索引；后台取 GT 读它）。
                   若提供则台账 path 记为 writable_copy（tabix 就绪、后端可读）。
    """
    src = path
    if not os.path.exists(src):
        print(f"[reg] SKIP missing: {src}")
        return
    # 在可写副本上建索引；无副本则用源文件（需可写）
    index_target = writable_copy or src
    if writable_copy and not os.path.exists(writable_copy):
        print(f"[reg] SKIP missing writable_copy: {writable_copy}")
        return
    tabix_ready = ensure_tabix(index_target)
    rel = index_target if os.path.isabs(index_target) else index_target
    vf, created = VariationFile.objects.update_or_create(
        path=rel,
        defaults={
            "category": category,
            "set_id": set_id,
            "ref_genome": ref_genome,
            "query_genome": query_genome,
            "tabix_ready": tabix_ready,
            "size": os.path.getsize(index_target),
            "md5": md5_of(index_target) if os.path.getsize(index_target) < 50 * 1024 * 1024 else None,
            "status": status if tabix_ready else "failed",
        },
    )
    print(f"[reg] {'NEW' if created else 'UPD'} path={rel} tabix={tabix_ready} set={set_id}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pan-dir", default=None, help="1913 clean_vcf 目录（final vcf 已索引）")
    ap.add_argument("--set-id", type=int, default=1)
    ap.add_argument("--gwas-snp", default=None)
    ap.add_argument("--gwas-cnv", default=None)
    ap.add_argument("--snp-set-id", type=int, default=2)
    ap.add_argument("--cnv-set-id", type=int, default=3)
    args = ap.parse_args()

    if args.pan_dir:
        import glob
        for f in sorted(glob.glob(os.path.join(args.pan_dir, "1913g.*.final.vcf.gz"))):
            chrom = os.path.basename(f).split(".")[1]
            register(f, category="pop_vcf", set_id=args.set_id, ref_genome=67,
                     pan_chrom=chrom)

    if args.gwas_snp:
        register(args.gwas_snp, category="pop_vcf", set_id=args.snp_set_id, ref_genome=67,
                 writable_copy="data/variant_vcf/gwas_snp_890.vcf.gz")
    if args.gwas_cnv:
        register(args.gwas_cnv, category="pop_vcf", set_id=args.cnv_set_id, ref_genome=67,
                 writable_copy="data/variant_vcf/gwas_cnv_419.vcf.gz")

    print("[reg] DONE")


if __name__ == "__main__":
    main()
