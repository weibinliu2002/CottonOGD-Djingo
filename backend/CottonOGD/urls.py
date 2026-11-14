from django.urls import path, re_path
from django.views.static import serve as static_serve
from django.conf import settings
#from CottonOGD.views.jbrowes_file import *
from CottonOGD.views.base import *
from CottonOGD.views.base_info import *
from CottonOGD.views.location_ID import *
from CottonOGD.views.gene_id_result import *
from CottonOGD.views.extract_seq import *
from CottonOGD.views.gene_expression import *
from CottonOGD.views.extract_seq_from_gff import *
from CottonOGD.views.primer_design import *
from CottonOGD.views.blast import *
from CottonOGD.views.expression_EFP import *
from CottonOGD.views.DownloadGenome import download_genome_file
from CottonOGD.views.gene_Go import go_annotation, go_enrichment
from CottonOGD.views.gene_Kegg import kegg_annotation, kegg_enrichment
from CottonOGD.views.Meilisearch import (
    search_genes_meilisearch, search_genes, proxy_search, get_search_indexes,
)
from CottonOGD.views.genome_api import *
from CottonOGD.views.protein3D import *
from CottonOGD.views.ai_chat import ai_chat
from CottonOGD.views.orthofinder import (
    ortholog_gene, orthogroup_detail, orthogroups_by_species,
    orthofinder_meta, orthofinder_sequence, orthofinder_tree,
    orthofinder_msa, orthofinder_tandem,
)
from CottonOGD.views.ppi_string import ppi_string_network
from CottonOGD.views.variant_api import (
    syri_pairs, syri_structural, syri_sequence,
    variant_sets, variant_region, variant_by_id, variant_density, variant_genotype,
    gwas_traits, gwas_accessions, gwas_phenotype, gwas_markers, gwas_associations,
)


urlpatterns = [
    #path('Browse/', include(('apps.Browse.urls', 'Browse'), namespace='browse')),
    #path('large/<str:genome_name>/<str:filename>', serve_large_file, name='serve_large_file'),
    path('login/', login, name='login'),
    path('logout/', logout, name="logout"),
    path('get_species_info/', get_species_info, name='species_info'),
    path('get_family_info/', get_family_info, name='family_info'),
    path('Id_map/', Id_map, name='Id_map'),
    path('geneid_result/', geneid_result, name='geneid_result'),
    path('geneid_summary/', geneid_summary, name='geneid_summary'),
    path('extract_seq/', extract_seq, name='extract_seq'),
    path('extract_seq_gff/', extract_seq_gff, name='extract_seq_gff'),
    path('extract_expression/', extract_expression, name='extract_expression'),
    path('regenerate_heatmap/', regenerate_heatmap, name='regenerate_heatmap'),
    path('extract_expression/tissues/', get_tissues, name='get_tissues'),
    path('extract_expression/genomes/', get_genomes_with_tissue, name='get_genomes_with_tissue'),
    path('search_genes/', search_genes, name='search_genes'),
    path('search_genes_meilisearch/', search_genes_meilisearch, name='search_genes_meilisearch'),
    # 统一检索代理（前端零密钥，Meilisearch 请求全部经后端透传）
    path('search/', proxy_search, name='search_proxy'),
    # 可用索引列表（前端首页渲染「选择库」下拉）
    path('get_search_indexes/', get_search_indexes, name='get_search_indexes'),

    # ========== AI Chat（对话式人工智能，第一版：3 个工具，见 server/ai_tools.py） ==========
    path('ai/chat/', ai_chat, name='ai_chat'),
    path('primer_design/', primer_design, name='primer_design'),
    path('blast_cmd/', blast_cmd, name='blast_cmd'),
    path('expression_EFP_image/', expression_EFP_image, name='expression_EFP_image'),
    path('download_genome/<str:genome_id>/<str:file_type>', download_genome_file, name='download_genome_file'),
    path('go_annotation/', go_annotation, name='go_annotation'),
    path('go_enrichment/', go_enrichment, name='go_enrichment'),
    path('kegg_annotation/', kegg_annotation, name='kegg_annotation'),
    path('kegg_enrichment/', kegg_enrichment, name='kegg_enrichment'),
    
    # ========== 基因组API端点（对应Shiny应用功能） ==========
    #path('search_by_gene_ids/', search_by_gene_ids, name='search_by_gene_ids'),
    path('search_by_genome_location/', search_by_genome_location, name='search_by_genome_location'),
    path('gene_genomic_distribution/', gene_genomic_distribution, name='gene_genomic_distribution'),
    #path('transcription_factors/', transcription_factors, name='transcription_factors'),
    path('genome_synteny/', genome_synteny, name='genome_synteny'),
    #path('structural_variations/', structural_variations, name='structural_variations'),

    # ========== 变异数据 API（SyRI / 群体 SNP·InDel / GWAS） ==========
    # A 域：SyRI 成对结构变异
    path('syri/pairs/', syri_pairs, name='syri_pairs'),
    path('syri/structural/', syri_structural, name='syri_structural'),
    path('syri/sequence/', syri_sequence, name='syri_sequence'),
    # B 域：群体 SNP/InDel 位点
    path('variant/sets/', variant_sets, name='variant_sets'),
    path('variant/region/', variant_region, name='variant_region'),
    path('variant/id/', variant_by_id, name='variant_by_id'),
    path('variant/density/', variant_density, name='variant_density'),
    path('variant/genotype/', variant_genotype, name='variant_genotype'),
    # C 域：GWAS
    path('gwas/traits/', gwas_traits, name='gwas_traits'),
    path('gwas/accessions/', gwas_accessions, name='gwas_accessions'),
    path('gwas/phenotype/', gwas_phenotype, name='gwas_phenotype'),
    path('gwas/markers/', gwas_markers, name='gwas_markers'),
    path('gwas/associations/', gwas_associations, name='gwas_associations'),
    
    # ========== OrthoFinder 直系同源（Ortholog） ==========
    path('orthofinder/ortholog_gene/', ortholog_gene, name='ortholog_gene'),
    path('orthofinder/orthogroup_detail/', orthogroup_detail, name='orthogroup_detail'),
    path('orthofinder/orthogroups_by_species/', orthogroups_by_species, name='orthogroups_by_species'),
    path('orthofinder/meta/', orthofinder_meta, name='orthofinder_meta'),
    path('orthofinder/sequence/<str:og_code>', orthofinder_sequence, name='orthofinder_sequence'),
    path('orthofinder/tree/<str:og_code>', orthofinder_tree, name='orthofinder_tree'),
    path('orthofinder/msa/<str:og_code>', orthofinder_msa, name='orthofinder_msa'),
    path('orthofinder/tandem/<str:og_code>', orthofinder_tandem, name='orthofinder_tandem'),

    # ========== PPI STRING 蛋白质互作网络 ==========
    path('ppi/string/', ppi_string_network, name='ppi_string_network'),

    # ========== TF/TR 系统发生树静态文件转发（前端 Phylotree.js 直接 fetch，无 API 逻辑） ==========
    # 路径示例：
    #   /CottonOGD_api/tf_tree/tree/genome/<genome_pro_name>/TF/<tf_name>.treefile
    #   /CottonOGD_api/tf_tree/tree/genome/<genome_pro_name>/TR/<tr_name>.treefile
    # 直接返回 Newick 文本（Content-Type: text/plain），Django 不做任何业务处理。
    re_path(
        r'^tf_tree/(?P<path>tree/genome/[^/]+/(?:TF|TR)/[^/]+\.treefile)$',
        static_serve,
        kwargs={'document_root': str(settings.BASE_DIR / 'data' / 'tf_phylogeny')},
        name='tf_tree_file',
    ),

]
