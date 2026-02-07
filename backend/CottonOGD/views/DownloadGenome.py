from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import FileResponse
import os
import logging

logger = logging.getLogger(__name__)

# 文件类型映射
FILE_TYPE_MAPPING = {
    'genome': '.genome.fa.gz',
    'cds': '.cds.fa.gz',
    'protein': '.pro.fa.gz',
    'upstream2000': '.upstream.fa.gz',
    'gff3': '.gff.gz'
}

@api_view(['GET'])
def download_genome_file(request, genome_id, file_type):
    """
    下载基因组文件
    参数:
        genome_id: 基因组ID
        file_type: 文件类型 (genome, cds, protein, upstream2000, gff3)
    """
    try:
        # 验证文件类型
        if file_type not in FILE_TYPE_MAPPING:
            return Response(
                {'error': 'Invalid file type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 构建文件路径
        file_extension = FILE_TYPE_MAPPING[file_type]
        file_name = f"{genome_id}{file_extension}"
        file_path = os.path.join(settings.BASE_DIR, 'data', 'genome', genome_id, file_name)
        
        logger.debug(f"Attempting to download file: {file_path}")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return Response(
                {'error': 'File not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 检查文件是否为常规文件
        if not os.path.isfile(file_path):
            logger.error(f"Not a regular file: {file_path}")
            return Response(
                {'error': 'Not a regular file'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 打开文件并返回
        try:
            file_handle = open(file_path, 'rb')
            response = FileResponse(file_handle)
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Length'] = str(os.path.getsize(file_path))
            
            return response
        except Exception as e:
            logger.error(f"Error opening file: {str(e)}")
            return Response(
                {'error': f'Error opening file: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return Response(
            {'error': f'Download error: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
