from django.urls import path
from . import views

urlpatterns = [
    path('', views.go_annotation, name='go_annotation'),
]