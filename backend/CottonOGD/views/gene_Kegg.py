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
from matplotlib.gridspec import GridSpec
import pandas as pd
from textwrap import wrap

from CottonOGD.models import GeneMaster

logger = logging.getLogger(__name__)


@api_view(['GET'])
def kegg_annotation(request):
    """
    KEGG注释API - 根据基因ID获取KEGG注释信息
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

        logger.info(f"KEGG注释 - gene_input: {gene_input}, genome_id: {genome_id}")

        if not gene_list:
            return JsonResponse({
                'status': 'success',
                'data': {
                    'results': [],
                    'gene_list': [],
                    'searched_ids': gene_input,
                    'chart': None,
                    'chart_data': None
                }
            })

        gene_masters = GeneMaster.objects.filter(genome_id=genome_id, geneid__in=gene_list)
        gene_id_map = {gm.geneid: gm.id for gm in gene_masters}
        gene_id_list = list(gene_id_map.values())

        results = []
        chart_data_raw = defaultdict(lambda: defaultdict(int))

        if gene_id_list:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            gi.seqid,
                            gi.start,
                            gi.end,
                            gi.id_id,
                            gi.geneid_id,
                            gk.kegg_id,
                            mp.name AS pathway_name,
                            mp.full_name AS pathway_full_name,
                            mp.category_id
                        FROM gene_assembly gi
                        LEFT JOIN gene_kegg gk ON gi.id_id = gk.id_id
                        LEFT JOIN metabolic_pathway mp ON gk.kegg_id = mp.ko_id
                        WHERE gi.type = 'gene'
                          AND gi.id_id IN %s
                    """, [tuple(gene_id_list)])

                    annotation_data = cursor.fetchall()
                    logger.info(f"KEGG annotation - 查询到 {len(annotation_data)} 条数据")

                    result_dict = defaultdict(list)
                    for row in annotation_data:
                        seqid, start, end, id_id, geneid_id, kegg_id, pathway_name, pathway_full_name, category_id = row
                        result_dict[id_id].append({
                            'seqid': seqid,
                            'start': start,
                            'end': end,
                            'geneid_id': geneid_id,
                            'kegg_id': kegg_id,
                            'pathway_name': pathway_name if pathway_name else '',
                            'pathway_full_name': pathway_full_name if pathway_full_name else '',
                            'category_id': category_id if category_id else ''
                        })

                    for id_id, items in result_dict.items():
                        for item in items:
                            if item['kegg_id']:
                                results.append({
                                    'Chr': item['seqid'],
                                    'Start': item['start'],
                                    'End': item['end'],
                                    'ID': item['geneid_id'],
                                    'KEGG_ID': item['kegg_id'],
                                    'Description': item['pathway_name'],
                                    'Type': '',
                                    'Pathway': item['pathway_name'],
                                    'Pathway_Full': item['pathway_full_name'],
                                    'Category_ID': item['category_id']
                                })

                                chart_data_raw['Pathway'][item['pathway_name']] += 1

                    categories = sorted({r['Description'] for r in results if r['Description']})
                    chart_data = {}

                    for kegg_type, desc_counts in chart_data_raw.items():
                        chart_data[kegg_type] = {
                            'labels': list(desc_counts.keys()),
                            'values': list(desc_counts.values())
                        }

                    logger.info(f"图表分类: {categories}")
                    logger.info(f"图表数据: {chart_data}")

                    chart = None
                    if categories and chart_data:
                        all_labels = []
                        all_values = []
                        all_types = []

                        for kegg_type, data in chart_data.items():
                            for label, value in zip(data['labels'], data['values']):
                                all_labels.append(label)
                                all_values.append(value)
                                all_types.append(kegg_type)

                        if all_labels:
                            fig, ax = plt.subplots(figsize=(12, 6))

                            types = list(set(all_types))
                            colors = plt.cm.Set3(np.linspace(0, 1, len(types)))
                            type_color_map = dict(zip(types, colors))

                            x_positions = range(len(all_labels))
                            bars = ax.bar(x_positions, all_values,
                                         color=[type_color_map[t] for t in all_types])

                            ax.set_xlabel('KEGG Description', fontsize=12)
                            ax.set_ylabel('Count', fontsize=12)
                            ax.set_title('KEGG Annotation Distribution', fontsize=14, pad=20)

                            short_labels = [label[:20] + '...' if len(label) > 20 else label
                                           for label in all_labels]
                            ax.set_xticks(x_positions)
                            ax.set_xticklabels(short_labels, rotation=45, ha='right', fontsize=8)

                            for bar, value in zip(bars, all_values):
                                height = bar.get_height()
                                if height > 0:
                                    ax.text(bar.get_x() + bar.get_width()/2., height,
                                            f'{int(height)}',
                                            ha='center', va='bottom', fontsize=8)

                            ax.spines['top'].set_visible(False)
                            ax.spines['right'].set_visible(False)
                            ax.grid(axis='y', linestyle='--', alpha=0.7)

                            legend_elements = [plt.Rectangle((0,0),1,1, facecolor=type_color_map[t],
                                                            label=t) for t in types]
                            ax.legend(handles=legend_elements, loc='upper right', fontsize=8)

                            plt.tight_layout()

                            buffer = BytesIO()
                            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
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
                                'categories': categories,
                                'data': chart_data
                            }
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
                    'chart': None,
                    'chart_data': None
                }
            })

    return JsonResponse({
        'status': 'error',
        'error': 'Method not allowed'
    })


@api_view(['POST'])
def kegg_enrichment(request):
    """
    KEGG富集分析API - 使用gseapy进行富集分析
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

        logger.info(f"KEGG富集分析 - gene_input: {gene_input}, genome_id: {genome_id}")

        with connection.cursor() as cursor:
            if genome_id:
                cursor.execute("""
                    SELECT gm.id, gm.geneid
                    FROM genemaster gm
                    WHERE gm.geneid IN %s AND gm.genome_id = %s
                """, [tuple(gene_list), genome_id])
            else:
                cursor.execute("""
                    SELECT gm.id, gm.geneid
                    FROM genemaster gm
                    WHERE gm.geneid IN %s
                """, [tuple(gene_list)])
            gene_id_map = {row[1]: row[0] for row in cursor.fetchall()}

            if gene_id_map:
                cursor.execute("""
                    SELECT gk.id_id, gk.kegg_id
                    FROM gene_kegg gk
                    WHERE gk.id_id IN %s
                      AND gk.kegg_id IS NOT NULL
                """, [tuple(gene_id_map.values())])
            else:
                cursor.execute("SELECT 1 FROM DUAL WHERE 1=0")
            gene_kegg_data = cursor.fetchall()

            if genome_id:
                cursor.execute("""
                    SELECT gk.id_id, gk.kegg_id
                    FROM gene_kegg gk
                    LEFT JOIN genemaster gm ON gk.id_id = gm.id
                    WHERE gk.kegg_id IS NOT NULL
                      AND gm.genome_id = %s
                """, [genome_id])
            else:
                cursor.execute("""
                    SELECT gk.id_id, gk.kegg_id
                    FROM gene_kegg gk
                    WHERE gk.kegg_id IS NOT NULL
                """)
            background_kegg_data = cursor.fetchall()

            cursor.execute("""
                SELECT mp.ko_id, mp.name, mp.full_name, mp.category_id, c.name as category_name
                FROM metabolic_pathway mp
                LEFT JOIN category c ON mp.category_id = c.category_id
            """)
            pathway_info = {}
            for row in cursor.fetchall():
                ko_id, name, full_name, category_id, category_name = row
                pathway_info[ko_id] = {
                    'name': name,
                    'full_name': full_name,
                    'category_id': category_id,
                    'category_name': category_name
                }

        gene_id_to_name = {v: k for k, v in gene_id_map.items()}

        input_kegg_terms = defaultdict(list)
        input_genes = set()

        for gene_id, kegg_id in gene_kegg_data:
            gene_name = next((k for k, v in gene_id_map.items() if v == gene_id), str(gene_id))
            input_genes.add(gene_name)
            if kegg_id:
                input_kegg_terms[kegg_id].append(gene_name)

        total_input_genes = len(input_genes)
        total_background_genes = len(set([row[0] for row in background_kegg_data]))

        if total_input_genes == 0:
            return JsonResponse({
                'status': 'success',
                'data': {
                    'results': [],
                    'input_gene_count': 0,
                    'background_gene_count': total_background_genes
                }
            })

        try:
            import gseapy as gp

            logger.info("使用gseapy进行KEGG富集分析...")

            kegg_gene_sets = defaultdict(set)
            for gene_id, kegg_id in background_kegg_data:
                if kegg_id and gene_id in gene_id_to_name:
                    kegg_gene_sets[kegg_id].add(gene_id_to_name[gene_id])

            if not kegg_gene_sets or not input_genes:
                logger.warning("没有有效的KEGG基因集数据")
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
                gene_sets={k: sorted(list(v)) for k, v in kegg_gene_sets.items() if v},
                background=sorted(set(gene_id_to_name.values())),
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
                pathway_id = row.get('Term', '')
                pathway = pathway_info.get(pathway_id, {})
                
                overlap_str = str(row.get('Overlap', '0/0'))
                match = overlap_str.split('/')
                gene_count = int(match[0]) if match and match[0].isdigit() else 0

                enrichment_results.append({
                    'pathway_id': pathway_id,
                    'description': {
                        'name': pathway.get('name', pathway_id),
                        'definition': pathway.get('full_name', '')
                    },
                    'gene_ratio': overlap_str,
                    'bg_ratio': '',
                    'rich_factor': row.get('Odds Ratio', 0),
                    'fold_enrichment': row.get('Odds Ratio', 0),
                    'p_value': row.get('P-value', 1),
                    'corrected_p_value': row.get('Adjusted P-value', row.get('P-value', 1)),
                    'gene_count': gene_count,
                    'genes': str(row.get('Genes', '')).split(';') if row.get('Genes', '') else [],
                    'category_id': pathway.get('category_id', ''),
                    'category_name': pathway.get('category_name', '')
                })

            enrichment_results.sort(key=lambda x: x['p_value'])
            filtered_results = [r for r in enrichment_results if r.get('p_value', 1.0) <= p_value_threshold]
            
            plot_image = plot_kegg_enrichment(filtered_results) if filtered_results else None

            logger.info(f"gseapy KEGG富集分析结果: {len(filtered_results)} 条显著富集项")

            return JsonResponse({
                'status': 'success',
                'data': {
                    'results': filtered_results,
                    'input_gene_count': total_input_genes,
                    'background_gene_count': total_background_genes,
                    'plot_image': plot_image,
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
            logger.error(f"gseapy KEGG富集分析失败: {str(e)}")
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
    """
    if not kegg_results:
        return None

    df = pd.DataFrame(kegg_results)

    if 'gene_count' in df.columns:
        df['Count'] = df['gene_count']
    else:
        df['Count'] = df['gene_ratio'].apply(lambda x: int(x.split('/')[0]) if isinstance(x, str) else 0)

    if 'GeneRatio' not in df.columns:
        df['GeneRatio'] = df['gene_ratio'].apply(lambda x: eval(x.replace('/', '/')) if isinstance(x, str) else 0)

    df = df.sort_values('p_value').head(max_terms)

    fig = plt.figure(figsize=figsize)
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1, 1.5])

    ax1 = fig.add_subplot(gs[0])
    colors = plt.cm.Blues_r(np.linspace(0.3, 0.9, len(df)))
    bars = ax1.barh(
        y=range(len(df)),
        width=df['Count'],
        color=colors
    )

    ax1.set_title('KEGG Pathway - Count', pad=20, fontsize=14, fontweight='bold')
    ax1.set_xlabel('Gene Count', fontsize=12)
    ax1.set_ylabel('')
    ax1.grid(axis='x', linestyle='--', alpha=0.7)

    y_labels = ['\n'.join(wrap(label, 40)) for label in df['description'].apply(lambda x: x.get('name', '') if isinstance(x, dict) else str(x))]
    ax1.set_yticks(range(len(y_labels)))
    ax1.set_yticklabels(y_labels, fontsize=9)

    ax2 = fig.add_subplot(gs[1])

    sizes = (df['Count'] / df['Count'].max() * 200 + 50) if df['Count'].max() > 0 else 50
    colors = -np.log10(df['p_value'].replace(0, 1e-10))

    scatter = ax2.scatter(
        x=df['GeneRatio'],
        y=range(len(df)),
        s=sizes,
        c=colors,
        cmap='Blues'
    )

    ax2.set_title('KEGG Pathway - Dotplot', pad=20, fontsize=14, fontweight='bold')
    ax2.set_xlabel('Gene Ratio', fontsize=12)
    ax2.set_ylabel('')
    ax2.grid(axis='x', linestyle='--', alpha=0.7)

    ax2.set_yticks(range(len(y_labels)))
    ax2.set_yticklabels(y_labels, fontsize=9)

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
