from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
from CottonOGD.models import gene_expression
import logging
logger = logging.getLogger(__name__)


@api_view(['POST'])
def extract_expression(request):
    if request.method == 'POST':
        uuid = request.headers.get('uuid')
        if not uuid or uuid not in UuidManager.uuid_storage:
            return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
        db_id = request.data.get('db_id')
        if not db_id:
             # 从多个来源获取 gene_id：请求体、查询参数
            gene_id = request.data.get('gene_id') or request.query_params.get('gene_id')
            genome_id = request.data.get('genome_id') or request.query_params.get('genome_id')
            db_id = Id_map(genome_id,gene_id)
            #return Response({'error': 'db_id is required'}, status=status.HTTP_400_BAD_REQUEST)
       
        sample_id = request.data.get('sample_id') or request.query_params.get('sample_id')
        gene_expr=gene_expression.objects.filter(id_id__in=db_id)

        return Response({'expression': gene_expr}, status=status.HTTP_200_OK)
