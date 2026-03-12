"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
import os
from django.conf.urls.static import static

from debug_toolbar.toolbar import debug_toolbar_urls
from django.http import HttpResponse
#from rest_framework.response import DefaultRenderer
from django.views.generic import TemplateView
# 导入jbrowse的views
from CottonOGD.views.jbrowes_file import serve_large_file
from CottonOGD.views.DownloadGenome import *

def chrome_devtools_config(request):
    return HttpResponse(status=204)  # 返回空内容的成功响应

# 添加jbrowse静态文件目录
#JBROWSE_STATIC_DIR = os.path.join(settings.BASE_DIR, '../vue_app/dist/jbrowse')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('CottonOGD_api/', include(('CottonOGD.urls', 'CottonOGD'), namespace='CottonOGD')),
    path('.well-known/appspecific/com.chrome.devtools.json', chrome_devtools_config),
    path('jbrowse/large/<str:genome_name>/<str:filename>', serve_large_file, name='serve_large_file'),
    path('static/jbrowse/data/<str:genome_name>/<str:filename>', serve_large_file, name='serve_large_file_static'),
    path('download_genome/<str:genome_id>/<str:file_type>', download_genome_file, name='download_genome_file'),
    # 处理基因组文件下载（静态文件服务）
] + static('/data/genome/', document_root=os.path.join(settings.BASE_DIR, 'data', 'genome')) + debug_toolbar_urls() + [
    # 捕获所有路由，指向index.html，让Vue Router处理
    path('', TemplateView.as_view(template_name='index.html')),
    path('<path:path>', TemplateView.as_view(template_name='index.html')),
]

# 注释掉的路径配置
'''
    path('', include('home.urls')),
    path('Browse/', include(('Browse.urls', 'Browse'), namespace='browse')),
    path('tools/', include(('tools.urls', 'tools'), namespace='tools')),

    # 添加jbrowse应用的URL配置
    # 在静态文件服务之前添加jbrowse大文件服务的URL配置
    path('jbrowse/large/<str:genome_name>/<str:filename>', serve_large_file, name='serve_large_file'),
    path('static/jbrowse/data/<str:genome_name>/<str:filename>', serve_large_file, name='serve_large_file_static'),
    # 添加jbrowse应用的URL配置
    path('jbrowse/', include(('apps.jbrowse.urls', 'jbrowse'), namespace='jbrowse')),
'''# + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static('/jbrowse/', document_root=JBROWSE_STATIC_DIR) + static('/static/jbrowse/', document_root=JBROWSE_STATIC_DIR)