from django.urls import path
from . import views

urlpatterns = [
    path('heatmap/', views.heatmap, name='heatmap'),
]