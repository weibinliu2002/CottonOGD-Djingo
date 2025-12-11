from django.shortcuts import render
from django.db import connection
from django.core.paginator import Paginator
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
from django.http import JsonResponse

import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def go_annotation(request):
    # 记录请求信息
    logger.debug(f"请求方法: {request.method}")
    logger.debug(f"请求路径: {request.path}")
    logger.debug(f"GET参数: {request.GET}")
    logger.debug(f"请求头: {dict(request.headers)}")
    
    # 检查是否是API请求
    is_api = request.headers.get('Accept') == 'application/json' or request.GET.get('api') == 'true'
    logger.debug(f"is_api标志: {is_api}")
    
    # 处理GET请求，支持直接通过gene_id参数获取结果
    if request.method == 'GET':
        # 检查是否有gene_id参数
        gene_input = request.GET.get('gene_id', '').strip()
        logger.debug(f"gene_input: '{gene_input}'")
        logger.debug(f"gene_input长度: {len(gene_input)}")
        
        if gene_input:
            per_page = int(request.GET.get('per_page', 10))
            page = int(request.GET.get('page', 1))
            
            gene_list = [gene.strip().upper() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
            
            results = []
            chart = None
            chart_data = None
            categories = []
            
            if gene_list:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT Chr, Start, End, ID 
                        FROM `eg_go_annotation` 
                        WHERE ID IN %s
                    """, [tuple(gene_list)])
                    annotation_data = cursor.fetchall()

                    cursor.execute("""
                        SELECT `Gene_Ontology`, Description, `GO_ID`, Query, dddd
                        FROM `eg_go_enrichment` 
                        WHERE Query IN %s
                    """, [tuple(gene_list)])
                    enrichment_data = cursor.fetchall()

                    for anno_row in annotation_data:
                        for enrich_row in enrichment_data:
                            if anno_row[3] == enrich_row[3]:
                                results.append({
                                    'Chr': anno_row[0],
                                    'Start': anno_row[1],
                                    'End': anno_row[2],
                                    'ID': anno_row[3],
                                    'GO_ID': enrich_row[2],
                                    'Description': enrich_row[1],
                                    'Gene_Ontology': enrich_row[0],
                                    'dddd': enrich_row[4]
                                })
                    
                    chart_data = {'BP': {}, 'MF': {}, 'CC': {}}

                    for result in results:
                        go_type = result['Gene_Ontology']
                        dddd_value = result['dddd']
                        if go_type in chart_data:
                            if dddd_value in chart_data[go_type]:
                                chart_data[go_type][dddd_value] += 1
                            else:
                                chart_data[go_type][dddd_value] = 1

                    categories = sorted({result['dddd'] for result in results if result['dddd']})
                    data = {
                        'BP': [chart_data['BP'].get(cat, 0) for cat in categories],
                        'MF': [chart_data['MF'].get(cat, 0) for cat in categories],
                        'CC': [chart_data['CC'].get(cat, 0) for cat in categories]
                    }

                    # 生成图表
                    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
                    axes = [ax1, ax2, ax3]
                    
                    max_value = max(max(data['BP']), max(data['MF']), max(data['CC'])) * 1.1
                    for ax in axes:
                        ax.set_ylim(0, max_value)
                        ax.grid(False) 

                    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
                    
                    for i, (ax, (group, values), color) in enumerate(zip(axes, data.items(), colors)):
                        bars = ax.bar(categories, values, color=color)
                        ax.set_title(group, fontsize=14, pad=15)
                        ax.set_xlabel('', fontsize=12)

                        ax.spines['top'].set_visible(False)
                        ax.spines['right'].set_visible(False)

                        if i > 0: 
                            ax.spines['left'].set_visible(False)
                            ax.tick_params(left=False)
                        
                        for bar in bars:
                            height = bar.get_height()
                            if height > 0:
                                ax.text(bar.get_x() + bar.get_width()/2., height,
                                        f'{int(height)}',
                                        ha='center', va='bottom', fontsize=10)
                    
                    ax1.set_ylabel('Count', fontsize=12)
                    
                    plt.tight_layout()

                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', bbox_inches='tight')
                    plt.close()
                    chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # 直接返回JSON响应，不依赖is_api标志
                return JsonResponse({
                    'success': True,
                    'data': {
                        'results': results,
                        'gene_list': gene_list,
                        'searched_ids': gene_input,
                        'per_page': per_page,
                        'chart': chart,
                        'chart_data': {
                            'data': data,
                            'categories': categories
                        }
                    }
                })
            else:
                # 当gene_list为空时，返回空结果
                return JsonResponse({
                    'success': True,
                    'data': {
                        'results': [],
                        'gene_list': [],
                        'searched_ids': gene_input,
                        'per_page': per_page,
                        'chart': None,
                        'chart_data': {
                            'data': {},
                            'categories': []
                        }
                    }
                })
        
        # 处理带page参数的GET请求
        elif 'page' in request.GET:
            results = request.session.get('annotation_results', [])
            gene_input = request.session.get('searched_ids', '')
            per_page = request.session.get('per_page', 10)
            chart = request.session.get('chart', None)
            
            if not results:
                if is_api:
                    return JsonResponse({'error': 'No results found in session'}, status=404)
                return render(request, 'tools/go_annotation/go_annotation.html')

            paginator = Paginator(results, per_page)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            
            if is_api:
                return JsonResponse({
                    'success': True,
                    'data': {
                        'results': [item for item in page_obj],
                        'gene_list': gene_input.split(),
                        'searched_ids': gene_input,
                        'per_page': per_page,
                        'chart': chart,
                        'pagination': {
                            'current_page': page_obj.number,
                            'total_pages': paginator.num_pages,
                            'total_results': paginator.count,
                            'has_next': page_obj.has_next(),
                            'has_previous': page_obj.has_previous()
                        }
                    }
                })
            
            return render(request, 'tools/go_annotation/go_annotation_result.html', {
                'page_obj': page_obj,
                'gene_list': gene_input.split(),
                'searched_ids': gene_input,
                'per_page': per_page,
                'chart': chart
            })
    
    # 处理POST请求
    elif request.method == 'POST':
        gene_input = request.POST.get('gene_id', '').strip()
        per_page = int(request.POST.get('per_page', 10))
        
        gene_list = [gene.strip() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        results = []
        chart = None
        chart_data = None
        categories = []
        
        if gene_list:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT Chr, Start, End, ID 
                    FROM `eg_go_annotation` 
                    WHERE ID IN %s
                """, [tuple(gene_list)])
                annotation_data = cursor.fetchall()

                cursor.execute("""
                    SELECT `Gene_Ontology`, Description, `GO_ID`, Query, dddd
                    FROM `eg_go_enrichment` 
                    WHERE Query IN %s
                """, [tuple(gene_list)])
                enrichment_data = cursor.fetchall()

                for anno_row in annotation_data:
                    for enrich_row in enrichment_data:
                        if anno_row[3] == enrich_row[3]:
                            results.append({
                                'Chr': anno_row[0],
                                'Start': anno_row[1],
                                'End': anno_row[2],
                                'ID': anno_row[3],
                                'GO_ID': enrich_row[2],
                                'Description': enrich_row[1],
                                'Gene_Ontology': enrich_row[0],
                                'dddd': enrich_row[4]
                            })
                    
                chart_data = {'BP': {}, 'MF': {}, 'CC': {}}

                for result in results:
                    go_type = result['Gene_Ontology']
                    dddd_value = result['dddd']
                    if go_type in chart_data:
                        if dddd_value in chart_data[go_type]:
                            chart_data[go_type][dddd_value] += 1
                        else:
                            chart_data[go_type][dddd_value] = 1

                categories = sorted({result['dddd'] for result in results if result['dddd']})
                data = {
                    'BP': [chart_data['BP'].get(cat, 0) for cat in categories],
                    'MF': [chart_data['MF'].get(cat, 0) for cat in categories],
                    'CC': [chart_data['CC'].get(cat, 0) for cat in categories]
                }

                # 生成图表
                fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
                axes = [ax1, ax2, ax3]
                
                max_value = max(max(data['BP']), max(data['MF']), max(data['CC'])) * 1.1
                for ax in axes:
                    ax.set_ylim(0, max_value)
                    ax.grid(False) 

                colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
                
                for i, (ax, (group, values), color) in enumerate(zip(axes, data.items(), colors)):
                    bars = ax.bar(categories, values, color=color)
                    ax.set_title(group, fontsize=14, pad=15)
                    ax.set_xlabel('', fontsize=12)

                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)

                    if i > 0: 
                        ax.spines['left'].set_visible(False)
                        ax.tick_params(left=False)
                    
                    for bar in bars:
                        height = bar.get_height()
                        if height > 0:
                            ax.text(bar.get_x() + bar.get_width()/2., height,
                                    f'{int(height)}',
                                    ha='center', va='bottom', fontsize=10)
                
                ax1.set_ylabel('Count', fontsize=12)
                
                plt.tight_layout()

                buffer = BytesIO()
                plt.savefig(buffer, format='png', bbox_inches='tight')
                plt.close()
                chart = base64.b64encode(buffer.getvalue()).decode('utf-8')

            if is_api:
                return JsonResponse({
                    'success': True,
                    'data': {
                        'results': results,
                        'gene_list': gene_list,
                        'searched_ids': gene_input,
                        'per_page': per_page,
                        'chart': chart,
                        'chart_data': {
                            'data': data,
                            'categories': categories
                        }
                    }
                })
            
            request.session['annotation_results'] = results
            request.session['searched_ids'] = gene_input
            request.session['per_page'] = per_page
            request.session['chart'] = chart

            paginator = Paginator(results, per_page)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            
            return render(request, 'tools/go_annotation/go_annotation_result.html', {
                'page_obj': page_obj,
                'gene_list': gene_list,
                'searched_ids': gene_input,
                'per_page': per_page,
                'chart': chart
            })
    
    # 处理API请求，返回欢迎信息
    if is_api:
        return JsonResponse({
            'success': True,
            'message': 'GO Annotation API is ready'
        })
    
    # 默认返回HTML页面
    return render(request, 'tools/go_annotation/go_annotation.html')