from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from django.conf import settings
import logging
import os
# 使用 pyfastx 提取序列
import pyfaidx

logger = logging.getLogger(__name__)


def extract_sequence_from_genome_file(genome_id, seqid, start, end, strand):
    """
    从基因组文件中根据位置提取序列
    :param genome_id: 基因组 ID
    :param seqid: 染色体/ scaffold ID
    :param start: 起始位置
    :param end: 结束位置
    :param strand: 链方向 (+/-)
    :return: 提取的序列
    """
    try:
        # 基因组文件路径（根据实际情况调整）
        genome_dir = os.path.join(settings.BASE_DIR, 'data', 'genome', genome_id)
        genome_file = os.path.join(genome_dir, f'{genome_id}.genome.fa.gz')
        
        # 尝试不同的文件扩展名
        if not os.path.exists(genome_file):
            # 尝试 .genome.fa.gz
            genome_file_gz = os.path.join(genome_dir, f'{genome_id}.genome.fa.gz')
            if os.path.exists(genome_file_gz):
                genome_file = genome_file_gz
            else:
                # 尝试 .fa
                genome_file_fa = os.path.join(genome_dir, f'{genome_id}.fa')
                if os.path.exists(genome_file_fa):
                    genome_file = genome_file_fa
                else:
                    logger.warning(f"Genome file not found: {genome_file}")
                    return None
        
        # 使用 pyfaidx 加载 FASTA 文件
        try:
            fa = pyfaidx.Fasta(genome_file)
        except Exception as e:
            logger.error(f"Error loading FASTA file with pyfaidx: {e}")
            return None
        
        # 检查 seqid 是否存在
        if seqid not in fa:
            logger.warning(f"Sequence not found for seqid: {seqid} in genome: {genome_id}")
            return None
        
        # 获取序列
        sequence = fa[seqid]
        
        # 提取指定位置的序列（注意：生物序列通常从1开始计数）
        # 确保位置有效
        if start < 1 or end > len(sequence) or start > end:
            logger.warning(f"Invalid position: start={start}, end={end}, sequence length={len(sequence)}")
            return None
        
        # 提取序列（pyfaidx 支持直接通过切片提取，从0开始计数）
        extracted_seq = sequence[start-1:end]
        
        # 如果是负链，需要反转互补
        if strand == '-':
            extracted_seq = extracted_seq.reverse.complement
        
        return str(extracted_seq)
        
    except Exception as e:
        logger.error(f"Error extracting sequence from file: {e}")
        return None

@api_view(['POST'])
def extract_seq_gff(request):

    if request.method == 'POST':
        uuid = request.headers.get('uuid')
        if not uuid or uuid not in UuidManager.uuid_storage:
            return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
        genome_id = request.data.get('genome_id') or request.query_params.get('genome_id')
        seqid = request.data.get('seqid') or request.query_params.get('seqid')
        start = request.data.get('start') or request.query_params.get('start')
        end = request.data.get('end') or request.query_params.get('end')
        strand = request.data.get('strand') or request.query_params.get('strand')
        
        # 参数验证
        if not all([genome_id, seqid, start, end]):
            return Response({'error': 'Missing required parameters'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            start = int(start)
            end = int(end)
        except ValueError:
            return Response({'error': 'Start and end must be integers'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 从基因组文件中提取序列
        sequence = extract_sequence_from_genome_file(genome_id, seqid, start, end, strand)
        
        if sequence:
            return Response({'sequence': sequence}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to extract sequence'}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response({'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
