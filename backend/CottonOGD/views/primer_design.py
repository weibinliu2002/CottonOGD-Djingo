from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from django.http import JsonResponse
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
import os, json
import subprocess
import re
import platform
from django.conf import settings
import logging
logger = logging.getLogger(__name__)


def parse_primer3_output(output):
    """
    解析primer3的输出，转换为前端期望的结构化格式
    :param output: primer3的输出字符串
    :return: 解析后的结果列表
    """
    results = []
    primer_data = {}
    
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            primer_data[key] = value
    
    # 查找引物对的数量
    pair_count = 0
    while f'PRIMER_PAIR_{pair_count + 1}_PENALTY' in primer_data:
        pair_count += 1
    
    # 解析每个引物对
    for i in range(1, pair_count + 1):
        prefix = f'PRIMER_LEFT_{i}_'
        forward = {
            'SEQUENCE': primer_data.get(f'{prefix}SEQUENCE', ''),
            'TM': float(primer_data.get(f'{prefix}TM', 0)),
            'GC_PERCENT': float(primer_data.get(f'{prefix}GC_PERCENT', 0)),
            'SELF_ANY': float(primer_data.get(f'{prefix}SELF_ANY_TH', 0)),
            'SELF_END': float(primer_data.get(f'{prefix}SELF_END_TH', 0)),
            'HAIRPIN': float(primer_data.get(f'{prefix}HAIRPIN_TH', 0)),
            'END_STABILITY': float(primer_data.get(f'{prefix}END_STABILITY', 0))
        }
        
        # 解析位置和长度 (格式: "1349,20")
        pos_str = primer_data.get(f'{prefix}POS', '0,0')
        if ',' in pos_str:
            start, size = pos_str.split(',')
            forward['START'] = int(start)
            forward['SIZE'] = int(size)
        else:
            forward['START'] = 0
            forward['SIZE'] = 0
        
        prefix = f'PRIMER_RIGHT_{i}_'
        reverse = {
            'SEQUENCE': primer_data.get(f'{prefix}SEQUENCE', ''),
            'TM': float(primer_data.get(f'{prefix}TM', 0)),
            'GC_PERCENT': float(primer_data.get(f'{prefix}GC_PERCENT', 0)),
            'SELF_ANY': float(primer_data.get(f'{prefix}SELF_ANY_TH', 0)),
            'SELF_END': float(primer_data.get(f'{prefix}SELF_END_TH', 0)),
            'HAIRPIN': float(primer_data.get(f'{prefix}HAIRPIN_TH', 0)),
            'END_STABILITY': float(primer_data.get(f'{prefix}END_STABILITY', 0))
        }
        
        # 解析位置和长度
        pos_str = primer_data.get(f'{prefix}POS', '0,0')
        if ',' in pos_str:
            start, size = pos_str.split(',')
            reverse['START'] = int(start)
            reverse['SIZE'] = int(size)
        else:
            reverse['START'] = 0
            reverse['SIZE'] = 0
        
        # 获取引物对信息
        penalty = float(primer_data.get(f'PRIMER_PAIR_{i}_PENALTY', 0))
        product_size = int(primer_data.get(f'PRIMER_PAIR_{i}_PRODUCT_SIZE', 0))
        product_tm = float(primer_data.get(f'PRIMER_PAIR_{i}_PRODUCT_TM', 0))
        compl_any = float(primer_data.get(f'PRIMER_PAIR_{i}_COMPL_ANY_TH', 0))
        compl_end = float(primer_data.get(f'PRIMER_PAIR_{i}_COMPL_END_TH', 0))
        
        results.append({
            'forward': forward,
            'reverse': reverse,
            'penalty': penalty,
            'productSize': product_size,
            'productTm': product_tm,
            'complAny': compl_any,
            'complEnd': compl_end
        })
    
    return results


@api_view(['POST'])
def primer_design(request):
    if request.method == 'POST':
        '''
        uuid = request.headers.get('uuid')
        if not uuid or uuid not in UuidManager.uuid_storage:
            return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
        '''
        # 获取序列和参数
        sequence = request.data.get('sequence') or request.query_params.get('sequence')
        sequence_id = request.data.get('sequence_id', 'default_id')
        parameters = request.data.get('parameters', {})
        
        # 验证序列
        if not sequence:
            return Response({'error': 'sequence is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查序列是否只包含ACTG字符
        if not re.match(r'^[ACTG]+$', sequence):
            return Response({'error': 'sequence must contain only ACTG characters'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 构建primer3的Boulder-IO格式输入
        boulder_input = []
        boulder_input.append(f'SEQUENCE_ID={sequence_id}')
        boulder_input.append(f'SEQUENCE_TEMPLATE={sequence}')
        boulder_input.append(f'PRIMER_PRODUCT_SIZE_RANGE={parameters.get("productSizeMin", 100)}-{parameters.get("productSizeMax", 250)}')
        boulder_input.append(f'PRIMER_MIN_SIZE={parameters.get("primerSizeMin", 18)}')
        boulder_input.append(f'PRIMER_MAX_SIZE={parameters.get("primerSizeMax", 27)}')
        boulder_input.append(f'PRIMER_MIN_TM={parameters.get("primerTmMin", 57)}')
        boulder_input.append(f'PRIMER_MAX_TM={parameters.get("primerTmMax", 63)}')
        boulder_input.append(f'PRIMER_MIN_GC={parameters.get("primerGCMin", 20)}')
        boulder_input.append(f'PRIMER_MAX_GC={parameters.get("primerGCMax", 80)}')
        boulder_input.append('=')  # 记录结束标记
        
        # 确保输入格式正确
        boulder_input_str = '\n'.join(boulder_input) + '\n'
        logger.debug(f"Boulder input: {boulder_input_str}")
        
        # 使用Django的BASE_DIR构建更可靠的路径
        
        
        # 定义primer3_core的路径
       
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows系统使用windows目录下的exe文件
            primer3_dir = 'windows'
            primer3_exec = 'primer3_core.exe'
        else:
            # Linux系统使用UNIX目录下的可执行文件
            primer3_dir = 'UNIX'
            primer3_exec = 'primer3_core'
        
        # 使用BASE_DIR构建路径，更可靠
        primer3_dir = os.path.join(settings.BASE_DIR, 'soft', primer3_dir, 'primer3', 'src')
        primer3_path = os.path.join(primer3_dir, primer3_exec)
        logger.debug(f"Primer3 path: {primer3_path}")
        logger.debug(f"Full Primer3 path: {os.path.abspath(primer3_path)}")
        
        # 检查primer3可执行文件是否存在
        if not os.path.exists(primer3_path):
            logger.error(f"Primer3 executable not found at: {primer3_path}")
            return JsonResponse({'status': 'error', 'error': f'Primer3 executable not found at: {primer3_path}'}, status=500)
        
        # 调用primer3_core工具
        logger.debug("Calling primer3_core...")
        
        try:
            # 设置环境变量，指向配置文件目录
            env = os.environ.copy()
            env['PRIMER3_CONFIG'] = primer3_dir
            
            # 调用primer3_core工具，设置工作目录
            process = subprocess.Popen(
                [primer3_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=primer3_dir,
                env=env
            )
            
            # 使用\n作为行分隔符，编码为字节流
            boulder_input_bytes = boulder_input_str.encode('utf-8', errors='replace')
            
            # 传递输入并获取输出
            stdout_bytes, stderr_bytes = process.communicate(input=boulder_input_bytes)
            
            # 解码输出
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            
            logger.debug(f"Primer3 stdout: {stdout}")
            logger.debug(f"Primer3 stderr: {stderr}")
            logger.debug(f"Primer3 return code: {process.returncode}")
            
            if process.returncode != 0:
                logger.error(f"Primer3 execution failed with code {process.returncode}: {stderr}")
                # 返回更详细的错误信息
                return JsonResponse({'status': 'error', 'error': f'Primer3 execution failed with code {process.returncode}: {stderr}'}, status=500)
        except Exception as e:
            logger.error(f"Error calling Primer3: {str(e)}", exc_info=True)
            return JsonResponse({'status': 'error', 'error': f'Error calling Primer3: {str(e)}'}, status=500)
        
        # 解析primer3的输出
        logger.debug("Parsing primer3 output...")
        results = parse_primer3_output(stdout)
        logger.debug(f"Parsed results: {results}")
        
        return JsonResponse({'status': 'success', 'results': results})
    else:
        return Response({'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)