from django.urls import path
from . import views

urlpatterns = [
    path('', views.go_enrichment, name='go_enrichment'),
    path('api/start/', views.start_go_enrichment_api, name='start_go_enrichment_api'),
    path('api/results/', views.get_go_enrichment_results, name='get_go_enrichment_results'),
]