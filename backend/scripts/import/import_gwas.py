#!/usr/bin/env python
"""
导入 GWAS 数据：性状元数据 + 表型 BLUP 值 + GWAS 标记集（variant 位点主表）。

数据：
  - snp2/890Gh_Fiber_traits.txt      890 材料 × 5 纤维性状 (FE/FL/FM/FS/FU)
  - snp2/890.hmp.biallele.vcf(.gz)   890 份 SNP 标记 (229 万位点) —— 仅导位点主表
  - snp2/419.CNV.MAF0.05.vcf.gz      419 份 CNV 标记 (2.7 万位点) —— 仅导位点主表

说明：基因型 GT 格子（逐样本）体量 = 229万×890 ≈ 20 亿，与泛基因组同量级，
需按方案 A/B/C 决策后再导；本脚本只落"位点主表" + 性状/表型。
GWAS 标记按各自 variation_set 进入 variant 表（chrom 前缀映射同泛基因组）。

用法：
  python scripts/import/import_gwas.py \
      --traits <890Gh_Fiber_traits.txt> \
      --snp-vcf <890.hmp.biallele.vcf(.gz)> \
      --cnv-vcf <419.CNV.MAF0.05.vcf.gz> \
      --ref-id 67 [--dry-run]
"""
import argparse
import gzip
import os
import sys
import django

sys.path.insert(0, "/data/web/CottonOGD/OGD/backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from CottonOGD.models import (  # noqa: E402
    GwasTrait, GwasAccession, GwasPhenotype, VariationSet, Variant,
)

TRAIT_NAMES = {
    "FE": ("Fiber elongation", "%"),
    "FL": ("Fiber length", "mm"),
    "FM": ("Fiber micronaire", "μg/inch"),
    "FS": ("Fiber strength", "cN/tex"),
    "FU": ("Fiber uniformity", "%"),
}


def open_any(fname):
    return gzip.open(fname, "rt", encoding="utf-8", errors="replace") if fname.endswith(".gz") \
        else open(fname, "rt", encoding="utf-8", errors="replace")


def load_traits(traits_path):
    with open(traits_path, "r", encoding="utf-8", errors="replace") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        # header: <Trait> FE FL FM FS FU
        trait_codes = [h for h in header if h != "<Trait>"]
        for code in trait_codes:
            name, unit = TRAIT_NAMES.get(code, (code, None))
            GwasTrait.objects.update_or_create(code=code, defaults={"name": name, "unit": unit})
        # 表型行
        batch = []
        acc_ids = {}
        for line in fh:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < len(trait_codes) + 1:
                continue
            acc_name = cols[0]
            acc, _ = GwasAccession.objects.update_or_create(name=acc_name, defaults={"species": "G. hirsutum"})
            acc_ids[acc_name] = acc.id
            for i, code in enumerate(trait_codes, start=1):
                val = cols[i]
                if val in ("", ".", "NA"):
                    continue
                try:
                    v = float(val)
                except ValueError:
                    continue
                trait = GwasTrait.objects.get(code=code)
                batch.append(GwasPhenotype(accession_id=acc.id, trait_id=trait.id, value=v))
        GwasPhenotype.objects.bulk_create(batch, batch_size=5000, ignore_conflicts=True)
    return len(trait_codes), len(batch)


def load_marker_vcf(vcf_path, set_name, ref_id, sample_count, dry_run=False):
    open_fn = open_any(vcf_path)
    n = 0
    rows = []
    vset = None
    chrom_seen = set()
    with open_fn as fh:
        for line in fh:
            if line.startswith("##"):
                continue
            if line.startswith("#CHROM"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 5:
                continue
            chrom_raw, pos, vid, ref, alt = cols[0], cols[1], cols[2], cols[3], cols[4]
            try:
                pos_i = int(pos)
            except ValueError:
                continue
            # 染色体映射：GWAS VCF 用 GHIR_A01 或 A01 —— 取末段数字映射到 A/D
            import re
            m = re.search(r"([AD])(\d+)$", chrom_raw)
            if m:
                chrom = f"{m.group(1)}{int(m.group(2)):02d}"
            else:
                chrom = chrom_raw
            if not dry_run:
                if vset is None:
                    vset, _ = VariationSet.objects.update_or_create(
                        name=set_name, defaults={"reference_genome": ref_id,
                                                  "caller": "GWAS marker", "sample_count": sample_count})
                    # 幂等：清空该标记集已有位点，避免重导重复
                    Variant.objects.filter(set_id=vset.id).delete()
                rows.append(Variant(
                    set_id=vset.id, chrom=chrom, pos=pos_i,
                    svtype="SNP" if len(ref) == 1 and len(alt) == 1 else "INDEL",
                    ref=ref if len(ref) <= 4 else None,
                    alt=alt if len(alt) <= 4 else alt,
                ))
                n += 1
                if len(rows) >= 50000:
                    Variant.objects.bulk_create(rows, batch_size=50000)
                    rows = []
            else:
                n += 1
    if not dry_run and rows:
        Variant.objects.bulk_create(rows, batch_size=50000)
    return n, vset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traits", required=True)
    ap.add_argument("--snp-vcf", required=True)
    ap.add_argument("--cnv-vcf", required=True)
    ap.add_argument("--ref-id", type=int, default=67)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    n_traits, n_pheno = load_traits(args.traits)
    print(f"[gwas] traits={n_traits} phenotype_cells={n_pheno}")

    if args.dry_run:
        sn, _ = load_marker_vcf(args.snp_vcf, "gwas_snp_890", args.ref_id, 890, dry_run=True)
        cn, _ = load_marker_vcf(args.cnv_vcf, "gwas_cnv_419", args.ref_id, 419, dry_run=True)
        print(f"[gwas] dry-run SNP sites={sn} CNV sites={cn}")
        return

    sn, v1 = load_marker_vcf(args.snp_vcf, "gwas_snp_890", args.ref_id, 890)
    print(f"[gwas] SNP markers={sn} set_id={v1.id if v1 else None}")
    cn, v2 = load_marker_vcf(args.cnv_vcf, "gwas_cnv_419", args.ref_id, 419)
    print(f"[gwas] CNV markers={cn} set_id={v2.id if v2 else None}")
    print("[gwas] DONE")


if __name__ == "__main__":
    main()
