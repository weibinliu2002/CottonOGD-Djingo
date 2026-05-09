from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.models import Species_info, Family, GeneMaster, gene_info, gene_seq, gene_annotation, gene_go, gene_kegg, gene_expression
import logging
import json
import re

logger = logging.getLogger(__name__)

# ==================== 2. 通过基因组位置搜索 ====================
@api_view(['POST'])
def search_by_genome_location(request):
    """
    通过基因组位置搜索基因
    对应Shiny应用中的"Search by genome location"功能
    
    请求参数:
    - genome: 基因组名称（必需）
    - region: 基因组区域，格式如 "chr1:20260371-20686979"
    
    返回:
    - genes: 该区域内的基因列表
    - gene_sequences: 基因序列
    - repeat_regions: 重复区域信息
    """
    uuid = request.headers.get('uuid')
    if not uuid or uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    genome_name = request.data.get('genome', '')
    region = request.data.get('region', '')
    
    if not genome_name or not region:
        return Response({'error': 'genome and region are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 解析区域
    match = re.match(r'^([^:]+):(\d+)-(\d+)$', region.strip())
    if not match:
        return Response({'error': 'Invalid region format. Use chr:start-end'}, status=status.HTTP_400_BAD_REQUEST)
    
    chr_name = match.group(1)
    start = int(match.group(2))
    end = int(match.group(3))
    
    try:
        # 获取指定基因组内该区域的基因
        gene_info_results = gene_info.objects.filter(
            genome__name=genome_name,
            seqid=chr_name,
            start__lte=end,
            end__gte=start
        ).values()
        
        # 获取对应的gene_master以获取db_ids
        '''
        gene_ids = set()
        for gi in gene_info_results:
            if gi.get('geneid_id'):
                gene_ids.add(gi['geneid_id'])
        '''
        #db_ids = [gm.id for gm in GeneMaster.objects.filter(geneid__in=gene_ids, genome__name=genome_name)]
        
        # 获取序列信息
        #gene_seq_results = gene_seq.objects.filter(id_id__in=db_ids).values()
        
        results = {
            'region': region,
            'genome': genome_name,
            'genes': list(gene_info_results),
            #'gene_sequences': list(gene_seq_results),
            'count': len(list(gene_info_results))
        }
        
        return Response(results, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in search_by_genome_location: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== 3. 基因的基因组分布 ====================
@api_view(['POST'])
def gene_genomic_distribution(request):
    """
    获取基因在基因组上的分布
    对应Shiny应用中的"Genomic distribution of genes"功能
    
    请求参数:
    - genome: 基因组名称（必需）
    - gene_ids: 基因ID列表
    
    返回:
    - distribution: 基因在各染色体上的分布统计
    - gene_locations: 每个基因的具体位置
    """
    uuid = request.headers.get('uuid')
    if not uuid or uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    genome_name = request.data.get('genome', '')
    gene_ids_input = request.data.get('gene_ids', '')
    
    if not genome_name:
        return Response({'error': 'genome is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 解析基因ID列表
    gene_ids = []
    if gene_ids_input:
        gene_ids = [g.strip() for g in re.split(r'[\n,;]+', gene_ids_input) if g.strip()]
    
    try:
        if gene_ids:
            gene_masters = GeneMaster.objects.filter(geneid__in=gene_ids, genome__name=genome_name)
            db_ids = [gm.id for gm in gene_masters]
            gene_info_results = gene_info.objects.filter(id_id__in=db_ids, type='gene').values()
        else:
            # 获取该基因组所有基因
            gene_info_results = gene_info.objects.filter(genome__name=genome_name, type='gene').values()
        
        # 统计染色体分布
        chr_distribution = {}
        gene_locations = []
        
        for gene in gene_info_results:
            chr_name = gene.get('seqid', 'unknown')
            if chr_name not in chr_distribution:
                chr_distribution[chr_name] = 0
            chr_distribution[chr_name] += 1
            
            gene_locations.append({
                'gene_id': gene.get('geneid_id', ''),
                'chr': chr_name,
                'start': gene.get('start', 0),
                'end': gene.get('end', 0),
                'strand': gene.get('strand', '')
            })
        
        results = {
            'genome': genome_name,
            'chr_distribution': chr_distribution,
            'gene_locations': gene_locations,
            'total_genes': len(gene_locations)
        }
        
        return Response(results, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in gene_genomic_distribution: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== 5. 基因组共线性 ====================
@api_view(['POST'])
def genome_synteny(request):
    """
    获取基因组共线性信息
    对应Shiny应用中的"Genome synteny"功能
    
    请求参数:
    - reference_genome: 参考基因组（如 "Zhonghuang 13" 或 "Williams 82"）
    - query_genome: 查询基因组
    - chromosome: 染色体名称（如 "chr1"）
    
    返回:
    - synteny_blocks: 共线性区块信息
    - reference_genes: 参考基因组基因
    - query_genes: 查询基因组基因
    """
    uuid = request.headers.get('uuid')
    if not uuid or uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    ref_genome = request.data.get('reference_genome', '')
    query_genome = request.data.get('query_genome', '')
    chromosome = request.data.get('chromosome', '')
    
    if not ref_genome or not query_genome:
        return Response({'error': 'reference_genome and query_genome are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 获取参考基因组的基因信息
        ref_genes = gene_info.objects.filter(
            genome__name=ref_genome,
            type='gene'
        )
        if chromosome:
            ref_genes = ref_genes.filter(seqid=chromosome)
        ref_genes = ref_genes.values()
        
        # 获取查询基因组的基因信息
        query_genes = gene_info.objects.filter(
            genome__name=query_genome,
            type='gene'
        )
        query_genes = query_genes.values()
        
        results = {
            'reference_genome': ref_genome,
            'query_genome': query_genome,
            'chromosome': chromosome,
            'reference_genes': list(ref_genes),
            'query_genes': list(query_genes),
            'ref_gene_count': len(list(ref_genes)),
            'query_gene_count': len(list(query_genes))
        }
        
        return Response(results, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in genome_synteny: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== 6. 结构变异 ====================
@api_view(['POST'])
def structural_variations(request):
    """
    获取结构变异信息
    对应Shiny应用中的"Structural variations"功能
    
    请求参数:
    - reference_genome: 参考基因组
    - query_genome: 查询基因组
    - chromosome: 染色体（可选）
    - sv_type: 变异类型（可选，如: deletion, duplication, inversion等）
    
    返回:
    - sv_list: 结构变异列表
    - sv_summary: 变异类型统计
    """
    uuid = request.headers.get('uuid')
    if not uuid or uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    ref_genome = request.data.get('reference_genome', '')
    query_genome = request.data.get('query_genome', '')
    chromosome = request.data.get('chromosome', '')
    sv_type = request.data.get('sv_type', '')
    
    if not ref_genome or not query_genome:
        return Response({'error': 'reference_genome and query_genome are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 由于结构变异数据可能存储在不同的表中，这里返回空结果作为占位
        # 实际实现需要根据实际数据模型调整
        results = {
            'reference_genome': ref_genome,
            'query_genome': query_genome,
            'chromosome': chromosome,
            'sv_type': sv_type,
            'sv_list': [],
            'sv_summary': {},
            'count': 0
        }
        
        return Response(results, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in structural_variations: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== 辅助函数 ====================
def get_genome_list():
    """获取所有可用的基因组列表"""
    species_list = Species_info.objects.all().values('name', 'alias', 'Category', 'Genome_type')
    return list(species_list)
