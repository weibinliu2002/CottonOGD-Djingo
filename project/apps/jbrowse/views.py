from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.conf import settings
import os
import mimetypes

JBROWSE_ROOT = os.path.join(settings.BASE_DIR, 'static', 'jbrowse', 'data')

def serve_large_file(request, genome_name, filename):
    """
    JBrowse 3.x safe file server
    - 支持 Range
    - 不会 fetch pending
    - 注意：不要设置Content-Encoding: gzip，让JBrowse自己处理解压缩
    """

    # 安全校验（防止 ../）
    if '..' in genome_name or '..' in filename:
        return HttpResponse(status=400)

    # 构建文件路径
    file_path = os.path.join(JBROWSE_ROOT, genome_name, filename)

    if not os.path.exists(file_path):
        return HttpResponse(f'File not found: {file_path}', status=404)

    # 检查文件名是否为大文件类型
    large_file_extensions = ['.bam', '.cram', '.vcf.gz', '.gff.gz', '.bigwig', '.beddb']
    if not any(filename.endswith(ext) for ext in large_file_extensions):
        # 不是大文件，使用默认静态文件服务
        return HttpResponseNotFound("File not found")

    # 获取文件大小
    file_size = os.path.getsize(file_path)
    print(f"DEBUG: Serving file: {file_path}")
    print(f"DEBUG: File size: {file_size} bytes")

    # 处理Range请求
    range_header = request.META.get('HTTP_RANGE', None)
    if range_header:
        # 解析Range头，例如: "bytes=0-1000" 或 "bytes=0-1000,2000-3000"
        try:
            # 简化处理，只处理单个范围
            range_part = range_header.replace('bytes=', '')
            start, end = range_part.split('-')
            start = int(start) if start else 0
            end = int(end) if end else file_size - 1
            
            if start >= file_size or end >= file_size or start > end:
                return HttpResponse(status=416)  # Range Not Satisfiable
                
            content_length = end - start + 1
            
            # 创建Range响应
            response = StreamingHttpResponse(
                file_iterator(file_path, start, content_length),
                status=206  # Partial Content
            )
            
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Content-Length'] = str(content_length)
            
        except (ValueError, IndexError):
            # Range解析失败，返回完整内容
            response = StreamingHttpResponse(open(file_path, 'rb'))
            response['Content-Length'] = str(file_size)
    else:
        # 正常请求，返回完整内容
        response = StreamingHttpResponse(open(file_path, 'rb'))
        response['Content-Length'] = str(file_size)
    
    # 关键 header - 支持Range请求
    response['Accept-Ranges'] = 'bytes'

    # 设置正确的Content-Type，但不要设置Content-Encoding
    # JBrowse的bgzf-filehandle库会自己处理解压缩
    if filename.endswith('.gff.gz'):
        # bgzip压缩的GFF文件需要特殊的Content-Type
        response['Content-Type'] = 'application/gff3+gzip'
    elif filename.endswith('.fa.gz'):
        # bgzip压缩的FASTA文件
        response['Content-Type'] = 'text/x-fasta+gzip'
    elif filename.endswith('.tbi'):
        response['Content-Type'] = 'application/octet-stream'
    elif filename.endswith('.fa'):
        response['Content-Type'] = 'text/x-fasta'
    elif filename.endswith('.fai'):
        response['Content-Type'] = 'text/plain'
    elif filename.endswith('.gff'):
        response['Content-Type'] = 'application/gff3'
    else:
        response['Content-Type'] = 'application/octet-stream'

    return response

def file_iterator(file_path, start=0, length=None):
    """文件迭代器，支持从指定位置开始读取指定长度"""
    with open(file_path, 'rb') as f:
        f.seek(start)
        remaining = length or os.path.getsize(file_path) - start
        chunk_size = 8192
        
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            yield data
            remaining -= len(data)