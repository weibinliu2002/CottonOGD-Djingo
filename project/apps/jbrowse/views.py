from django.http import FileResponse, HttpResponse
from django.conf import settings
import os

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

    file_path = os.path.join(JBROWSE_ROOT, genome_name, filename)

    if not os.path.exists(file_path):
        return HttpResponse(f'File not found: {file_path}', status=404)

    response = FileResponse(open(file_path, 'rb'))

    # 关键 header
    response['Accept-Ranges'] = 'bytes'

    # 设置正确的Content-Type，但不要设置Content-Encoding
    # JBrowse的bgzf-filehandle库会自己处理解压缩
    if filename.endswith('.gff.gz'):
        response['Content-Type'] = 'application/octet-stream'
    elif filename.endswith('.fa.gz'):
        response['Content-Type'] = 'application/octet-stream'
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

# 保留jbrowse_file函数作为兼容别名
def jbrowse_file(request, genome, filename):
    return serve_large_file(request, genome, filename)