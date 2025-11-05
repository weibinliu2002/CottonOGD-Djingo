from django.urls import include, path
from . import views 
app_name = 'submit' 
urlpatterns = [
    path('submit/', views.submit, name='submit'),
    path('batch_import_data/', views.batch_import_data, name='batch_import_data'),
    path('batch_import_history/', views.batch_import_history, name='batch_import_history'),
]