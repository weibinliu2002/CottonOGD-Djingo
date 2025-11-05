from django.urls import path
from Browse.Species import browse_species

urlpatterns = [
    path('.', browse_species),
]

