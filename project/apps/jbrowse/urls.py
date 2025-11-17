from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='jbrowse'),
    path('large/<str:filename>', views.serve_large_file, name='serve_large_file'),
]