from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.
def genome(request):
    return render(request, 'Genome/index.html')
def species(request):
    return render(request, 'Species/index.html')
def tf(request):
    return render(request, 'TF/index.html')
