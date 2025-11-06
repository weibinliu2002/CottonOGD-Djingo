from django.urls import path, include
urlpatterns = [
    path('Genome/', include('Browse.Genome.urls')),
    path('Species/', include('Browse.Species.urls')),
    path('TF/', include('Browse.TF.urls')),
]