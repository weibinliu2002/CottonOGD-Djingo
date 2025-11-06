from django.shortcuts import render

# Create your views here.
def tf(request):
    return render(request, 'TF/index.html')
