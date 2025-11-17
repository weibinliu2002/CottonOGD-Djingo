from django.urls import path
from . import views

urlpatterns = [
    path('kegg_annotation/', views.kegg_annotation, name='kegg_annotation'),
]