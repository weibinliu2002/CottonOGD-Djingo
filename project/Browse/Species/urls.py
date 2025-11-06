from django.urls import path
from . import views

urlpatterns = [
    path('', views.browse_species, name='browse_species'),
    path('<path:species>/', views.single_show, name='single_show'),
]