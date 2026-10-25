
from CottonOGD.models import AnnotationSource, AnnotationDetail,  gene_annotation
"""根据基因ID查询注释
"""

def get_annotation(id_id: str or list):
    """根据基因ID查询注释信息"""
    if not id_id:
        return []
    
    # 如果是单个ID
    if isinstance(id_id, str):
        annotations = gene_annotation.objects.filter(id_id=id_id).select_related('annotation_detail', 'source')
    # 如果是多个ID列表
    elif isinstance(id_id, list):
        annotations = gene_annotation.objects.filter(id_id__in=id_id).select_related('annotation_detail', 'source')
    else:
        return []
    
    # 整理结果
    result = []
    for ann in annotations:
        detail = ann.annotation_detail
        result.append({
            'id_id': ann.id_id_id if ann.id_id else None,
            'genome_id': ann.genome_id if ann.genome else None,
            'source': {
                'id': ann.source.id if ann.source else None,
                'name': ann.source.name if ann.source else None,
                'description': ann.source.description if ann.source else None
            },
            'annotation': {
                'id': detail.id,
                'annotation_id': detail.annotation_id,
                'description': detail.description,
                'protein_name': detail.protein_name,
                'gene_name': detail.gene_name,
                'species': detail.species,
                'ox': detail.ox,
                'pe': detail.pe,
                'sv': detail.sv,
                'full_header': detail.full_header,
                'accession': detail.accession,
                'pfam_type': detail.pfam_type,
                'clan': detail.clan,
                'model_length': detail.model_length,
                'gathering_threshold': detail.gathering_threshold,
                'cog_category': detail.cog_category,
                'cog_class': detail.cog_class,
                'eggnog_og': detail.eggnog_og,
                'other_info': detail.other_info
            }
        })
    return result

def get_annotation_source():
    """获取所有注释来源"""
    sources = AnnotationSource.objects.all()
    return [{'id': s.id, 'name': s.name, 'description': s.description} for s in sources]

def get_genes_by_annotation_id(annotation_id: str, genome_ids: list = None):
    """
    根据注释ID获取对应的基因组中的所有基因ID
    
    参数:
        annotation_id: 注释ID（如 UniProt ID）
        genome_ids: 基因组ID列表，可选，如果提供则只返回指定基因组的基因
    
    返回:
        基因ID列表
    """
    # 获取注释详情ID
    try:
        detail = AnnotationDetail.objects.get(annotation_id=annotation_id)
    except AnnotationDetail.DoesNotExist:
        return []
    
    # 查询关联的基因注释
    query = gene_annotation.objects.filter(annotation_detail=detail)
    
    # 如果指定了基因组，则筛选
    if genome_ids and isinstance(genome_ids, list) and len(genome_ids) > 0:
        query = query.filter(genome_id__in=genome_ids)
    
    # 返回所有匹配的基因ID
    return list(query.values_list('id_id_id', flat=True))

def get_annotation_detail(annotation_id: str):
    """根据注释ID获取注释详情"""
    try:
        detail = AnnotationDetail.objects.get(annotation_id=annotation_id)
        return {
            'id': detail.id,
            'annotation_id': detail.annotation_id,
            'source': detail.source.name if detail.source else None,
            'description': detail.description,
            'protein_name': detail.protein_name,
            'gene_name': detail.gene_name,
            'species': detail.species,
            'ox': detail.ox,
            'pe': detail.pe,
            'sv': detail.sv,
            'full_header': detail.full_header,
            'accession': detail.accession,
            'pfam_type': detail.pfam_type,
            'clan': detail.clan,
            'model_length': detail.model_length,
            'gathering_threshold': detail.gathering_threshold,
            'cog_category': detail.cog_category,
            'cog_class': detail.cog_class,
            'eggnog_og': detail.eggnog_og,
            'other_info': detail.other_info
        }
    except AnnotationDetail.DoesNotExist:
        return None