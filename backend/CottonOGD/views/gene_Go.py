from django.http import JsonResponse
from rest_framework.decorators import api_view
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
import logging

from CottonOGD.views.gene_id_result import resolve_input_ids
from CottonOGD.models import gene_go, gene_info, GeneMaster, GoTerm

logger = logging.getLogger(__name__)

# GoTerm.namespace -> 前端使用的短码（前端按 BP/MF/CC 过滤，必须归一化成这三个值）
GO_NAMESPACE_TO_SHORT = {
    'biological_process': 'BP',
    'molecular_function': 'MF',
    'cellular_component': 'CC',
}


def _load_go_terms(go_ids):
    """批量取 GO 术语信息，返回 {go_id: {name, definition, namespace}}。"""
    terms = {}
    for term in GoTerm.objects.filter(id__in=list(go_ids)).values(
            'id', 'name', 'definition', 'namespace'):
        terms[term['id']] = term
    return terms


def _get_param(request, key, default=''):
    """GET/POST/JSON body 统一取参。"""
    if hasattr(request, 'data') and request.data:
        value = request.data.get(key)
        if value not in (None, ''):
            return value
    value = request.POST.get(key) if request.method == 'POST' else request.GET.get(key)
    return value if value not in (None, '') else default


@api_view(['GET', 'POST'])
def go_annotation(request):
    """
    GO注释API - 根据基因ID获取GO注释信息

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

    results = []
    chart = None
    chart_data = None
    categories = []
    data = {'BP': [], 'MF': [], 'CC': []}

    if gene_list:
        try:
            db_ids = resolve_input_ids(gene_input, genome_id)
            logger.info(f"GO annotation - 解析到 {len(db_ids)} 个 db_id")

            if db_ids:
                # 基因坐标 + geneid 展示名
                geneid_map = dict(GeneMaster.objects.filter(id__in=db_ids)
                                  .values_list('id', 'geneid'))
                coords = {row['id_id']: row for row in gene_info.objects
                          .filter(id_id__in=db_ids, type='gene')
                          .values('id_id', 'seqid', 'start', 'end')}

                # GO 注释（term 信息一次取全）
                go_rows = (gene_go.objects
                           .filter(id_id__in=db_ids, go_id__isnull=False)
                           .values('id_id', 'go_id_id', 'go_id__name', 'go_id__namespace'))
                logger.info(f"GO annotation - 查询到 {len(go_rows)} 条GO数据")

                # 直接构建结果和图表数据，减少循环
                chart_data = {'BP': {}, 'MF': {}, 'CC': {}}
                go_type_map = GO_NAMESPACE_TO_SHORT

                for row in go_rows:
                    gene_db_id = row['id_id']
                    coord = coords.get(gene_db_id, {})
                    go_name = row['go_id__name']
                    namespace = row['go_id__namespace'] or ''
                    go_type_short = go_type_map.get(namespace, 'Unknown')

                    results.append({
                        'Chr': coord.get('seqid', ''),
                        'Start': coord.get('start', 0),
                        'End': coord.get('end', 0),
                        'ID': geneid_map.get(gene_db_id, ''),
                        'GO_ID': row['go_id_id'],
                        'Description': go_name or '',
                        'Gene_Ontology': namespace or 'Unknown',
                        'dddd': namespace or 'Unknown'
                    })

                    # 直接更新图表数据
                    if go_type_short in chart_data and go_name:
                        chart_data[go_type_short][go_name] = chart_data[go_type_short].get(go_name, 0) + 1

                # 获取所有 GO 描述用于图表
                categories = sorted(set(r['Description'] for r in results if r['Description']))
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


@api_view(['GET', 'POST'])
def go_enrichment(request):
    """
    GO富集分析API - 使用gseapy进行富集分析

    入参与 go_annotation 相同；解析统一走 Meilisearch + MySQL 兜底，
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

    try:
        db_ids = resolve_input_ids(gene_input, genome_id)
        logger.info(f"GO富集分析 - 解析到 {len(db_ids)} 个 db_id")

        # 输入基因的 GO 注释
        enrichment_rows = list(gene_go.objects
                               .filter(id_id__in=db_ids, go_id__isnull=False)
                               .values_list('id_id__geneid', 'go_id_id'))
        logger.info(f"GO富集分析 - 查询到 {len(enrichment_rows)} 条富集数据")

        # 背景基因总数（该基因组有 GO 注释的基因数）
        total_background_genes = (gene_go.objects
                                  .filter(id_id__genome__name=genome_id, go_id__isnull=False)
                                  .values('id_id').distinct().count())
        logger.info(f"GO富集分析 - 背景基因总数: {total_background_genes}")

        # 背景数据（geneid, go_id）
        background_rows = list(gene_go.objects
                               .filter(id_id__genome__name=genome_id, go_id__isnull=False)
                               .values_list('id_id__geneid', 'go_id_id'))
        logger.info(f"GO富集分析 - 背景数据条数: {len(background_rows)}")

        input_go_terms = defaultdict(list)
        input_genes = set()

        for gene, go_id in enrichment_rows:
            if go_id:
                go_id = str(go_id).strip()
                if go_id and go_id != '-':
                    input_genes.add(gene)
                    input_go_terms[go_id].append({'gene': gene})

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

        try:
            import gseapy as gp

            logger.info("使用gseapy进行GO富集分析...")

            # 构建基因集：go_id -> 基因集合
            go_gene_sets = defaultdict(set)
            for gene, go_id in background_rows:
                if go_id:
                    go_id = str(go_id).strip()
                    if go_id and go_id != '-':
                        go_gene_sets[go_id].add(gene)

            # 获取背景基因列表
            background_genes_list = list({gene for gene, go_id in background_rows if go_id})

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
            # 一次性取回本轮命中的 GO 术语名称/定义/namespace，用于填充 description 与 go_type
            go_terms = _load_go_terms(
                row.get('Term', '') for _, row in enr.results.iterrows())

            for _, row in enr.results.iterrows():
                go_id = row.get('Term', '')
                term = go_terms.get(go_id) or {}

                overlap_str = str(row.get('Overlap', '0/0'))
                match = overlap_str.split('/')
                gene_count = int(match[0]) if match and match[0].isdigit() else 0

                enrichment_results.append({
                    'go_id': go_id,
                    'description': {
                        'name': term.get('name') or go_id,
                        'definition': term.get('definition') or ''
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
                    # 归一化成前端过滤用的 BP/MF/CC，取不到术语时保持 Unknown
                    'go_type': GO_NAMESPACE_TO_SHORT.get(term.get('namespace'), 'Unknown')
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
