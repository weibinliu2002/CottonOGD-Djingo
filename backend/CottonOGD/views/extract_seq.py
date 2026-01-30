from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
from CottonOGD.models import gene_seq
import logging
logger = logging.getLogger(__name__)


@api_view(['POST'])
def extract_seq(request):
    if request.method == 'POST':
        '''
        uuid = request.headers.get('uuid')
        if not uuid or uuid not in UuidManager.uuid_storage:
            return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)'''
        db_id = request.data.get('db_id')
        logger.info(f"extract_seq db_id: {db_id}")
        if not db_id:
            return Response({'error': 'db_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 确保 db_id 是一个列表
        if not isinstance(db_id, list):
            db_id = [db_id]
        
        # 尝试将每个值转换为整数
        converted_db_id = []
        for id_value in db_id:
            try:
                converted_id = int(id_value)
                converted_db_id.append(converted_id)
            except (ValueError, TypeError):
                # 跳过无法转换为整数的值
                logger.warning(f"Invalid db_id value skipped: {id_value}")
        
        db_id = converted_db_id
        
        if not db_id:
            return Response({'error': 'db_id must contain valid integers'}, status=status.HTTP_400_BAD_REQUEST)
        
        gene_seqs=gene_seq.objects.filter(id_id__in=db_id)
        seq_data={
            'genome_seq':gene_seqs.filter(gene_type='genome'),
            'mrna_seq':gene_seqs.filter(gene_type='mRNA'),
            'upstream_seq':gene_seqs.filter(gene_type='upstream'),
            'downstream_seq':gene_seqs.filter(gene_type='downstream'),
            'cdna_seq':gene_seqs.filter(gene_type='cdna'),
            'cds_seq':gene_seqs.filter(gene_type='cds'),
            'protein_seq':gene_seqs.filter(gene_type='protein'),
        }
        for key in seq_data:
            seq_data[key]=[{'id':item.id_id,'seq':item.sequence} for item in seq_data[key]]
        

        return Response({'seq': seq_data}, status=status.HTTP_200_OK)
        
