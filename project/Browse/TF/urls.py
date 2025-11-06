from django.urls import path
from . import views

urlpatterns = [
    path('', views.tf, name='browse_tf'),
]
