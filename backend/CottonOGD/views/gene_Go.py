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
from CottonOGD.models import GeneMaster, gene_go, gene_info, GoTerm
from collections import Counter

logger = logging.getLogger(__name__)

_clusterProfiler_cache = None

def _get_clusterProfiler():
    global _clusterProfiler_cache
    if _clusterProfiler_cache is None:
        from rpy2.robjects.packages import importr
        _clusterProfiler_cache = importr('clusterProfiler')
        logger.info("clusterProfiler 包已缓存")
    return _clusterProfiler_cache

@api_view(['GET'])
def go_annotation(request):
    """
    GO注释API - 根据基因ID获取GO注释信息
    """
    if request.method == 'GET':
        gene_input = request.GET.get('gene_id', '')
        genome_id = request.GET.get('genome_id', 'G.kirkii_ISU_ISU_v3.0')
        logger.info(f'gene_input:{gene_input}, genome_id:{genome_id}')        
        if not gene_input:
            return JsonResponse({
                'status': 'error',
                'error': 'Missing gene_id parameter'
            })

        gene_list = [gene.strip() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        # 获取基因ID映射（geneid -> id 和 id -> geneid）
        gene_masters = GeneMaster.objects.filter(genome_id=genome_id, geneid__in=gene_list)
        gene_id_map = {gm.geneid: gm.id for gm in gene_masters}
        gene_id_map_reverse = {gm.id: gm.geneid for gm in gene_masters}
        gene_id_list = list(gene_id_map.values())
        
        logger.info(f'gene_id_map:{gene_id_map}')
        
        results = []
        chart = None
        chart_data = None
        categories = []
        
        if gene_id_list:
            try:
                with connection.cursor() as cursor:
                    # 使用JOIN查询：gene_info + gene_go + GoTerm
                    cursor.execute("""
                        SELECT 
                            gi.seqid,
                            gi.start,
                            gi.end,
                            gi.id_id,
                            gg.go_id,
                            gt.name AS go_description,
                            gt.namespace AS go_type
                        FROM gene_assembly gi
                        LEFT JOIN gene_go gg ON gi.id_id = gg.id_id
                        LEFT JOIN go_term gt ON gg.go_id = gt.id
                        WHERE gi.type = 'gene' 
                          AND gi.id_id IN %s
                    """, [tuple(gene_id_list)])
                    
                    annotation_data = cursor.fetchall()
                    logger.info(f"GO annotation - 查询到 {len(annotation_data)} 条数据")

                    # 创建结果字典，便于处理（使用全称）
                    result_dict = defaultdict(list)
                    for row in annotation_data:
                        seqid, start, end, id_id, go_id, go_description, go_type = row
                        result_dict[id_id].append({
                            'seqid': seqid,
                            'start': start,
                            'end': end,
                            'go_id': go_id,
                            'go_description': go_description if go_description else '',
                            'go_type': go_type if go_type else ''
                        })

                    # 转换为最终结果格式（使用全称）
                    for id_id, items in result_dict.items():
                        for item in items:
                            results.append({
                                'Chr': item['seqid'],
                                'Start': item['start'],
                                'End': item['end'],
                                'ID': id_id,
                                'Gene_ID': gene_id_map_reverse.get(id_id, ''),
                                'GO_ID': item['go_id'],
                                'Description': item['go_description'],
                                'Gene_Ontology': item['go_type'],
                                'dddd': item['go_description']  # dddd 就是 description
                            })

                    # 统计GO类型分布用于图表（只在绘图时转换为简写）
                    GO_MAP = {
                        'biological_process': 'BP',
                        'molecular_function': 'MF',
                        'cellular_component': 'CC'
                    }
                    
                    chart_data_raw = defaultdict(lambda: defaultdict(int))
                    for result in results:
                        go_type_full = result['Gene_Ontology']
                        dddd_value = result['dddd']
                        chart_data_raw[go_type_full][dddd_value] += 1
                    
                    # 只在绘图时将全称转换为简写
                    chart_data = {'BP': {}, 'MF': {}, 'CC': {}}
                    for go_type_full, desc_counts in chart_data_raw.items():
                        # 转换为简写
                        go_type = GO_MAP.get(go_type_full, go_type_full)
                        if 'biological' in str(go_type_full).lower():
                            go_type = 'BP'
                        elif 'molecular' in str(go_type_full).lower():
                            go_type = 'MF'
                        elif 'cellular' in str(go_type_full).lower():
                            go_type = 'CC'
                        
                        if go_type in chart_data:
                            chart_data[go_type].update(desc_counts)

                    categories = sorted({result['dddd'] for result in results if result['dddd']})
                    logger.info(f"图表分类: {categories}")
                    logger.info(f"图表数据: {chart_data}")
                    
                    data = {
                        'BP': [chart_data['BP'].get(cat, 0) for cat in categories],
                        'MF': [chart_data['MF'].get(cat, 0) for cat in categories],
                        'CC': [chart_data['CC'].get(cat, 0) for cat in categories]
                    }

                    # 生成图表
                    if categories and any(data.values()):
                        # 确保所有值都是非负整数
                        bp_values = [max(0, int(v)) for v in data['BP']]
                        mf_values = [max(0, int(v)) for v in data['MF']]
                        cc_values = [max(0, int(v)) for v in data['CC']]
                        
                        max_count = max(max(bp_values), max(mf_values), max(cc_values))
                        logger.info(f"最大计数: {max_count}")
                        
                        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
                        axes = [ax1, ax2, ax3]
                        
                        # 设置Y轴范围
                        y_max = max_count + 1 if max_count > 0 else 5
                        for ax in axes:
                            ax.set_ylim(0, y_max)
                            ax.grid(False) 

                        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
                        data_items = [('BP', bp_values), ('MF', mf_values), ('CC', cc_values)]
                        
                        for i, (ax, (group, values), color) in enumerate(zip(axes, data_items, colors)):
                            bars = ax.bar(categories, values, color=color)
                            ax.set_title(group, fontsize=14, pad=15)
                            ax.set_xlabel('', fontsize=12)
                            ax.tick_params(axis='x', rotation=45, labelsize=8)

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
    GO富集分析API - 先提取数据，再决定使用R或Python进行富集分析
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
        
        # 第一步：先从数据库提取所有需要的数据
        with connection.cursor() as cursor:
            # 获取输入基因的ID映射（根据genome_id过滤）
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
            
            # 获取输入基因的GO注释
            if gene_id_map:
                cursor.execute("""
                    SELECT gg.id_id, gg.go_id, gt.name, gt.namespace
                    FROM gene_go gg
                    LEFT JOIN go_term gt ON gg.go_id = gt.id
                    WHERE gg.id_id IN %s AND gg.go_id IS NOT NULL
                """, [tuple(gene_id_map.values())])
            else:
                cursor.execute("SELECT 1 FROM DUAL WHERE 1=0")
            gene_go_data = cursor.fetchall()
            
            # 获取背景基因的GO注释（根据genome_id过滤）
            if genome_id:
                cursor.execute("""
                    SELECT gg.id_id, gg.go_id
                    FROM gene_go gg
                    LEFT JOIN genemaster gm ON gg.id_id = gm.id
                    WHERE gg.go_id IS NOT NULL AND gm.genome_id = %s
                """, [genome_id])
            else:
                cursor.execute("""
                    SELECT gg.id_id, gg.go_id
                    FROM gene_go gg
                    WHERE gg.go_id IS NOT NULL
                """)
            background_go_data = cursor.fetchall()
            
            # 获取GO术语信息
            cursor.execute("""
                SELECT gt.id, gt.name, gt.namespace
                FROM go_term gt
            """)
            go_term_info = {row[0]: {'name': row[1], 'namespace': row[2]} for row in cursor.fetchall()}
            
            # 获取背景基因及其GO注释（用于R富集分析）
            # 需要从genemaster获取背景基因的名称
            background_gene_ids = set([row[0] for row in background_go_data])
            if background_gene_ids and genome_id:
                cursor.execute("""
                    SELECT gm.id, gm.geneid
                    FROM genemaster gm
                    WHERE gm.id IN %s AND gm.genome_id = %s
                """, [tuple(background_gene_ids), genome_id])
            elif background_gene_ids:
                cursor.execute("""
                    SELECT gm.id, gm.geneid
                    FROM genemaster gm
                    WHERE gm.id IN %s
                """, [tuple(background_gene_ids)])
            else:
                cursor.execute("SELECT 1 FROM DUAL WHERE 1=0")
            
            background_gene_name_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 构建输入基因到GO的映射
        gene2go_dict = {}
        for gene_id, go_id, name, namespace in gene_go_data:
            gene_name = next((k for k, v in gene_id_map.items() if v == gene_id), str(gene_id))
            if gene_name not in gene2go_dict:
                gene2go_dict[gene_name] = []
            gene2go_dict[gene_name].append(go_id)
        
        # 构建背景基因到GO的完整映射（用于R富集分析）
        background_gene2go_dict = {}
        for gene_id, go_id in background_go_data:
            gene_name = background_gene_name_map.get(gene_id, str(gene_id))
            if gene_name not in background_gene2go_dict:
                background_gene2go_dict[gene_name] = []
            background_gene2go_dict[gene_name].append(go_id)
        
        # 获取所有背景GO术语
        background_gos = set([row[1] for row in background_go_data])
        
        logger.info(f"GO富集分析 - 输入基因数: {len(gene_list)}")
        logger.info(f"GO富集分析 - 有GO注释的基因数: {len(gene2go_dict)}")
        logger.info(f"GO富集分析 - 背景GO术语数: {len(background_gos)}")
        
        if not gene2go_dict:
            return JsonResponse({
                'status': 'success',
                'data': {
                    'results': [],
                    'input_gene_count': len(gene_list),
                    'background_gene_count': len(background_gos)
                }
            })
        
        # 第二步：尝试使用R的clusterProfiler，如果不可用则使用Python
        try:
            # 先尝试导入rpy2验证R环境是否可用
            import rpy2.robjects as ro
            
            logger.info("R环境可用，调用R富集分析...")
            
            return execute_r_enrichment(
                gene_list, gene2go_dict, background_gene2go_dict, 
                go_term_info, p_value_threshold
            )
            
        except ImportError as e:
            logger.warning(f"R环境不可用，使用Python实现: {str(e)}")
            return execute_python_enrichment(
                gene_list, gene_id_map, gene_go_data, 
                background_go_data, go_term_info, 
                p_value_threshold, genome_id
            )
        except Exception as e:
            logger.error(f"R执行失败，回退到Python: {str(e)}")
            return execute_python_enrichment(
                gene_list, gene_id_map, gene_go_data, 
                background_go_data, go_term_info, 
                p_value_threshold, genome_id
            )

    return JsonResponse({
        'status': 'error',
        'error': 'Method not allowed'
    })


def execute_r_enrichment(gene_list, gene2go_dict, background_gene2go_dict, go_term_info, p_value_threshold):
    """使用R的clusterProfiler执行富集分析"""
    import rpy2.robjects as ro
    from rpy2.robjects import pandas2ri
    from rpy2.robjects.conversion import localconverter
    from rpy2.robjects.packages import importr
    import pandas as pd
    from itertools import chain
    
    # 显式设置转换上下文（解决多线程问题）
    converter = ro.default_converter + pandas2ri.converter
    
    # 过滤有效基因（使用集合加速查找）
    gene_set = set(gene_list)
    gene2go_keys = set(gene2go_dict.keys())
    valid_genes = list(gene_set & gene2go_keys)
    logger.info(f"准备调用clusterProfiler::enricher，基因数量: {len(valid_genes)}")
    
    if len(valid_genes) == 0:
        logger.warning("没有有效的基因数据")
        raise ValueError("没有有效的基因数据")
    
    # 构建完整的TERM2GENE格式的数据（使用itertools和列表推导式加速）
    term2gene_df = pd.DataFrame([
        {'term': go_id, 'gene': gene}
        for gene, gos in background_gene2go_dict.items()
        for go_id in gos
    ])
    
    if term2gene_df.empty:
        logger.warning("没有有效的GO注释数据")
        raise ValueError("没有有效的GO注释数据")
    
    # 构建TERM2NAME格式的数据（使用字典推导式）
    term2name_dict = {go_id: info.get('name', '') for go_id, info in go_term_info.items()}
    
    # 使用localconverter包装所有R操作
    with localconverter(converter):
        # 创建TERM2GENE数据框
        r_term2gene = ro.conversion.py2rpy(term2gene_df)
        
        # 创建TERM2NAME数据框（如果有）
        r_term2name = ro.NULL
        if term2name_dict:
            term2name_df = pd.DataFrame(list(term2name_dict.items()), columns=['term', 'name'])
            r_term2name = ro.conversion.py2rpy(term2name_df)
        
        r_gene_list = ro.StrVector(valid_genes)
        
        # universe是背景基因列表
        background_genes = list(background_gene2go_dict.keys())
        r_universe = ro.StrVector(background_genes)
        
        logger.info(f"背景基因数量: {len(background_genes)}")
        logger.info(f"GO注释关系数量: {len(term2gene_df)}")

        # 使用缓存的clusterProfiler
        clusterProfiler = _get_clusterProfiler()
        
        # 调用clusterProfiler的enricher函数（使用TERM2GENE参数，调整基因集大小限制）
        go_result = clusterProfiler.enricher(
            gene = r_gene_list,
            universe = r_universe,
            pAdjustMethod = ro.StrVector(['fdr']),
            qvalueCutoff = ro.FloatVector([p_value_threshold]),
            TERM2GENE = r_term2gene,
            TERM2NAME = r_term2name,
            minGSSize = ro.IntVector([1]),
            maxGSSize = ro.IntVector([10000])
        )
        
        logger.info("R富集分析完成")
        
        # 检查结果是否为NULL
        if go_result is None or ro.r['is.null'](go_result)[0]:
            logger.warning("R富集分析返回NULL，没有找到显著富集的GO项")
            raise ValueError("R富集分析没有找到显著富集的GO项")
        
        # 将结果转换为DataFrame
        go_df = ro.r['as.data.frame'](go_result)
    
    # 处理结果
    enrichment_results = []
    for _, row in go_df.iterrows():
        go_id = row.get('ID', '')
        go_info = go_term_info.get(go_id, {'name': '', 'namespace': ''})
        
        namespace = go_info.get('namespace', '')
        if 'biological' in str(namespace).lower():
            go_type_short = 'BP'
        elif 'molecular' in str(namespace).lower():
            go_type_short = 'MF'
        elif 'cellular' in str(namespace).lower():
            go_type_short = 'CC'
        else:
            go_type_short = 'Unknown'
        
        enrichment_results.append({
            'go_id': go_id,
            'description': {
                'name': row.get('Description', go_info.get('name', '')),
                'definition': ''
            },
            'gene_ratio': row.get('GeneRatio', ''),
            'bg_ratio': row.get('BgRatio', ''),
            'rich_factor': float(row.get('GeneRatio', '0/1').split('/')[0]) / float(row.get('BgRatio', '1/1').split('/')[0]) if '/' in str(row.get('GeneRatio')) else 0,
            'fold_enrichment': float(row.get('OddsRatio', 0)),
            'z_score': 0,
            'p_value': float(row.get('pvalue', 1.0)),
            'corrected_p_value': float(row.get('p.adjust', 1.0)),
            'genes': str(row.get('geneID', '')).split('/') if row.get('geneID') else [],
            'go_type': go_type_short,
            'q_value': float(row.get('qvalue', 1.0))
        })
    
    enrichment_results.sort(key=lambda x: x['p_value'])
    filtered_results = [r for r in enrichment_results if r.get('p_value', 1.0) <= p_value_threshold]
    
    logger.info(f"R GO富集分析结果: {len(filtered_results)} 条显著富集项")
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'results': filtered_results,
            'input_gene_count': len(gene_list),
            'background_gene_count': len(background_gene2go_dict),
            'method': 'R_clusterProfiler'
        }
    })


def execute_python_enrichment(gene_list, gene_id_map, gene_go_data, background_go_data, go_term_info, p_value_threshold, genome_id):
    """使用Python执行GO富集分析"""
    gene_ids = list(gene_id_map.values())
    
    if not gene_ids:
        return JsonResponse({
            'status': 'success',
            'data': {
                'results': [],
                'input_gene_count': len(gene_list),
                'background_gene_count': len(background_go_data)
            }
        })
    
    
    # 获取背景基因总数
    total_background_genes = len(set([row[0] for row in background_go_data]))
    
    # 构建background_data
    background_data = [(row[1], '', '') for row in background_go_data]
    
    input_genes = set(gene_ids)
    
    def normalize_go_type(go_type):
        if not go_type:
            return 'Unknown'
        go_type_lower = str(go_type).lower()
        if 'biological' in go_type_lower:
            return 'BP'
        elif 'molecular' in go_type_lower:
            return 'MF'
        elif 'cellular' in go_type_lower:
            return 'CC'
        return go_type
    
    # 处理输入基因的GO项
    input_go_terms = defaultdict(list)
    
    for row in gene_go_data:
        gene_id, go_id, description, go_type_raw = row
        
        go_type = normalize_go_type(go_type_raw)
        
        if go_id and go_id != '-':
            input_go_terms[go_id].append({
                'gene_id': gene_id,
                'go_type': go_type,
                'description': description
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
    
    # 处理背景数据
    background_counts = Counter(row[1] for row in background_go_data if row[1] and row[1] != '-')
    background_descriptions = {}
    
    for row in background_data:
        go_id, description, go_type_raw = row
        
        if go_id and go_id != '-':
            background_counts[go_id] += 1
            if go_id not in background_descriptions:
                background_descriptions[go_id] = description
    
    # 计算富集结果
    enrichment_results = []
    for go_id, genes in input_go_terms.items():
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
            
            go_info = go_term_info.get(go_id, {'name': '', 'namespace': ''})
            go_type = normalize_go_type(go_info.get('namespace', ''))
            
            enrichment_results.append({
                'go_id': go_id,
                'description': {
                    'name': background_descriptions.get(go_id, go_info.get('name', 'No description available')),
                    'definition': ''
                },
                'gene_ratio': f"{a}/{total_input_genes}",
                'bg_ratio': f"{c}/{total_background_genes}",
                'rich_factor': a / c if c > 0 else 0,
                'fold_enrichment': fold_enrichment,
                'z_score': z_score,
                'p_value': p_value,
                'genes': [g['gene_id'] for g in genes],
                'go_type': go_type
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
    
    logger.info(f"Python GO富集分析结果: {len(filtered_results)} 条显著富集项")
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'results': filtered_results,
            'input_gene_count': total_input_genes,
            'background_gene_count': total_background_genes,
            'method': 'Python_fisher_exact'
        }
    })
