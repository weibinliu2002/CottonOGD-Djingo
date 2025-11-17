from django.urls import path
from . import views

urlpatterns = [
    path('gene_expression/', views.gene_expression, name='gene_expression'),
]