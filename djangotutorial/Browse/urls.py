from django.urls import path

from . import views

app_name = 'Browse'  # 新增应用命名空间

urlpatterns = [
    path("", views.index, name="index"), 
]