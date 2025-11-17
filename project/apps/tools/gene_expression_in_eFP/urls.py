from django.urls import path
from . import views

app_name = 'tools.gene_expression_in_eFP'

urlpatterns = [
    path('gene_expression_in_eFP/', views.gene_expression_in_eFP_view, name='gene_expression_in_eFP'),
    path('generate-thermal-image/', views.generate_thermal_image, name='generate_thermal_image'),
]