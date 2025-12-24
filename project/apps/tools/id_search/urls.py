from django.urls import path
from .views import  IdSearchFormAPIView, SequenceAPIView

urlpatterns = [
    #path('id-search/', IdSearchResults.as_view(), name='id_search_results'),
    #path('api/id-search/', IdSearchAPIView.as_view(), name='id_search_api'),
    path('api/id-search-form/', IdSearchFormAPIView.as_view(), name='id_search_form_api'),
    path('api/sequence/', SequenceAPIView.as_view(), name='sequence_api'),
]
