# views.py
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import re

# 导入模型
from .models import gene_info, gene_annotation, gene_seq, genome_seq

# ===========================
# 工具函数
# ===========================
def normalize_gene_id(id_str: str) -> str:
    """去掉括号、引号、转录本后缀，只保留合法字符"""
    id_str = re.sub(r'[()\[\]"\'\s]', '', id_str.strip())
    id_str = re.sub(r'[^a-zA-Z0-9_:.-]', '', id_str)
    id_str = re.sub(r'\.\d+$', '', id_str)
    id_str = re.sub(r'\.[tT]\d+$', '', id_str)
    if not re.match(r'^[a-zA-Z0-9_:.-]+$', id_str):
        id_str = f"ID_{id_str}"
    return id_str

def build_jbrowse_url(seqid: str, start: int, end: int) -> str:
    """拼装 JBrowse 单基因视图地址"""
    # 使用config-based URL格式，这是之前有问题的格式
    
    genome_name = 'G.hirsutum(AD1)TM-1_HAU_v1.1'
    gff_name = 'GFF'
    loc = f"{seqid}:{max(0, start-1000)}-{end+1000}"
    # 使用正确的JBrowse 3.6.5 URL格式，包含index.html
    return f"/assets/jbrowse/index.html?config=data/{genome_name}/config.json&assembly={genome_name}&loc={loc}&tracks={gff_name}"
    '''
    genome_name = 'Ghirsutum_genome_HAU_v1.0'
    gff_name = 'TM-1.gff'
    loc = f"{seqid}:{max(0, start-1000)}-{end+1000}"
    return f"/assets/jbrowse/index.html?assembly={genome_name}&loc={loc}&tracks={gff_name}"'''
# ===========================
# 核心批量查询函数
# ===========================
from django.core.cache import cache
import hashlib,logging
logger = logging.getLogger(__name__)
def handle_bulk_request(gene_ids):
    
    
    logger.info(f"handle_bulk_request 被调用，基因ID数量: {len(gene_ids)}")
    
    # 创建请求的唯一标识，用于缓存
    request_hash = hashlib.md5(str(sorted(gene_ids)).encode('utf-8')).hexdigest()
    cache_key = f"id_search:{request_hash}"
    # 检查缓存中是否有相同请求的结果
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"使用缓存结果，请求哈希: {request_hash}")
        return JsonResponse(cached_result) 
    gene_ids = gene_ids[:100]  # 限制100个ID
    # 构建归一化映射
    id_mapping = {}
    all_ids = []
    for gid in gene_ids:
        normalized_gid = normalize_gene_id(gid)
        all_ids.append(normalized_gid)
        id_mapping[normalized_gid] = gid
    
    logger.debug(f"归一化ID映射: {id_mapping}")
    
    # 一次性查询所有表
    # 优化：使用prefetch_related和values只选择需要的字段
    genes = list(gene_info.objects.filter(IDs__in=all_ids).values(
        'IDs', 'seqid', 'start', 'end', 'strand', 'type', 'species', 'source', 'attributes'
    ))
    # 优化：使用values只选择需要的字段，避免获取大字段
    genome_seqs_qs = genome_seq.objects.filter(gene_id__in=all_ids).values(
        'gene_id', 'seq'
    )
    
    #logger.debug(f"从genome_seq表查询到 {len(genome_seqs_qs)} 条记录")
    
    annotations_qs = gene_annotation.objects.filter(Gene_ID__in=all_ids).values(
        'Gene_ID', 'GO_annotation','KEGG_annotation','Swissprot_annotation','KOG_class_annotation',
        'Pfam_annotation','TrEMBL_annotation','nr_annotation'
    )
    
    #logger.debug(f"从gene_annotation表查询到 {len(annotations_qs)} 条记录")
    '''
    # 构建映射，便于快速访问
    print(genes)
    genes_data={info['IDs']:info for info in genes}
    print(genes_data)
    #gene_seqs = {seq['gene_id']: seq for seq in gene_seqs_qs}
    genome_seqs = {seq['gene_id']: seq for seq in genome_seqs_qs}
    annotations = {annot['Gene_ID']: annot for annot in annotations_qs}
'''
    # 构建结果列表
    results = []

    for gene_id in all_ids:
        gene = next((info for info in genes if info['IDs'] == gene_id and info['type'] == 'gene'), {})
        mrna_transcripts = [info for info in genes if info['IDs'] == gene_id and info['type'] == 'mRNA']
        genome_seq_data = next((seq for seq in genome_seqs_qs if seq['gene_id'] == gene_id), {})
        annotation_data = next((annot for annot in annotations_qs if annot['Gene_ID'] == gene_id), {})

        result = {
            'IDs': gene_id,
            'original_id': id_mapping.get(gene_id, gene_id),

            'seqid': gene.get('seqid', ''),
            'start': gene.get('start', 0),
            'end': gene.get('end', 0),
            'strand': gene.get('strand', ''),
            'type': gene.get('type', ''),
            'species': gene.get('species', ''),
            'source': gene.get('source', ''),
            'attributes': gene.get('attributes', ''),

            # ⚠️ genome 序列是否真的需要？如果很大，建议也懒加载
            'gene_seq': genome_seq_data.get('seq', ''),
            # 只保留 transcript 的「存在性 & 坐标」
            'mrna_transcripts': [{
                'gene_id': gene_id,
                'id': {
                    # 解析attributes字段，提取Parent值
                    # attributes格式: "ID=Gh_D01G0001;Parent=Gh_D01G0001"
                    **dict(item.split('=') for item in mrna.get('attributes', '').split(';') if '=' in item)
                }.get('ID', ''),
                
                'seqid': mrna.get('seqid', ''),
                'start': mrna.get('start', 0),
                'end': mrna.get('end', 0),
                'strand': mrna.get('strand', '')
            } for mrna in mrna_transcripts],
            'gff_data': genes,
            'annotations': {
                k: [v] if v else []
                for k, v in annotation_data.items()
                if k != 'Gene_ID'
            },

            'jbrowse_url': build_jbrowse_url(
                gene.get('seqid', ''),
                gene.get('start', 0),
                gene.get('end', 0)
            )
        }

        results.append(result)


    has_sequences = any(
        bool(r.get('gene_seq')) or bool(r.get('mrna_transcripts'))
        for r in results
    )


    logger.info(f"handle_bulk_request 执行完成，返回结果数量: {len(results)}")
    
    # 创建响应对象
    response = {
        'status': 'success',
        'results': results,
        'total': len(results),
        'query_ids': gene_ids,
        'has_sequences': has_sequences
    }
    
    # 缓存结果，有效期5分钟
    cache.set(cache_key, response, timeout=300)
    logger.info(f"缓存结果，请求哈希: {request_hash}，有效期5分钟")
    
    logger.info(f"handle_bulk_request 执行完成，返回结果数量: {len(results)}")
    return JsonResponse(response)


# ===========================
# POST 表单提交 API
# ===========================
@method_decorator(csrf_exempt, name='dispatch')
class IdSearchFormAPIView(View):
    """表单提交基因ID搜索"""

    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        # 记录请求信息
        logger.info(f"IdSearchFormAPIView.post 被调用")
        logger.info(f"请求方法: {request.method}")
        logger.info(f"请求路径: {request.path}")
        logger.info(f"请求参数: {request.POST}")
        
        gene_ids_text = request.POST.get('gene_ids', '')
        query_ids = [line.strip() for line in gene_ids_text.split('\n') if line.strip()]
        if not query_ids:
            return JsonResponse({
                'status': 'success',
                'results': [],
                'total': 0,
                'query_ids': [],
                'has_sequences': False
            })

        
        # 调用handle_bulk_request并记录调用信息
        logger.info(f"调用handle_bulk_request，基因ID数量: {len(query_ids)}")
        result = handle_bulk_request(query_ids)
        print(result)
        logger.info(f"handle_bulk_request执行完成，返回结果数量: {len(result.get('results', []))}")
        
        return result


@method_decorator(csrf_exempt, name='dispatch')
class SequenceAPIView(View):
    def get(self, request):
        return self._handle_request(request)
    
    def post(self, request):
        return self._handle_request(request)
    
    def _handle_request(self, request):
        # 从GET或POST中获取参数
        mrna_id = None
        seq_type = None
        transcript_id = None
        
        if request.method == 'GET':
            # 处理GET请求
            mrna_id = request.GET.get('gene_id')
            seq_type = request.GET.get('type')  # mrna / cds / protein
            transcript_id = request.GET.get('transcript_id')
        else:
            # 处理POST请求，支持表单数据和JSON数据
            try:
                # 尝试解析JSON数据
                import json
                post_data = json.loads(request.body)
                mrna_id = post_data.get('gene_id')
                seq_type = post_data.get('type')
                transcript_id = post_data.get('transcript_id')
            except Exception as e:
                # 如果解析失败，尝试从表单数据中获取
                logger.error(f"解析POST数据失败: {e}")
                mrna_id = request.POST.get('gene_id')
                seq_type = request.POST.get('type')
                transcript_id = request.POST.get('transcript_id')
        
        logger.info(f"获取到的参数: gene_id={mrna_id}, type={seq_type}, transcript_id={transcript_id}")
        
        # 验证参数
        if not mrna_id or seq_type not in {'mrna', 'cds', 'protein','cdna','upstream','downstream'}:
            return JsonResponse({'status': 'error', 'msg': f'无效的参数: gene_id={mrna_id}, type={seq_type}'}, status=400)

        # 字段映射
        field_map = {
            'mrna': 'mrna_seq',
            'cds': 'cds_seq',
            'protein': 'protein_seq',
            'cdna': 'cdna_seq',
            'upstream': 'upstream_seq',
            'downstream': 'downstream_seq'
        }

        # 查询序列，同时支持gene_id和mrna_id
        # 先获取所有gene_seq记录
        seq_query = gene_seq.objects
        
        # 构建查询条件：同时检查gene_id和mrna_id字段
        if mrna_id:
            # 使用简单的OR查询，不使用Q对象
            seq_query = seq_query.filter(gene_id=mrna_id) | seq_query.filter(mrna_id=mrna_id)
        
        # 如果transcript_id存在，也可以用来过滤
        if transcript_id:
            # 使用简单的OR查询，不使用Q对象
            seq_query = seq_query.filter(gene_id=transcript_id) | seq_query.filter(mrna_id=transcript_id)
        
        seq = seq_query.values_list(field_map[seq_type], flat=True).first()
        
        logger.info(f"查询结果: gene_id={mrna_id}, type={seq_type}, sequence_length={len(seq) if seq else 0}")
        
        # 返回结果
        return JsonResponse({
            'status': 'success',
            'mrna_id': mrna_id,
            'type': seq_type,
            'sequence': seq or ''
        })

