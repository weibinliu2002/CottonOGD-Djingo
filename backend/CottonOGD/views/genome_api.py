from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.models import Species_info, Family, GeneMaster, gene_info,Genome_Synteny, gene_seq, gene_annotation, gene_go, gene_kegg, gene_expression
from CottonOGD.views.location_ID import clean_gene_id
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
    '''
    if not uuid or uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    '''
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
            end__gte=start,
            type='gene',
        ).values('geneid_id', 'seqid','start', 'end', 'strand', 'type','id_id')
        
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
    '''
    uuid = request.headers.get('uuid')
    if not uuid or uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    '''
    genome_name = request.data.get('genome', '')
    gene_ids_input = request.data.get('gene_ids', '')
    
    if not genome_name:
        return Response({'error': 'genome is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 解析基因ID列表
    gene_ids = []
    if gene_ids_input:
        # 清理基因ID列表中的空格和换行符
        
        # 解析基因ID列表
        gene_ids = [clean_gene_id(g) for g in re.split(r'[\n|,|;]+', gene_ids_input) if g.strip()]
    logger.info(f"gene_genomic_distribution: gene_ids: {gene_ids}")
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
    '''
    uuid = request.headers.get('uuid')
    if not uuid or uuid not in UuidManager.uuid_storage:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    '''
    ref_genome = request.data.get('reference_genome', '')
    query_genome = request.data.get('query_genome', '')
    chromosome = request.data.get('chromosome', '')
    Variation_type = request.data.get('Variation_type', '')
    
    if not ref_genome or not query_genome or not chromosome or not Variation_type:
        return Response({'error': 'reference_genome, query_genome, chromosome, and Variation_type are required'}, status=status.HTTP_400_BAD_REQUEST)
    ref_genome_id = Species_info.objects.get(name=ref_genome).id
    query_genome_id = Species_info.objects.get(name=query_genome).id
    logger.info(f"genome_synteny: ref_genome_id: {ref_genome_id}, query_genome_id: {query_genome_id}, chromosome: {chromosome}, Variation_type: {Variation_type}")
    try:
        # 获取参考基因组的基因信息
        ref_genes = Genome_Synteny.objects.filter(
            Ref_genome=ref_genome_id,
            Query_genome=query_genome_id,
            Ref_genome_chr=chromosome,
            son_type=Variation_type,
        ).values()
        logger.info(f"genome_synteny: ref_genes count: {ref_genes.count()}")
        ref_genes_list = list(ref_genes)
        results = {
            'reference_genome': ref_genome,
            'query_genome': query_genome,
            'chromosome': chromosome,
            'reference_genes': ref_genes_list,
            'ref_gene_count': len(ref_genes_list),
        }
        
        return Response(results, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in genome_synteny: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

