from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
from CottonOGD.models import gene_annotation, gene_info,gene_seq,gene_go,gene_kegg
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
   
    db_id = request.data.get('db_id') or request.query_params.get('db_id')
    db_ids = []
    if db_id:
        db_ids=db_ids+[db_id]
        genome_gene_id = []
    #logger.info(f"get_gene_id_result gene_id: {genome_gene_id}")
    else:
        # 从 Id_map 返回的字典中提取所有 db_id
        gene_id = request.data.get('gene_id') or request.query_params.get('gene_id')
        genome_id = request.data.get('genome_id') or request.query_params.get('genome_id')
        genome_gene_id = Id_map(gene_id,genome_id)
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
    # 获取GO和KEGG注释数据
    gene_go_result = gene_go.objects.filter(id_id__in=db_ids).values()
    gene_kegg_result = gene_kegg.objects.filter(id_id__in=db_ids).values()
    # 构建 JBrowse URL
    geneid_result=json.dumps(list(gene_annotation_result))
    gene_info_result=json.dumps(list(gene_info_result))
    search_map=json.dumps(genome_gene_id)
    return Response({'geneid_result': geneid_result,
                     'gene_info_result': gene_info_result,
                     'search_map': search_map,
                     'gene_go_result': list(gene_go_result),
                     'gene_kegg_result': list(gene_kegg_result),
                     }, status=status.HTTP_200_OK)



@api_view(['POST'])
def geneid_result(request):
    '''
    uuid=request.headers.get('uuid')
    
    if uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    '''
    # 从多个来源获取参数：request.data（JSON）、request.POST（表单）、request.query_params（查询参数）
    gene_id=request.data.get('gene_id') or request.POST.get('gene_id') or request.query_params.get('gene_id')
    genome_id=request.data.get('genome_id') or request.POST.get('genome_id') or request.query_params.get('genome_id')
    db_id=request.data.get('db_id') or request.POST.get('db_id') or request.query_params.get('db_id')
    logger.info(f"get_gene_id_result gene_id: {gene_id}, genome_id: {genome_id}, db_id: {db_id}")
    
    # 处理 db_id 参数
    if db_id:
        # 如果 db_id 存在，直接使用 db_id
        if isinstance(db_id, str) and db_id.strip():
            db_ids = [db_id]
        elif isinstance(db_id, list):
            db_ids = db_id
        else:
            # 尝试转换为整数
            try:
                db_ids = [int(float(db_id))]
            except (ValueError, TypeError):
                db_ids = []
    else:
        # 如果 db_id 不存在，使用 gene_id 和 genome_id 通过 Id_map 获取
        if not gene_id or not genome_id:
            return Response({'error': 'db_id or (gene_id and genome_id) are required'}, status=status.HTTP_400_BAD_REQUEST)
        
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
    genome_seq_result = gene_seq.objects.filter(id_id__in=db_ids).values()
    gene_go_result = gene_go.objects.filter(id_id__in=db_ids).values()
    gene_kegg_result = gene_kegg.objects.filter(id_id__in=db_ids).values()
    
    # 初始化变量
    seqid = ''
    start = 0
    end = 0
    IDs = ''
    
    # 构建 JBrowse URL（如果有基因信息）
    jbrowse_url = None
    if gene_info_result:
        # 取第一个基因信息来构建 URL
        gene = gene_info_result.filter(type='gene').first()
        if gene:
            seqid = gene.get('seqid', '')
            start = gene.get('start', 0)
            end = gene.get('end', 0)
            IDs = gene.get('geneid_id', '')
            genome_id = gene.get('genome_id', '')
            jbrowse_url = build_jbrowse_url(seqid, start, end, genome_id)
            
    mran_id = []
    for item in gene_info_result.filter(type='mRNA'):
        mran_id.append(item.get('attributes', '').split(';')[0].split('=')[1])
    logger.info(f"get_gene_id_result mran_id: {mran_id}")
    mrna_transcript_result=[]
    for item in mran_id:
        cdna_seq = genome_seq_result.filter(mrna_id=item, gene_type='cdna').first()
        cds_seq = genome_seq_result.filter(mrna_id=item, gene_type='cds').first()
        downstream_seq = genome_seq_result.filter(mrna_id=item, gene_type='downstream').first()
        mrna_seq = genome_seq_result.filter(mrna_id=item, gene_type='mrna').first()
        protein_seq = genome_seq_result.filter(mrna_id=item, gene_type='pro').first()
        upstream_seq = genome_seq_result.filter(mrna_id=item, gene_type='upstream').first()
        
        mrna_transcript_result.append({  
                'id': item,
                'cdna_seq': cdna_seq.get('sequence', '') if cdna_seq else '',
                'cds_seq': cds_seq.get('sequence', '') if cds_seq else '',
                'downstream_seq': downstream_seq.get('sequence', '') if downstream_seq else '',
                'mrna_seq': mrna_seq.get('sequence', '') if mrna_seq else '',
                'protein_seq': protein_seq.get('sequence', '') if protein_seq else '',
                'upstream_seq': upstream_seq.get('sequence', '') if upstream_seq else '',
            })
     
    #logger.info(f"get_gene_id_result mrna_transcript_result: {mrna_transcript_result}")

    results={}
    
    results={
        'seqid': seqid,
        'start': start,
        'end': end,
        'genome_id': genome_id,
        'IDs': IDs,
        'db_id': db_id,
        'gene_seq': genome_seq_result.filter(mrna_id=IDs, gene_type='genome').values_list('sequence', flat=True).first(),
        'geneid_result': list(gene_annotation_result),
        'gff_data': list(gene_info_result),
        'gene_go_result': list(gene_go_result),
        'gene_kegg_result': list(gene_kegg_result),
        'mrna_transcripts': mrna_transcript_result,    
        'jbrowse_url': jbrowse_url
                         }
    #logger.info(f"get_gene_id_result genes: {gene_info_result}")
    return Response({'results': json.dumps(results)}, status=status.HTTP_200_OK)
