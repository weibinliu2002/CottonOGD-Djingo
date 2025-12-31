from django.urls import include, path
from .views import PrimerDesignAPIView

app_name = 'tools' 
urlpatterns = [
    path('blastp/', include('tools.blastp.urls')),
    path('id-search/', include('tools.id_search.urls')),
    path('go_enrichment/', include('tools.go_enrichment.urls')),
    path('go_annotation/', include('tools.go_annotation.urls')),
    path('kegg_annotation/', include('tools.kegg_annotation.urls')),
    path('kegg_enrichment/', include('tools.kegg_enrichment.urls')),
    path('gene_expression/', include('tools.gene_expression.urls')),
    path('gene_expression_in_eFP/', include('tools.gene_expression_in_eFP.urls')),
    path('primer_design/api/primers/', PrimerDesignAPIView.as_view(), name='primer_design_api'),
]