from django.urls import path,include
from .views import HomeView 
from jbrowse import views as jbrowse_views 


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('jbrowse/', include('jbrowse.urls'),name='jbrowse'),
]