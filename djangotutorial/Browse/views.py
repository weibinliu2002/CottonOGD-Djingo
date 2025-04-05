from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'Browse/index.html')  # 确保模板名称拼写正确
