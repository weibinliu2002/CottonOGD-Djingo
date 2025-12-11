from django.shortcuts import render
from django.db import connection
from django.core.paginator import Paginator
from collections import Counter
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import uuid
import time
import json

def kegg_annotation(request):
    if request.method == 'POST':
        gene_input = request.POST.get('gene_id', '').strip()
        per_page = int(request.POST.get('per_page', 10))
        
        gene_list = [gene.strip() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        results = []
        if gene_list:
            with connection.cursor() as cursor:
                for gene_id in gene_list:
                    cursor.execute("""
                        SELECT Chr, Start, End, ID 
                        FROM `eg_go_annotation` 
                        WHERE ID = %s
                    """, [gene_id])
                    annotation_data = cursor.fetchall()

                    cursor.execute("""
                        SELECT  Query, `match` ,Description
                        FROM `eg_kegg` 
                        WHERE Query = %s
                    """, [gene_id])
                    kegg_data = cursor.fetchall()

                    for anno_row in annotation_data:
                        for ke_row in kegg_data:
                            results.append({
                                'Chr': anno_row[0],
                                'Start': anno_row[1],
                                'End': anno_row[2],
                                'ID': anno_row[3],
                                'match': ke_row[1],
                                'Description': ke_row[2],
                            })

            match_counts = Counter([result['match'] for result in results if result['match']])
            chart_data = {
                'labels': list(match_counts.keys()),
                'data': list(match_counts.values()),
            }

            request.session['annotation_results'] = results
            request.session['searched_ids'] = gene_input
            request.session['per_page'] = per_page
            request.session['chart_data'] = chart_data

            paginator = Paginator(results, per_page)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            
            return render(request, 'tools/kegg_annotation/kegg_annotation_result.html', {
                'page_obj': page_obj,
                'gene_list': gene_list,
                'searched_ids': gene_input,
                'per_page': per_page,
                'chart_data': chart_data,
            })
    
    elif request.method == 'GET' and 'page' in request.GET:
        results = request.session.get('annotation_results', [])
        gene_input = request.session.get('searched_ids', '')
        per_page = request.session.get('per_page', 10)
        chart_data = request.session.get('chart_data', {})
        
        if not results:
            return render(request, 'tools/kegg_annotation/kegg_annotation.html')
        
        paginator = Paginator(results, per_page)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'tools/kegg_annotation/kegg_annotation_result.html', {
            'page_obj': page_obj,
            'gene_list': gene_input.split(),
            'searched_ids': gene_input,
            'per_page': per_page,
            'chart_data': chart_data,
        })
    
    return render(request, 'tools/kegg_annotation/kegg_annotation.html')

# 模拟任务存储（实际项目中应使用Redis或数据库）
TASKS = {}

@csrf_exempt
def start_kegg_annotation_api(request):
    # API视图：开始KEGG注释任务
    if request.method == 'POST':
        try:
            # 解析JSON数据
            data = json.loads(request.body)
            gene_ids = data.get('gene_id', '').strip()
            gene_list = [gene.strip() for gene in gene_ids.replace(',', '\n').split() if gene.strip()]
            
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 模拟异步任务
            # 实际项目中应使用Celery等任务队列
            TASKS[task_id] = {
                'status': 'processing',
                'created_at': time.time(),
                'parameters': {
                    'gene_list': gene_list
                }
            }
            
            # 执行注释
            results = []
            if gene_list:
                with connection.cursor() as cursor:
                    for gene_id in gene_list:
                        cursor.execute("""
                            SELECT Chr, Start, End, ID 
                            FROM `eg_go_annotation` 
                            WHERE ID = %s
                        """, [gene_id])
                        annotation_data = cursor.fetchall()

                        cursor.execute("""
                            SELECT  Query, `match` ,Description
                            FROM `eg_kegg` 
                            WHERE Query = %s
                        """, [gene_id])
                        kegg_data = cursor.fetchall()

                        for anno_row in annotation_data:
                            for ke_row in kegg_data:
                                results.append({
                                    'Chr': anno_row[0],
                                    'Start': anno_row[1],
                                    'End': anno_row[2],
                                    'ID': anno_row[3],
                                    'match': ke_row[1],
                                    'Description': ke_row[2],
                                })
            
            # 计算统计信息
            total_genes = len(gene_list)
            annotated_genes = len(results)
            
            # 统计匹配数据
            match_counts = Counter([result['match'] for result in results if result['match']])
            chart_data = {
                'labels': list(match_counts.keys()),
                'data': list(match_counts.values()),
            }
            
            # 更新任务状态
            TASKS[task_id].update({
                'status': 'success',
                'results': results,
                'total_genes': total_genes,
                'annotated_genes': annotated_genes,
                'chart_data': chart_data
            })
            
            # 返回任务ID
            return JsonResponse({
                'status': 'success',
                'task_id': task_id
            })
        
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'error': 'Method not allowed'
    })

@csrf_exempt
def get_kegg_annotation_results(request):
    # API视图：获取KEGG注释结果
    if request.method == 'GET':
        task_id = request.GET.get('task_id')
        if not task_id:
            return JsonResponse({
                'status': 'error',
                'error': 'Missing task_id parameter'
            })
        
        # 检查任务状态
        if task_id not in TASKS:
            return JsonResponse({
                'status': 'error',
                'error': 'Task not found'
            })
        
        task = TASKS[task_id]
        
        # 返回任务状态和结果
        if task['status'] == 'success':
            # 获取分页参数
            page_size = int(request.GET.get('page_size', 10))
            page = int(request.GET.get('page', 1))
            start = (page - 1) * page_size
            end = start + page_size
            
            # 返回分页结果
            return JsonResponse({
                'status': 'success',
                'results': task['results'][start:end],
                'total': len(task['results']),
                'total_genes': task['total_genes'],
                'annotated_genes': task['annotated_genes'],
                'chart_data': task['chart_data']
            })
        elif task['status'] == 'processing':
            return JsonResponse({
                'status': 'processing'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'error': task.get('error', 'Unknown error')
            })
    
    return JsonResponse({
        'status': 'error',
        'error': 'Method not allowed'
    })