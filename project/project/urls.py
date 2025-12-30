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
from home.views import HomeView
from django.conf.urls.static import static
from django.conf import settings
from debug_toolbar.toolbar import debug_toolbar_urls
from django.http import HttpResponse
#from rest_framework.response import DefaultRenderer
from django.views.generic import TemplateView
from django.conf.urls.static import static
from django.conf import settings
import os
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
def chrome_devtools_config(request):
    return HttpResponse(status=204)  # 返回空内容的成功响应

schema_view = get_schema_view(
    openapi.Info(
        title="Your API",
        default_version='v1',
        description="API description",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
# 添加jbrowse静态文件目录
JBROWSE_STATIC_DIR = os.path.join(settings.BASE_DIR, '../vue_app/dist/jbrowse')


urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('admin/', admin.site.urls),
    #path('', include('home.urls')),
    path('Browse/', include(('Browse.urls', 'Browse'), namespace='browse')),
    
    # 处理jbrowse基础请求
    #path('jbrowse/', TemplateView.as_view(template_name='index.html'), name='jbrowse'),
    #path('submit/', include(('submit.urls', 'submit'), namespace='submit')),
    path('tools/', include(('tools.urls', 'tools'), namespace='tools')),
    #path('tools/', include(('tools.id_search.urls', 'tools.id_search'), namespace='tools_id_search')),
    #path('tools/', include(('tools.blastp.urls', 'tools.blastp'), namespace='tools_blastp')),
    #path('tools/', include(('tools.go_enrichment.urls', 'tools.go_enrichment'), namespace='tools_go_enrichment')), 
    #path('tools/', include(('tools.go_annotation.urls', 'tools.go_annotation'), namespace='tools_go_annotation')),
    #path('tools/', include(('tools.kegg_annotation.urls', 'tools.kegg_annotation'), namespace='tools_kegg_annotation')),  
    #path('tools/', include(('tools.kegg_enrichment.urls', 'tools.kegg_enrichment'), namespace='tools_kegg_enrichment')), 
    #path('tools/', include(('tools.heatmap.urls', 'tools.heatmap'), namespace='tools_heatmap')),
    #path('tools/', include(('tools.gene_expression.urls', 'tools.gene_expression'), namespace='tools_gene_expression')),
    #path('tools/', include(('tools.gene_expression_in_eFP.urls', 'tools.gene_expression_in_eFP'), namespace='tools_gene_expression_in_eFP')),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # ...

    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('.well-known/appspecific/com.chrome.devtools.json', chrome_devtools_config),
    # 捕获所有其他路由，指向index.html，让Vue Router处理
    path('<path:path>', TemplateView.as_view(template_name='index.html')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static('/jbrowse/', document_root=JBROWSE_STATIC_DIR) + static('/static/jbrowse/', document_root=JBROWSE_STATIC_DIR)