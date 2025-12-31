from django.urls import path
from . import views

urlpatterns = [
    path('large/<str:genome_name>/<str:filename>', views.serve_large_file, name='serve_large_file'),
]