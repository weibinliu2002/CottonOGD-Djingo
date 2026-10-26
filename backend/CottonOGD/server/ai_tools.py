"""
AI Chat 工具层（第一版）。

供大模型 Tool Calling 使用的三个只读查询工具：
  - search_gene                基因关键词搜索（复用 Meilisearch genemaster 索引 + 转录本兜底）
  - get_gene_detail            基因详情（复用 gene_id_result 的解析链路 + 注释/GO/KEGG service）
  - search_transcription_factor TF/TR 家族查询（Meilisearch family 索引优先，MySQL 兜底）

安全约束：
  - 模型只能调用 TOOL_REGISTRY 中登记的函数，参数做类型与范围钳制；
  - 本层只返回结构化 JSON，不生成自然语言回答；
  - 不向模型暴露任何数据库凭证，全部查询经由 Django ORM / 既有 service 完成。
"""
import json
import logging
import time

from django.db.models import Count

from CottonOGD.config.meilisearch_config import MeilisearchConfig
from CottonOGD.models import Family, GeneMaster, Species_info, gene_info, gene_seq
from CottonOGD.server.annotation_search import get_annotation
from CottonOGD.server.Go_kegg_search import go_annotation, kegg_annotation
from CottonOGD.server.seq_fetch import fetch_by_id
from CottonOGD.views.Meilisearch import search_genes
from CottonOGD.views.gene_id_result import (
    _db_fallback,
    _exact_db_ids,
    build_jbrowse_url,
    parse_mrna_ids,
)

logger = logging.getLogger(__name__)

# 业务限制：单次工具调用返回条数上限
SEARCH_GENE_MAX_LIMIT = 50
TF_MAX_LIMIT = 50
# 注释/GO/KEGG 输出条数上限（防止 tool 结果撑爆 LLM 上下文）
MAX_ANNOTATION_ITEMS = 20
MAX_GO_ITEMS = 30
MAX_KEGG_ITEMS = 15


# =============================================================================
# 公共辅助
# =============================================================================

def _clamp_limit(limit, default=10, maximum=50):
    """limit 钳制到 [1, maximum]，非法输入回落默认值。"""
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, maximum))


def _resolve_genome(genome):
    """
    把模型给的基因组名解析成 Species_info.name。

    物种全名很长（如 G.hirsutumAD1_TM-1_HAU_v1.1），模型难以精确拼写，
    故按「精确 -> 子串唯一命中」两级解析；仍无法唯一定位时返回错误并
    附候选列表，供模型下一次调用自行纠正。

    Returns:
        (species_name, None) 或 (None, error_dict)
    """
    genome = str(genome or '').strip()
    if not genome:
        return None, None  # 未提供 genome 属正常情况，由调用方处理

    exact = Species_info.objects.filter(name=genome).values_list('name', flat=True).first()
    if exact:
        return exact, None

    fuzzy = list(Species_info.objects.filter(name__icontains=genome)
                 .values_list('name', flat=True)[:10])
    if len(fuzzy) == 1:
        return fuzzy[0], None
    if fuzzy:
        return None, {
            'error': f"genome '{genome}' 匹配到多个物种，请从中选择一个：{fuzzy}"
        }
    return None, {'error': f"genome '{genome}' 不存在，可留空 genome 或提供正确物种名"}


# =============================================================================
# Tool 1: search_gene
# =============================================================================

def search_gene(query, genome='', limit=10):
    """
    按关键词搜索基因（基因 ID / 别名 / 部分关键词均可）。

    复用 views.Meilisearch.search_genes：Meilisearch genemaster 索引优先，
    输入带版本号自动去后缀重试，转录本 ID 走 TranscriptMaster 兜底。
    """
    query = str(query or '').strip()
    if not query:
        return {'error': 'query 不能为空'}

    limit = _clamp_limit(limit, default=10, maximum=SEARCH_GENE_MAX_LIMIT)

    genome_id = None
    if str(genome or '').strip():
        genome_id, err = _resolve_genome(genome)
        if err:
            return err

    result = search_genes(query, limit=limit, offset=0, genome_id=genome_id)
    if result.get('error'):
        logger.error('ai_tools.search_genes failed: %s', result['error'])
        return {'error': f'搜索服务出错：{result["error"]}'}

    hits = result.get('results', [])
    return {
        'total': result.get('total', len(hits)),
        'results': [{
            'gene_id': h.get('geneid', ''),
            'genome': h.get('genome_id', ''),
            'db_id': h.get('id', ''),
            'alias': h.get('alias', ''),
            'match_type': h.get('match_type', 'gene'),
        } for h in hits],
    }


# =============================================================================
# Tool 2: get_gene_detail
# =============================================================================

def _resolve_single_db_id(gene_id, genome):
    """
    gene_id -> GeneMaster 主键。

    与 views.gene_id_result.resolve_db_ids 相同的解析链路：
    Meilisearch 精确命中 -> MySQL (genome_id, geneid) 精确兜底。
    """
    genome_id = None
    if str(genome or '').strip():
        genome_id, err = _resolve_genome(genome)
        if err:
            return None, err

    result = search_genes(gene_id, limit=100, offset=0, genome_id=genome_id)
    db_ids = _exact_db_ids(result.get('results', []), [gene_id], genome_id)
    if not db_ids:
        db_ids = _db_fallback([gene_id], genome_id)
    if not db_ids:
        return None, {
            'error': f"基因 '{gene_id}' 未找到"
                     + (f"（限定基因组 {genome_id}）" if genome_id else '')
                     + '。可先调用 search_gene 确认正确的基因 ID。'
        }
    return db_ids[0], None


def _transcript_payloads(db_id, genome_name, mrna_rows):
    """每个 mRNA 的精简信息（ID + 蛋白长度）。"""
    seq_rows = {
        (r.mrna_id, r.gene_type): r.sequence
        for r in gene_seq.objects.filter(id_id=db_id, gene_type='pro')
        .only('mrna_id', 'gene_type', 'sequence')
    }
    transcripts = []
    for row in mrna_rows[:10]:
        tr_id = row['mrna_id']
        # 产物文件优先（与 views.gene_id_result.get_transcript_seq 一致），表数据回退
        seq = fetch_by_id(genome_name, 'pro', tr_id)
        if seq is None:
            seq = seq_rows.get((tr_id, 'pro'))
        transcripts.append({
            'transcript_id': tr_id,
            'seqid': row['seqid'],
            'start': row['start'],
            'end': row['end'],
            'strand': row['strand'],
            'protein_length': len(seq) if seq else None,
        })
    return transcripts


def get_gene_detail(gene_id, genome=''):
    """
    按基因 ID 返回 CottonOGD 已有详情：基因组坐标、转录本、注释、GO、KEGG、
    TF 家族归属、JBrowse 链接。序列只返回长度，不返回全文（控制上下文体积）。
    """
    gene_id = str(gene_id or '').strip()
    if not gene_id:
        return {'error': 'gene_id 不能为空'}

    db_id, err = _resolve_single_db_id(gene_id, genome)
    if err:
        return err

    gene_master = GeneMaster.objects.select_related('genome').filter(id=db_id).first()
    if not gene_master:
        return {'error': f'基因 {gene_id} 已从索引解析为主键 {db_id}，但 GeneMaster 中不存在'}

    genome_name = gene_master.genome.name if gene_master.genome else ''

    # 基因行（type='gene'）与 mRNA 行（type='mRNA'）
    info_rows = list(
        gene_info.objects.filter(id_id=db_id).values(
            'seqid', 'source', 'type', 'start', 'end', 'strand', 'attributes')
    )
    gene_row = next((r for r in info_rows if r['type'] == 'gene'), None)

    mrna_rows = []
    for r in info_rows:
        if r['type'] != 'mRNA':
            continue
        for tr_id in parse_mrna_ids(r['attributes']):
            mrna_rows.append({'mrna_id': tr_id,
                              **{k: r[k] for k in ('seqid', 'start', 'end', 'strand')}})

    # 注释（uniprot / pfam / eggnog 等，按来源精简）
    annotations = []
    for ann in get_annotation([db_id])[:MAX_ANNOTATION_ITEMS]:
        detail = (ann.get('annotation') or {})
        annotations.append({
            'source': (ann.get('source') or {}).get('name'),
            'annotation_id': detail.get('annotation_id'),
            'protein_name': detail.get('protein_name'),
            'description': detail.get('description'),
        })

    go_terms = [{
        'go_id': g.get('go_id'),
        'name': g.get('name'),
        'namespace': g.get('namespace'),
    } for g in go_annotation([db_id])[:MAX_GO_ITEMS]]

    kegg_terms = [{
        'ko_id': k.get('kegg_id') or k.get('ko_id'),
        'name': k.get('name'),
        'pathway': k.get('pathway'),
    } for k in kegg_annotation([db_id])[:MAX_KEGG_ITEMS]]

    family = Family.objects.filter(id=db_id).values('TF_class', 'class_name', 'TF_name').first()

    jbrowse_url = None
    if gene_row:
        # build_jbrowse_url 期望 Species_info 数字主键；GeneMaster.genome 的
        # to_field='name'，其 genome_id 是字符串物种名，故取 .pk
        jbrowse_url = build_jbrowse_url(
            gene_row['seqid'], gene_row['start'], gene_row['end'], gene_master.genome.pk)

    return {
        'gene_id': gene_master.geneid,
        'db_id': db_id,
        'genome': genome_name,
        'seqid': gene_row['seqid'] if gene_row else None,
        'start': gene_row['start'] if gene_row else None,
        'end': gene_row['end'] if gene_row else None,
        'strand': gene_row['strand'] if gene_row else None,
        'transcripts': _transcript_payloads(db_id, genome_name, mrna_rows),
        'annotations': annotations,
        'go': go_terms,
        'kegg': kegg_terms,
        'tf_family': family,
        'jbrowse_url': jbrowse_url,
    }


# =============================================================================
# Tool 3: search_transcription_factor
# =============================================================================

def _tf_family_overview(tf_type, genome_id):
    """family 为空时返回家族概览（家族名 + 数量），引导模型/用户先选家族。"""
    qs = Family.objects.filter(TF_class=tf_type)
    if genome_id:
        qs = qs.filter(genome__name=genome_id)
    overview = list(
        qs.values('class_name').annotate(count=Count('id')).order_by('-count')[:50]
    )
    return {
        'total_families': len(overview),
        'families': [{'family': r['class_name'], 'count': r['count']} for r in overview],
        'hint': 'family 参数为空，已返回家族列表；请指定 family 后再次查询基因',
    }


def _quote_filter_value(value):
    """Meilisearch filter 值转义（与 views.Meilisearch 一致）。"""
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def _search_tf_via_meilisearch(family, genome_id, tf_type, limit):
    """Meilisearch family 索引查询；索引不存在或不可达返回 None（走 MySQL 兜底）。"""
    try:
        # search-only key 只授权 genemaster 索引，覆盖不了 family；
        # 与 proxy_search 一致使用 master key，密钥仅存在于服务端
        client = MeilisearchConfig.get_client(use_master=True)
        search_params = {
            'limit': limit,
            'attributesToRetrieve': ['id', 'geneid', 'alias', 'genome_id',
                                     'TF_class', 'class_name', 'TF_name'],
            'filter': f'TF_class = {_quote_filter_value(tf_type)}',
        }
        if genome_id:
            search_params['filter'] += f' AND genome_id = {_quote_filter_value(genome_id)}'
        result = client.index(MeilisearchConfig.FAMILY_INDEX_NAME).search(family, search_params)
        if not isinstance(result, dict) and hasattr(result, 'model_dump'):
            result = result.model_dump()
        hits = result.get('hits', [])
        return {
            'total': result.get('estimatedTotalHits', result.get('nbHits', len(hits))),
            'results': [{
                'gene_id': h.get('geneid', ''),
                'genome': h.get('genome_id', ''),
                'family': h.get('class_name', ''),
                'type': h.get('TF_class', ''),
            } for h in hits],
        }
    except Exception as exc:  # noqa: BLE001 任何失败都回退 MySQL
        logger.warning('TF 查询 Meilisearch 失败，回退 MySQL: %s', exc)
        return None


def search_transcription_factor(genome='', family='', type='TF', limit=10):
    """
    查询转录因子（TF）/ 转录调节子（TR）基因。

    family 为空时返回家族概览；否则按家族名（支持模糊）返回基因列表。
    优先 Meilisearch family 索引，失败回退 MySQL genefamily 表。
    """
    tf_type = str(type or 'TF').strip().upper()
    if tf_type not in ('TF', 'TR'):
        return {'error': "type 只支持 'TF' 或 'TR'"}

    limit = _clamp_limit(limit, default=10, maximum=TF_MAX_LIMIT)
    family = str(family or '').strip()

    genome_id = None
    if str(genome or '').strip():
        genome_id, err = _resolve_genome(genome)
        if err:
            return err

    if not family:
        return _tf_family_overview(tf_type, genome_id)

    # 1) Meilisearch family 索引（支持家族名模糊匹配）
    result = _search_tf_via_meilisearch(family, genome_id, tf_type, limit)
    if result is not None and result['results']:
        return result

    # 2) MySQL 兜底：class_name 精确优先，无命中再模糊
    qs = Family.objects.filter(TF_class=tf_type).select_related('genome')
    if genome_id:
        qs = qs.filter(genome__name=genome_id)

    rows = list(qs.filter(class_name=family)
                .values('geneid', 'TF_class', 'class_name', 'genome__name')[:limit])
    if not rows:
        rows = list(qs.filter(class_name__icontains=family)
                    .values('geneid', 'TF_class', 'class_name', 'genome__name')[:limit])

    if not rows:
        return {
            'total': 0,
            'results': [],
            'hint': f'未找到 {tf_type} 家族 {family!r} 的基因；'
                    '可调用本工具且 family 留空，获取可用家族列表',
        }

    exact_matched = bool(qs.filter(class_name=family).exists())
    return {
        'total': len(rows),
        'results': [{
            'gene_id': r['geneid'],
            'genome': r['genome__name'],
            'family': r['class_name'],
            'type': r['TF_class'],
        } for r in rows],
        'hint': None if exact_matched else f'family={family!r} 无精确匹配，以下为模糊匹配结果',
    }


# =============================================================================
# Tool 注册表（LLM 只能调用这里登记的函数）
# =============================================================================

TOOL_REGISTRY = {
    'search_gene': search_gene,
    'get_gene_detail': get_gene_detail,
    'search_transcription_factor': search_transcription_factor,
}

# OpenAI function calling 的 JSON Schema 定义
TOOL_SPECS = [
    {
        'type': 'function',
        'function': {
            'name': 'search_gene',
            'description': (
                '在 CottonOGD 全部棉花基因组中按关键词搜索基因。'
                '适用于：基因 ID 精确/模糊查找（如 Gh_A01G000100）、'
                '按部分关键词找基因。返回基因 ID、所属基因组和数据库主键 db_id。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string', 'description': '基因关键词或基因 ID（必填）'},
                    'genome': {
                        'type': 'string',
                        'description': '限定基因组（物种名，如 G.hirsutumAD1_TM-1_HAU_v1.1，可留空）',
                    },
                    'limit': {'type': 'integer', 'description': '返回数量，默认 10，最大 50'},
                },
                'required': ['query'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_gene_detail',
            'description': (
                '根据基因 ID 获取单个基因的详细信息：基因组坐标（seqid/start/end/strand）、'
                '转录本及蛋白长度、功能注释、GO、KEGG、TF 家族、JBrowse 基因组浏览器链接。'
                '通常先 search_gene 拿到正确 gene_id 再调用本工具。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'gene_id': {'type': 'string', 'description': '基因 ID（必填）'},
                    'genome': {'type': 'string', 'description': '所属基因组名（可选，多基因组重名时用于消歧）'},
                },
                'required': ['gene_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_transcription_factor',
            'description': (
                '查询转录因子（TF）或转录调节子（TR）。'
                '用户询问某家族（如 NAC、MYB、WRKY）的转录因子时使用本工具而不是 search_gene。'
                'family 为空时返回可用家族列表及数量，可据此引导用户选择。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'genome': {'type': 'string', 'description': '限定基因组（物种名，可留空查全部物种）'},
                    'family': {'type': 'string', 'description': '转录因子家族名，如 NAC、MYB、bHLH（可留空获取家族列表）'},
                    'type': {'type': 'string', 'enum': ['TF', 'TR'], 'description': 'TF=转录因子（默认），TR=转录调节子'},
                    'limit': {'type': 'integer', 'description': '返回数量，默认 10，最大 50'},
                },
                'required': [],
            },
        },
    },
]


def execute_tool(name, arguments):
    """
    执行模型请求的工具调用。

    Args:
        name: 工具名（必须在 TOOL_REGISTRY 白名单内）
        arguments: JSON 字符串或已解析的 dict

    Returns:
        (result_dict, elapsed_ms)
    """
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return {'error': f'未知工具：{name}，可用工具：{sorted(TOOL_REGISTRY)}'}, 0

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or '{}')
        except json.JSONDecodeError:
            return {'error': f'工具 {name} 的参数不是合法 JSON'}, 0
    if not isinstance(arguments, dict):
        return {'error': f'工具 {name} 的参数必须是 JSON 对象'}, 0

    start = time.time()
    try:
        return fn(**arguments), int((time.time() - start) * 1000)
    except Exception as exc:  # noqa: BLE001 工具失败要作为结果回给模型，而不是打断对话
        logger.exception('AI tool %s 执行失败', name)
        return {'error': f'工具执行出错：{exc}'}, int((time.time() - start) * 1000)
