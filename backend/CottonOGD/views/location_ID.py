from ast import alias
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.decorators import api_view
from CottonOGD.views.base import UuidManager
from CottonOGD.models import GeneMaster
import re, logging
logger = logging.getLogger(__name__)



import hashlib
from django.core.cache import cache

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
#def Id_map(request):
def Id_map(gene_id: str, genome_id: str):
    # 生成缓存键
    cache_key = f"id_map:{hashlib.md5(f'{gene_id}:{genome_id}'.encode()).hexdigest()}"
    
    # 尝试从缓存获取
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # 以逗号或换行符分割输入，过滤空字符串
    gene_ids = [gid.strip() for gid in re.split(r'[,|\n]+', gene_id) if gid.strip()]
    genome_ids = [gid.strip() for gid in re.split(r'[,|\n]+', genome_id) if gid.strip()]
    
    # 如果没有基因ID或基因组ID，直接返回空字典
    if not gene_ids or not genome_ids:
        return {}
    
    id_map = {}
    search_ids = []
    
    logger.info(f"gene_ids: {gene_ids}")
    for i, gid in enumerate(gene_ids):
        # 如果基因 ID 数量大于基因组 ID 数量，重复使用第一个基因组 ID
        genome = genome_ids[0] if len(gene_ids) > len(genome_ids) else genome_ids[i]
        nid = clean_gene_id(gid)
        search_id = f"{genome}_{nid}"
        search_ids.append(search_id)
        id_map[gid] = {'geneid': nid, 'genome_id': genome, 'search_id': search_id}
    
    # 优化数据库查询，直接使用search_ids查询alias字段
    # 这样可以避免使用OR条件，提高查询效率
    map_ids = GeneMaster.objects.filter(alias__in=search_ids).values('alias', 'id')
    map_ids = {item['alias']: item['id'] for item in map_ids}
    
    genome_gene_id = attach_db_id(id_map, map_ids)
    
    # 保存到缓存，设置过期时间为1小时
    cache.set(cache_key, genome_gene_id, 3600)
    
    return genome_gene_id
    #logger.info(f"id_map: {id_map}")
    #return Response({'map':genome_gene_id,'normalized_ids':norm_map})
