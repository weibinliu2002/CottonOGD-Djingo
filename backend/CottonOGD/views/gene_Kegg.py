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
from matplotlib.gridspec import GridSpec
import pandas as pd
from textwrap import wrap
import math

logger = logging.getLogger(__name__)

@api_view(['GET'])
def kegg_annotation(request):
    """
    KEGG注释API - 根据基因ID获取KEGG注释信息
    """
    if request.method == 'GET':
        gene_input = request.GET.get('gene_id', '').strip()
        
        if not gene_input:
            return JsonResponse({
                'status': 'error',
                'error': 'Missing gene_id parameter'
            })
        
        gene_list = [gene.strip() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        results = []
        chart_data = None
        
        if gene_list:
            try:
                with connection.cursor() as cursor:
                    for gene_id in gene_list:
                        cursor.execute("""
                            SELECT seqid, start, end ,geneid_id
                            FROM `GeneAssembly` 
                            WHERE genome_id = "G.kirkii_ISU_ISU_v3.0" and type = 'gene' AND geneid_id = %s
                        """, [gene_id])
                        annotation_data = cursor.fetchall()

                        cursor.execute("""
                            SELECT `geneid`, `kegg_id`, `kegg_description`
                            FROM `GeneKegg` 
                            WHERE `geneid` = %s
                        """, [gene_id])
                        kegg_data = cursor.fetchall()

                        for anno_row in annotation_data:
                            for ke_row in kegg_data:
                                results.append({
                                    'Chr': anno_row[0],
                                    'Start': anno_row[1],
                                    'End': anno_row[2],
                                    'ID': anno_row[3],
                                    'match': ke_row[1],
                                    'Description': ke_row[2],
                                })
                
                match_counts = defaultdict(int)
                for result in results:
                    match_value = result['match']
                    if match_value:
                        match_counts[match_value] += 1
                
                chart_data = {
                    'labels': list(match_counts.keys()),
                    'data': list(match_counts.values()),
                }
                
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'results': results,
                        'gene_list': gene_list,
                        'searched_ids': gene_input,
                        'chart_data': chart_data,
                    }
                })
            except Exception as e:
                logger.error(f"KEGG annotation error: {str(e)}")
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
                    'chart_data': {
                        'labels': [],
                        'data': []
                    }
                }
            })
    
    return JsonResponse({
        'status': 'error',
        'error': 'Method not allowed'
    })

@api_view(['GET'])
def kegg_enrichment(request):
    """
    KEGG富集分析API
    """
    if request.method == 'GET':
        gene_input = request.GET.get('gene_id', '').strip()
        p_value_threshold = float(request.GET.get('p_value_threshold', 0.05))
        
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
                cursor.execute(
                    "SELECT DISTINCT `kegg_id`, `kegg_description` FROM GeneKegg "
                    "WHERE `kegg_id` IS NOT NULL AND `kegg_id` != '-' and kegg_type = 'pathway'")
                pathways = {}
                for pathway_id, description in cursor:
                    for pathway in pathway_id.split(','):
                        pathway = pathway.strip()
                        if pathway:
                            pathways[pathway] = description
                
                cursor.execute(
                    "SELECT COUNT(*) FROM gene_kegg"
                )
                total_background_genes = cursor.fetchone()[0]
                
                cursor.execute(
                    "SELECT `geneid`, `kegg_id`, `kegg_description` FROM GeneKegg "
                    "WHERE `geneid` IN %s AND `kegg_id` IS NOT NULL AND `kegg_id` != '-'",
                    [tuple(gene_list)])
                input_genes_kegg = cursor.fetchall()
                
                cursor.execute(
                    "SELECT `kegg_id`, `kegg_description` FROM GeneKegg "
                    "WHERE `kegg_id` IS NOT NULL AND `kegg_id` != '-'")
                background_counts = defaultdict(int)
                background_descriptions = {}
                
                for pathway_id, description in cursor:
                    for pathway in pathway_id.split(','):
                        pathway = pathway.strip()
                        if pathway:
                            background_counts[pathway] += 1
                            if pathway not in background_descriptions:
                                background_descriptions[pathway] = description
            
            input_pathways = defaultdict(list)
            input_genes = set()
            
            for gene, pathway_id, _ in input_genes_kegg:
                input_genes.add(gene)
                for pathway in pathway_id.split(','):
                    pathway = pathway.strip()
                    if pathway:
                        input_pathways[pathway].append(gene)
            
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
            
            enrichment_results = []
            for pathway, genes in input_pathways.items():
                a = len(genes)
                b = total_input_genes - a
                c = background_counts.get(pathway, 0)
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
                        'pathway_id': pathway,
                        'description': {
                            'name': background_descriptions.get(pathway, 'No description available'),
                            'definition': ''
                        },
                        'gene_ratio': f"{a}/{total_input_genes}",
                        'bg_ratio': f"{c}/{total_background_genes}",
                        'rich_factor': a / c if c > 0 else 0,
                        'fold_enrichment': fold_enrichment,
                        'z_score': z_score,
                        'p_value': p_value,
                        'genes': genes
                    })
                except Exception as e:
                    logger.error(f"Error calculating enrichment for pathway {pathway}: {str(e)}")
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
            
            plot_image = None
            if filtered_results:
                plot_image = plot_kegg_enrichment(filtered_results)
            
            return JsonResponse({
                'status': 'success',
                'data': {
                    'results': filtered_results,
                    'input_gene_count': total_input_genes,
                    'background_gene_count': total_background_genes,
                    'plot_image': plot_image
                }
            })
        except Exception as e:
            logger.error(f"KEGG enrichment error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'error': 'Method not allowed'
    })

def plot_kegg_enrichment(kegg_results, max_terms=30, figsize=(15, 7)):
    """
    Create combined barplot and dotplot for KEGG enrichment results
    
    Parameters:
    - kegg_results: List of dicts with KEGG enrichment results
    - max_terms: int, maximum number of terms to display
    - figsize: tuple, size of the figure
    """
    
    if not kegg_results:
        return None

    df = pd.DataFrame(kegg_results)

    df['Count'] = df['gene_ratio'].apply(lambda x: int(x.split('/')[0]))
    df['GeneRatio'] = df['gene_ratio'].apply(lambda x: eval(x.replace('/', '/')))

    df = df.sort_values('p_value').head(max_terms)

    fig = plt.figure(figsize=figsize)
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1, 1.5])

    ax1 = fig.add_subplot(gs[0])
    colors = plt.cm.Reds_r(df['p_value'] / df['p_value'].max())
    bars = ax1.barh(
        y=df['description'].apply(lambda x: x['name']),
        width=df['Count'],
        color=colors
    )

    ax1.set_title('KEGG Pathway - Count', pad=20, fontsize=14, fontweight='bold')
    ax1.set_xlabel('Gene Count', fontsize=12)
    ax1.set_ylabel('')
    ax1.grid(axis='x', linestyle='--', alpha=0.7)

    y_labels = ['\n'.join(wrap(label, 40)) for label in df['description'].apply(lambda x: x['name'])]
    ax1.set_yticks(range(len(y_labels)))
    ax1.set_yticklabels(y_labels, fontsize=10)

    ax2 = fig.add_subplot(gs[1])

    sizes = (df['Count'] / df['Count'].max() * 200 + 50)
    colors = -np.log10(df['p_value'])
    
    scatter = ax2.scatter(
        x=df['GeneRatio'],
        y=df['description'].apply(lambda x: x['name']),
        s=sizes,
        c=colors,
        cmap='Reds_r'
    )

    ax2.set_title('KEGG Pathway - Dotplot', pad=20, fontsize=14, fontweight='bold')
    ax2.set_xlabel('Gene Ratio', fontsize=12)
    ax2.set_ylabel('')
    ax2.grid(axis='x', linestyle='--', alpha=0.7)

    ax2.set_yticks(range(len(y_labels)))
    ax2.set_yticklabels(y_labels, fontsize=10)

    cbar = plt.colorbar(scatter, ax=ax2, pad=0.01)
    cbar.set_label('-log10(p-value)', fontsize=10)

    plt.tight_layout()
    plt.subplots_adjust(wspace=0.3)

    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)

    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()
    
    return image_base64
