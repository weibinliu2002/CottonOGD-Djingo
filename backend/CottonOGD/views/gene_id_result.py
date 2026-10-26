from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from django.db.models import Q
from CottonOGD.server.annotation_search import get_annotation
from CottonOGD.server.Go_kegg_saearch import go_annotation, kegg_annotation
from CottonOGD.server.seq_fetch import fetch_by_id, fetch_region
from CottonOGD.views.Meilisearch import search_genes, normalize_gene_query
from CottonOGD.models import gene_annotation, gene_info, gene_seq, gene_go, gene_kegg, Species_info, GeneMaster
import logging
import re

logger = logging.getLogger(__name__)

# 多个 gene_id 的分隔符（逗号/竖线/换行/空格，兼容前端 URL 中 '+' 解码为空格）
_ID_SPLIT_RE = re.compile(r'[,|\s]+')


def build_jbrowse_url(seqid: str, start: int, end: int, genome_name: int) -> str:
    """生成 JBrowse 3.6.5 单基因视图 URL"""
    gff_name = 'GFF'
    genome_name = Species_info.objects.get(id=genome_name).name
    loc = f"{seqid}:{max(0, start-1000)}-{end+1000}"
    return f"/assets/jbrowse/index.html?config=data/{genome_name}/config.json&assembly={genome_name}&loc={loc}&tracks={gff_name}"


def _split_ids(raw):
    """按逗号/竖线/换行拆分多个基因 ID（与 Id_map 的输入约定一致）。"""
    return [part.strip() for part in _ID_SPLIT_RE.split(str(raw or '')) if part.strip()]


def _geneid_matches(hit_geneid, input_id) -> bool:
    """
    判断命中的 geneid 是否与输入 ID 精确对应。

    只容忍两类等价形式（Meilisearch 大小写不敏感，Python 比较需自行处理）：
      - 大小写差异：ghir_a01g000290 == Ghir_A01G000290
      - 输入带版本/转录本后缀：Ghir_A01G000290.1 / .t1 / .1_cds_1 → Ghir_A01G000290
    其余一律视为模糊噪声（Ghir_A01G013980 不匹配 Ghir_A01G000290）。
    """
    if not hit_geneid or not input_id:
        return False
    hit = str(hit_geneid).strip().lower()
    raw = str(input_id).strip().lower()
    if not hit or not raw:
        return False
    if raw == hit:
        return True
    # 仅允许「输入更长、且紧跟分隔符」的形态；
    # 避免把部分 ID（Ghir_A01G00029）扩散成全 ID（Ghir_A01G000290）
    return (len(raw) > len(hit) and raw.startswith(hit)
            and raw[len(hit)] in '._-')


def _dedupe(values):
    """去重并保持顺序。"""
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _exact_db_ids(hits, input_ids, genome_id):
    """
    从 Meilisearch 命中中只保留与输入 ID 精确对应的 db_id。

    Meilisearch 是模糊检索：查询 Ghir_A01G000290 时命中列表里会连带返回
    同基因组的无关基因（Ghir_A01G013980 等）。若直接采信全部 hit 作为
    db_id，后续按 id_id__in 取注释就会返回上百个基因、数千行无关数据。
    """
    matched = []
    for hit in hits:
        if hit.get('id') is None:
            continue
        # 转录本兜底由精确 transcriptid 查询得到，直接采信
        if hit.get('match_type') == 'transcript':
            matched.append(hit['id'])
            continue
        if any(_geneid_matches(hit.get('geneid'), gid) for gid in input_ids):
            matched.append(hit['id'])
    return _dedupe(matched)


def _db_fallback(input_ids, genome_id):
    """
    Meilisearch 无精确命中时的 MySQL 兜底。

    索引可能缺少部分基因组：实测 G.hirsutumAD1_TM-1_HAU_v1 在 GeneMaster 有
    70199 条，但 genemaster 索引里 0 命中，只走 Meilisearch 会把有效基因误判为
    「无法解析」。此处直接按 (genome_id, geneid) 精确查库。
    """
    query = Q()
    for gid in input_ids:
        for candidate in {gid, normalize_gene_query(gid)} - {''}:
            query |= Q(geneid__iexact=candidate)
    if not query:
        return []
    qs = GeneMaster.objects.filter(query)
    if genome_id:
        qs = qs.filter(genome_id=genome_id)
    return _dedupe(list(qs.values_list('id', flat=True)[:100]))


def resolve_input_ids(raw_gene_id, genome_id=None):
    """
    公共解析入口（脱离 request）：raw_gene_id 支持单 ID 或逗号/竖线/换行分隔多 ID。

    优先 Meilisearch（仅采信精确命中），无精确命中回退 MySQL（覆盖索引未同步的基因组）。
    GO/KEGG annotation、enrichment、primer_design 等视图共用。
    返回 db_id 列表（可能为空）。
    """
    genome_id = (genome_id or '').strip()
    input_ids = _split_ids(raw_gene_id)
    if not input_ids:
        return []

    db_ids = []
    for gid in input_ids:
        result = search_genes(gid, limit=100, offset=0, genome_id=genome_id or None)
        matched = _exact_db_ids(result['results'], [gid], genome_id)
        if not matched:
            matched = _db_fallback([gid], genome_id)
            logger.warning(
                f"resolve_input_ids: Meilisearch 无精确命中，已回退 MySQL gene_id={gid!r} "
                f"genome_id={genome_id!r} search_err={result['error']} "
                f"meili_top={[(h['geneid'], h['genome_id']) for h in result['results'][:5]]} "
                f"db_fallback_hits={len(matched)}")
        db_ids.extend(matched)

    return _dedupe(db_ids)


def resolve_db_ids(request):
    """
    解析请求中的 db_id；未提供时用 gene_id（+ 可选 genome_id）解析。
    支持逗号/竖线/换行分隔的多个 gene_id。
    返回 db_id 列表（可能为空）。
    """
    db_id = (request.data.get('db_id') or request.query_params.get('db_id'))
    if db_id:
        if isinstance(db_id, list):
            return list(db_id)
        try:
            return [int(float(db_id))]
        except (ValueError, TypeError):
            return [db_id] if str(db_id).strip() else []

    raw_gene_id = (request.data.get('gene_id') or request.query_params.get('gene_id') or '')
    genome_id = (request.data.get('genome_id') or request.query_params.get('genome_id') or '')

    input_ids = _split_ids(raw_gene_id)
    if not input_ids:
        logger.warning(f"resolve_db_ids: no usable gene_id, genome_id={genome_id!r} "
                       f"request.data={dict(request.data)} query={request.META.get('QUERY_STRING', '')}")
        return []

    return resolve_input_ids(raw_gene_id, genome_id)


def parse_mrna_ids(attributes: str):
    """从 GFF attributes 提取 ID=（即转录本 ID）；解析失败返回空列表。"""
    if not attributes:
        return []
    for field in attributes.split(';'):
        key, _, value = field.partition('=')
        if key.strip() == 'ID' and value.strip():
            return [value.strip()]
    return []


def get_transcript_seq(genome_name: str, tr_id: str, gene_type: str, db_fallback):
    """文件优先提取转录本序列，失败回退 gene_seq 表（备用数据，保留未删）。"""
    seq = fetch_by_id(genome_name, gene_type, tr_id)
    if seq is not None:
        return seq
    row = db_fallback.filter(mrna_id=tr_id, gene_type=gene_type).first()
    return row.sequence if row else ''


@api_view(['POST'])
def geneid_summary(request):
    db_ids = resolve_db_ids(request)
    if not db_ids:
        return Response({'error': 'db_id or (gene_id and genome_id) resolvable via search is required'},
                        status=status.HTTP_400_BAD_REQUEST)

    # 使用 db_id 过滤基因注释
    gene_annotation_result = get_annotation(db_ids)

    # 获取基因信息
    gene_info_queryset = gene_info.objects.filter(id_id__in=db_ids).values(
        'id', 'id_id', 'seqid', 'source', 'type', 'start', 'end', 'strand',
        'phase', 'value', 'attributes', 'genome'
    )
    gene_info_result = list(gene_info_queryset)

    # 获取相关物种名称并替换（只查询需要的物种）
    genome_ids = set(item['genome'] for item in gene_info_result if item.get('genome'))
    if genome_ids:
        species_map = {sp.id: sp.name for sp in Species_info.objects.filter(id__in=genome_ids)}
        for item in gene_info_result:
            if item.get('genome') in species_map:
                item['genome'] = species_map[item['genome']]

    # 获取GO和KEGG注释数据
    gene_go_result = gene_go.objects.filter(id_id__in=db_ids).values()
    gene_kegg_result = gene_kegg.objects.filter(id_id__in=db_ids).values()

    return Response({'geneid_result': list(gene_annotation_result),
                     'gene_info_result': gene_info_result,
                     'gene_go_result': list(gene_go_result),
                     'gene_kegg_result': list(gene_kegg_result),
                     }, status=status.HTTP_200_OK)


@api_view(['POST'])
def geneid_result(request):
    db_ids = resolve_db_ids(request)
    if not db_ids:
        return Response({'error': 'db_id or (gene_id and genome_id) resolvable via search is required'},
                        status=status.HTTP_400_BAD_REQUEST)

    gene_annotation_result = get_annotation(db_ids)
    gene_info_result = gene_info.objects.filter(id_id__in=db_ids)
    genome_seq_result = gene_seq.objects.filter(id_id__in=db_ids)  # 备用回退数据源
    gene_go_result = go_annotation(db_ids)
    gene_kegg_result = kegg_annotation(db_ids)

    # 构建 JBrowse URL（如果有基因信息）
    jbrowse_url = None
    seqid, start, end, IDs, genome_name = '', 0, 0, '', ''
    gene = gene_info_result.filter(type='gene').first()
    if gene:
        seqid = gene.seqid or ''
        start = gene.start or 0
        end = gene.end or 0
        gene_master = GeneMaster.objects.filter(id=db_ids[0]).first()
        IDs = gene_master.geneid if gene_master else ''
        genome_name = gene.genome.name if gene.genome else ''
        jbrowse_url = build_jbrowse_url(seqid, start, end, gene.genome_id)

    # 每个转录本的六类序列：产物文件优先，gene_seq 表回退
    mrna_transcript_result = []
    for item in gene_info_result.filter(type='mRNA'):
        tr_ids = parse_mrna_ids(item.attributes)
        for tr_id in tr_ids:
            mrna_transcript_result.append({
                'id': tr_id,
                'cdna_seq': get_transcript_seq(genome_name, tr_id, 'cdna', genome_seq_result),
                'cds_seq': get_transcript_seq(genome_name, tr_id, 'cds', genome_seq_result),
                'downstream_seq': get_transcript_seq(genome_name, tr_id, 'downstream', genome_seq_result),
                'mrna_seq': get_transcript_seq(genome_name, tr_id, 'mrna', genome_seq_result),
                'protein_seq': get_transcript_seq(genome_name, tr_id, 'pro', genome_seq_result),
                'upstream_seq': get_transcript_seq(genome_name, tr_id, 'upstream', genome_seq_result),
            })

    # 基因（基因组坐标型）序列：优先按坐标从基因组 fa.gz 提取
    gene_seq_text = fetch_region(genome_name, seqid, start, end, '+') if genome_name and seqid else None
    if gene_seq_text is None:
        gene_seq_text = genome_seq_result.filter(mrna_id=IDs, gene_type='genome').values_list('sequence', flat=True).first() or ''

    results = {
        'seqid': seqid,
        'start': start,
        'end': end,
        'genome_id': genome_name,
        'IDs': IDs,
        'db_id': str(db_ids[0]) if db_ids else '',
        'gene_seq': gene_seq_text,
        'geneid_result': gene_annotation_result,
        'gff_data': list(gene_info_result.values()),
        'gene_go_result': list(gene_go_result),
        'gene_kegg_result': list(gene_kegg_result),
        'mrna_transcripts': mrna_transcript_result,
        'jbrowse_url': jbrowse_url,
    }
    return Response({'results': results}, status=status.HTTP_200_OK)
