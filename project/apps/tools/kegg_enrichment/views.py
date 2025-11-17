from django.core.paginator import Paginator
from django.shortcuts import render
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from scipy.stats import fisher_exact
from statsmodels.stats.multitest import multipletests
from matplotlib.gridspec import GridSpec
import math
import requests
import numpy as np
import pickle
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
from textwrap import wrap
import base64
from io import BytesIO
def plot_kegg_enrichment(kegg_results, max_terms=30, figsize=(15, 7)):
    """
    Create combined barplot and dotplot for KEGG enrichment results
    
    Parameters:
    - kegg_results: List of dicts with KEGG enrichment results
    - max_terms: int, maximum number of terms to display
    - figsize: tuple, size of the figure
    """
    
    if not kegg_results:
        print("No significant KEGG results to plot")
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

class KEGGEnrichment:
    _kegg_pathway_cache = None
    _last_cache_time = 0
    
    @classmethod
    def _load_kegg_pathways_from_db(cls):
        """从数据库加载KEGG通路信息"""
        pathways = {}
        start_time = time.time()
        
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT `Match`, Description FROM eg_kegg "
                "WHERE `Match` IS NOT NULL AND `Match` != '-'"
            )
            for pathway_id, description in cursor:
                for pathway in pathway_id.split(','):
                    pathway = pathway.strip()
                    if pathway:
                        pathways[pathway] = description
        
        print(f"从数据库加载KEGG通路完成，耗时: {time.time()-start_time:.2f}秒")
        return pathways

    @classmethod
    def get_kegg_pathways(cls):
        """获取KEGG通路数据（带缓存）"""
        if cls._kegg_pathway_cache is None or time.time() - cls._last_cache_time > 3600:
            cached = cache.get('kegg_pathways')
            if cached:
                cls._kegg_pathway_cache = pickle.loads(cached)
            else:
                cls._kegg_pathway_cache = cls._load_kegg_pathways_from_db()
                cache.set('kegg_pathways', pickle.dumps(cls._kegg_pathway_cache), timeout=86400)
            
            cls._last_cache_time = time.time()
        
        return cls._kegg_pathway_cache

    def __init__(self):
        self.kegg_pathways = self.get_kegg_pathways()

    def _calculate_enrichment(self, a, b, c, d):
        """计算富集指标"""
        total = a + b + c + d
        expected = (a + b) * (a + c) / total
        variance = expected * (1 - (a + b)/total) * (1 - (a + c)/total)
        
        _, p_value = fisher_exact([[a, b], [c, d]], alternative='greater')
        z_score = (a - expected) / math.sqrt(variance) if variance > 0 else 0
        fold_enrichment = (a / (a + b)) / (c / (c + d)) if (c + d) > 0 else 0
        
        return {
            'p_value': p_value,
            'z_score': z_score,
            'fold_enrichment': fold_enrichment,
            'expected': expected
        }

    def perform_enrichment(self, gene_list):
        """KEGG富集分析主函数"""
        start_time = time.time()
        
        # 1. 查询输入基因的KEGG注释
        with connection.cursor() as cursor:
            if not gene_list:
                return {
                    'gene_list': gene_list,
                    'results': [],
                    'input_gene_count': 0,
                    'background_gene_count': 0
                }
            
            # 构建参数化查询
            placeholders = ','.join(['%s'] * len(gene_list))
            query = f"""
                SELECT Query, `Match`, Description 
                FROM eg_kegg 
                WHERE Query IN ({placeholders}) 
                AND `Match` IS NOT NULL 
                AND `Match` != '-'
            """
            cursor.execute(query, gene_list)
            input_genes_kegg = cursor.fetchall()
            
            # 2. 获取背景统计信息
            cursor.execute("SELECT COUNT(*) FROM eg_kegg")
            total_background_genes = cursor.fetchone()[0]
            
            # 3. 预计算背景KEGG通路频率和描述
            cursor.execute(
                "SELECT `Match`, Description FROM eg_kegg "
                "WHERE `Match` IS NOT NULL AND `Match` != '-'"
            )
            background_counts = defaultdict(int)
            background_descriptions = {}
            
            for pathway_id, description in cursor:
                for pathway in pathway_id.split(','):
                    pathway = pathway.strip()
                    if pathway:
                        background_counts[pathway] += 1
                        # 存储KEGG通路的描述
                        if pathway not in background_descriptions:
                            background_descriptions[pathway] = description
        
        # 4. 处理输入基因的KEGG通路
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
            return {
                'gene_list': gene_list,
                'results': [],
                'input_gene_count': 0,
                'background_gene_count': total_background_genes
            }
        
        # 5. 并行计算富集结果
        enrichment_results = []
        for pathway, genes in input_pathways.items():
            a = len(genes)
            b = total_input_genes - a
            c = background_counts.get(pathway, 0)
            d = total_background_genes - c
            
            if c == 0:
                continue
            
            metrics = self._calculate_enrichment(a, b, c, d)
            
            enrichment_results.append({
                'pathway_id': pathway,
                'description': {
                    'name': background_descriptions.get(pathway, 'No description available'),
                    'definition': ''
                },
                'gene_ratio': f"{a}/{total_input_genes}",
                'bg_ratio': f"{c}/{total_background_genes}",
                'rich_factor': a / c if c > 0 else 0,
                'fold_enrichment': metrics['fold_enrichment'],
                'z_score': metrics['z_score'],
                'p_value': metrics['p_value'],
                
            })
        
        # 6. 多重检验校正
        if enrichment_results:
            p_values = [r['p_value'] for r in enrichment_results]
            _, corrected_p_values, _, _ = multipletests(p_values, method='fdr_bh')
            for i, p in enumerate(corrected_p_values):
                enrichment_results[i]['corrected_p_value'] = p
            
            # 按p值排序
            enrichment_results.sort(key=lambda x: x['p_value'])
        
        print(f"KEGG富集分析完成，总耗时: {time.time()-start_time:.2f}秒")
        return {
            'gene_list': gene_list,
            'results': enrichment_results,
            'input_gene_count': total_input_genes,
            'background_gene_count': total_background_genes
        }

def kegg_enrichment(request):
    if request.method == 'GET':
        # 检查是否是分页请求
        if 'page' in request.GET:
            # 从session获取之前提交的基因列表
            gene_list = request.session.get('kegg_enrichment_gene_list', [])
            if not gene_list:
                return render(request, 'tools/kegg_enrichment/kegg_enrichment.html')
            
            try:
                kegg_analysis = KEGGEnrichment()
                result_data = kegg_analysis.perform_enrichment(gene_list)
                per_page = int(request.GET.get('per_page', 10))
                
                paginator = Paginator(result_data['results'], per_page)
                page_number = request.GET.get('page', 1)
                page_obj = paginator.get_page(page_number)
                
                # 生成图形
                plot_image = plot_kegg_enrichment(result_data['results'])
                
                context = {
                    'results': page_obj,
                    'input_gene_count': result_data['input_gene_count'],
                    'background_gene_count': result_data['background_gene_count'],
                    'per_page': per_page,
                    'gene_list': ', '.join(gene_list),
                    'plot_image': plot_image
                }
                return render(request, 'tools/kegg_enrichment/kegg_enrichment_result.html', context)
            except Exception as e:
                return render(request, 'tools/kegg_enrichment/kegg_enrichment.html', 
                            {'error': f'分页出错: {str(e)}'})
        return render(request, 'tools/kegg_enrichment/kegg_enrichment.html')
    
    elif request.method == 'POST':
        gene_list = request.POST.get('gene_list', '').strip().split()
        gene_list = [gene.strip().upper() for gene in gene_list if gene.strip()]
        
        if not gene_list:
            return render(request, 'tools/kegg_enrichment/kegg_enrichment.html', 
                         {'error': '请输入有效的基因列表'})
        
        # 保存基因列表到session
        request.session['kegg_enrichment_gene_list'] = gene_list
        
        try:
            kegg_analysis = KEGGEnrichment()
            result_data = kegg_analysis.perform_enrichment(gene_list)
            per_page = int(request.POST.get('per_page', 10))
            
            paginator = Paginator(result_data['results'], per_page)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            
            # 生成图形
            plot_image = plot_kegg_enrichment(result_data['results'])
            
            context = {
                'results': page_obj,
                'input_gene_count': result_data['input_gene_count'],
                'background_gene_count': result_data['background_gene_count'],
                'per_page': per_page,
                'gene_list': ', '.join(gene_list),
                'plot_image': plot_image
            }
            return render(request, 'tools/kegg_enrichment_result.html', context)
        except Exception as e:
            return render(request, 'tools/kegg_enrichment.html', 
                         {'error': f'分析出错: {str(e)}'})