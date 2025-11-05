from django.urls import path,include

from . import views
urlpatterns = [
    path('Genome', views.genome, name='browse_genome'),
    path('Species', views.species, name='browse_species'),
    path('TF', views.tf, name='browse_tf'),
]