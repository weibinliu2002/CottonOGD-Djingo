from django.urls import include, path
#from CottonOGD.views.jbrowes_file import *
from CottonOGD.views.base import *
from CottonOGD.views.base_info import *
from CottonOGD.views.location_ID import *
from CottonOGD.views.gene_id_result import *
from CottonOGD.views.extract_seq import *
from CottonOGD.views.gene_expression import *
from CottonOGD.views.extract_seq_from_gff import *
from CottonOGD.views.primer_design import *



urlpatterns = [
    #path('Browse/', include(('apps.Browse.urls', 'Browse'), namespace='browse')),
    #path('large/<str:genome_name>/<str:filename>', serve_large_file, name='serve_large_file'),
    path('login/', login, name='login'),
    path('logout/', logout, name="logout"),
    path('get_species_info/', get_species_info, name='species_info'),
    path('get_family_info/', get_family_info, name='family_info'),
    path('Id_map/', Id_map, name='Id_map'),
    path('geneid_result/', geneid_result, name='geneid_result'),
    path('geneid_summary/', geneid_summary, name='geneid_summary'),
    path('extract_seq/', extract_seq, name='extract_seq'),
    path('extract_seq_gff/', extract_seq_gff, name='extract_seq_gff'),
    path('extract_expression/', extract_expression, name='extract_expression'),
    path('primer_design/', primer_design, name='primer_design'),
]