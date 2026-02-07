from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os
import platform
import subprocess
import logging
import json
import logging
from io import StringIO
from django import forms
from Bio.Blast import NCBIXML

#from apps.tools import blastp

logger = logging.getLogger(__name__)

class blast:
    @classmethod
    def clean_sequence(cls, sequence):
        """预处理序列数据：移除空格/空行，提取纯序列"""
        raw_seq = sequence.strip()
        fasta_sequences = []
        
        if raw_seq.startswith('>'):
            # 处理FASTA格式，支持多序列
            lines = [line.strip() for line in raw_seq.split('\n') if line.strip()]
            current_header = None
            current_seq = []
            
            for line in lines:
                if line.startswith('>'):
                    # 新序列开始
                    if current_header and current_seq:
                        # 保存之前的序列
                        seq_str = ''.join(current_seq)
                        if len(seq_str) >= 10 and seq_str.isalpha():
                            fasta_sequences.append(f">{current_header}")
                            fasta_sequences.append(seq_str.upper())
                    current_header = line[1:].strip()  # 移除'>'符号
                    current_seq = []
                else:
                    # 序列内容
                    current_seq.append(line)
            
            # 处理最后一条序列
            if current_header and current_seq:
                seq_str = ''.join(current_seq)
                if len(seq_str) >= 10 and seq_str.isalpha():
                    fasta_sequences.append(f">{current_header}")
                    fasta_sequences.append(seq_str.upper())
        else:
            # 处理纯序列，转换为FASTA格式
            seq_str = ''.join(raw_seq.split())
            if len(seq_str) < 10:
                raise forms.ValidationError("序列太短（至少10个氨基酸）")
            if not seq_str.isalpha():
                raise forms.ValidationError("包含非字母字符")
            fasta_sequences.append(">Query")
            fasta_sequences.append(seq_str.upper())
        #logging.Logger('fasta_sequences', fasta_sequences)
        if not fasta_sequences:
            raise forms.ValidationError("没有有效的序列")
            
        # 返回FASTA格式的字符串，多个序列用换行符分隔
        return '\n'.join(fasta_sequences)

    @classmethod
    def validate_type(cls,type):
        """验证BLAST类型"""
        valid_types = ['blastn', 'blastp', 'blastx', 'tblastn', 'tblastx']
        if type not in valid_types:
            raise forms.ValidationError(f"不支持的BLAST类型: {type}")
        return type

    @classmethod
    def run_blast(cls, sequence, type, genome_id, data_type='genome', evalue='1e-5', max_hits='10',
                  word_size=None, match_score=None, gap_open=None, gap_extend=None, low_complexity_filter=True):
        """运行BLAST搜索"""
        cleaned_seq = cls.clean_sequence(sequence)
        system = platform.system().lower()
        
        # 构建BLAST可执行文件路径
        if system == 'windows':
            blast_path = os.path.join(settings.BASE_DIR,  'soft', 'windows','blast+', 'bin')
        elif system == 'linux':
            blast_path = os.path.join(settings.BASE_DIR,  'soft', 'UNIX','blast+', 'bin')
        else:
            raise OSError(f"不支持的操作系统: {system}")
        
        # 根据BLAST类型选择可执行文件
        if type == 'blastn':
            blast_exe = os.path.join(blast_path, 'blastn.exe' if system == 'windows' else 'blastn')
        elif type == 'blastp':
            blast_exe = os.path.join(blast_path, 'blastp.exe' if system == 'windows' else 'blastp')
        elif type == 'blastx':
            blast_exe = os.path.join(blast_path, 'blastx.exe' if system == 'windows' else 'blastx')
        elif type == 'tblastn':
            blast_exe = os.path.join(blast_path, 'tblastn.exe' if system == 'windows' else 'tblastn')
        elif type == 'tblastx':
            blast_exe = os.path.join(blast_path, 'tblastx.exe' if system == 'windows' else 'tblastx')
        else:
            raise OSError(f"不支持的BLAST类型: {type}")
        
        # 构建数据库路径
        db_path = os.path.join(settings.BASE_DIR, 'data','blast_db','CottonOGD', genome_id, data_type,genome_id)
        
        # 构建BLAST命令
        cmd = [
            blast_exe,
            '-query', '-',  # 从标准输入读取序列
            '-db', db_path,
            '-outfmt', '5',  # XML格式输出
            '-evalue', str(evalue),
            '-max_target_seqs', str(max_hits),
            '-num_threads', '2'  # 使用2个线程加速
        ]
        '''
        # 添加高级参数
        if word_size is not None:
            # 根据BLAST类型控制word_size的最大值
            if type in ['blastp', 'blastx', 'tblastn']:
                # 对于这些类型，word_size必须小于8
                word_size = min(int(word_size), 7)
            elif type in ['blastn', 'tblastx']:
                # 对于这些类型，word_size可以更大
                word_size = min(int(word_size), 28)
            cmd.extend(['-word_size', str(word_size)])
        if gap_open is not None:
            cmd.extend(['-gapopen', str(gap_open)])
        if gap_extend is not None:
            cmd.extend(['-gapextend', str(gap_extend)])
        if not low_complexity_filter:
            cmd.append('-seg')  # 禁用低复杂度过滤
        '''
        try:
            # 执行BLAST命令
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 传递序列并获取结果
            stdout, stderr = process.communicate(input=cleaned_seq)
            
            # 检查执行状态
            if process.returncode != 0:
                #logger.error(f"BLAST执行失败: {stderr}")
                raise OSError(f"BLAST执行失败: {stderr}")
            
            # 解析XML结果并转换为JSON
            try:
                # 使用Biopython解析XML
                blast_records = NCBIXML.parse(StringIO(stdout))
                all_results = []
                
                # 处理多个查询序列的结果
                for i, blast_record in enumerate(blast_records):
                    logger.info(f"BLAST record {i+1} parsed successfully: {blast_record.query_id}")
                    # 转换为字典格式
                    blast_dict = {
                        'query_id': blast_record.query_id,
                        'query_def': blast_record.query,
                        'query_length': blast_record.query_length,
                        'program': blast_record.application,
                        'version': blast_record.version,
                        'reference': blast_record.reference,
                        'db': blast_record.database,
                        'parameters': {
                            'matrix': getattr(blast_record, 'matrix', 'BLOSUM62'),
                            'expect': getattr(blast_record, 'expect', 1e-5),
                            'gap_open': getattr(blast_record, 'gap_open', 11),
                            'gap_extend': getattr(blast_record, 'gap_extend', 1),
                            'filter': getattr(blast_record, 'filter', None),
                            'sc_match': getattr(blast_record, 'sc_match', 2),
                            'sc_mismatch': getattr(blast_record, 'sc_mismatch', -3),
                            'word_size': getattr(blast_record, 'word_size', 3)
                        },
                        'hits': []
                    }
                    
                    # 提取hits
                    for hit in blast_record.alignments:
                        for hsp in hit.hsps:
                            hit_dict = {
                                'protein_id': hit.hit_id,
                                'description': hit.hit_def,
                                'length': hit.length,
                                'identity': hsp.identities,
                                'alignment_length': hsp.align_length,
                                'mismatches': hsp.align_length - hsp.identities - hsp.gaps,
                                'gaps': hsp.gaps,
                                'query_start': hsp.query_start,
                                'query_end': hsp.query_end,
                                'subject_start': hsp.sbjct_start,
                                'subject_end': hsp.sbjct_end,
                                'evalue': hsp.expect,
                                'bit_score': hsp.bits,
                                'score': hsp.score,
                                'query_frame': getattr(hsp, 'query_frame', 0),
                                'subject_frame': getattr(hsp, 'sbjct_frame', 0),
                                'query_sequence': hsp.query,
                                'subject_sequence': hsp.sbjct,
                                'match_sequence': hsp.match
                            }
                            blast_dict['hits'].append(hit_dict)
                    
                    # 添加到所有结果中
                    all_results.append(blast_dict)
                
                # 如果只有一个结果，直接返回
                if len(all_results) == 1:
                    return json.dumps(all_results[0], indent=2)
                    #return all_results[0]
                # 否则返回结果列表
                return json.dumps(all_results, indent=2)
                #return all_results
            except Exception as e:
                logger.error(f"解析BLAST结果失败: {str(e)}")
                # 如果解析失败，返回原始XML
                return stdout
        except Exception as e:
            logger.error(f"运行BLAST时出错: {str(e)}")
            raise

@api_view(['POST'])
def blast_cmd(request):
    """BLAST搜索视图"""
    if request.method == 'POST':
        sequence = request.data.get('sequence')
        blast_type = request.data.get('type') or request.data.get('blast_type')
        selected_genomes = request.data.get('selected_genomes')
        data_type = request.data.get('data_type', 'genome')
        evalue = request.data.get('evalue', '1e-5')
        max_hits = request.data.get('max_hits') or request.data.get('max_target_seqs', '10')
        logger.info(f"Received request: sequence={sequence[:10] if sequence else ''},\n"
                    f"blast_type={blast_type}, \n"
                    f"selected_genomes={selected_genomes},\n"
                     f"data_type={data_type}, \n"
                     f"evalue={evalue},\n"
                     f"max_hits={max_hits}")
        # 高级参数
        word_size = request.data.get('word_size')
        match_score = request.data.get('match_score')
        gap_open = request.data.get('gap_open')
        gap_extend = request.data.get('gap_extend')
        low_complexity_filter = request.data.get('low_complexity_filter', True)

        # 验证必要参数
        if not sequence:
            return Response({'error': '序列不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if not blast_type:
            return Response({'error': 'BLAST类型不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 处理基因组选择
        if selected_genomes:
            if isinstance(selected_genomes, str):
                genome_list = [g.strip() for g in selected_genomes.split(',') if g.strip()]
            else:
                genome_list = selected_genomes
        else:
            return Response({'error': '基因组ID不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 验证BLAST类型
            validated_type = blast.validate_type(blast_type)
        except forms.ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # 确保只处理第一个基因组ID
        genome_id = genome_list[0] if genome_list else None
        if not genome_id:
            return Response({'error': '基因组ID不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 运行BLAST搜索
            result = blast.run_blast(
                sequence=sequence,
                type=validated_type,
                genome_id=genome_id,
                data_type=data_type,
                evalue=str(evalue),
                max_hits=str(max_hits),
                word_size=word_size,
                match_score=match_score,
                gap_open=gap_open,
                gap_extend=gap_extend,
                low_complexity_filter=low_complexity_filter
            )
            #logger.log('result',result)
            return Response({'results': {genome_id: result}})
        except forms.ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except OSError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"BLAST搜索失败 ({genome_id}): {str(e)}")
            return Response({'error': f"BLAST搜索失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
