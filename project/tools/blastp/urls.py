from django.urls import path
from .views import BlastpView
from .views import ProteinDetailView
from .views import DownloadSequenceView

app_name = 'blastp'

urlpatterns = [
    
    path('blastp/', BlastpView.as_view(), name='blastp'),
    path('protein/<str:protein_id>/', ProteinDetailView.as_view(), name='protein_detail'),
    path('protein/<str:protein_id>/download/', DownloadSequenceView.as_view(), name='download_sequence'),
]