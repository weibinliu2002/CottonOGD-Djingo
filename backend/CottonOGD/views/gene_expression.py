from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
from CottonOGD.models import gene_expression
import pandas as pd
import re
import logging
logger = logging.getLogger(__name__)

# 尝试导入Clustergrammer-PY
try:
    from clustergrammer import Network
    CLUSTERGRAMMER_AVAILABLE = True
except ImportError:
    CLUSTERGRAMMER_AVAILABLE = False
    logger.warning('Clustergrammer-PY not available, will use basic JSON format')

TISSUE_ORDER = [
    'Root', 'Stem', 'Cotyledon', 'Leaf', 'Pholem', 
    'Sepal', 'Bract', 'Petal', 'Anther', 'Stigma', 
    'Ovules', 'Fibers', 'Seed'
]

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
            
            # 检查gene_id和genome_id是否都有值
            if not gene_id or not genome_id:
                return Response({'error': 'gene_id and genome_id are required when db_id is not provided'}, status=status.HTTP_400_BAD_REQUEST)
                
            id_map_result = Id_map(gene_id, genome_id)
            
            # 从 id_map_result 中提取 db_id 值
            db_id = []
            if isinstance(id_map_result, dict):
                for gid, info in id_map_result.items():
                    if info.get('db_id'):
                        db_id.append(info['db_id'])
            logger.info(f"Extracted db_id: {db_id}")
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
        
        if not db_id:
            return Response({'error': 'db_id must contain valid integers'}, status=status.HTTP_400_BAD_REQUEST)

        sample_id = request.data.get('sample_id') or request.query_params.get('sample_id')
        gene_expr=gene_expression.objects.filter(id_id__in=db_id).values('id_id','geneid','stage','tissue','value')
        df = pd.DataFrame(list(gene_expr))
        
        # 处理空值
        df['stage'] = df['stage'].fillna('')
        df['tissue'] = df['tissue'].fillna('Unknown')
        
        # 构建sample列名，处理空stage的情况
        df['sample'] = df.apply(lambda row: 
            re.sub(r'^X(\d+)', r'\1', row['stage']) + row['tissue'] if row['stage'] else row['tissue'], 
            axis=1
        )
        
        # 对数据进行排序：先按组织，再按时期（数字顺序）
        # 添加组织索引列用于排序
        df['tissue_idx'] = df['tissue'].apply(lambda x: TISSUE_ORDER.index(x) if x in TISSUE_ORDER else len(TISSUE_ORDER))
        # 从stage中提取数字部分用于排序
        df['stage_num'] = df['stage'].str.extract(r'(\d+)').astype(float).fillna(0)
        # 按组织索引和时期数字排序
        df = df.sort_values(by=['tissue_idx', 'stage_num'], ascending=[True, True])
        
        # 直接使用pivot_table，不创建中间副本
        result = df.pivot_table(
            index=['id_id', 'geneid'],  # 保持不变的ID列
            columns='sample',               # stage_tissue 组合成列名
            values='value',                 # 表达量作为值
            aggfunc='mean'                  # 如果有重复值，取平均（可选：'first', 'sum'）
        ).reset_index()
        result.columns.name = None
        
        # 确保列的顺序也是按照排序后的顺序
        sample_order = df['sample'].unique()
        existing_columns = [col for col in sample_order if col in result.columns]
        id_columns = ['id_id', 'geneid']
        result = result[id_columns + existing_columns]
       
        # 准备前端需要的数据格式
        genes_data = []
        tissues = existing_columns
        
        for _, row in result.iterrows():
            gene_data = {
                'gene_id': row['geneid'],
                'expression': {}
            }
            for tissue in tissues:
                gene_data['expression'][tissue] = float(row[tissue]) if pd.notna(row[tissue]) else 0
            genes_data.append(gene_data)
        
        # 使用Clustergrammer-PY生成可视化JSON（如果可用）
        if CLUSTERGRAMMER_AVAILABLE:
            try:
                net = Network()
                # 转换数据为Clustergrammer格式
                for _, row in result.iterrows():
                    gene_id = row['geneid']
                    for tissue in tissues:
                        value = float(row[tissue]) if pd.notna(row[tissue]) else 0
                        net.add_row(gene_id, tissue, value)
                
                # 聚类数据
                net.make_clust()
                
                # 获取可视化JSON
                clustergrammer_json = net.export_net_json()
                
                return Response({
                    'expression': result.to_dict(orient='records'),
                    'genes': genes_data,
                    'tissues': tissues,
                    'clustergrammer_data': clustergrammer_json
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error('Error generating Clustergrammer JSON: %s', e)
                # 如果生成失败，返回基本格式
                return Response({
                    'expression': result.to_dict(orient='records'),
                    'genes': genes_data,
                    'tissues': tissues
                }, status=status.HTTP_200_OK)
        else:
            # Clustergrammer-PY不可用时，返回基本格式
            return Response({
                'expression': result.to_dict(orient='records'),
                'genes': genes_data,
                'tissues': tissues
            }, status=status.HTTP_200_OK)
