from django.http import HttpResponse, StreamingHttpResponse
from django.templatetags.static import static
import os
from django.shortcuts import render
from django.conf import settings

# Create your views here.
def index(request):
    # 我们已经在settings.py中添加了tools/templates目录到模板搜索路径
    # 现在我们可以使用正确的模板路径进行渲染
    # 确保模板路径为'tools/jbrowse/index.html'
    context = {
        'jbrowse_url': '/static/jbrowse/index.html'
    }
    
    # 尝试使用render函数渲染模板
    # 请注意：您需要确保在tools/templates目录下创建了正确的目录结构和模板文件
    # 模板文件应该位于：tools/templates/tools/jbrowse/index.html
    return render(request, 'index.html', context)


def serve_large_file(request, filename):
    """自定义视图用于处理大文件下载，支持断点续传"""
    # 直接在项目static/jbrowse目录中查找文件
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
