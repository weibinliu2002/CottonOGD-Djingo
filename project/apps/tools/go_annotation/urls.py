from django.urls import path
from . import views

urlpatterns = [
    path('go_annotation/', views.go_annotation, name='go_annotation'),
]