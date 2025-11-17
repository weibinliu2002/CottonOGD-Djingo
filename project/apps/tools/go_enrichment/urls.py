from django.urls import path
from . import views

urlpatterns = [
    path('go_enrichment/', views.go_enrichment, name='go_enrichment'),
]