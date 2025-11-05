from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.
def browse_species(request):
    return HttpResponse("Hello, world. You're at the Species browse.")
    #return render(request, 'browse/species.html')