from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
from CottonOGD.models import gene_seq
import json
import logging
logger = logging.getLogger(__name__)


@api_view(['POST'])
def extract_seq(request):
    if request.method == 'POST':
        '''
        uuid = request.headers.get('uuid')
        if not uuid or uuid not in UuidManager.uuid_storage:
            return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)'''
        # 支持两种方式：直接使用 db_id，或者通过 gene_id 和 genome_id 获取
        db_id = request.data.get('db_id')
        gene_id = request.data.get('gene_id')
        genome_id = request.data.get('genome_id')
        
        # 如果没有提供 db_id，则使用 gene_id 和 genome_id
        if not db_id:
            if not gene_id or not genome_id:
                return Response({'error': 'db_id or (gene_id and genome_id) are required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 使用 Id_map 获取 db_id
            db_map = Id_map(gene_id, genome_id)
            logger.info(f"extract_seq db_map: {db_map}")
            
            # 从 db_map 中提取 db_id
            db_ids = []
            if isinstance(db_map, dict):
                for key, value in db_map.items():
                    if isinstance(value, dict) and 'db_id' in value:
                        db_ids.append(value['db_id'])
            
            if not db_ids:
                return Response({'error': 'Gene not found'}, status=status.HTTP_404_NOT_FOUND)
            
            db_id = db_ids
        
        logger.info(f"extract_seq db_id: {db_id}")
        
        # 处理 db_id 参数
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
        
        gene_seqs=gene_seq.objects.filter(id_id__in=db_id)
        seq_data={
            'genome_seq': [{'db_id': item.id_id, 'seq': item.sequence,'gene_type':item.gene_type,'mrna_id':item.mrna_id} for item in gene_seqs.filter(gene_type='genome')],
            'mrna_seq': [{'db_id': item.id_id, 'seq': item.sequence,'gene_type':item.gene_type,'mrna_id':item.mrna_id} for item in gene_seqs.filter(gene_type='mRNA')],
            'upstream_seq': [{'db_id': item.id_id, 'seq': item.sequence,'gene_type':item.gene_type,'mrna_id':item.mrna_id} for item in gene_seqs.filter(gene_type='upstream')],
            'downstream_seq': [{'db_id': item.id_id, 'seq': item.sequence,'gene_type':item.gene_type,'mrna_id':item.mrna_id} for item in gene_seqs.filter(gene_type='downstream')],
            'cdna_seq': [{'db_id': item.id_id, 'seq': item.sequence,'gene_type':item.gene_type,'mrna_id':item.mrna_id} for item in gene_seqs.filter(gene_type='cdna')],
            'cds_seq': [{'db_id': item.id_id, 'seq': item.sequence,'gene_type':item.gene_type,'mrna_id':item.mrna_id} for item in gene_seqs.filter(gene_type='cds')],
            'protein_seq': [{'db_id': item.id_id, 'seq': item.sequence,'gene_type':item.gene_type,'mrna_id':item.mrna_id} for item in gene_seqs.filter(gene_type='pro')]
        }
        
        return Response({'seq': seq_data}, status=status.HTTP_200_OK)
        
