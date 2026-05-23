from django.db import connection
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from django.views.decorators.http import require_http_methods
import json
import logging
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

logger = logging.getLogger(__name__)


@api_view(['GET'])
def go_annotation(request):
    """
    GO注释API - 根据基因ID获取GO注释信息
    """
    if request.method == 'GET':
        gene_input = request.GET.get('gene_id', '').strip()
        genome_id = request.GET.get('genome_id', 'G.kirkii_ISU_ISU_v3.0')
        
        if not gene_input:
            return JsonResponse({
                'status': 'error',
                'error': 'Missing gene_id parameter'
            })
        
        gene_list = [gene.strip() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        results = []
        chart = None
        chart_data = None
        categories = []
        
        if gene_list:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT seqid, start, end, geneid_id 
                        FROM `GeneAssembly` 
                        WHERE genome_id = %s and type = 'gene' AND geneid_id IN %s 
                    """, [genome_id, tuple(gene_list)])
                    annotation_data = cursor.fetchall()

                    cursor.execute("""
                        SELECT go_type, go_description, go_id, geneid, go_type
                        FROM `GeneGo` 
                        WHERE genome_id = %s and geneid IN %s
                    """, [genome_id, tuple(gene_list)])
                    enrichment_data = cursor.fetchall()
                    logger.info(f"GO annotation - 数据库样本数据: {len(annotation_data)}")
                    logger.info(f"GO annotation - 查询到 {len(enrichment_data)} 条GO数据，基因列表: {gene_list}")
              

                    enrichment_dict = {}
                    for row in enrichment_data:
                        gene_id = row[3]
                        if gene_id not in enrichment_dict:
                            enrichment_dict[gene_id] = []
                        enrichment_dict[gene_id].append(row)

                    for anno_row in annotation_data:
                        gene_id = anno_row[3]
                        if gene_id in enrichment_dict:
                            for enrich_row in enrichment_dict[gene_id]:
                                results.append({
                                    'Chr': anno_row[0],
                                    'Start': anno_row[1],
                                    'End': anno_row[2],
                                    'ID': anno_row[3],
                                    'GO_ID': enrich_row[2],
                                    'Description': enrich_row[1],
                                    'Gene_Ontology': enrich_row[0],
                                    'dddd': enrich_row[4]
                                })
                    
                    chart_data = {'BP': {}, 'MF': {}, 'CC': {}}

                    for result in results:
                        go_type = result['Gene_Ontology']
                        dddd_value = result['dddd']
                        if go_type in chart_data:
                            if dddd_value in chart_data[go_type]:
                                chart_data[go_type][dddd_value] += 1
                            else:
                                chart_data[go_type][dddd_value] = 1

                    categories = sorted({result['dddd'] for result in results if result['dddd']})
                    data = {
                        'BP': [chart_data['BP'].get(cat, 0) for cat in categories],
                        'MF': [chart_data['MF'].get(cat, 0) for cat in categories],
                        'CC': [chart_data['CC'].get(cat, 0) for cat in categories]
                    }

                    if categories and any(data.values()):
                        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
                        axes = [ax1, ax2, ax3]
                        
                        max_value = max(max(data['BP']), max(data['MF']), max(data['CC'])) * 1.1
                        for ax in axes:
                            ax.set_ylim(0, max_value)
                            ax.grid(False) 

                        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
                        
                        for i, (ax, (group, values), color) in enumerate(zip(axes, data.items(), colors)):
                            bars = ax.bar(categories, values, color=color)
                            ax.set_title(group, fontsize=14, pad=15)
                            ax.set_xlabel('', fontsize=12)

                            ax.spines['top'].set_visible(False)
                            ax.spines['right'].set_visible(False)

                            if i > 0: 
                                ax.spines['left'].set_visible(False)
                                ax.tick_params(left=False)
                            
                            for bar in bars:
                                height = bar.get_height()
                                if height > 0:
                                    ax.text(bar.get_x() + bar.get_width()/2., height,
                                            f'{int(height)}',
                                            ha='center', va='bottom', fontsize=10)
                        
                        ax1.set_ylabel('Count', fontsize=12)
                        
                        plt.tight_layout()

                        buffer = BytesIO()
                        plt.savefig(buffer, format='png', bbox_inches='tight')
                        plt.close()
                        chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'results': results,
                        'gene_list': gene_list,
                        'searched_ids': gene_input,
                        'chart': chart,
                        'chart_data': {
                            'data': data,
                            'categories': categories
                        }
                    }
                })
            except Exception as e:
                logger.error(f"GO annotation error: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'error': str(e)
                })
        else:
            return JsonResponse({
                'status': 'success',
                'data': {
                    'results': [],
                    'gene_list': [],
                    'searched_ids': gene_input,
                    'chart': None,
                    'chart_data': {
                        'data': {},
                        'categories': []
                    }
                }
            })
    
    return JsonResponse({
        'status': 'error',
        'error': 'Method not allowed'
    })


@api_view(['POST'])
def go_enrichment(request):
    """
    GO富集分析API - 使用gseapy进行富集分析
    """
    if request.method == 'POST':
        gene_input = request.POST.get('gene_id', '').strip()
        genome_id = request.POST.get('genome_id', 'G.kirkii_ISU_ISU_v3.0')
        p_value_threshold = float(request.POST.get('p_value_threshold', 0.05))
        
        if not gene_input:
            return JsonResponse({
                'status': 'error',
                'error': 'Missing gene_id parameter'
            })
        
        gene_list = [gene.strip() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        if not gene_list:
            return JsonResponse({
                'status': 'error',
                'error': 'Empty gene list'
            })
        
        try:
            with connection.cursor() as cursor:
                logger.info(f"GO富集分析 - 输入基因列表: {gene_list}")
                
                cursor.execute("""
                    SELECT go_type, go_description, go_id, geneid, go_type
                    FROM `GeneGo` 
                    WHERE genome_id = %s AND geneid IN %s
                """, [genome_id, tuple(gene_list)])
                enrichment_data = cursor.fetchall()
                
                logger.info(f"GO富集分析 - 查询到 {len(enrichment_data)} 条富集数据")

                cursor.execute("""
                    SELECT COUNT(*) FROM `GeneGo` WHERE genome_id = %s
                """, [genome_id])
                total_background_genes = cursor.fetchone()[0]
                
                logger.info(f"GO富集分析 - 背景基因总数: {total_background_genes}")

                cursor.execute("""
                    SELECT `go_type`, `go_description`, `go_id`, `geneid`, `go_type`
                    FROM `GeneGo` 
                    WHERE genome_id = %s AND `go_type` IS NOT NULL 
                    AND `go_id` IS NOT NULL
                """, [genome_id])
                background_data = cursor.fetchall()
                
                logger.info(f"GO富集分析 - 背景数据条数: {len(background_data)}")

            def normalize_go_type(go_type):
                if not go_type:
                    return 'Unknown'
                go_type_upper = str(go_type).upper().strip()
                if go_type_upper in ['BP', 'BIOLOGICAL_PROCESS', 'BIOLOGICAL PROCESS']:
                    return 'BP'
                elif go_type_upper in ['MF', 'MOLECULAR_FUNCTION', 'MOLECULAR FUNCTION']:
                    return 'MF'
                elif go_type_upper in ['CC', 'CELLULAR_COMPONENT', 'CELLULAR COMPONENT']:
                    return 'CC'
                return go_type_upper
            
            input_go_terms = defaultdict(list)
            input_genes = set()
            
            for row in enrichment_data:
                gene = row[3]
                go_type_raw = row[0]
                go_id_str = row[2]
                description = row[1]
                
                go_type = normalize_go_type(go_type_raw)
                
                for go_id in go_id_str.split(','):
                    go_id = go_id.strip()
                    if go_id and go_id != '-':
                        input_genes.add(gene)
                        input_go_terms[go_id].append({
                            'gene': gene,
                            'go_type': go_type,
                            'description': description
                        })
            
            logger.info(f"GO富集分析 - 输入GO术语数: {len(input_go_terms)}")
            logger.info(f"GO富集分析 - 输入基因数: {len(input_genes)}")
            
            total_input_genes = len(input_genes)
            if total_input_genes == 0:
                logger.warning("GO富集分析 - 没有找到输入基因的富集数据")
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'results': [],
                        'input_gene_count': 0,
                        'background_gene_count': total_background_genes
                    }
                })
            
            background_counts = defaultdict(int)
            background_categories = {}
            background_descriptions = {}
            
            for row in background_data:
                go_type_raw = row[0]
                go_id_str = row[2]
                description = row[1]
                
                go_type = normalize_go_type(go_type_raw)
                
                for go_id in go_id_str.split(','):
                    go_id = go_id.strip()
                    if go_id and go_id != '-':
                        background_counts[go_id] += 1
                        if go_id not in background_categories:
                            background_categories[go_id] = go_type
                        if go_id not in background_descriptions:
                            background_descriptions[go_id] = description
            
            logger.info(f"GO富集分析 - 背景GO术语数: {len(background_counts)}")

            try:
                import gseapy as gp
                
                logger.info("使用gseapy进行GO富集分析...")

                go_gene_sets = defaultdict(set)
                for row in background_data:
                    go_id_str = row[2]
                    gene = row[3]
                    for go_id in go_id_str.split(','):
                        go_id = go_id.strip()
                        if go_id and go_id != '-':
                            go_gene_sets[go_id].add(gene)

                if not go_gene_sets or not input_genes:
                    logger.warning("没有有效的GO基因集数据")
                    return JsonResponse({
                        'status': 'success',
                        'data': {
                            'results': [],
                            'input_gene_count': total_input_genes,
                            'background_gene_count': total_background_genes,
                            'method': 'Python_gseapy'
                        }
                    })

                enr = gp.enrich(
                    gene_list=sorted(list(input_genes)),
                    gene_sets={k: sorted(list(v)) for k, v in go_gene_sets.items() if v},
                    background=sorted(set([row[3] for row in background_data])),
                    no_plot=True,
                    outdir=None
                )

                if enr is None or not hasattr(enr, "results") or enr.results.empty:
                    logger.warning("gseapy没有返回富集结果")
                    return JsonResponse({
                        'status': 'success',
                        'data': {
                            'results': [],
                            'input_gene_count': total_input_genes,
                            'background_gene_count': total_background_genes,
                            'method': 'Python_gseapy'
                        }
                    })

                enrichment_results = []
                for _, row in enr.results.iterrows():
                    go_id = row.get('Term', '')
                    go_type = background_categories.get(go_id, 'Unknown')
                    
                    overlap_str = str(row.get('Overlap', '0/0'))
                    match = overlap_str.split('/')
                    gene_count = int(match[0]) if match and match[0].isdigit() else 0

                    enrichment_results.append({
                        'go_id': go_id,
                        'description': {
                            'name': background_descriptions.get(go_id, 'No description available'),
                            'definition': ''
                        },
                        'gene_ratio': overlap_str,
                        'bg_ratio': '',
                        'rich_factor': row.get('Odds Ratio', 0),
                        'fold_enrichment': row.get('Odds Ratio', 0),
                        'z_score': 0,
                        'p_value': row.get('P-value', 1),
                        'corrected_p_value': row.get('Adjusted P-value', row.get('P-value', 1)),
                        'gene_count': gene_count,
                        'genes': str(row.get('Genes', '')).split(';') if row.get('Genes', '') else [],
                        'go_type': go_type
                    })

                enrichment_results.sort(key=lambda x: x['p_value'])
                filtered_results = [r for r in enrichment_results if r.get('p_value', 1.0) <= p_value_threshold]

                logger.info(f"gseapy GO富集分析结果: {len(filtered_results)} 条显著富集项")

                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'results': filtered_results,
                        'input_gene_count': total_input_genes,
                        'background_gene_count': total_background_genes,
                        'method': 'Python_gseapy'
                    }
                })

            except ImportError as e:
                logger.error(f"gseapy未安装: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'error': 'gseapy is not installed'
                })
            except Exception as e:
                logger.error(f"gseapy GO富集分析失败: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'error': str(e)
                })
        
        except Exception as e:
            logger.error(f"GO enrichment error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'error': 'Method not allowed'
    })
