"""
变异数据 API：SyRI 结构变异（syri_sr / syri_seq）、群体 SNP/InDel 位点（variant）、
GWAS 性状/表型/标记。支持多种查询方式：按区间、染色体、类型、ID、样本/材料。

B 域 A+C 混合：
  - A 侧（MySQL）：位点主表查询 + 密度统计（variant / variant_density）
  - C 侧（tabix 文件层）：逐样本基因型经 tabix 实时取回（variant_genotype）

所有端点统一返回 JsonResponse，参数从 request.GET / request.POST 读取。
"""
import json
import logging
import os
import subprocess

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from CottonOGD.models import (
    GenomePair, SyriSR, SyriSeq, Variant, VariationSet, VariationFile,
    GwasTrait, GwasAccession, GwasPhenotype, GwasAssociation,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 辅助
# ----------------------------------------------------------------------
def _int_or_none(v):
    try:
        return int(v) if v not in (None, "", "null") else None
    except (ValueError, TypeError):
        return None


def _build_region_filter(qs, chrom, start, end, pos_field="pos"):
    if chrom:
        qs = qs.filter(chrom=chrom)
    if start is not None:
        qs = qs.filter(**{f"{pos_field}__gte": start})
    if end is not None:
        qs = qs.filter(**{f"{pos_field}__lte": end})
    return qs


# ----------------------------------------------------------------------
# 染色体命名映射（display A01/D13 ↔ VCF 内部 contig）
# ----------------------------------------------------------------------
# 三个数据集的 VCF 内部 contig 命名不同：
#   - 泛基因组 (set 1)：26 个分染色体文件，contig 统一编为 1..26（A01→1 … D13→26）
#   - GWAS SNP   (set 2)：单个文件，contig 为 GHIR_A01..GHIR_D13
#   - GWAS CNV   (set 3)：单个文件，contig 为 1..26（裸编号，同泛基因组）
def _display_to_vcf_contig(chrom, set_id):
    """display chrom（A01..A13/D01..D13）→ 该数据集 VCF 内部 contig 名。"""
    if not chrom:
        return chrom
    # 解析 A01 / D13
    sub = chrom[0].upper()
    num = chrom[1:]
    if set_id == 2:  # GWAS SNP：GHIR_A01
        return f"GHIR_{sub}{num}"
    # set 1 / set 3：裸编号 1..26
    n = int(num)
    offset = 0 if sub == "A" else 13
    return str(n + offset)


def _pan_file_for_chrom(vfs, chrom):
    """泛基因组 26 个分染色体文件，按文件名中的 A01/D01 匹配。"""
    sub, num = chrom[0].upper(), chrom[1:]
    target = f"1913g.{sub}{num}.final.vcf.gz"
    for vf in vfs:
        if os.path.basename(vf.path) == target:
            return vf
    return None


# ----------------------------------------------------------------------
# A 域：SyRI 成对结构变异
# ----------------------------------------------------------------------
@api_view(["GET", "POST"])
def syri_pairs(request):
    """列出所有 genome_pair（成对比较批次）。"""
    pairs = GenomePair.objects.values(
        "id", "ref_genome_id", "query_genome_id", "status",
        "syri_version", "created_at"
    ).order_by("id")
    return Response(list(pairs), status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
def syri_structural(request):
    """查询 SyRI 结构重排（syri_sr）。

    参数：pair_id（必需）| chrom | start | end | son_type（如 SYN/DUP/INV）| ref_genome_id
    返回：分页的结构重排事件 + 按类型统计。
    """
    pair_id = _int_or_none(request.GET.get("pair_id") or request.data.get("pair_id"))
    if not pair_id:
        # 允许用 ref/query 反查
        rg = _int_or_none(request.GET.get("ref_genome_id") or request.data.get("ref_genome_id"))
        qg = _int_or_none(request.GET.get("query_genome_id") or request.data.get("query_genome_id"))
        if rg and qg:
            pair = GenomePair.objects.filter(ref_genome_id=rg, query_genome_id=qg).first()
            pair_id = pair.id if pair else None
    if not pair_id:
        return Response({"error": "pair_id 或 (ref_genome_id,query_genome_id) 必需"},
                        status=status.HTTP_400_BAD_REQUEST)

    chrom = request.GET.get("chrom") or request.data.get("chrom")
    start = _int_or_none(request.GET.get("start") or request.data.get("start"))
    end = _int_or_none(request.GET.get("end") or request.data.get("end"))
    son_type = request.GET.get("son_type") or request.data.get("son_type")
    limit = min(_int_or_none(request.GET.get("limit") or request.data.get("limit")) or 500, 2000)

    qs = SyriSR.objects.filter(genome_pair_id=pair_id)
    if chrom:
        qs = qs.filter(ref_genome_chr=chrom)
    if son_type:
        qs = qs.filter(son_type=son_type)
    qs = _build_region_filter(qs, None, start, end, pos_field="ref_start")
    qs = qs.order_by("ref_genome_chr", "ref_start")[:limit]

    rows = list(qs.values())
    type_stat = list(SyriSR.objects.filter(genome_pair_id=pair_id)
                    .values("son_type").annotate(count=Count("id")).order_by("son_type"))
    return Response({"pair_id": pair_id, "count": len(rows), "type_stat": type_stat, "rows": rows},
                    status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
def syri_sequence(request):
    """查询 SyRI 序列级注释（syri_seq）：HDR/TDM/CPG/CPL。参数同 syri_structural。"""
    pair_id = _int_or_none(request.GET.get("pair_id") or request.data.get("pair_id"))
    if not pair_id:
        rg = _int_or_none(request.GET.get("ref_genome_id") or request.data.get("ref_genome_id"))
        qg = _int_or_none(request.GET.get("query_genome_id") or request.data.get("query_genome_id"))
        if rg and qg:
            pair = GenomePair.objects.filter(ref_genome_id=rg, query_genome_id=qg).first()
            pair_id = pair.id if pair else None
    if not pair_id:
        return Response({"error": "pair_id 或 (ref_genome_id,query_genome_id) 必需"},
                        status=status.HTTP_400_BAD_REQUEST)

    chrom = request.GET.get("chrom") or request.data.get("chrom")
    start = _int_or_none(request.GET.get("start") or request.data.get("start"))
    end = _int_or_none(request.GET.get("end") or request.data.get("end"))
    son_type = request.GET.get("son_type") or request.data.get("son_type")
    limit = min(_int_or_none(request.GET.get("limit") or request.data.get("limit")) or 500, 2000)

    qs = SyriSeq.objects.filter(genome_pair_id=pair_id)
    if chrom:
        qs = qs.filter(ref_genome_chr=chrom)
    if son_type:
        qs = qs.filter(son_type=son_type)
    qs = _build_region_filter(qs, None, start, end, pos_field="ref_start")
    qs = qs.order_by("ref_genome_chr", "ref_start")[:limit]

    rows = list(qs.values())
    type_stat = list(SyriSeq.objects.filter(genome_pair_id=pair_id)
                    .values("son_type").annotate(count=Count("id")).order_by("son_type"))
    return Response({"pair_id": pair_id, "count": len(rows), "type_stat": type_stat, "rows": rows},
                    status=status.HTTP_200_OK)


# ----------------------------------------------------------------------
# B 域：群体 SNP/InDel 位点（variant 主表，位点级查询）
# ----------------------------------------------------------------------
@api_view(["GET", "POST"])
def variant_sets(request):
    """列出所有 variation_set（群体数据集）。"""
    sets = VariationSet.objects.values("id", "name", "reference_genome", "caller", "sample_count")
    return Response(list(sets), status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
def variant_region(request):
    """按区间/染色体/类型查询群体变异位点（variant 主表）。

    参数：set_id（必需，群体数据集）| chrom | start | end | svtype(SNP/INDEL) | limit
    """
    set_id = _int_or_none(request.GET.get("set_id") or request.data.get("set_id"))
    if not set_id:
        return Response({"error": "set_id 必需"}, status=status.HTTP_400_BAD_REQUEST)
    chrom = request.GET.get("chrom") or request.data.get("chrom")
    start = _int_or_none(request.GET.get("start") or request.data.get("start"))
    end = _int_or_none(request.GET.get("end") or request.data.get("end"))
    svtype = request.GET.get("svtype") or request.data.get("svtype")
    limit = min(_int_or_none(request.GET.get("limit") or request.data.get("limit")) or 1000, 5000)

    qs = Variant.objects.filter(set_id=set_id)
    qs = _build_region_filter(qs, chrom, start, end, pos_field="pos")
    if svtype:
        qs = qs.filter(svtype=svtype)
    qs = qs.order_by("chrom", "pos")[:limit]

    rows = list(qs.values("id", "chrom", "pos", "end_pos", "svtype", "ref", "alt", "filter"))
    type_stat = list(Variant.objects.filter(set_id=set_id)
                    .values("svtype").annotate(count=Count("id")).order_by("svtype"))
    return Response({"set_id": set_id, "count": len(rows), "type_stat": type_stat, "rows": rows},
                    status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
def variant_by_id(request):
    """按 variant id 查询单一位点详情。"""
    vid = _int_or_none(request.GET.get("id") or request.data.get("id"))
    if not vid:
        return Response({"error": "id 必需"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        v = Variant.objects.get(id=vid)
    except ObjectDoesNotExist:
        return Response({"error": "variant not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response({
        "id": v.id, "set_id": v.set_id, "chrom": v.chrom, "pos": v.pos,
        "end_pos": v.end_pos, "svtype": v.svtype, "ref": v.ref, "alt": v.alt,
        "qual": v.qual, "filter": v.filter, "info_json": v.info_json,
    }, status=status.HTTP_200_OK)


# ----------------------------------------------------------------------
# C 域：GWAS 性状 / 表型 / 关联
# ----------------------------------------------------------------------
@api_view(["GET", "POST"])
def gwas_traits(request):
    """列出 GWAS 性状（FE/FL/FM/FS/FU）。"""
    traits = GwasTrait.objects.values("id", "code", "name", "unit", "description")
    return Response(list(traits), status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
def gwas_accessions(request):
    """列出 GWAS 材料（accession）。可选 species 过滤。"""
    species = request.GET.get("species") or request.data.get("species")
    qs = GwasAccession.objects.all()
    if species:
        qs = qs.filter(species=species)
    rows = list(qs.values("id", "name", "species", "population"))
    return Response(rows, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
def gwas_phenotype(request):
    """查询表型 BLUP 值。

    参数（任选其一）：
      - trait_code（如 FE）+ 全部材料 → 该性状分布
      - accession（材料名）→ 该材料所有性状
      - trait_code + accession → 单值
    """
    trait_code = request.GET.get("trait_code") or request.data.get("trait_code")
    accession = request.GET.get("accession") or request.data.get("accession")

    qs = GwasPhenotype.objects.select_related(None).all()
    joins = Q()
    if trait_code:
        t = GwasTrait.objects.filter(code=trait_code).first()
        if not t:
            return Response({"error": f"trait {trait_code} 不存在"}, status=status.HTTP_400_BAD_REQUEST)
        joins &= Q(trait_id=t.id)
    if accession:
        a = GwasAccession.objects.filter(name=accession).first()
        if not a:
            return Response({"error": f"accession {accession} 不存在"}, status=status.HTTP_400_BAD_REQUEST)
        joins &= Q(accession_id=a.id)
    qs = qs.filter(joins)

    rows = list(qs.values("accession_id", "trait_id", "value"))
    # 回填名称
    acc_map = {a.id: a.name for a in GwasAccession.objects.all()}
    trait_map = {t.id: t.code for t in GwasTrait.objects.all()}
    out = [{"accession": acc_map.get(r["accession_id"]),
            "trait": trait_map.get(r["trait_id"]),
            "value": r["value"]} for r in rows]
    return Response({"count": len(out), "rows": out}, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
def gwas_markers(request):
    """查询 GWAS 标记位点（variant 表中 gwas_* 数据集）。

    参数：set_id（gwas_snp_890 / gwas_cnv_419 的 id）| chrom | start | end | limit
    """
    set_id = _int_or_none(request.GET.get("set_id") or request.data.get("set_id"))
    if not set_id:
        return Response({"error": "set_id 必需"}, status=status.HTTP_400_BAD_REQUEST)
    chrom = request.GET.get("chrom") or request.data.get("chrom")
    start = _int_or_none(request.GET.get("start") or request.data.get("start"))
    end = _int_or_none(request.GET.get("end") or request.data.get("end"))
    limit = min(_int_or_none(request.GET.get("limit") or request.data.get("limit")) or 1000, 5000)

    qs = _build_region_filter(Variant.objects.filter(set_id=set_id), chrom, start, end, pos_field="pos")
    qs = qs.order_by("chrom", "pos")[:limit]
    rows = list(qs.values("id", "chrom", "pos", "svtype", "ref", "alt"))
    return Response({"set_id": set_id, "count": len(rows), "rows": rows}, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
def gwas_associations(request):
    """查询 GWAS 关联结果（gwas_association，当前为空，预留接口）。

    参数：trait_code | chrom | start | end | top_n（按 pvalue 取前 N）| threshold（pvalue<=）
    """
    trait_code = request.GET.get("trait_code") or request.data.get("trait_code")
    chrom = request.GET.get("chrom") or request.data.get("chrom")
    start = _int_or_none(request.GET.get("start") or request.data.get("start"))
    end = _int_or_none(request.GET.get("end") or request.data.get("end"))
    threshold = request.GET.get("threshold") or request.data.get("threshold")
    top_n = min(_int_or_none(request.GET.get("top_n") or request.data.get("top_n")) or 100, 1000)

    qs = GwasAssociation.objects.all()
    if trait_code:
        t = GwasTrait.objects.filter(code=trait_code).first()
        if t:
            qs = qs.filter(trait_id=t.id)
    qs = _build_region_filter(qs, chrom, start, end, pos_field="pos")
    if threshold:
        try:
            qs = qs.filter(pvalue__lte=float(threshold))
        except ValueError:
            pass
    qs = qs.order_by("pvalue")[:top_n]
    rows = list(qs.values())
    return Response({"count": len(rows), "rows": rows}, status=status.HTTP_200_OK)


# ----------------------------------------------------------------------
# B 域 A 侧：密度统计（variant 主表聚合，毫秒级，无需全表扫描）
# ----------------------------------------------------------------------
@api_view(["GET", "POST"])
def variant_density(request):
    """按等宽 bin 统计某区间的位点数分布（用于密度图 / JBrowse histogram）。

    参数：set_id（必需）| chrom | start | end | bins（默认 100，最大 1000）
    """
    set_id = _int_or_none(request.GET.get("set_id") or request.data.get("set_id"))
    if not set_id:
        return Response({"error": "set_id 必需"}, status=status.HTTP_400_BAD_REQUEST)
    chrom = request.GET.get("chrom") or request.data.get("chrom")
    start = _int_or_none(request.GET.get("start") or request.data.get("start"))
    end = _int_or_none(request.GET.get("end") or request.data.get("end"))
    bins = min(_int_or_none(request.GET.get("bins") or request.data.get("bins")) or 100, 1000)
    if not chrom or start is None or end is None:
        return Response({"error": "chrom / start / end 必需"},
                        status=status.HTTP_400_BAD_REQUEST)
    if end <= start:
        return Response({"error": "end 必须大于 start"}, status=status.HTTP_400_BAD_REQUEST)

    bin_size = (end - start + 1) / bins
    histogram = []
    total = 0
    from django.db import connection
    # 用 (set_id, chrom, pos) 索引做区间计数，逐 bin 范围聚合（毫秒级）
    for i in range(bins):
        b_start = start + int(i * bin_size)
        b_end = start + int((i + 1) * bin_size) - 1
        if i == bins - 1:
            b_end = end
        cnt = Variant.objects.filter(
            set_id=set_id, chrom=chrom, pos__gte=b_start, pos__lte=b_end
        ).count()
        total += cnt
        histogram.append({
            "bin": i, "start": b_start, "end": b_end, "count": cnt,
        })
    return Response({
        "set_id": set_id, "chrom": chrom, "start": start, "end": end,
        "bins": bins, "bin_size": round(bin_size, 2), "total": total,
        "histogram": histogram,
    }, status=status.HTTP_200_OK)


# ----------------------------------------------------------------------
# B 域 C 侧：逐样本基因型（tabix 文件层，不进 MySQL）
# ----------------------------------------------------------------------
@api_view(["GET", "POST"])
def variant_genotype(request):
    """经 tabix 从群体 VCF 取回区间/单点的逐样本基因型。

    A+C 混合决策：逐样本 GT 不进 MySQL，原始 VCF 经 bgzip+tabix 索引，
    后端调 tabix 按区间/位点取回，零入库成本。

    参数：set_id（必需）| chrom | start+end（区间）或 pos（单点）
          | samples（逗号分隔子集，可选）| format（默认 GT）
    返回：samples（样本列序）+ records（每位点 genotypes 字典）
    """
    set_id = _int_or_none(request.GET.get("set_id") or request.data.get("set_id"))
    if not set_id:
        return Response({"error": "set_id 必需"}, status=status.HTTP_400_BAD_REQUEST)
    chrom = request.GET.get("chrom") or request.data.get("chrom")
    start = _int_or_none(request.GET.get("start") or request.data.get("start"))
    end = _int_or_none(request.GET.get("end") or request.data.get("end"))
    pos = _int_or_none(request.GET.get("pos") or request.data.get("pos"))
    samples_arg = request.GET.get("samples") or request.data.get("samples")
    fmt = request.GET.get("format") or request.data.get("format") or "GT"

    if not chrom:
        return Response({"error": "chrom 必需"}, status=status.HTTP_400_BAD_REQUEST)
    if pos is not None:
        pass
    elif start is not None and end is not None:
        if end - start > 1_000_000:
            return Response({"error": "区间超过 1 Mb，请分块请求"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"error": "需提供 pos 或 start+end"}, status=status.HTTP_400_BAD_REQUEST)

    # display chrom → VCF 内部 contig
    vcf_chrom = _display_to_vcf_contig(chrom, set_id)

    # 从台账定位 VCF 文件（按 set_id + 染色体）
    vfs = list(VariationFile.objects.filter(set_id=set_id, tabix_ready=True))
    if set_id == 1:
        # 泛基因组：26 个分染色体文件，按文件名匹配
        vf = _pan_file_for_chrom(vfs, chrom)
    else:
        # GWAS SNP/CNV：每 set 单个文件
        vf = vfs[0] if vfs else None
    if not vf:
        return Response({"error": f"该数据集无 tabix 索引的 VCF（set_id={set_id}, chrom={chrom}）"},
                        status=status.HTTP_400_BAD_REQUEST)
    vcf_path = os.path.join(settings.BASE_DIR, vf.path) if not os.path.isabs(vf.path) else vf.path
    if not os.path.exists(vcf_path):
        return Response({"error": f"VCF 文件不存在: {vcf_path}"}, status=status.HTTP_404_NOT_FOUND)
    tbi = vcf_path + ".tbi"
    if not os.path.exists(tbi):
        return Response({"error": f"vcf not tabix-indexed: {vcf_path}"}, status=status.HTTP_400_BAD_REQUEST)

    # 构建 tabix region（用 VCF 内部 contig 名）
    if pos is not None:
        region = f"{vcf_chrom}:{pos}-{pos}"
    else:
        region = f"{vcf_chrom}:{start}-{end}"

    sample_filter = None
    if samples_arg:
        sample_filter = [s.strip() for s in samples_arg.split(",") if s.strip()]

    # 取样列顺序：tabix -H 仅返回 header 行（含 #CHROM），region 查询不含 header
    try:
        hdr = subprocess.run(
            ["tabix", "-H", vcf_path, region],
            capture_output=True, text=True, check=True, timeout=120,
        )
        header_samples = []
        for hl in hdr.stdout.split("\n"):
            if hl.startswith("#CHROM"):
                header_samples = hl.split("\t")[9:]
                break
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        header_samples = []

    try:
        result = subprocess.run(
            ["tabix", "-f", vcf_path, region],
            capture_output=True, text=True, check=True, timeout=120,
        )
        lines = result.stdout.strip().split("\n")
    except subprocess.CalledProcessError as e:
        return Response({"error": f"tabix 查询失败: {e.stderr[:200]}"},
                        status=status.HTTP_500_INTERNAL_ERROR)
    except subprocess.TimeoutExpired:
        return Response({"error": "tabix 查询超时"}, status=status.HTTP_500_INTERNAL_ERROR)

    records = []
    for line in lines:
        if not line:
            continue
        cols = line.split("\t")
        if cols[0].startswith("#CHROM"):
            header_samples = cols[9:]
            continue
        if cols[0].startswith("#"):
            continue
        v_chrom, v_pos, v_id, v_ref, v_alt = cols[0], cols[1], cols[2], cols[3], cols[4]
        # FORMAT 中 GT 的位置
        fmt_fields = cols[8].split(":")
        try:
            gt_idx = fmt_fields.index(fmt)
        except ValueError:
            gt_idx = 0 if "GT" in fmt_fields else None
        genotypes = {}
        for si, samp in enumerate(header_samples):
            if sample_filter and samp not in sample_filter:
                continue
            cell = cols[9 + si] if 9 + si < len(cols) else ""
            if gt_idx is not None:
                parts = cell.split(":")
                genotypes[samp] = parts[gt_idx] if gt_idx < len(parts) else cell
            else:
                genotypes[samp] = cell
        records.append({
            "chrom": chrom, "pos": int(v_pos), "id": v_id,
            "ref": v_ref, "alt": v_alt, "genotypes": genotypes,
        })

    out_samples = sample_filter if sample_filter else header_samples
    return Response({
        "set_id": set_id, "chrom": chrom,
        "start": pos if pos is not None else start,
        "end": pos if pos is not None else end,
        "samples": out_samples,
        "records": records,
    }, status=status.HTTP_200_OK)
