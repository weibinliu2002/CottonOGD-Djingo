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
        uuid = request.headers.get('uuid')
        if not uuid or uuid not in UuidManager.uuid_storage:
            return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 处理批量查询的情况（db_id参数）
        db_id = request.data.get('db_id')
        if db_id:
            logger.info(f"extract_seq db_id: {db_id}")
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
            return Response({'seq': seq_data}, status=status.HTTP_200_OK)
        
        # 处理单个序列查询的情况（gene_id、transcript_id、type参数）
        gene_id = request.data.get('gene_id')
        transcript_id = request.data.get('transcript_id')
        type = request.data.get('type')
        
        if not gene_id or not type:
            return Response({'error': 'gene_id and type are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"extract_seq gene_id: {gene_id}, transcript_id: {transcript_id}, type: {type}")
        
        # 根据type参数映射到gene_type
        type_map = {
            'mrna': 'mRNA',
            'cdna': 'cdna',
            'cds': 'cds',
            'protein': 'protein',
            'upstream': 'upstream',
            'downstream': 'downstream'
        }
        
        gene_type = type_map.get(type, type)
        
        # 查询序列
        query = gene_seq.objects.filter(geneid__geneid=gene_id, gene_type=gene_type)
        if transcript_id:
            query = query.filter(mrna_id=transcript_id)
        
        gene_seq_obj = query.first()
        sequence = gene_seq_obj.sequence if gene_seq_obj else '未找到序列'
        
        return Response({'sequence': sequence}, status=status.HTTP_200_OK)
        
