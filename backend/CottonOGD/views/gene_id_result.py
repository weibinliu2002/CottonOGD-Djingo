from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
from CottonOGD.models import gene_annotation, gene_info
import logging,json
logger = logging.getLogger(__name__)


def build_jbrowse_url(seqid: str, start: int, end: int,genome_name: str) -> str:
    """生成 JBrowse 3.6.5 单基因视图 URL"""
    gff_name = 'GFF'
    loc = f"{seqid}:{max(0, start-1000)}-{end+1000}"
    return f"/assets/jbrowse/index.html?config=data/{genome_name}/config.json&assembly={genome_name}&loc={loc}&tracks={gff_name}"

@api_view(['POST'])
def geneid_summary(request):
    uuid = request.headers.get('uuid')
    if not uuid or uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    # 从多个来源获取 gene_id：请求体、查询参数
    gene_id = request.data.get('gene_id') or request.query_params.get('gene_id')
    genome_id = request.data.get('genome_id') or request.query_params.get('genome_id')
    genome_gene_id = Id_map(gene_id,genome_id)
    #logger.info(f"get_gene_id_result gene_id: {genome_gene_id}")
    try:
        # 从 Id_map 返回的字典中提取所有 db_id
        db_ids = []
        if isinstance(genome_gene_id, dict):
            for key, value in genome_gene_id.items():
                if isinstance(value, dict) and 'db_id' in value:
                    db_ids.append(value['db_id'])
        
        # 去重
        db_ids = list(set(db_ids))
        logger.info(f"get_gene_id_result db_ids: {db_ids}")
        
        # 使用 db_id 过滤基因注释
        gene_annotation_result = gene_annotation.objects.filter(id_id__in=db_ids).values()
        gene_info_result = gene_info.objects.filter(id_id__in=db_ids).values()
        # 构建 JBrowse URL
        geneid_result=json.dumps(list(gene_annotation_result))
        gene_info_result=json.dumps(list(gene_info_result))
        search_map=json.dumps(genome_gene_id)
        return Response({'geneid_result': geneid_result,
                         'gene_info_result': gene_info_result,
                         'search_map': search_map,
                         }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"get_gene_id_result error: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
def geneid_result(request):
    uuid=request.headers.get('uuid')
    
    if uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    # 从多个来源获取参数：request.data（JSON）、request.POST（表单）、request.query_params（查询参数）
    gene_id=request.data.get('gene_id') or request.POST.get('gene_id') or request.query_params.get('gene_id')
    genome_id=request.data.get('genome_id') or request.POST.get('genome_id') or request.query_params.get('genome_id')
    db_id=request.data.get('db_id') or request.POST.get('db_id') or request.query_params.get('db_id')
    logger.info(f"get_gene_id_result gene_id: {gene_id}, genome_id: {genome_id}, db_id: {db_id}")
    
    if isinstance(db_id, str) and db_id.strip():
        db_ids = [db_id]
    else:
        # 处理 Id_map 返回的字典
        db_map = Id_map(gene_id, genome_id)
        logger.info(f"get_gene_id_result db_ids: {db_map}")
        
        # 从 db_map 中提取 db_id（单个基因）
        db_ids = []
        if isinstance(db_map, dict):
            # 直接获取第一个值，因为是单个基因
            first_value = next(iter(db_map.values()), None)
            if isinstance(first_value, dict) and 'db_id' in first_value:
                db_ids.append(first_value['db_id'])
        
        logger.info(f"get_gene_id_result db_ids: {db_ids}")
    
    # 确保 db_ids 不为空
    if not db_ids:
        return Response({'error': 'No valid db_id found'}, status=status.HTTP_400_BAD_REQUEST)

    gene_annotation_result = gene_annotation.objects.filter(id_id__in=db_ids).values()
    gene_info_result = gene_info.objects.filter(id_id__in=db_ids).values()
    
    # 构建 JBrowse URL（如果有基因信息）
    jbrowse_url = None
    if gene_info_result:
        # 取第一个基因信息来构建 URL
        gene = gene_info_result.first()
        if gene:
            seqid = gene.get('seqid', '')
            start = gene.get('start', 0)
            end = gene.get('end', 0)
            genome_id = gene.get('genome_id', '')
            jbrowse_url = build_jbrowse_url(seqid, start, end, genome_id)
    #logger.info(f"get_gene_id_result genes: {gene_info_result}")
    return Response({'geneid_result': list(gene_annotation_result),
                         'gene_info_result': list(gene_info_result),
                         'jbrowse_url': jbrowse_url
                         }, status=status.HTTP_200_OK)
