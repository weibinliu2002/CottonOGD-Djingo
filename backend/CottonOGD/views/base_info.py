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
        species_info = Species_info.objects.all().values('Cotton_Species','Genome_type','name','alias','Article')
        response_payload = json.dumps(list(species_info), ensure_ascii=False)
        return Response({'species_info': response_payload}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching species info: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def get_family_info(request):

    uuid=request.headers.get('uuid')
    if uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    selectedGenome=request.data.get('selectedGenome') or ''
    selectedClass=request.data.get('Class') or ''
    logger.info(f"selectedGenome: {selectedGenome}, selectedClass: {selectedClass}")
    try:
        if selectedGenome and selectedClass:
            family_list = list(Family.objects.filter(genome_id=selectedGenome,TF_class=selectedClass).values())
        else:
            family_list = list(Family.objects.all().values())
        #logger.info(f"family_list: {family_list}")
        
        # 计算每个家族的基因数量
        family_counts = {}
        for family in family_list:
            tf_name = family['TF_name']
            if tf_name in family_counts:
                family_counts[tf_name] += 1
            else:
                family_counts[tf_name] = 1
        
        # 构建家族信息列表
        family_info = [{'name': name, 'count': count} for name, count in family_counts.items()]
        #logger.info(f"family_info: {family_info}")
        
        info=json.dumps(family_info, ensure_ascii=False)
        family_list_json=json.dumps(family_list, ensure_ascii=False)
        return Response({'family_info': info,'family_list':family_list_json}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching family info: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



