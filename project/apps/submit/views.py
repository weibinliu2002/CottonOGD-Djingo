from django.shortcuts import render
from django.http import JsonResponse
from django.db import transaction
import json
import csv
from io import StringIO
from datetime import datetime
from .models import SubmittedData, BatchSubmission

# Create your views here.
def submit(request):
    bool_list = []
    if request.method == 'POST':
        bool_list.append(True)
    else:
        bool_list.append(False)
    return render(request, 'submit/index.html', {'bool_list': bool_list})


def batch_import_data(request):
    """
    批量导入数据的视图函数
    支持JSON和CSV格式的数据导入
    使用Django的bulk_create优化批量插入性能
    """
    if request.method == 'POST':
        try:
            # 检查提交类型
            if 'file' in request.FILES:
                # 文件上传方式
                file = request.FILES['file']
                file_type = request.POST.get('file_type', '').lower()
                batch_name = request.POST.get('batch_name', f'Batch Import {datetime.now().strftime("%Y%m%d_%H%M%S")}')
                submitter = request.POST.get('submitter', 'Anonymous')
                
                # 处理文件内容
                file_content = file.read().decode('utf-8')
                
                if file_type == 'json':
                    # 处理JSON格式数据
                    data_list = json.loads(file_content)
                elif file_type == 'csv':
                    # 处理CSV格式数据
                    csv_reader = csv.DictReader(StringIO(file_content))
                    data_list = list(csv_reader)
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '不支持的文件类型，请选择json或csv格式'
                    })
                
            elif request.body:
                # JSON直接提交方式
                json_data = json.loads(request.body)
                data_list = json_data.get('data', [])
                batch_name = json_data.get('batch_name', f'Batch Import {datetime.now().strftime("%Y%m%d_%H%M%S")}')
                submitter = json_data.get('submitter', 'Anonymous')
            else:
                return JsonResponse({
                    'success': False,
                    'message': '请求体为空，请提供数据'
                })
            
            # 准备批量插入
            total_records = len(data_list)
            success_count = 0
            error_count = 0
            error_log = []
            submitted_objects = []
            
            # 开始事务处理
            with transaction.atomic():
                # 批量创建数据对象
                for idx, item in enumerate(data_list):
                    try:
                        # 构建数据对象
                        data_obj = SubmittedData(
                            data_name=item.get('data_name', f'Data {idx+1}'),
                            data_type=item.get('data_type', 'other'),
                            description=item.get('description', ''),
                            gene_id=item.get('gene_id'),
                            species_name=item.get('species_name'),
                            data_value=item.get('data_value'),
                            submitter=submitter,
                            reference=item.get('reference')
                        )
                        submitted_objects.append(data_obj)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        error_log.append(f"Row {idx+1}: {str(e)}")
                
                # 使用bulk_create进行批量插入
                if submitted_objects:
                    SubmittedData.objects.bulk_create(submitted_objects, batch_size=1000)
                
                # 记录批次提交信息
                batch_record = BatchSubmission(
                    batch_name=batch_name,
                    total_records=total_records,
                    success_count=success_count,
                    error_count=error_count,
                    submitter=submitter,
                    error_log='\n'.join(error_log) if error_log else None
                )
                batch_record.save()
            
            # 返回成功响应
            return JsonResponse({
                'success': True,
                'message': '批量数据导入完成',
                'details': {
                    'batch_id': batch_record.id,
                    'total_records': total_records,
                    'success_count': success_count,
                    'error_count': error_count,
                    'batch_name': batch_name,
                    'errors': error_log
                }
            })
            
        except json.JSONDecodeError as e:
            return JsonResponse({
                'success': False,
                'message': f'JSON解析错误: {str(e)}'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'导入过程中发生错误: {str(e)}'
            })
    else:
        # GET请求返回页面或API说明
        return JsonResponse({
            'success': False,
            'message': '请使用POST请求提交数据',
            'api_info': {
                'description': '批量导入数据API',
                'methods': 'POST',
                'data_format': '支持JSON和CSV格式',
                'required_fields': {
                    'json_direct': {'data': '数据列表', 'batch_name': '批次名称', 'submitter': '提交者'},
                    'file_upload': {'file': '上传文件', 'file_type': '文件类型(json/csv)', 'batch_name': '批次名称', 'submitter': '提交者'}
                }
            }
        })


def batch_import_history(request):
    """
    获取批量导入历史记录的视图函数
    """
    if request.method == 'GET':
        # 获取分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        
        # 查询批次历史记录
        history = BatchSubmission.objects.all().order_by('-created_at')
        
        # 分页处理
        total = history.count()
        start = (page - 1) * page_size
        end = start + page_size
        paginated_history = history[start:end]
        
        # 构造响应数据
        history_list = []
        for record in paginated_history:
            history_list.append({
                'id': record.id,
                'batch_name': record.batch_name,
                'total_records': record.total_records,
                'success_count': record.success_count,
                'error_count': record.error_count,
                'submitter': record.submitter,
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'has_errors': record.error_count > 0
            })
        
        return JsonResponse({
            'success': True,
            'data': history_list,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        })
    
    return JsonResponse({
        'success': False,
        'message': '请使用GET请求'
    })
