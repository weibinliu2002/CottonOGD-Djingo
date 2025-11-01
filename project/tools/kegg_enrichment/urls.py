from django.urls import path
from . import views

urlpatterns = [
    path('kegg_enrichment/', views.kegg_enrichment, name='kegg_enrichment'),
]