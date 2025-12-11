import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection
import json
from django.http import JsonResponse

def gene_expression(request):
    # 定义三个选择框的选项
    top_options = ['Root', 'Stem', 'Cotyledon', 'Leaf','Pholem', 'Sepal', 'Bract', 'Petal', 'Anther', 'Stigma']
    bottom_left_options = ['0_DPA_ovules', '3_DPA_fibers', '6_DPA_fibers', '9_DPA_fibers', 
                          '12_DPA_fibers', '15_DPA_fibers', '18_DPA_fibers', '21_DPA_fibers', '24_DPA_fibers']
    bottom_right_options = ['DPA0', '5_DPA_ovules', '10_DPA_ovules', '20_DPA_ovules', 'Seed']
    
    # 设置默认选中的列（所有选项）
    default_selected_top = top_options
    default_selected_bottom_left = []
    default_selected_bottom_right = []
    
    # 检查是否是API请求
    is_api = request.headers.get('Accept') == 'application/json' or request.GET.get('api') == 'true'
    
    if request.method == 'POST':
        # 获取用户输入的基因ID（列格式，每行一个）
        gene_input = request.POST.get('gene_ids', '').strip()
        
        # 获取用户选择的列（如果用户有选择，则使用用户的选择，否则使用默认值）
        selected_top = request.POST.getlist('top_columns') or default_selected_top
        selected_bottom_left = request.POST.getlist('bottom_left_columns')
        selected_bottom_right = request.POST.getlist('bottom_right_columns')
        # 合并所有选中的列
        selected_columns = selected_top + selected_bottom_left + selected_bottom_right

        # 处理基因ID输入（每行一个）
        gene_ids = []
        if gene_input:
            lines = gene_input.split('\n')
            for line in lines:
                gene_id = line.strip()
                if gene_id:  # 只添加非空行
                    gene_ids.append(gene_id)
        
        if not gene_ids:
            error_msg = "请输入基因ID"
            if is_api:
                return JsonResponse({'error': error_msg}, status=400)
            return render(request, 'tools/gene_expression/gene_expression.html', {
                'error': error_msg,
                'gene_ids': gene_input,
                'top_options': top_options,
                'bottom_left_options': bottom_left_options,
                'bottom_right_options': bottom_right_options,
                'selected_top': selected_top,
                'selected_bottom_left': selected_bottom_left,
                'selected_bottom_right': selected_bottom_right
            })
        
        if not selected_columns:
            error_msg = "请至少选择一个组织/发育阶段"
            if is_api:
                return JsonResponse({'error': error_msg}, status=400)
            return render(request, 'tools/gene_expression.html', {
                'error': error_msg,
                'gene_ids': gene_input,
                'top_options': top_options,
                'bottom_left_options': bottom_left_options,
                'bottom_right_options': bottom_right_options,
                'selected_top': selected_top,
                'selected_bottom_left': selected_bottom_left,
                'selected_bottom_right': selected_bottom_right
            })
        
        try:
            # 从数据库获取数据
            heatmap_data, gene_ids_list, columns_list = generate_gene_expression_data(gene_ids, selected_columns)
            
            result_data = {
                'heatmap_data': heatmap_data,
                'gene_ids': gene_ids_list,
                'columns': columns_list,
                'options': {
                    'top': top_options,
                    'bottom_left': bottom_left_options,
                    'bottom_right': bottom_right_options
                },
                'selected': {
                    'top': selected_top,
                    'bottom_left': selected_bottom_left,
                    'bottom_right': selected_bottom_right
                }
            }
            
            if is_api:
                return JsonResponse({
                    'success': True,
                    'data': result_data
                })
            
            # 将数据传递给模板
            context = {
                'heatmap_data': json.dumps(heatmap_data),
                'gene_ids': json.dumps(gene_ids_list),
                'columns': json.dumps(columns_list),
                'gene_id': ', '.join(gene_ids),
                'top_options': top_options,
                'bottom_left_options': bottom_left_options,
                'bottom_right_options': bottom_right_options,
                'selected_top': selected_top,
                'selected_bottom_left': selected_bottom_left,
                'selected_bottom_right': selected_bottom_right
            }
            return render(request, 'tools/gene_expression_result.html', context)
            
        except Exception as e:
            error_msg = f"处理数据时出错: {str(e)}"
            if is_api:
                return JsonResponse({'error': error_msg}, status=500)
            return render(request, 'tools/gene_expression.html', {
                'error': error_msg,
                'gene_ids': gene_input,
                'top_options': top_options,
                'bottom_left_options': bottom_left_options,
                'bottom_right_options': bottom_right_options,
                'selected_top': selected_top,
                'selected_bottom_left': selected_bottom_left,
                'selected_bottom_right': selected_bottom_right
            })
    
    if is_api:
        return JsonResponse({
            'success': True,
            'options': {
                'top': top_options,
                'bottom_left': bottom_left_options,
                'bottom_right': bottom_right_options
            },
            'default_selected': {
                'top': default_selected_top,
                'bottom_left': default_selected_bottom_left,
                'bottom_right': default_selected_bottom_right
            }
        })
    
    # GET请求显示输入表单（使用默认选中所有选项）
    return render(request, 'tools/gene_expression.html', {
        'top_options': top_options,
        'bottom_left_options': bottom_left_options,
        'bottom_right_options': bottom_right_options,
        'selected_top': default_selected_top,
        'selected_bottom_left': default_selected_bottom_left,
        'selected_bottom_right': default_selected_bottom_right
    })

def generate_gene_expression_data(gene_ids, selected_columns):
    # 构建SQL查询
    columns_str = ', '.join(selected_columns)
    placeholders = ', '.join(['%s'] * len(gene_ids))
    query = f"SELECT gene_id, {columns_str} FROM fpkm4 WHERE gene_id IN ({placeholders})"
    
    # 执行查询
    with connection.cursor() as cursor:
        cursor.execute(query, gene_ids)
        rows = cursor.fetchall()
    
    if not rows:
        raise ValueError(f"未找到基因ID: {gene_ids}")
    
    # 创建DataFrame
    data = []
    gene_ids_list = []
    for row in rows:
        row_data = {}
        for i, col in enumerate(['gene_id'] + selected_columns):
            # 保留原始值，不进行转换
            row_data[col] = row[i]
        data.append(row_data)
        gene_ids_list.append(row[0])  # 添加基因ID到列表
    
    df = pd.DataFrame(data)
    df.set_index('gene_id', inplace=True)
    
    # 处理数据：将"NA"字符串转换为None，其他转换为数值
    processed_data = []
    for gene_id in gene_ids_list:
        row_data = []
        for col in selected_columns:
            value = df.loc[gene_id, col]
            if value in ['NA', 'na', 'N/A', ''] or value is None:
                row_data.append(None)  # 使用None表示缺失值
            else:
                try:
                    # 转换为数值并进行对数转换
                    numeric_value = float(value)
                    log_value = np.log2(numeric_value + 1)
                    row_data.append(log_value)
                except (ValueError, TypeError):
                    row_data.append(None)
        processed_data.append(row_data)
    
    return processed_data, gene_ids_list, selected_columns