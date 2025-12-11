from django.urls import path
from . import id_search_views

app_name = 'tools' 
urlpatterns = [
    # 基因ID搜索端点 - 匹配前端请求的URL
    path('id-search/api/id-search-form/', id_search_views.id_search_form, name='id_search_form'),
]