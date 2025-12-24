import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import logging
from django.db import connection
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt

# 抑制matplotlib调试日志
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

@csrf_exempt
def gene_expression(request):
    # ===== 选项定义 =====
    TOP = ['Root', 'Stem', 'Cotyledon', 'Leaf','Pholem', 'Sepal', 'Bract', 'Petal', 'Anther', 'Stigma']
    BL  = ['0_DPA_ovules', '3_DPA_fibers', '6_DPA_fibers', '9_DPA_fibers',
           '12_DPA_fibers', '15_DPA_fibers', '18_DPA_fibers', '21_DPA_fibers', '24_DPA_fibers']
    BR  = ['DPA0', '5_DPA_ovules', '10_DPA_ovules', '20_DPA_ovules', 'Seed']

    is_api = request.headers.get('Accept') == 'application/json' or request.GET.get('api') == 'true'

    if request.method != 'POST':
        return JsonResponse({
            'success': True,
            'options': {'top': TOP, 'bottom_left': BL, 'bottom_right': BR},
            'default_selected': {'top': TOP, 'bottom_left': [], 'bottom_right': []}
        })

    # ===== 参数解析 =====
    gene_ids = [g.strip() for g in request.POST.get('gene_ids', '').splitlines() if g.strip()]
    selected_columns = (
        request.POST.getlist('top_columns') or TOP
    ) + request.POST.getlist('bottom_left_columns') + request.POST.getlist('bottom_right_columns')

    if not gene_ids or not selected_columns:
        return JsonResponse({'error': 'gene_id 或列不能为空'}, status=400)

    # ===== 数据处理 =====
    try:
        heatmap_data, numeric_data, gene_ids_list, columns = \
            generate_gene_expression_data(gene_ids, selected_columns)

        return JsonResponse({
            'success': True,
            'data': {
                'gene_ids': gene_ids_list,
                'columns': columns,
                'heatmap_data': heatmap_data,
                'heatmap_image': generate_heatmap_image(numeric_data, gene_ids_list, columns)
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def generate_gene_expression_data(gene_ids, selected_columns):
    cols = ', '.join(selected_columns)
    ph   = ', '.join(['%s'] * len(gene_ids))

    query = f"""
        SELECT gene_id, {cols}
        FROM fpkm4
        WHERE gene_id IN ({ph})
        GROUP BY gene_id
        ORDER BY FIELD(gene_id, {ph})
    """

    with connection.cursor() as cursor:
        cursor.execute(query, gene_ids * 2)
        rows = cursor.fetchall()

    if not rows:
        raise ValueError('未找到基因')

    gene_ids_list = []
    numeric_data  = []
    heatmap_data  = []

    for row in rows:
        gene_ids_list.append(row[0])

        row_vals = []
        num_vals = []
        for v in row[1:]:
            if v in (None, 'NA', 'na', ''):
                row_vals.append(None)
                num_vals.append(np.nan)
            else:
                val = np.log2(float(v) + 1)
                row_vals.append(val)
                num_vals.append(val)

        heatmap_data.append(row_vals)
        numeric_data.append(num_vals)

    return heatmap_data, numeric_data, gene_ids_list, selected_columns



def generate_heatmap_image(numeric_data, gene_ids_list, selected_columns):
    # 创建DataFrame
    df = pd.DataFrame(numeric_data, index=gene_ids_list, columns=selected_columns)
    
    # 设置图形大小
    plt.figure(figsize=(12, max(5, len(gene_ids_list) * 0.5)))
    
    # 使用seaborn绘制热图
    ax = sns.heatmap(df, cmap='RdYlBu_r', 
                    vmin=0, vmax=15,  # 设置颜色范围
                    xticklabels=True, yticklabels=True, 
                    cbar_kws={'label': 'Log2(FPKM+1)'})
    
    # 设置x轴标签旋转
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    
    # 设置标题
    plt.title('Gene Expression Heatmap', fontsize=14)
    
    # 调整布局
    plt.tight_layout()
    
    # 将图形转换为base64字符串
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    
    # 转换为base64
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    plt.close()
    
    return image_base64
