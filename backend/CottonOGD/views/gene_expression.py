from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
from CottonOGD.models import gene_expression
import pandas as pd
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import json
import io ,re
import base64

import logging
logger = logging.getLogger(__name__)

TISSUE_ORDER = [
    'Root', 'Stem', 'Cotyledon', 'Leaf', 'Pholem', 
    'Sepal', 'Bract', 'Petal', 'Anther', 'Stigma', 
    'Ovules', 'Fibers', 'Seed'
]

def get_sort_key(row):
    tissue = row['tissue']
    stage = row['stage'] if row['stage'] else ''
    try:
        tissue_idx = TISSUE_ORDER.index(tissue)
    except ValueError:
        tissue_idx = len(TISSUE_ORDER)
    return (tissue_idx, stage)

def generate_heatmap_image(numeric_data, gene_ids_list, selected_columns):
    # 创建DataFrame
    df = pd.DataFrame(numeric_data, index=gene_ids_list, columns=selected_columns)
    
    # 设置图形大小
    # 计算合适的图形大小
    # 根据基因数量和组织数量动态调整
    num_genes = len(gene_ids_list)
    num_tissues = len(selected_columns)
    
    # 基础宽度和高度
    base_width = max(12, num_tissues * 1.2)  # 每个组织至少1.2英寸
    base_height = max(5, num_genes * 0.6)    # 每个基因至少0.6英寸
    
    # 限制最大大小，避免内存问题
    max_width = 30
    max_height = 20
    
    fig_width = min(base_width, max_width)
    fig_height = min(base_height, max_height)
    
    # 创建图形和轴
    f, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    # 使用seaborn绘制热图，添加数值显示（仅当数据量适中时）
    annot = False
    fmt = '.2f'
    
    # 当数据量适中时显示数值
    if num_genes <= 10 and num_tissues <= 15:
        annot = True
    
    ax = sns.heatmap(df, cmap='RdYlBu_r', 
                    vmin=0, vmax=15,  # 设置颜色范围
                    xticklabels=True, yticklabels=True, 
                    cbar_kws={'label': 'FPKM'},
                    annot=annot,  # 显示数值（数据量适中时）
                    fmt=fmt,  # 数值格式，保留2位小数
                    linewidths=.5,  # 网格线宽度
                    ax=ax)  # 指定轴
    
    # 设置x轴标签旋转和字体大小
    ax.set_xticklabels(ax.get_xticklabels(), rotation=60, ha='right', fontsize=8)
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=8)
    
    # 设置标题
    ax.set_title('Gene Expression Heatmap', fontsize=12)
    
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


@api_view(['POST'])
def extract_expression(request):
    if request.method == 'POST':
        '''
        uuid = request.headers.get('uuid')
        if not uuid or uuid not in UuidManager.uuid_storage:
            return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
        db_id = request.data.get('db_id')'''
        db_id  = request.data.get('db_id') or request.query_params.get('db_id')
        if not db_id:
             # 从多个来源获取 gene_id：请求体、查询参数
            gene_id = request.data.get('gene_id') or request.query_params.get('gene_id')
            genome_id = request.data.get('genome_id') or request.query_params.get('genome_id')
            logger.info(f"genome_id: {genome_id}, gene_id: {gene_id}")
            id_map_result = Id_map(gene_id, genome_id)
            
            # 从 id_map_result 中提取 db_id 值
            db_id = []
            if isinstance(id_map_result, dict):
                for gid, info in id_map_result.items():
                    if info.get('db_id'):
                        db_id.append(info['db_id'])
            logger.info(f"Extracted db_id: {db_id}")
            #return Response({'error': 'db_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(db_id, str):
            # 如果是逗号分割的字符串，分割并转换为整数
            db_id = db_id.split(',')
        
        # 确保 db_id 是一个列表
        if not isinstance(db_id, list):
            db_id = [db_id]
        
        # 尝试将每个值转换为整数
        converted_db_id = []
        for id_value in db_id:
            try:
                converted_id = int(float(id_value))
                logger.info(f"Converted db_id value: {converted_id}")
                converted_db_id.append(converted_id)
            except (ValueError, TypeError):
                # 跳过无法转换为整数的值
                logger.warning(f"Invalid db_id value skipped: {id_value}")
        
        db_id = converted_db_id
        #logger.info(db_id)
        #db_id=[10,12]
        
        if not db_id:
            return Response({'error': 'db_id must contain valid integers'}, status=status.HTTP_400_BAD_REQUEST)

        sample_id = request.data.get('sample_id') or request.query_params.get('sample_id')
        gene_expr=gene_expression.objects.filter(id_id__in=db_id).values('id_id','geneid','stage','tissue','value')
        df = pd.DataFrame(list(gene_expr))
        
        # 处理空值
        df['stage'] = df['stage'].fillna('')
        df['tissue'] = df['tissue'].fillna('Unknown')
        
        # 对数据进行排序：先按组织，再按时期（数字顺序）
        df_sorted = df.copy()
        # 添加组织索引列用于排序
        df_sorted['tissue_idx'] = df_sorted['tissue'].apply(lambda x: TISSUE_ORDER.index(x) if x in TISSUE_ORDER else len(TISSUE_ORDER))
        # 从stage中提取数字部分用于排序
        df_sorted['stage_num'] = df_sorted['stage'].str.extract(r'(\d+)').astype(float).fillna(0)
        # 按组织索引和时期数字排序
        df_sorted = df_sorted.sort_values(by=['tissue_idx', 'stage_num'], ascending=[True, True])
        
        # 构建sample列名，处理空stage的情况
        df_sorted['sample'] = df_sorted.apply(lambda row: 
            re.sub(r'^X(\d+)', r'\1', row['stage']) + row['tissue'] if row['stage'] else row['tissue'], 
            axis=1
        )
        result = df_sorted.pivot_table(
            index=['id_id', 'geneid'],  # 保持不变的ID列
            columns='sample',               # stage_tissue 组合成列名
            values='value',                 # 表达量作为值
            aggfunc='mean'                  # 如果有重复值，取平均（可选：'first', 'sum'）
        ).reset_index()
        result.columns.name = None
        
        # 确保列的顺序也是按照排序后的顺序
        sample_order = df_sorted['sample'].unique()
        existing_columns = [col for col in sample_order if col in result.columns]
        id_columns = ['id_id', 'geneid']
        result = result[id_columns + existing_columns]
       

        # 生成热图
        heatmap_image = generate_heatmap_image(
            numeric_data=result.drop(columns=['id_id', 'geneid']).values,
            gene_ids_list=result['geneid'].tolist(),
            selected_columns=result.columns[2:]  # 从第3列开始是样本列
        )
        
        return Response({'expression': result.to_dict(orient='records'),'heatmap_image':heatmap_image}, status=status.HTTP_200_OK)
        # return Response({'expression': gene_expr}, status=status.HTTP_200_OK)


