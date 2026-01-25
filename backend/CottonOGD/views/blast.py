from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os
import platform

logger = logging.getLogger(__name__)

class blast:
    @classmethod
    def clean_sequence(cls, sequence):
        """预处理序列数据：移除空格/空行，提取纯序列"""
        raw_seq = sequence.strip()
        
        if raw_seq.startswith('>'):
            lines = [line.strip() for line in raw_seq.split('\n') if line.strip()]
            sequence = ''.join(lines[1:]) 
        else:
            sequence = ''.join(raw_seq.split())
            
        if len(sequence) < 10:
            raise forms.ValidationError("序列太短（至少10个氨基酸）")
        if not sequence.isalpha():
            raise forms.ValidationError("包含非字母字符")
            
        return sequence.upper()

    @classmethod
    def validate_type(cls,type):
        """验证BLAST类型"""
        valid_types = ['blastn', 'blastp', 'blastx', 'tblastn', 'tblastx']
        if type not in valid_types:
            raise forms.ValidationError(f"不支持的BLAST类型: {type}")
        return type

    @classmethod
    def run_blast(cls, sequence,type):
        """运行BLAST搜索"""
        cleaned_seq = cls.clean_sequence(sequence)
        system = platform.system().lower()
        if system == 'windows':
            blast_path = os.path.join(settings.BASE_DIR,'backend','soft','windows','bin')
        elif system == 'linux':
            blast_path = os.path.join(settings.BASE_DIR,'backend','soft','UNIX','bin')
        else:
            raise OSError(f"不支持的操作系统: {system}")
        if type == 'blastn':
            blast_exe = os.path.join(blast_path,'blastn.exe')
        elif type == 'blastp':
            blast_exe = os.path.join(blast_path,'blastp.exe')
        elif type == 'blastx':
            blast_exe = os.path.join(blast_path,'blastx.exe')
        elif type == 'tblastn':
            blast_exe = os.path.join(blast_path,'tblastn.exe')
        elif type == 'tblastx':
            blast_exe = os.path.join(blast_path,'tblastx.exe')
        else:
            raise OSError(f"不支持的BLAST类型: {type}")
        
        # 这里添加实际的BLAST搜索逻辑
        # 可以使用Python的subprocess模块调用BLAST命令
        # 或者使用Python的BLAST库（如biopython）
        # 返回BLAST结果
        return "BLAST结果"

@api_view(['POST'])
def blast(request):
    """BLAST搜索视图"""
    if request.method == 'POST':
        sequence = request.data.get('sequence')
        type = request.data.get('type')
        genome_id = request.data.get('genome_id')
        data_type = request.data.get('data_type')
        evalue = request.data.get('evalue')
        max_hits = request.data.get('max_hits')

        try:
            type = cls.validate_type(type)
        except forms.ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cleaned_seq = cls.clean_sequence(sequence)
        except forms.ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = cls.run_blast(cleaned_seq,type)
        except OSError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'result': result})
