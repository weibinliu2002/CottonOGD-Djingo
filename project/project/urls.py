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


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('tools/', include(('tools.urls', 'tools'), namespace='tools')),
    path('tools/', include(('tools.id_search.urls', 'tools.id_search'), namespace='tools_id_search')),
    path('tools/', include(('tools.blastp.urls', 'tools.blastp'), namespace='tools_blastp')),
    path('tools/', include(('tools.go_enrichment.urls', 'tools.go_enrichment'), namespace='tools_go_enrichment')), 
    path('tools/', include(('tools.go_annotation.urls', 'tools.go_annotation'), namespace='tools_go_annotation')),
    path('tools/', include(('tools.kegg_annotation.urls', 'tools.kegg_annotation'), namespace='tools_kegg_annotation')),  
    path('tools/', include(('tools.kegg_enrichment.urls', 'tools.kegg_enrichment'), namespace='tools_kegg_enrichment')), 
    path('tools/', include(('tools.heatmap.urls', 'tools.heatmap'), namespace='tools_heatmap')),
    path('tools/', include(('tools.gene_expression.urls', 'tools.gene_expression'), namespace='tools_gene_expression')),
    path('tools/', include(('tools.gene_expression_in_eFP.urls', 'tools.gene_expression_in_eFP'), namespace='tools_gene_expression_in_eFP')),
    path('tools/', include(('tools.jbrowse.urls', 'tools.jbrowse'), namespace='tools_jbrowse')),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 
