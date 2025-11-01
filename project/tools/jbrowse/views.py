from django.http import HttpResponse
from django.templatetags.static import static

# Create your views here.
def index(request):
    # 获取JBrowse index.html的正确静态文件URL
    jbrowse_index_url = static('index.html')
    
    # 直接返回包含iframe的HTML响应
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>JBrowse Genome Browser</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                height: 100vh;
                overflow: hidden;
            }}
            iframe {{
                width: 100%;
                height: 100%;
                border: none;
            }}
        </style>
    </head>
    <body>
        <iframe src="{jbrowse_index_url}"></iframe>
    </body>
    </html>
    """
    return HttpResponse(html_content)
