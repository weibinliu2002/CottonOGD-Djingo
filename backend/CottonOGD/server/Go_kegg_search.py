from CottonOGD.models import gene_go, GoTerm, GoRelationship, gene_kegg, KOTerm


def go_annotation(ids:list or str):
    results = []
    if not ids:
        return []
    
    # 如果是单个ID
    if isinstance(ids, str):
        annotations = gene_go.objects.filter(id_id=ids).select_related('go_id')
    # 如果是多个ID列表
    elif isinstance(ids, list):
        annotations = gene_go.objects.filter(id_id__in=ids).select_related('go_id')
    else:
        return []
    
    for ann in annotations:
        go_term = ann.go_id
        results.append({
            'id_id': ann.id_id_id if ann.id_id else None,  # 使用 id_id_id 获取外键的实际值
            'go_id': go_term.id if go_term else None,
            'description': go_term.definition if go_term else '',
            'name': go_term.name if go_term else '',
            'namespace': go_term.namespace if go_term else ''
        })
    return results


def kegg_annotation(ids: list or str):
    """
    根据基因ID查询KEGG注释信息
    
    参数:
        ids: 基因ID（单个字符串或列表）
    
    返回:
        KEGG注释列表，包含 kegg_id, description, name, pathway 等信息
    """
    results = []
    if not ids:
        return []
    
    # 如果是单个ID
    if isinstance(ids, str):
        annotations = gene_kegg.objects.filter(id_id=ids).select_related('kegg_id')
    # 如果是多个ID列表
    elif isinstance(ids, list):
        annotations = gene_kegg.objects.filter(id_id__in=ids).select_related('kegg_id')
    else:
        return []
    
    for ann in annotations:
        ko_term = ann.kegg_id
        results.append({
            'id_id': ann.id_id_id if ann.id_id else None,
            'kegg_id': ko_term.ko_id if ko_term else None,
            'description': ko_term.full_name if ko_term else '',
            'name': ko_term.name if ko_term else '',
            'ec_number': ko_term.ec_number if ko_term else '',
            'is_enzyme': ko_term.is_enzyme if ko_term else False
        })
    
    return results