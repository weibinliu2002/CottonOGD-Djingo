from django.http import HttpResponse, StreamingHttpResponse
from django.templatetags.static import static
import os
from django.shortcuts import render
from django.conf import settings

# Create your views here.
genome_name = 'Ghirsutum_genome_HAU_v1.0'
location = 'Ghir_A01:1-1000000'
gff_name = 'TM-1.gff'
def index(request):
    # 直接返回jbrowse的静态HTML文件，只显示基础的JBrowse视图
    jbrowse_index_path = os.path.join(settings.BASE_DIR, 'static/jbrowse/index.html')
    if os.path.exists(jbrowse_index_path):
        with open(jbrowse_index_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HttpResponse(html_content)
    else:
        return HttpResponse(f'JBrowse index file not found at: {jbrowse_index_path}', status=404)


def serve_large_file(request, filename):
    """自定义视图用于处理大文件下载，支持断点续传"""
    # 使用Django的静态文件查找机制
    from django.contrib.staticfiles import finders
    file_path = finders.find(f'jbrowse/{filename}')
    if not file_path:
        # 回退到旧路径
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(base_dir, 'static', 'jbrowse', filename)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return HttpResponse(f'File not found: {file_path}', status=404)
    
    # 获取文件大小
    file_size = os.path.getsize(file_path)
    
    # 处理Range请求头
    range_header = request.headers.get('Range', '')
    if range_header:
        # 支持断点续传
        try:
            range_match = range_header.split('=')[1]
            if '-' in range_match:
                start, end = range_match.split('-')
                start = int(start)
                end = int(end) if end else file_size - 1
                length = end - start + 1
                
                response = StreamingHttpResponse(stream_file(file_path, start, length))
                response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                response['Content-Length'] = str(length)
                response.status_code = 206  # Partial Content
            else:
                return HttpResponse('Invalid Range header', status=400)
        except Exception as e:
            return HttpResponse(f'Error processing range: {str(e)}', status=400)
    else:
        # 完整文件传输
        response = StreamingHttpResponse(stream_file(file_path))
        response['Content-Length'] = str(file_size)
    
    # 设置响应头
    response['Content-Type'] = 'application/octet-stream'
    response['Accept-Ranges'] = 'bytes'
    
    return response


def stream_file(file_path, start=0, length=None):
    """流式传输文件内容"""
    chunk_size = 8192  # 8KB块
    with open(file_path, 'rb') as f:
        f.seek(start)
        remaining = length
        while True:
            if remaining is not None:
                if remaining <= 0:
                    break
                chunk = f.read(min(chunk_size, remaining))
                remaining -= len(chunk)
            else:
                chunk = f.read(chunk_size)
            
            if not chunk:
                break
            yield chunk
