from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
import logging
import os
import re

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
        genome_dir = os.path.join('d:\\科研\\CottonOGD\\python\\OGD\\backend\\data\\genome', genome_id)
        genome_file = os.path.join(genome_dir, f'{genome_id}.fasta')
        
        if not os.path.exists(genome_file):
            logger.warning(f"Genome file not found: {genome_file}")
            return None
        
        # 读取基因组文件，找到对应的序列
        sequence = ''
        current_seqid = ''
        with open(genome_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    # 新的序列
                    header = line[1:]
                    # 提取 seqid（假设格式为 ">seqid ..."）
                    current_seqid = header.split()[0]
                    if current_seqid == seqid:
                        # 找到目标序列，开始读取
                        sequence = ''
                    elif sequence:
                        # 已经找到并读取了目标序列，退出循环
                        break
                elif current_seqid == seqid:
                    # 读取序列部分
                    sequence += line
        
        if not sequence:
            logger.warning(f"Sequence not found for seqid: {seqid} in genome: {genome_id}")
            return None
        
        # 提取指定位置的序列（注意：生物序列通常从1开始计数）
        # 确保位置有效
        if start < 1 or end > len(sequence) or start > end:
            logger.warning(f"Invalid position: start={start}, end={end}, sequence length={len(sequence)}")
            return None
        
        # Python 字符串索引从0开始，所以需要调整
        extract_start = start - 1
        extract_end = end
        extracted_seq = sequence[extract_start:extract_end]
        
        # 如果是负链，需要反转互补
        if strand == '-':
            complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C', 'a': 't', 't': 'a', 'c': 'g', 'g': 'c'}
            extracted_seq = ''.join([complement.get(base, base) for base in extracted_seq[::-1]])
        
        return extracted_seq
        
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