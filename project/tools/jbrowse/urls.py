from django.urls import path
from . import views

urlpatterns = [
    path('jbrowse/', views.index, name='index'),
    path('jbrowse/large/<str:filename>', views.serve_large_file, name='serve_large_file'),
]