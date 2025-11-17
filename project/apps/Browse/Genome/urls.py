from django.urls import path
from . import views

urlpatterns = [
    path('', views.browse_genome, name='browse_genome'),
    path('show/<int:species_id>/', views.single_show, name='single_show'),
]
