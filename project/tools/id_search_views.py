from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def id_search_form(request):
    """
    处理基因ID搜索请求的视图函数
    """
    if request.method == 'POST':
        try:
            # 获取表单数据
            gene_ids = request.POST.get('gene_ids', '')
            request_id = request.POST.get('request_id', '')
            
            # 解析基因ID列表
            query_ids = [id.strip() for id in gene_ids.split('\n') if id.strip()]
            
            # 返回成功响应
            return JsonResponse({
                'status': 'success',
                'query_ids': query_ids,
                'message': f'成功处理了 {len(query_ids)} 个基因ID'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=400)
    else:
        return JsonResponse({
            'status': 'error',
            'error': '只接受POST请求'
        }, status=405)