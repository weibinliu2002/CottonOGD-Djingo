"""
URL configuration for Browse application
"""
from django.urls import path
from . import views

app_name = 'browse'

urlpatterns = [
    # 主页面
    #path('', views.index, name='index'),
    
    # API 路由
    path('api/tf/', views.TFApiView.as_view(), name='tf_api'),
    path('api/tf/families/', views.TFFamilyApiView.as_view(), name='tf_families_api'),
    path('api/species/', views.SpeciesApiView.as_view(), name='species_api'),
]