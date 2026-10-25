from django.http import JsonResponse
from rest_framework.decorators import api_view
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
from matplotlib.gridspec import GridSpec
import pandas as pd
from textwrap import wrap
from collections import defaultdict
import logging

from CottonOGD.views.gene_id_result import resolve_input_ids
from CottonOGD.models import gene_info, gene_kegg, GeneMaster, PathwayEnzyme

logger = logging.getLogger(__name__)


def _get_param(request, key, default=''):
    """GET/POST/JSON body 统一取参。"""
    if hasattr(request, 'data') and request.data:
        value = request.data.get(key)
        if value not in (None, ''):
            return value
    value = request.POST.get(key) if request.method == 'POST' else request.GET.get(key)
    return value if value not in (None, '') else default


@api_view(['GET', 'POST'])
def kegg_annotation(request):
    """
    KEGG注释API - 根据基因ID获取KEGG注释信息

    入参：gene_id（单 ID 或逗号/竖线/换行分隔多 ID，可带版本号/转录本后缀）、
          genome_id（可选，物种名）。解析统一走 Meilisearch + MySQL 兜底。
    """
    gene_input = str(_get_param(request, 'gene_id', '')).strip()
    genome_id = str(_get_param(request, 'genome_id', '')).strip()

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

    results = []
    categories = []
    chart_data = {}
    chart = None

    try:
        db_ids = resolve_input_ids(gene_input, genome_id)
        logger.info(f"KEGG注释 - 解析到 {len(db_ids)} 个 db_id")

        chart_data_raw = defaultdict(lambda: defaultdict(int))

        if db_ids:
            # geneid 展示名 + 基因坐标
            geneid_map = dict(GeneMaster.objects.filter(id__in=db_ids)
                              .values_list('id', 'geneid'))
            coords = {row['id_id']: row for row in gene_info.objects
                      .filter(id_id__in=db_ids, type='gene')
                      .values('id_id', 'seqid', 'start', 'end')}

            # KO -> 通路映射（与旧 SQL 的 pathway_enzyme 联结语义一致）
            pe_rows = (PathwayEnzyme.objects
                       .select_related('pathway', 'pathway__category')
                       .values('enzyme_id', 'pathway__name',
                               'pathway__full_name', 'pathway__category_id',
                               'pathway__category__name'))
            ko_pathway = defaultdict(list)
            for row in pe_rows:
                ko_pathway[row['enzyme_id']].append(row)

            # KEGG 注释
            gk_rows = (gene_kegg.objects
                       .filter(id_id__in=db_ids)
                       .values('id_id', 'kegg_id', 'kegg_id__name', 'kegg_id__full_name'))
            logger.info(f"KEGG annotation - 查询到 {len(gk_rows)} 条数据")

            result_dict = defaultdict(list)
            for row in gk_rows:
                gene_db_id = row['id_id']
                coord = coords.get(gene_db_id, {})
                pathways = ko_pathway.get(row['kegg_id']) or [{}]
                for pw in pathways:
                    result_dict[gene_db_id].append({
                        'seqid': coord.get('seqid', ''),
                        'start': coord.get('start', 0),
                        'end': coord.get('end', 0),
                        'geneid_id': geneid_map.get(gene_db_id, ''),
                        'kegg_id': row['kegg_id'],
                        'kegg_name': row['kegg_id__name'] or '',
                        'kegg_full_name': row['kegg_id__full_name'] or '',
                        'pathway_name': pw.get('pathway__name') or '',
                        'pathway_full_name': pw.get('pathway__full_name') or '',
                        'category_id': pw.get('pathway__category_id') or '',
                        'category_name': pw.get('pathway__category__name') or ''
                    })

            for items in result_dict.values():
                for item in items:
                    if item['kegg_id']:
                        results.append({
                            'Chr': item['seqid'],
                            'Start': item['start'],
                            'End': item['end'],
                            'ID': item['geneid_id'],
                            'KEGG_ID': item['kegg_id'],
                            'Description': item['kegg_name'],
                            'Type': '',
                            'Pathway': item['pathway_name'],
                            'Pathway_Full': item['pathway_full_name'],
                            'Category_ID': item['category_id'],
                            'Category_Name': item['category_name']
                        })

                        chart_data_raw['Pathway'][item['pathway_name']] += 1

            categories = sorted({r['Description'] for r in results if r['Description']})

            for kegg_type, desc_counts in chart_data_raw.items():
                chart_data[kegg_type] = {
                    'labels': list(desc_counts.keys()),
                    'values': list(desc_counts.values())
                }

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
                                    f'{int(height)}', ha='center', va='bottom', fontsize=8)

                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    ax.grid(axis='y', linestyle='--', alpha=0.7)

                    legend_elements = [plt.Rectangle((0, 0), 1, 1, facecolor=type_color_map[t],
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


@api_view(['GET', 'POST'])
def kegg_enrichment(request):
    """
    KEGG富集分析API - 使用gseapy进行富集分析

    入参与 kegg_annotation 相同；解析统一走 Meilisearch + MySQL 兜底，
    背景集合按 genome_id（物种名）圈定。
    """
    gene_input = str(_get_param(request, 'gene_id', '')).strip()
    genome_id = str(_get_param(request, 'genome_id', '')).strip()
    p_value_threshold = float(_get_param(request, 'p_value_threshold', 0.05))

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

    try:
        db_ids = resolve_input_ids(gene_input, genome_id)
        logger.info(f"KEGG富集分析 - 解析到 {len(db_ids)} 个 db_id")

        # 输入基因的 KEGG 注释
        gene_kegg_data = list(gene_kegg.objects
                              .filter(id_id__in=db_ids, kegg_id__isnull=False)
                              .values_list('id_id', 'kegg_id'))

        # 背景数据（该基因组全部 KO 注释）
        background_kegg_data = list(gene_kegg.objects
                                    .filter(id_id__genome__name=genome_id, kegg_id__isnull=False)
                                    .values_list('id_id', 'kegg_id'))

        # db_id -> geneid 展示名
        involved_ids = {gid for gid, _ in gene_kegg_data} | {gid for gid, _ in background_kegg_data}
        geneid_map = dict(GeneMaster.objects.filter(id__in=involved_ids)
                          .values_list('id', 'geneid'))

        # KO -> 通路信息
        pe_rows = (PathwayEnzyme.objects
                   .select_related('pathway', 'pathway__category')
                   .values('enzyme_id', 'pathway__name', 'pathway__full_name',
                           'pathway__category_id', 'pathway__category__name'))
        ko_pathway = defaultdict(list)
        for row in pe_rows:
            ko_pathway[row['enzyme_id']].append(row)

        kegg_info = {}
        from CottonOGD.models import KOTerm
        for row in KOTerm.objects.values('ko_id', 'name', 'full_name'):
            pws = ko_pathway.get(row['ko_id']) or [{}]
            pw = pws[0]
            kegg_info[row['ko_id']] = {
                'name': row['name'] or '',
                'full_name': row['full_name'] or '',
                'pathway_name': pw.get('pathway__name') or '',
                'pathway_full_name': pw.get('pathway__full_name') or '',
                'category_id': pw.get('pathway__category_id') or '',
                'category_name': pw.get('pathway__category__name') or ''
            }

        input_kegg_terms = defaultdict(list)
        input_genes = set()

        for gene_db_id, kegg_id in gene_kegg_data:
            gene_name = geneid_map.get(gene_db_id, str(gene_db_id))
            input_genes.add(gene_name)
            if kegg_id:
                input_kegg_terms[kegg_id].append(gene_name)

        total_input_genes = len(input_genes)
        total_background_genes = len({row[0] for row in background_kegg_data})

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
            for gene_db_id, kegg_id in background_kegg_data:
                if kegg_id and gene_db_id in geneid_map:
                    kegg_gene_sets[kegg_id].add(geneid_map[gene_db_id])

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

            background_genes_list = list({geneid_map[gid] for gid, _ in background_kegg_data
                                          if gid in geneid_map})

            enr = gp.enrich(
                gene_list=sorted(list(input_genes)),
                gene_sets={k: sorted(list(v)) for k, v in kegg_gene_sets.items() if v},
                background=sorted(background_genes_list),
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
                kegg_id = row.get('Term', '')
                kegg = kegg_info.get(kegg_id, {})

                overlap_str = str(row.get('Overlap', '0/0'))
                match = overlap_str.split('/')
                gene_count = int(match[0]) if match and match[0].isdigit() else 0

                enrichment_results.append({
                    'pathway_id': kegg_id,
                    'description': {
                        'name': kegg.get('name', kegg_id),
                        'definition': kegg.get('full_name', '')
                    },
                    'gene_ratio': overlap_str,
                    'bg_ratio': '',
                    'rich_factor': row.get('Odds Ratio', 0),
                    'fold_enrichment': row.get('Odds Ratio', 0),
                    'p_value': row.get('P-value', 1),
                    'corrected_p_value': row.get('Adjusted P-value', row.get('P-value', 1)),
                    'gene_count': gene_count,
                    'genes': str(row.get('Genes', '')).split(';') if row.get('Genes', '') else [],
                    'category_id': kegg.get('category_id', ''),
                    'category_name': kegg.get('category_name', '')
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

    except Exception as e:
        logger.error(f"KEGG enrichment error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': str(e)
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
