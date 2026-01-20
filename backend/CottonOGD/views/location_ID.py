from rest_framework.response import Response
from rest_framework.decorators import api_view
from CottonOGD.views.base import UuidManager
from CottonOGD.models import GeneMaster
import re, logging
logger = logging.getLogger(__name__)



def clean_gene_id(id_str: str) -> str:
    id_str = re.sub(r'[()\[\]"\'\s]', '', id_str.strip())
    id_str = re.sub(r'[^a-zA-Z0-9_:.-]', '', id_str)
    id_str = re.sub(r'\.\d+$|\.t\d+$', '', id_str)  # 一步去掉 .数字 或 .t数字
    if not re.match(r'^[a-zA-Z0-9_:.-]+$', id_str):
        id_str = f"ID_{id_str}"
    return id_str
def attach_db_id(genome_gene_id: dict, map_ids: dict) -> dict:
    """
    将 map_ids 中的数据库 id，关联回 genome_gene_id
    """
    for raw_id, info in genome_gene_id.items():
        search_id = info.get("search_id")
        info["db_id"] = map_ids.get(search_id)  # 不存在就 None

    return genome_gene_id

#@api_view(['POST'])
def Id_map(gene_id: str,genome_id: str):
    '''
    uuid=request.headers.get('uuid')
    if not uuid:
        return Response({'error': 'uuid is required'}, status=400)
    gene_id = request.data.get('gene_id') or request.query_params.get('gene_id')
    genome_id = request.data.get('genome_id') or request.query_params.get('genome_id')
    if not gene_id or not genome_id:
        return Response({'error': 'gene_id and genome_id are required'}, status=400)'''
    gene_ids = [gid.strip() for gid in gene_id.split(',')]
    genome_ids = [gid.strip() for gid in genome_id.split(',')]
    # 检查基因 ID 和基因组 ID 列表长度是否相同
    '''
    if len(gene_ids) != len(genome_ids):
        return Response({'error': 'gene_id and genome_id lists must have the same length'}, status=400)'''
    norm_map = []
    id_map = {}
    normalized_ids = {}
    search_ids=[]
    for gid, genome in zip(gene_ids, genome_ids):
        nid = clean_gene_id(gid)
        if nid not in norm_map:
            norm_map.append(nid)
            search_ids.append(f"{genome}_{nid}")
            normalized_ids[nid] = {'normalized_id': nid, 'genome_id': genome,'search_id':f"{genome}_{nid}"}
        id_map[gid] = {'geneid':nid,'genome_id':genome,'search_id':f"{genome}_{nid}"}
    map_ids=GeneMaster.objects.filter(alias__in=search_ids).values('alias','id')
    map_ids={item['alias']:item['id'] for item in map_ids}
    genome_gene_id = attach_db_id(id_map, map_ids)
    return genome_gene_id
    #logger.info(f"id_map: {id_map}")
    #return Response({'map':genome_gene_id})
