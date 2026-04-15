"""
Meilisearch 搜索 API
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import traceback
from CottonOGD.config.meilisearch_config import MeilisearchConfig

@require_http_methods(["GET", "POST"])
@csrf_exempt
def search_genes_meilisearch(request):
    """
    使用 Meilisearch 搜索基因
    
    参数:
        q: 搜索关键词
        limit: 返回结果数量限制（默认20）
        offset: 结果偏移量（默认0）
        genome_id: 基因组ID过滤（可选）
    
    返回:
        JSON格式的搜索结果
    """
    try:
        # 获取搜索参数
        if request.method == 'GET':
            query = request.GET.get('q', '')
            limit = int(request.GET.get('limit', 20))
            offset = int(request.GET.get('offset', 0))
            genome_id = request.GET.get('genome_id', None)
        else:
            data = json.loads(request.body)
            query = data.get('q', '')
            limit = int(data.get('limit', 20))
            offset = int(data.get('offset', 0))
            genome_id = data.get('genome_id', None)
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Search query is required'
            }, status=400)
        
        # 获取 Meilisearch 客户端
        client = MeilisearchConfig.get_client()
        
        # 构建搜索参数
        search_params = {
            'limit': limit,
            'offset': offset,
            'attributesToRetrieve': ['geneid', 'alias', 'genome_id', 'id'],
            'attributesToHighlight': ['geneid', 'alias']
        }
        
        # 如果指定了基因组ID，添加过滤条件
        if genome_id:
            search_params['filter'] = f'genome_id = {genome_id}'
        
        # 执行搜索
        results = client.index('genemaster').search(query, search_params)
        
        # 格式化结果
        formatted_results = []
        for hit in results['hits']:
            formatted_results.append({
                'geneid': hit.get('geneid', ''),
                'alias': hit.get('alias', ''),
                'genome_id': hit.get('genome_id', ''),
                'id': hit.get('id', ''),
                'highlighted': hit.get('_formatted', {})
            })
        
        return JsonResponse({
            'success': True,
            'results': formatted_results,
            'total': results['estimatedTotalHits'],
            'processing_time': results['processingTimeMs']
        })
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Meilisearch search error: {str(e)}")
        print(f"Traceback: {error_trace}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }, status=500)

def search_genes(query, limit=20, offset=0):
    """
    使用 Meilisearch 搜索基因
    
    Args:
        query: 搜索关键词
        limit: 返回结果数量限制
        offset: 结果偏移量（分页）
    
    Returns:
        搜索结果字典
    """
    client = MeilisearchConfig.get_client()
    
    try:
        results = client.index('genemaster').search(
            query,
            {
                'limit': limit,
                'offset': offset,
                'attributesToRetrieve': ['geneid', 'alias', 'genome_id', 'id'],
                'attributesToHighlight': ['geneid', 'alias']
            }
        )
        
        # 格式化结果
        formatted_results = []
        for hit in results['hits']:
            formatted_results.append({
                'geneid': hit.get('geneid', ''),
                'alias': hit.get('alias', ''),
                'genome_id': hit.get('genome_id', ''),
                'id': hit.get('id', ''),
                'highlighted': hit.get('_formatted', {})
            })
        
        return {
            'results': formatted_results,
            'total': results['estimatedTotalHits'],
            'processing_time': results['processingTimeMs']
        }
        
    except Exception as e:
        return {
            'results': [],
            'total': 0,
            'error': str(e)
        }
