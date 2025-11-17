from django.urls import path
from .views import IDSearchView, IdSearchResults

app_name = 'id_search'

urlpatterns = [
    path('id-search/', IDSearchView.as_view(), name='id_search'),
    path('id-search-results/', IdSearchResults.as_view(), name='id_search_results'),
    #path('get_flanking_sequences/<str:gene_id>/', get_flanking_sequences, name='get_flanking_sequences'),
]