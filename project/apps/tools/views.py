import logging
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import subprocess
import os
from django.views import View
from django.http import JsonResponse

# 显式初始化logger，设置propagate=False避免日志向上传播
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)

# 创建文件处理器
log_file = os.path.join(os.path.dirname(__file__), 'primer_design.log')
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器到日志记录器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

@method_decorator(csrf_exempt, name='dispatch')
class PrimerDesignAPIView(View):
    def post(self, request, format=None):
        try:
            #logger.debug(f"Request body: {request.body}")
            
            data = json.loads(request.body.decode('utf-8'))
            sequence_id = data.get('sequence_id', 'default_id')
            sequence_template = data.get('sequence_template', '')
            parameters = data.get('parameters', {})
            
            #logger.debug(f"Parsed data: sequence_id={sequence_id}, sequence_template={sequence_template[:50]}..., parameters={parameters}")
            
            if not sequence_template:
                logger.warning("No sequence template provided")
                return JsonResponse({'status': 'error', 'error': 'No sequence provided'}, status=400)
            
            # 构建primer3的Boulder-IO格式输入
            boulder_input = []
            boulder_input.append(f'SEQUENCE_ID={sequence_id}')
            boulder_input.append(f'SEQUENCE_TEMPLATE={sequence_template}')
            boulder_input.append(f'PRIMER_PRODUCT_SIZE_RANGE={parameters.get("productSizeMin", 100)}-{parameters.get("productSizeMax", 250)}')
            boulder_input.append(f'PRIMER_MIN_SIZE={parameters.get("primerSizeMin", 18)}')
            boulder_input.append(f'PRIMER_MAX_SIZE={parameters.get("primerSizeMax", 27)}')
            boulder_input.append(f'PRIMER_MIN_TM={parameters.get("primerTmMin", 57)}')
            boulder_input.append(f'PRIMER_MAX_TM={parameters.get("primerTmMax", 63)}')
            boulder_input.append(f'PRIMER_MIN_GC={parameters.get("primerGCMin", 20)}')
            boulder_input.append(f'PRIMER_MAX_GC={parameters.get("primerGCMax", 80)}')
            boulder_input.append('=')  # 记录结束标记
            
            # 确保输入格式正确，每一行以换行符结束
            # 替换Windows换行符为Unix换行符
            boulder_input_str = '\n'.join(boulder_input) + '\n'
            #logger.debug(f"Boulder input: {boulder_input_str}")
            
            # 使用Django的BASE_DIR构建更可靠的路径
            from django.conf import settings
            
            # 定义primer3_core的路径
            import platform
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
            primer3_path = os.path.join(settings.BASE_DIR, 'soft', primer3_dir, 'primer3', 'src', primer3_exec)
            #logger.debug(f"Primer3 path: {primer3_path}")
            #logger.debug(f"Full Primer3 path: {os.path.abspath(primer3_path)}")
            
            # 检查primer3可执行文件是否存在
            if not os.path.exists(primer3_path):
                logger.error(f"Primer3 executable not found at: {primer3_path}")
                return JsonResponse({'status': 'error', 'error': f'Primer3 executable not found at: {primer3_path}'}, status=500)
            
            # 调用primer3_core工具
            #logger.debug("Calling primer3_core...")
            
            try:
                # 调用primer3_core工具
                process = subprocess.Popen(
                    [primer3_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # 使用\n作为行分隔符，编码为字节流
                boulder_input_bytes = boulder_input_str.encode('utf-8', errors='replace')
                
                # 传递输入并获取输出
                stdout_bytes, stderr_bytes = process.communicate(input=boulder_input_bytes)
                
                # 解码输出
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                
                #logger.debug(f"Primer3 stdout: {stdout}")
                #logger.debug(f"Primer3 stderr: {stderr}")
                #logger.debug(f"Primer3 return code: {process.returncode}")
                
                if process.returncode != 0:
                    logger.error(f"Primer3 execution failed with code {process.returncode}: {stderr}")
                    # 返回更详细的错误信息
                    return JsonResponse({'status': 'error', 'error': f'Primer3 execution failed with code {process.returncode}: {stderr}'}, status=500)
            except Exception as e:
                logger.error(f"Error calling Primer3: {str(e)}", exc_info=True)
                return JsonResponse({'status': 'error', 'error': f'Error calling Primer3: {str(e)}'}, status=500)
            
            # 解析primer3的输出
            #logger.debug("Parsing primer3 output...")
            results = self.parse_primer3_output(stdout)
            logger.debug(f"Parsed results: {results}")
            
            return JsonResponse({'status': 'success', 'results': results})
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse({'status': 'error', 'error': f'Invalid JSON format: {e}'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
    
    def parse_primer3_output(self, output):
        """解析primer3的输出并转换为JSON格式"""
        try:
            results = {}  # 使用字典存储结果，键为引物对编号
            lines = output.strip().split('\n')
            
           # logger.debug(f"Parsing output lines: {lines}")
            
            # 遍历所有输出行
            for line in lines:
                line = line.strip()
                if not line or line == '=':
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 使用正则表达式匹配PRIMER_LEFT_0_SEQUENCE这种格式
                    import re
                    match = re.match(r'PRIMER_(LEFT|RIGHT|PAIR)_([0-9]+)_(.*)$', key)
                    if match:
                        # 提取引物类型、编号和属性名称
                        primer_type = match.group(1)
                        primer_num = match.group(2)
                        attr_name = match.group(3)
                        
                        # 初始化引物对结果
                        if primer_num not in results:
                            results[primer_num] = {
                                'forward': {},
                                'reverse': {},
                                'pair': {}
                            }
                        
                        # 将属性保存到相应的引物对中
                        if primer_type == 'LEFT':
                            results[primer_num]['forward'][attr_name] = value
                        elif primer_type == 'RIGHT':
                            results[primer_num]['reverse'][attr_name] = value
                        elif primer_type == 'PAIR':
                            results[primer_num]['pair'][attr_name] = value
                            # 同时处理全局属性
                            if attr_name == 'PENALTY':
                                results[primer_num]['penalty'] = value
                            elif attr_name == 'PRODUCT_SIZE':
                                results[primer_num]['product_size'] = value
                            elif attr_name == 'PRODUCT_TM':
                                results[primer_num]['product_tm'] = value
                    else:
                        # 处理PRIMER_LEFT_0=464,20这种格式，其中464是起始位置，20是长度
                        match = re.match(r'PRIMER_(LEFT|RIGHT|PAIR)_([0-9]+)$', key)
                        if match:
                            primer_type = match.group(1)
                            primer_num = match.group(2)
                            
                            if primer_num not in results:
                                results[primer_num] = {
                                    'forward': {},
                                    'reverse': {},
                                    'pair': {}
                                }
                            
                            # 解析位置和长度，格式：464,20
                            if ',' in value:
                                position, length = value.split(',')
                                position = position.strip()
                                length = length.strip()
                            else:
                                # 如果没有长度信息，只保存位置
                                position = value
                                length = ''
                            
                            if primer_type == 'LEFT':
                                results[primer_num]['forward']['START'] = position
                                results[primer_num]['forward']['SIZE'] = length
                            elif primer_type == 'RIGHT':
                                results[primer_num]['reverse']['START'] = position
                                results[primer_num]['reverse']['SIZE'] = length
                            elif primer_type == 'PAIR':
                                results[primer_num]['pair']['position'] = value
            
            # 转换为列表格式并返回
            result_list = [results[key] for key in sorted(results.keys())]
            logger.debug(f"Final parsed results: {result_list}")
            return result_list
        except Exception as e:
            logger.error(f"Error parsing primer3 output: {e}", exc_info=True)
            raise