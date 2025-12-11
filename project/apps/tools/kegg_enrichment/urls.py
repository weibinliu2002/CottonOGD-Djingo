from django.urls import path
from . import views

urlpatterns = [
    path('', views.kegg_enrichment, name='kegg_enrichment'),
    path('api/start/', views.start_kegg_enrichment_api, name='start_kegg_enrichment_api'),
    path('api/results/', views.get_kegg_enrichment_results, name='get_kegg_enrichment_results'),
]