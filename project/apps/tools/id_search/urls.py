from django.urls import path
from .views import IDSearchView, IdSearchResults, IdSearchAPIView, IdSearchFormAPIView

app_name = 'id_search'

urlpatterns = [
    # 仅保留API路由，让Vue前端处理页面路由
    # API端点 - 为Vue前端提供数据
    path('api/id-search/', IdSearchAPIView.as_view(), name='id_search_api'),
    path('api/id-search-form/', IdSearchFormAPIView.as_view(), name='id_search_form_api'),
]