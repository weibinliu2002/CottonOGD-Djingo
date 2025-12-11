from django.urls import path
from .views import BlastpView
from .views import DownloadSequenceView

app_name = 'blastp'

urlpatterns = [
    # 保留API路由和功能性路由
    path('api/blastp/', BlastpView.as_view(), name='blastp_api'),  # API路由用于blastp搜索
    path('api/protein/<str:protein_id>/download/', DownloadSequenceView.as_view(), name='download_sequence'),  # 文件下载路由
]