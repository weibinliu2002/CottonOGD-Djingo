"""
PPI STRING 互作网络视图。

路由：POST /CottonOGD_api/ppi/string/
请求：{"gene_ids": ["geneA", ...], "genome_id": "G.hirsutumAD1_TM-1_HAU_v1.1", "score_threshold": 400}
响应：{"code": 0, "message": "", "data": {"elements": {"nodes": [...], "edges": [...]}, ...}}
"""
from __future__ import annotations

import logging

import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from CottonOGD.server import string_service

logger = logging.getLogger(__name__)

MAX_GENE_IDS = 300


def _err(code: int, message: str, http_status: int) -> Response:
    """统一错误响应。"""
    return Response({'code': code, 'message': message, 'data': None},
                    status=http_status)


def _ok(message: str, data: dict) -> Response:
    """统一成功响应。"""
    return Response({'code': 0, 'message': message, 'data': data},
                    status=status.HTTP_200_OK)


@api_view(['POST'])
def ppi_string_network(request):
    """PPI STRING 互作网络端点。"""
    # ---- 1. 参数提取与校验 ----
    gene_ids = request.data.get('gene_ids')
    genome_id = request.data.get('genome_id')
    score_threshold = request.data.get('score_threshold', 400)

    # genome_id
    if not genome_id or not isinstance(genome_id, str) or not genome_id.strip():
        return _err(1, 'genome_id 必须为非空字符串', status.HTTP_400_BAD_REQUEST)
    genome_id = genome_id.strip()

    # gene_ids
    if not isinstance(gene_ids, list):
        return _err(1, 'gene_ids 必须为字符串数组', status.HTTP_400_BAD_REQUEST)
    if not gene_ids:
        return _err(1, 'gene_ids 不能为空', status.HTTP_400_BAD_REQUEST)

    # 类型检查 + 去空 + 去重（保持顺序）
    cleaned: list[str] = []
    seen: set[str] = set()
    for i, g in enumerate(gene_ids):
        if not isinstance(g, str):
            return _err(1, f'gene_ids[{i}] 必须为字符串，收到 {type(g).__name__}',
                        status.HTTP_400_BAD_REQUEST)
        g = g.strip()
        if not g:
            return _err(1, f'gene_ids[{i}] 不能为空字符串', status.HTTP_400_BAD_REQUEST)
        if g not in seen:
            seen.add(g)
            cleaned.append(g)
    gene_ids = cleaned

    if len(gene_ids) > MAX_GENE_IDS:
        return _err(1, f'gene_ids 数量 {len(gene_ids)} 超过上限 {MAX_GENE_IDS}',
                    status.HTTP_400_BAD_REQUEST)

    # score_threshold
    try:
        score_threshold = int(score_threshold)
    except (TypeError, ValueError):
        return _err(1, 'score_threshold 必须为整数', status.HTTP_400_BAD_REQUEST)
    if not (150 <= score_threshold <= 1000):
        return _err(1, 'score_threshold 须在 150–1000 之间', status.HTTP_400_BAD_REQUEST)

    logger.info('PPI: 请求 genome=%s, genes=%d, score=%d',
                genome_id, len(gene_ids), score_threshold)

    # ---- 2. genome → STRING taxon ----
    try:
        taxid = string_service.resolve_taxon(genome_id)
    except Exception as e:
        logger.error('PPI: resolve_taxon 失败: %s', e)
        return _err(2, f'解析基因组 {genome_id} 的 STRING 物种映射时出错',
                    status.HTTP_422_UNPROCESSABLE_ENTITY)
    if not taxid:
        return _err(2, f'基因组 {genome_id} 未配置 STRING 物种映射',
                    status.HTTP_422_UNPROCESSABLE_ENTITY)

    # ---- 3. 基因 → STRING ID ----
    try:
        mapping, unmapped = string_service.map_genes_to_string(gene_ids, genome_id)
    except RuntimeError as e:
        logger.warning('PPI: 映射失败: %s', e)
        return _err(3, str(e), status.HTTP_422_UNPROCESSABLE_ENTITY)
    except Exception as e:
        logger.error('PPI: 映射异常: %s', e)
        return _err(3, f'基因映射过程出错: {e}', status.HTTP_422_UNPROCESSABLE_ENTITY)

    if not mapping:
        sample = unmapped[:10]
        return _err(4, f'所有基因 ID 无法映射到 STRING；未映射: {sample}',
                    status.HTTP_422_UNPROCESSABLE_ENTITY)

    # ---- 4. 获取互作 ----
    string_ids = [info['string_id'] for info in mapping.values()]
    try:
        edges = string_service.fetch_interactions(string_ids, taxid, score_threshold)
    except requests.Timeout:
        return _err(5, 'STRING API 请求超时，请稍后重试或降低基因数量',
                    status.HTTP_504_GATEWAY_TIMEOUT)
    except requests.ConnectionError:
        return _err(6, 'STRING API 不可用，请稍后重试',
                    status.HTTP_502_BAD_GATEWAY)
    except requests.RequestException as e:
        logger.error('PPI: STRING API 调用失败: %s', e)
        return _err(6, f'STRING API 调用失败: {e}', status.HTTP_502_BAD_GATEWAY)

    # ---- 5. 构建 Cytoscape 网络 ----
    elements = string_service.build_cytoscape_network(gene_ids, mapping, edges)

    if not elements['nodes']:
        return _err(7, '无可用节点构建网络', status.HTTP_422_UNPROCESSABLE_ENTITY)

    # ---- 6. 成功响应 ----
    n_mapped = len(mapping)
    n_total = len(gene_ids)
    if unmapped:
        sample = unmapped[:10]
        msg = f'{len(unmapped)}/{n_total} 基因未映射到 STRING: {sample}'
    else:
        msg = ''

    return _ok(msg, {
        'elements': elements,
        'stats': {
            'total_genes': n_total,
            'mapped_genes': n_mapped,
            'unmapped_genes': len(unmapped),
            'edges': len(elements['edges']),
        },
    })
