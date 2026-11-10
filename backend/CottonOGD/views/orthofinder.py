"""
OrthoFinder 直系同源（Ortholog）查询接口。

数据：MySQL 表 orthofinder_og_gene / orthofinder_orthogroup（由 build_orthofinder_index 构建）。
基因 id 即 TranscriptMaster.transcriptid；查询时按需 join 到 GeneMaster 以链接既有基因详情页。

一对一 / 一对多 / 多对多 由每个物种在 OG 内的成员数实时判定，不落表。

按需单文件读取（MSA / 序列 / 基因树 / WGS）零全量加载，文件不存在返回裸 404（前端静默降级）。
基因重复事件（tandem / wgd 端点）实时解析 Gene_Duplication_Events/Duplications.tsv。
"""
from __future__ import annotations

import os
import re
import json

from django.conf import settings
from django.db.models import Count
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from CottonOGD.models import (
    Species_info, TranscriptMaster, GeneMaster,
    OrthofinderOrthogroup, OrthofinderOgGene,
)

logger = __import__('logging').getLogger(__name__)

# OrthoFinder transcript id 末尾 .\d 版本号（如 Gano_01G009710.1）
_VERSION_RE = re.compile(r'\.\d+$')


def _strip_version(gid: str) -> str:
    return _VERSION_RE.sub('', gid) if gid else gid


def _clean_dup_gene(raw: str, species_node: str = '') -> str:
    """Duplications.tsv 的基因列形如 <SpeciesWithUnderscores>_<GeneidWithUnderscores>
    （逗号聚合多个基因）。去掉已知 Species 前缀（注意 species 名里的 . 在基因列里是 _），
    再把基因部分内部的 _ 还原为 .（版本号）。"""
    raw = raw.strip()
    if species_node:
        prefix = species_node.replace('.', '_') + '_'
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    # 其余下划线视为版本号分隔（如 Gano_07G007520.1）
    return raw.replace('_', '.')


def _resolve_genemaster(species_name: str, geneids: list[str]) -> dict[str, str]:
    """
    把一组 OrthoFinder geneid 解析为 GeneMaster.geneid（通过 TranscriptMaster）。
    返回 {ortho_geneid: genemaster_geneid|None}。
    仅命中 TranscriptMaster.transcriptid（含去版本）的才给值，未命中留 None。
    """
    out: dict[str, str] = {}
    species = Species_info.objects.filter(name=species_name).first()
    if species is None:
        for g in geneids:
            out[g] = None
        return out
    bases = {_strip_version(g): g for g in geneids}
    trs = list(
        TranscriptMaster.objects.filter(genome=species)
        .filter(transcriptid__in=list(geneids) + list(bases.keys()))
        .values('transcriptid', 'id_id')
    )
    # transcriptid -> genemaster_id
    tr_to_gm: dict[str, int] = {}
    for tr in trs:
        tr_to_gm[tr['transcriptid']] = tr['id_id']
    gm_ids = {tr['id_id'] for tr in trs}
    gm_map = dict(GeneMaster.objects.filter(id__in=gm_ids).values_list('id', 'geneid'))
    for g in geneids:
        gid_pk = tr_to_gm.get(g) or tr_to_gm.get(_strip_version(g))
        out[g] = gm_map.get(gid_pk) if gid_pk else None
    return out


def _build_species_members(og_code: str) -> tuple[list[dict], int]:
    """
    返回某 OG 跨物种成员（含 genemaster 解析）与物种数。
    每行：{species, display_name, genes:[{ortho_gene, genemaster_geneid}], n}
    relation 判定留给前端（依据每个 species 的 n）。
    """
    rows = list(
        OrthofinderOgGene.objects.filter(og_code=og_code)
        .values('species', 'geneid')
    )
    by_species: dict[str, list[str]] = {}
    for r in rows:
        by_species.setdefault(r['species'], []).append(r['geneid'])

    # 批量解析 genemaster（按物种分批，避免 N+1）
    members: list[dict] = []
    sp_names = set(by_species.keys())
    disp = dict(Species_info.objects.filter(name__in=sp_names)
                .values_list('name', 'alias'))
    for species in sorted(by_species, key=lambda s: -len(by_species[s])):
        geneids = by_species[species]
        gm_map = _resolve_genemaster(species, geneids)
        members.append({
            'species': species,
            'display_name': disp.get(species) or species,
            'n': len(geneids),
            'genes': [
                {'ortho_gene': g, 'genemaster_geneid': gm_map.get(g)}
                for g in geneids
            ],
        })
    return members, len(by_species)


def _relation_type(members: list[dict]) -> str:
    """
    依据物种成员数粗略判定主关系类型：
      one_to_one / one_to_many / many_to_one / many_to_many / single。
    """
    present = [m['n'] for m in members]
    if not present:
        return 'none'
    if all(n == 1 for n in present):
        return 'one_to_one'
    if len(present) == 2:
        a, b = present
        if a == 1 and b > 1:
            return 'many_to_one'   # 查询物种视角：对方多个
        if a > 1 and b == 1:
            return 'one_to_many'
        return 'many_to_many'
    # 多物种：只要有任一 >1 视为 many_to_many，否则 one_to_one
    return 'many_to_many' if any(n > 1 for n in present) else 'one_to_one'


@api_view(['POST'])
def ortholog_gene(request):
    """基因 -> 所属 OG -> 跨物种直系同源。"""
    geneid = (request.data.get('geneid') or request.query_params.get('geneid') or '').strip()
    if not geneid:
        return Response({'error': 'geneid is required'}, status=status.HTTP_400_BAD_REQUEST)

    candidates = {geneid, _strip_version(geneid)}
    og_rows = list(
        OrthofinderOgGene.objects.filter(geneid__in=candidates)
        .values_list('og_code', flat=True).distinct()
    )
    if not og_rows:
        return Response({
            'query_gene': geneid,
            'found': False,
            'orthogroups': [],
        }, status=status.HTTP_200_OK)

    orthogroups = []
    for og_code in og_rows:
        members, n_sp = _build_species_members(og_code)
        og_meta = OrthofinderOrthogroup.objects.filter(og_code=og_code).first()
        orthogroups.append({
            'og_code': og_code,
            'species_count': n_sp,
            'gene_count': og_meta.gene_count if og_meta else sum(m['n'] for m in members),
            'is_single_copy': og_meta.is_single_copy if og_meta else False,
            'relation_type': _relation_type(members),
            'species_members': members,
        })

    return Response({
        'query_gene': geneid,
        'found': True,
        'orthogroups': orthogroups,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def orthogroup_detail(request):
    """OG -> 全部跨物种成员。"""
    og_code = (request.data.get('og_code') or request.query_params.get('og_code') or '').strip()
    if not og_code:
        return Response({'error': 'og_code is required'}, status=status.HTTP_400_BAD_REQUEST)

    og_meta = OrthofinderOrthogroup.objects.filter(og_code=og_code).first()
    if og_meta is None:
        return Response({'found': False, 'og_code': og_code}, status=status.HTTP_200_OK)

    members, n_sp = _build_species_members(og_code)
    return Response({
        'found': True,
        'og_code': og_code,
        'species_count': n_sp,
        'gene_count': og_meta.gene_count,
        'is_single_copy': og_meta.is_single_copy,
        'relation_type': _relation_type(members),
        'species_members': members,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def orthogroups_by_species(request):
    """
    从物种筛选 OG。
    入参：species: [名称...], mode: 'all'|'any' (默认 all),
          limit (默认 50), offset (默认 0)。
    """
    species = request.data.get('species') or request.query_params.getlist('species') or []
    if isinstance(species, str):
        species = [s.strip() for s in re.split(r'[,|]', species) if s.strip()]
    if not species:
        return Response({'error': 'species list is required'}, status=status.HTTP_400_BAD_REQUEST)
    mode = (request.data.get('mode') or request.query_params.get('mode') or 'all').strip().lower()
    try:
        limit = int(request.data.get('limit') or request.query_params.get('limit') or 50)
        offset = int(request.data.get('offset') or request.query_params.get('offset') or 0)
    except (TypeError, ValueError):
        return Response({'error': 'limit/offset must be integers'},
                        status=status.HTTP_400_BAD_REQUEST)
    limit = max(1, min(limit, 500))

    known = set(Species_info.objects.filter(name__in=species).values_list('name', flat=True))
    if not known:
        return Response({'found': False, 'species': species, 'orthogroups': [],
                        'total': 0}, status=status.HTTP_200_OK)

    qs = (
        OrthofinderOgGene.objects.filter(species__in=known)
        .values('og_code')
        .annotate(n_sp=Count('species', distinct=True))
    )
    if mode == 'all':
        qs = qs.filter(n_sp=len(known))
    total = qs.count()

    page = qs.order_by('-n_sp', 'og_code')[offset:offset + limit]
    og_codes = [r['og_code'] for r in page]

    meta_map = {
        o.og_code: o for o in
        OrthofinderOrthogroup.objects.filter(og_code__in=og_codes)
    }
    results = []
    for og_code in og_codes:
        o = meta_map.get(og_code)
        results.append({
            'og_code': og_code,
            'species_count': o.species_count if o else len(known),
            'gene_count': o.gene_count if o else None,
            'is_single_copy': o.is_single_copy if o else False,
        })

    return Response({
        'found': True,
        'mode': mode,
        'species': list(known),
        'total': total,
        'limit': limit,
        'offset': offset,
        'orthogroups': results,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def orthofinder_meta(request):
    """物种列表（来自 Species_info，复用显示名/类别），供前端下拉筛选。"""
    rows = list(
        Species_info.objects.filter(name__in=settings_orthofinder_species())
        .values('name', 'alias', 'Cotton_Species', 'Genome_type', 'Category')
        .order_by('name')
    )
    return Response({'species': rows}, status=status.HTTP_200_OK)


def settings_orthofinder_species():
    """返回已导入索引的物种集合（取 og_gene 中出现过的 species）。"""
    return set(OrthofinderOgGene.objects.values_list('species', flat=True).distinct())


# ---------- 按需单文件读取（序列 / 基因树 / MSA / WGS） ----------
@api_view(['GET'])
def orthofinder_sequence(request, og_code):
    """按 OG id 读取单个 Orthogroup_Sequences/<og>.fa（零全量加载）。"""
    return _serve_orthofinder_file(
        request, og_code, subdir='Orthogroup_Sequences', ext='.fa',
        content_type='text/plain; charset=utf-8')


@api_view(['GET'])
def orthofinder_tree(request, og_code):
    """按 OG id 读取单个 Resolved_Gene_Trees/<og>.treefile（newick）。"""
    return _serve_orthofinder_file(
        request, og_code, subdir='Resolved_Gene_Trees', ext='.treefile',
        content_type='text/plain; charset=utf-8')


@api_view(['GET'])
def orthofinder_msa(request, og_code):
    """MSA（多序列比对）：读取 MultipleSequenceAlignments/<og>.fa（FASTA，纯文本）。未就绪 404。"""
    return _serve_orthofinder_file(
        request, og_code, subdir='MultipleSequenceAlignments', ext='.fa',
        content_type='text/plain; charset=utf-8')


@api_view(['GET'])
def orthofinder_wgs(request, og_code):
    """
    WGS（全基因组区块 / 比对数据）：读取 <results>/WGS/<og>.*。
    OrthoFinder 标准结果不含 WGS 区块数据，文件缺失时返回裸 404，前端静默降级。
    """
    results_dir = getattr(settings, 'ORTHOFINDER_RESULTS_DIR', None)
    if not results_dir:
        return Response(status=status.HTTP_404_NOT_FOUND)
    base = os.path.join(os.path.abspath(results_dir), 'WGS', og_code)
    for ext in ('.fa', '.fasta', '.bed', '.txt', '.tsv'):
        path = base + ext
        if os.path.isfile(path):
            from django.http import FileResponse
            return FileResponse(open(path, 'rb'),
                               content_type='text/plain; charset=utf-8',
                               filename=f'{og_code}{ext}')
    return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def orthofinder_tandem(request, og_code):
    """
    基因重复事件（基于 Gene_Duplication_Events/Duplications.tsv 实时解析）。

    OrthoFinder 不输出「串联重复」专门数据，但产出更全面的全基因组/片段/末端重复事件。
    本端点把这些事件按 OG 下发，供前端在进化树/表格中展示重复类型与涉及基因簇。

    成功（200）返回 JSON：
    {
      "og_code": "OG0000001",
      "events": [
        {"species": "G.anomalumB1_HAU_v1", "type": "Terminal",
         "support": 1.0, "gene_tree_node": "n2642",
         "genes1": ["Gano_09G024420.1"], "genes2": ["Gano_09G025120.1"]},
        ...
      ]
    }
    若 OG 无重复事件或无 Duplications.tsv，返回空对象 {}（前端显示「暂未就绪」）。
    """
    results_dir = getattr(settings, 'ORTHOFINDER_RESULTS_DIR', None)
    if not results_dir:
        return Response({}, status=status.HTTP_200_OK)
    dup_tsv = os.path.join(os.path.abspath(results_dir),
                          'Gene_Duplication_Events', 'Duplications.tsv')
    if not os.path.isfile(dup_tsv):
        return Response({}, status=status.HTTP_200_OK)

    events = []
    try:
        with open(dup_tsv, 'r', encoding='utf-8') as fh:
            header = fh.readline()  # 跳过表头
            for line in fh:
                if not line.strip():
                    continue
                parts = line.rstrip('\n').split('\t')
                if len(parts) < 7 or parts[0] != og_code:
                    continue
                # Orthogroup, Species Node, Gene Tree Node, Support, Type, Genes1, Genes2
                _, species_node, gene_node, support, dtype, g1, g2 = parts[:7]
                species_short = species_node.split('_')[0] if species_node else ''
                events.append({
                    'species': species_node,
                    'species_short': species_short,
                    'type': dtype,
                    'support': float(support) if support else None,
                    'gene_tree_node': gene_node,
                    'genes1': [_clean_dup_gene(g, species_node) for g in g1.split(',') if g.strip()],
                    'genes2': [_clean_dup_gene(g, species_node) for g in g2.split(',') if g.strip()],
                })
    except OSError:
        return Response({}, status=status.HTTP_200_OK)

    return Response({'og_code': og_code, 'events': events},
                    status=status.HTTP_200_OK)


@api_view(['GET'])
def orthofinder_wgd(request, og_code):
    """
    该 OG 的重复事件汇总（按类型/物种计数），便于前端渲染重复类型徽标或小图。

    成功（200）返回 JSON：
    {
      "og_code": "OG0000001",
      "total": 12,
      "by_type": {"Terminal": 8, "Non-Terminal": 3, "Non-Terminal: STRIDE": 1},
      "by_species": {"G.anomalumB1_HAU_v1": 5, ...}
    }
    无数据时返回空对象 {}（前端显示「暂未就绪」）。
    """
    results_dir = getattr(settings, 'ORTHOFINDER_RESULTS_DIR', None)
    if not results_dir:
        return Response({}, status=status.HTTP_200_OK)
    dup_tsv = os.path.join(os.path.abspath(results_dir),
                          'Gene_Duplication_Events', 'Duplications.tsv')
    if not os.path.isfile(dup_tsv):
        return Response({}, status=status.HTTP_200_OK)

    by_type: dict[str, int] = {}
    by_species: dict[str, int] = {}
    total = 0
    try:
        with open(dup_tsv, 'r', encoding='utf-8') as fh:
            fh.readline()  # 表头
            for line in fh:
                if not line.strip():
                    continue
                parts = line.rstrip('\n').split('\t')
                if len(parts) < 5 or parts[0] != og_code:
                    continue
                species_node, _, _, _, dtype = parts[:5]
                total += 1
                by_type[dtype] = by_type.get(dtype, 0) + 1
                by_species[species_node] = by_species.get(species_node, 0) + 1
    except OSError:
        return Response({}, status=status.HTTP_200_OK)

    return Response({
        'og_code': og_code,
        'total': total,
        'by_type': by_type,
        'by_species': by_species,
    }, status=status.HTTP_200_OK)


def _serve_orthofinder_file(request, og_code, subdir, ext, content_type):
    """按需读取单个 OG 文件（MSA/序列/基因树）。文件不存在返回裸 404（前端静默降级）。"""
    results_dir = getattr(settings, 'ORTHOFINDER_RESULTS_DIR', None)
    if not results_dir:
        return Response(status=status.HTTP_404_NOT_FOUND)
    path = os.path.join(os.path.abspath(results_dir), subdir, f'{og_code}{ext}')
    if not os.path.isfile(path):
        return Response(status=status.HTTP_404_NOT_FOUND)
    from django.http import FileResponse
    return FileResponse(open(path, 'rb'), content_type=content_type,
                        filename=f'{og_code}{ext}')
