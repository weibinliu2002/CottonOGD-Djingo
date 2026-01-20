from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from CottonOGD.views.base import UuidManager
from CottonOGD.models import Species_info, Family
import logging
import json

logger = logging.getLogger(__name__)

@api_view(['GET'])
def get_species_info(request):
    uuid=request.headers.get('uuid')
    if uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        species_info = Species_info.objects.all().values('Cotton_Species','Genome_type','name','alias')
        return Response({'species_info': list(species_info)}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching species info: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_family_info(request):
    uuid=request.headers.get('uuid')
    if uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    #species=request.GET.get('species')
    try:
        family_info = Family.objects.all().values()
        return Response({'family_info': list(family_info)}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching family info: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



