"""
Meilisearch 搜索 API
"""
import json
import logging
import re
import traceback

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from CottonOGD.config.meilisearch_config import MeilisearchConfig
from CottonOGD.views.base import UuidManager

logger = logging.getLogger(__name__)

INDEX_NAME = MeilisearchConfig.INDEX_NAME

# 业务层限制
MAX_LIMIT = MeilisearchConfig.MAX_LIMIT
MAX_OFFSET = MeilisearchConfig.MAX_OFFSET

RETREIVE_FIELDS = MeilisearchConfig.RETRIEVE_FIELDS

# ---- 统一检索代理（/search/）限制 ----
# index 白名单来自 MeilisearchConfig.INDEX_META 注册表，新增索引只需在注册表登记
ALLOWED_INDEXES = MeilisearchConfig.allowed_indexes()
MAX_TOTAL_HITS = 1000          # offset + limit 上限，防深分页拖垮 Meilisearch
MAX_QUERY_LENGTH = 500         # q 最大字符数
MAX_BODY_BYTES = 64 * 1024     # 请求体大小上限（64KB）


def _quote_filter_value(value):
    """转义过滤值中的特殊字符，防止 filter 注入"""
    value = str(value).replace('\\', '\\\\').replace('"', '\\"')
    return f'"{value}"'


def _parse_search_params(data):
    """
    解析并校验搜索参数，返回 (query, limit, offset, genome_id, error_response)
    出错时 error_response 非 None
    """
    query = str(data.get('q') or '').strip()

    try:
        limit = int(data.get('limit', 20))
    except (TypeError, ValueError):
        return None, None, None, None, JsonResponse(
            {'success': False, 'error': 'limit must be an integer'}, status=400)

    try:
        offset = int(data.get('offset', 0))
    except (TypeError, ValueError):
        return None, None, None, None, JsonResponse(
            {'success': False, 'error': 'offset must be an integer'}, status=400)

    # 钳制到合法范围
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, min(offset, MAX_OFFSET))

    genome_id = data.get('genome_id') or None

    # q 为空且无过滤条件时拒绝（避免全量扫索引）
    if not query and not genome_id:
        return None, None, None, None, JsonResponse(
            {'success': False, 'error': 'Search query or genome_id is required'},
            status=400)

    return query, limit, offset, genome_id, None


def _format_hits(hits):
    """统一格式化搜索结果"""
    formatted = []
    for hit in hits:
        formatted.append({
            'id': hit.get('id', ''),
            'geneid': hit.get('geneid', ''),
            'alias': hit.get('alias', ''),
            'genome_id': hit.get('genome_id', ''),
            'highlighted': hit.get('_formatted', {}),
            'match_type': hit.get('match_type', 'gene'),
        })
    return formatted


# 匹配末尾版本号：Gano_01G000010.1 / xxx.t1 等
_VERSION_SUFFIX_RE = re.compile(r'\.t?\d+$')


def normalize_gene_query(query: str) -> str:
    """去掉 ID 末尾的版本号（.1 / .t1 等）；genemaster 索引只存去除版本号的基因 ID。"""
    return _VERSION_SUFFIX_RE.sub('', query.strip())


def _transcript_fallback(query, genome_id=None, limit=10):
    """
    转录本 ID 兜底：genemaster 索引不含转录本 ID，用户输入转录本（如
    Gano_01G000010.1）时经 TranscriptMaster（transcriptid 有索引）映射回基因。
    返回合成 hits（id 即该转录本所属基因的 GeneMaster 主键）。
    """
    from CottonOGD.models import TranscriptMaster

    candidates = {query, normalize_gene_query(query)} - {''}
    qs = TranscriptMaster.objects.filter(transcriptid__in=candidates)
    if genome_id:
        qs = qs.filter(genome__name=genome_id)
    rows = list(qs.values('transcriptid', 'id_id', 'genome__name')[:limit])

    hits = []
    for row in rows:
        hits.append({
            'id': row['id_id'],
            'geneid': normalize_gene_query(row['transcriptid']),
            'alias': row['transcriptid'],
            'genome_id': row['genome__name'],
            '_formatted': {},
            'match_type': 'transcript',
        })
    return hits


def _search_index(client, query, search_params):
    results = client.index(INDEX_NAME).search(query, search_params)
    total = results.get('estimatedTotalHits', results.get('nbHits', 0))
    return results.get('hits', []), total, results.get('processingTimeMs', 0)


def search_genes(query, limit=20, offset=0, genome_id=None):
    """
    使用 Meilisearch 搜索基因（供视图和其他模块复用）

    解析顺序：
      1. 原始 query 查 genemaster 索引；
      2. 0 命中且 query 带版本号 → 去版本号重试；
      3. 仍 0 命中 → TranscriptMaster 按转录本 ID 兜底（match_type='transcript'）。

    Args:
        query: 搜索关键词，可为空（但此时必须提供 genome_id）
        limit: 返回结果数量限制
        offset: 结果偏移量（分页）
        genome_id: 基因组过滤（物种名，对应外键 to_field='name'）

    Returns:
        dict: {results, total, processing_time, error}
    """
    client = MeilisearchConfig.get_client()

    try:
        search_params = {
            'limit': limit,
            'offset': offset,
            'attributesToRetrieve': RETREIVE_FIELDS,
            'attributesToHighlight': ['geneid', 'alias'],
        }

        # 过滤条件：字符串值必须加双引号
        if genome_id:
            search_params['filter'] = f'genome_id = {_quote_filter_value(genome_id)}'

        hits, total, processing_time = _search_index(client, query, search_params)

        # 输入带版本号（如 ZY10_A01000010.1）时索引中无此 ID，去版本号重试
        if not hits and query:
            normalized = normalize_gene_query(query)
            if normalized != query:
                hits, total, processing_time = _search_index(client, normalized, search_params)

        # 仍无命中：按转录本 ID 兜底
        if not hits and query:
            t_hits = _transcript_fallback(query, genome_id=genome_id, limit=min(limit, 10))
            if t_hits:
                return {
                    'results': _format_hits(t_hits),
                    'total': len(t_hits),
                    'processing_time': processing_time,
                    'error': None,
                }

        return {
            'results': _format_hits(hits),
            'total': total,
            'processing_time': processing_time,
            'error': None,
        }

    except Exception as e:
        return {
            'results': [],
            'total': 0,
            'processing_time': 0,
            'error': str(e),
        }


@require_http_methods(["GET", "POST"])
@csrf_exempt
def search_genes_meilisearch(request):
    """
    使用 Meilisearch 搜索基因

    参数（GET query string 或 POST JSON body）:
        q:         搜索关键词（与 genome_id 至少提供一个）
        limit:     返回结果数量限制（默认 20，最大 100）
        offset:    结果偏移量（默认 0）
        genome_id: 基因组过滤（可选，物种名，如 Cotton）
    """
    try:
        if request.method == 'GET':
            data = request.GET
        else:
            try:
                data = json.loads(request.body or '{}')
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON body'},
                                    status=400)

        query, limit, offset, genome_id, error_response = _parse_search_params(data)
        if error_response:
            return error_response

        result = search_genes(query, limit=limit, offset=offset, genome_id=genome_id)

        if result['error']:
            print(f"Meilisearch search error: {result['error']}")
            return JsonResponse({'success': False, 'error': result['error']}, status=500)

        return JsonResponse({
            'success': True,
            'query': query,
            'genome_id': genome_id,
            'results': result['results'],
            'total': result['total'],
            'processing_time': result['processing_time'],
        })

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Meilisearch search error: {e}")
        print(f"Traceback: {error_trace}")
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


# =============================================================================
# 统一检索代理：POST /CottonOGD_api/search/
#
# 前端不再直连 Meilisearch、不再持有任何 key；本端点只做「校验 + 透传」：
#   - filter 由前端拼好整体传入，后端不解析、不拼进 q；
#   - Meilisearch 原始响应原样返回（hits / _formatted / estimatedTotalHits /
#     processingTimeMs / offset / limit / facetDistribution）。
# 客户端凭证（MEILISEARCH_URL / KEY）只存在于服务器环境变量。
# =============================================================================


class MeiliUnavailable(Exception):
    """Meilisearch 不可达或请求失败，调用方据此返回 503。"""


class MeiliIndexNotFound(Exception):
    """请求的索引不存在（已登记但尚未建立），调用方据此返回 400。"""


def _proxy_error(message, code, http_status):
    """统一错误响应体：{message, code}"""
    return JsonResponse({'message': message, 'code': code}, status=http_status)


def parse_proxy_payload(data):
    """
    校验统一代理请求体。

    Args:
        data: 已解析的 JSON dict

    Returns:
        (payload, None)  校验通过
        (None, JsonResponse)  校验失败，直接返回该响应
    """
    payload = {}

    # index 白名单
    index = str(data.get('index') or INDEX_NAME).strip()
    if index not in ALLOWED_INDEXES:
        return None, _proxy_error(f'index not allowed: {index}', 'invalid_index', 400)
    payload['index'] = index

    # q：字符串，长度受限
    q = data.get('q')
    if q is None:
        q = ''
    if not isinstance(q, str):
        return None, _proxy_error('q must be a string', 'invalid_q', 400)
    if len(q) > MAX_QUERY_LENGTH:
        return None, _proxy_error(
            f'q is too long (max {MAX_QUERY_LENGTH} characters)', 'invalid_q', 400)
    payload['q'] = q

    # offset / limit
    try:
        offset = int(data.get('offset', 0))
        limit = int(data.get('limit', 20))
    except (TypeError, ValueError):
        return None, _proxy_error(
            'offset and limit must be integers', 'invalid_pagination', 400)
    if offset < 0 or limit < 1:
        return None, _proxy_error(
            'offset must be >= 0 and limit must be >= 1', 'invalid_pagination', 400)
    if offset + limit > MAX_TOTAL_HITS:
        return None, _proxy_error(
            f'offset + limit must not exceed {MAX_TOTAL_HITS}', 'limit_exceeded', 400)
    payload['offset'] = offset
    payload['limit'] = limit

    # filter：Meilisearch 过滤表达式，原样透传（前端已拼好多基因组 OR）
    flt = data.get('filter')
    if flt is not None:
        if not isinstance(flt, str):
            return None, _proxy_error('filter must be a string', 'invalid_filter', 400)
        if flt.strip():
            payload['filter'] = flt

    # 列表型透传参数
    for key in ('facets', 'attributesToRetrieve', 'attributesToHighlight'):
        value = data.get(key)
        if value is None:
            continue
        if not isinstance(value, (list, tuple)) or not all(
                isinstance(item, str) for item in value):
            return None, _proxy_error(
                f'{key} must be an array of strings', f'invalid_{key}', 400)
        payload[key] = list(value)

    return payload, None


def execute_proxy_search(payload):
    """
    按已校验的 payload 调用 Meilisearch，返回其原始响应。

    Raises:
        MeiliUnavailable: 客户端不可达或 Meilisearch 返回错误。
    """
    search_params = {
        'offset': payload['offset'],
        'limit': payload['limit'],
    }
    for key in ('filter', 'facets', 'attributesToRetrieve', 'attributesToHighlight'):
        if key in payload:
            search_params[key] = payload[key]

    try:
        # 代理需覆盖注册表中的全部索引，而 search-only key 被限制到单个索引，
        # 故此处使用 master key；密钥仅存在于服务器端，绝不返回给前端。
        client = MeilisearchConfig.get_client(use_master=True)
        result = client.index(payload['index']).search(payload['q'], search_params)
    except Exception as exc:  # noqa: BLE001
        # 索引未建立属于客户端错误，不能误报为服务不可用
        if 'index_not_found' in str(exc):
            raise MeiliIndexNotFound(payload['index']) from exc
        logger.error('Meilisearch proxy search failed index=%s: %s',
                     payload['index'], exc, exc_info=True)
        raise MeiliUnavailable(str(exc)) from exc

    # meilisearch 客户端版本差异兜底：pydantic 模型 -> dict
    if not isinstance(result, dict) and hasattr(result, 'model_dump'):
        result = result.model_dump()
    return result


@require_http_methods(["POST"])
@csrf_exempt
def proxy_search(request):
    """
    统一检索代理：前端零密钥，所有检索经后端转发。

    认证与全站一致（Authorization: Bearer <token> 或 auth_token cookie，
    由 ClientTokenMiddleware 桥接为 uuid header）。

    请求体（与 Meilisearch search API 对齐）::

        {
          "index": "genemaster",
          "q": "Ghir_A01G000040",
          "offset": 0,
          "limit": 20,
          "filter": "genome_id = \\"G.hirsutumAD1_TM-1_HAU_v1.1\\"",
          "facets": ["genome_id"],
          "attributesToRetrieve": ["id", "geneid", "alias", "genome_id"],
          "attributesToHighlight": ["geneid", "alias"]
        }

    响应：Meilisearch 原始 JSON。
    """
    # 1) 认证
    uuid = request.headers.get('uuid')
    if uuid not in UuidManager.uuid_storage:
        return JsonResponse({'error': 'uuid is required'}, status=400)

    # 2) 请求体大小限制
    if len(request.body or b'') > MAX_BODY_BYTES:
        return _proxy_error(
            f'request body is too large (max {MAX_BODY_BYTES} bytes)',
            'payload_too_large', 413)

    # 3) 解析 JSON
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _proxy_error('invalid JSON body', 'invalid_json', 400)
    if not isinstance(data, dict):
        return _proxy_error('request body must be a JSON object', 'invalid_json', 400)

    # 4) 校验
    payload, error_response = parse_proxy_payload(data)
    if error_response:
        return error_response

    # 5) 透传执行
    try:
        result = execute_proxy_search(payload)
    except MeiliIndexNotFound as exc:
        return _proxy_error(f'index not found: {exc}', 'index_not_found', 400)
    except MeiliUnavailable as exc:
        return _proxy_error(f'search service unavailable: {exc}',
                            'meili_unavailable', 503)

    return JsonResponse(result, status=200)


# =============================================================================
# 可用索引列表：GET /CottonOGD_api/get_search_indexes/
#
# 前端首页据此渲染「选择库」下拉，新增索引只改后端注册表，前端无需改代码。
# =============================================================================


def _list_index_uids(client):
    """列出 Meilisearch 现有索引 uid（兼容 dict / pydantic 两种返回）。"""
    res = client.get_indexes()
    if hasattr(res, 'results'):
        items = list(res.results or [])
    elif isinstance(res, dict):
        items = res.get('results', [])
    else:
        items = []
    uids = []
    for item in items:
        if isinstance(item, dict):
            uids.append(item.get('uid') or item.get('name'))
        else:
            uids.append(getattr(item, 'uid', None))
    return {u for u in uids if u}


def _doc_count(client, uid):
    """取索引文档数；兼容 dict / pydantic 两种返回，取不到返回 None。"""
    stats = client.index(uid).get_stats()
    if isinstance(stats, dict):
        return stats.get('numberOfDocuments', stats.get('number_of_documents'))
    return getattr(stats, 'number_of_documents', None)


@require_http_methods(["GET"])
def get_search_indexes(request):
    """
    返回后端登记且前端可用的 Meilisearch 索引列表。

    - `available` 为 false 表示索引已在注册表登记但尚未建立（如未导入数据）；
    - `documents` 为该索引当前文档数，取不到为 null。

    Meilisearch 不可达时返回 503 {message, code: "meili_unavailable"}。
    """
    uuid = request.headers.get('uuid')
    if uuid not in UuidManager.uuid_storage:
        return JsonResponse({'error': 'uuid is required'}, status=400)

    try:
        # 列举索引/统计文档数需要 admin 权限，search-only key 会返回 403
        client = MeilisearchConfig.get_client(use_master=True)
        existing = _list_index_uids(client)
    except Exception as exc:  # noqa: BLE001  统一转 503
        logger.error('获取 Meilisearch 索引列表失败: %s', exc, exc_info=True)
        return _proxy_error(f'search service unavailable: {exc}',
                            'meili_unavailable', 503)

    indexes = []
    for uid, meta in MeilisearchConfig.INDEX_META.items():
        available = uid in existing
        documents = None
        if available:
            try:
                documents = _doc_count(client, uid)
            except Exception as exc:  # noqa: BLE001 计数失败不影响列表返回
                logger.warning('获取索引 %s 文档数失败: %s', uid, exc)
        indexes.append({
            'uid': uid,
            'label': meta['label'],
            'description': meta['description'],
            'available': available,
            'documents': documents,
            'searchableAttributes': meta['searchable_attributes'],
            'filterableAttributes': meta['filterable_attributes'],
            'defaultAttributesToRetrieve': meta['default_attributes_to_retrieve'],
            'defaultAttributesToHighlight': meta['default_attributes_to_highlight'],
        })

    return JsonResponse({'indexes': indexes}, status=200)
