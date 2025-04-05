from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.views import generic

# Create your views here.
def index(request):
    return render(request, 'Home/index.html')

def big_image(request,image_id):
    return render(request, 'Home/big_image.html')
from .models import Browse
class DetailView(generic.DetailView):
    model = Browse
    template_name = "Home/index.html"