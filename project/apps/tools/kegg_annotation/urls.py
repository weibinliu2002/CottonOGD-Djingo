from django.urls import path
from . import views

urlpatterns = [
    path('', views.kegg_annotation, name='kegg_annotation'),
    path('api/start/', views.start_kegg_annotation_api, name='start_kegg_annotation_api'),
    path('api/results/', views.get_kegg_annotation_results, name='get_kegg_annotation_results'),
]