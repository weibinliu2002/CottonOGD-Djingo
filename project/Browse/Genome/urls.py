from django.urls import path
from . import views

urlpatterns = [
    path('', views.genome, name='browse_genome'),
]
