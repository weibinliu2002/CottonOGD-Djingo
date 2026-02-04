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
import io
import base64

import logging
logger = logging.getLogger(__name__)

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
        gene_expr=gene_expression.objects.filter(id_id__in=db_id).values('id_id','geneid_id','stage','tissue','value')
        df = pd.DataFrame(list(gene_expr))
        df['sample'] = df['stage'] + '' + df['tissue']
        result = df.pivot_table(
            index=['id_id', 'geneid_id'],  # 保持不变的ID列
            columns='sample',               # stage_tissue 组合成列名
            values='value',                 # 表达量作为值
            aggfunc='mean'                  # 如果有重复值，取平均（可选：'first', 'sum'）
        ).reset_index()
        result.columns.name = None
       

        # 生成热图
        heatmap_image = generate_heatmap_image(
            numeric_data=result.drop(columns=['id_id', 'geneid_id']).values,
            gene_ids_list=result['geneid_id'].tolist(),
            selected_columns=result.columns[2:]  # 从第3列开始是样本列
        )
        
        return Response({'expression': result.to_dict(orient='records'),'heatmap_image':heatmap_image}, status=status.HTTP_200_OK)
        # return Response({'expression': gene_expr}, status=status.HTTP_200_OK)


