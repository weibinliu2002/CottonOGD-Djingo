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
from scipy.stats import fisher_exact
from statsmodels.stats.multitest import multipletests
import math

logger = logging.getLogger(__name__)

@api_view(['GET'])
def go_annotation(request):
    """
    GO注释API - 根据基因ID获取GO注释信息
    """
    if request.method == 'GET':
        gene_input = request.GET.get('gene_id', '').strip()
        
        if not gene_input:
            return JsonResponse({
                'status': 'error',
                'error': 'Missing gene_id parameter'
            })
        
        gene_list = [gene.strip().upper() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        results = []
        chart = None
        chart_data = None
        categories = []
        
        if gene_list:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT Chr, Start, End, ID 
                        FROM `eg_go_annotation` 
                        WHERE ID IN %s
                    """, [tuple(gene_list)])
                    annotation_data = cursor.fetchall()

                    cursor.execute("""
                        SELECT `Gene_Ontology`, Description, `GO_ID`, Query, dddd
                        FROM `eg_go_enrichment` 
                        WHERE Query IN %s
                    """, [tuple(gene_list)])
                    enrichment_data = cursor.fetchall()

                    for anno_row in annotation_data:
                        for enrich_row in enrichment_data:
                            if anno_row[3] == enrich_row[3]:
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
@api_view(['GET'])
def go_enrichment(request):
    """
    GO富集分析API
    """
    if request.method == 'GET':
        gene_input = request.GET.get('gene_id', '').strip()
        p_value_threshold = float(request.GET.get('p_value_threshold', 0.05))
        
        if not gene_input:
            return JsonResponse({
                'status': 'error',
                'error': 'Missing gene_id parameter'
            })
        
        gene_list = [gene.strip().upper() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        if not gene_list:
            return JsonResponse({
                'status': 'error',
                'error': 'Empty gene list'
            })
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT `Gene_Ontology`, Description, `GO_ID`, Query, dddd
                    FROM `eg_go_enrichment` 
                    WHERE Query IN %s
                """, [tuple(gene_list)])
                enrichment_data = cursor.fetchall()

                cursor.execute("SELECT COUNT(*) FROM `eg_go_enrichment`")
                total_background_genes = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT `Gene_Ontology`, Description, `GO_ID`, Query, dddd
                    FROM `eg_go_enrichment` 
                    WHERE `Gene_Ontology` IS NOT NULL 
                    AND `GO_ID` IS NOT NULL
                """)
                background_data = cursor.fetchall()

            input_genes = set(gene_list)
            input_pathways = defaultdict(list)
            
            for row in enrichment_data:
                gene = row[3]
                go_type = row[0]
                go_id = row[2]
                description = row[1]
                dddd = row[4]
                
                if gene in input_genes:
                    input_pathways[go_id].append({
                        'gene': gene,
                        'go_type': go_type,
                        'description': description,
                        'dddd': dddd
                    })
            
            total_input_genes = len(input_genes)
            if total_input_genes == 0:
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'results': [],
                        'input_gene_count': 0,
                        'background_gene_count': total_background_genes
                    }
                })
            
            background_counts = defaultdict(int)
            background_descriptions = {}
            
            for row in background_data:
                go_id = row[2]
                description = row[1]
                background_counts[go_id] += 1
                if go_id not in background_descriptions:
                    background_descriptions[go_id] = description
            
            enrichment_results = []
            for go_id, genes in input_pathways.items():
                a = len(genes)
                b = total_input_genes - a
                c = background_counts.get(go_id, 0)
                d = total_background_genes - c
                
                if c == 0:
                    continue
                
                try:
                    _, p_value = fisher_exact([[a, b], [c, d]], alternative='greater')
                    
                    expected = (a + b) * (a + c) / (a + b + c + d)
                    variance = expected * (1 - (a + b)/(a + b + c + d)) * (1 - (a + c)/(a + b + c + d))
                    z_score = (a - expected) / math.sqrt(variance) if variance > 0 else 0
                    fold_enrichment = (a / (a + b)) / (c / (c + d)) if (c + d) > 0 else 0
                    
                    enrichment_results.append({
                        'go_id': go_id,
                        'description': background_descriptions.get(go_id, 'No description'),
                        'gene_ratio': f"{a}/{total_input_genes}",
                        'bg_ratio': f"{c}/{total_background_genes}",
                        'rich_factor': a / c if c > 0 else 0,
                        'fold_enrichment': fold_enrichment,
                        'z_score': z_score,
                        'p_value': p_value,
                        'genes': [g['gene'] for g in genes],
                        'go_type': genes[0]['go_type']
                    })
                except Exception as e:
                    logger.error(f"Error calculating enrichment for GO ID {go_id}: {str(e)}")
                    continue
            
            if enrichment_results:
                p_values = [r['p_value'] for r in enrichment_results]
                try:
                    _, corrected_p_values, _, _ = multipletests(p_values, method='fdr_bh')
                    for i, p in enumerate(corrected_p_values):
                        enrichment_results[i]['corrected_p_value'] = p
                except Exception as e:
                    logger.error(f"Error in multiple testing correction: {str(e)}")
                    for r in enrichment_results:
                        r['corrected_p_value'] = r['p_value']
                
                enrichment_results.sort(key=lambda x: x['p_value'])
            
            filtered_results = [r for r in enrichment_results if r.get('p_value', 1.0) <= p_value_threshold]
            
            return JsonResponse({
                'status': 'success',
                'data': {
                    'results': filtered_results,
                    'input_gene_count': total_input_genes,
                    'background_gene_count': total_background_genes
                }
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
