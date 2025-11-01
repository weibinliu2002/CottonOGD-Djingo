from django.urls import path
from .views import IDSearchView

app_name = 'id_search'

urlpatterns = [
    path('id-search/', IDSearchView.as_view(), name='id_search'),
    
]