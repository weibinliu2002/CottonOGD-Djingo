from django.core.paginator import Paginator
from django.shortcuts import render
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from scipy.stats import fisher_exact
from statsmodels.stats.multitest import multipletests
import math
import requests
import pickle
import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
from textwrap import wrap
import base64
from io import BytesIO

class GOEnrichment:
    _go_ontology_cache = None
    _last_cache_time = 0
    
    @classmethod
    def _load_go_ontology_from_db(cls):
        """从数据库加载GO类别信息"""
        ontology = {}
        start_time = time.time()
        
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT GO_ID, `Gene_Ontology` FROM eg_go_enrichment "
                "WHERE GO_ID IS NOT NULL AND GO_ID != '-' AND `Gene_Ontology` IS NOT NULL"
            )
            for go_id, go_type in cursor:
                for go in go_id.split(','):
                    go = go.strip()
                    if go:
                        if go_type.upper() == 'BIOLOGICAL_PROCESS':
                            ontology[go] = 'BP'
                        elif go_type.upper() == 'MOLECULAR_FUNCTION':
                            ontology[go] = 'MF'
                        elif go_type.upper() == 'CELLULAR_COMPONENT':
                            ontology[go] = 'CC'
                       
        
        print(f"从数据库加载GO类别完成，耗时: {time.time()-start_time:.2f}秒")
        return ontology

    @classmethod
    def get_go_ontology(cls):
        """获取GO本体数据（带缓存）"""
        if cls._go_ontology_cache is None or time.time() - cls._last_cache_time > 3600:
            cached = cache.get('go_ontology')
            if cached:
                cls._go_ontology_cache = pickle.loads(cached)
            else:
                cls._go_ontology_cache = cls._load_go_ontology_from_db()
                cache.set('go_ontology', pickle.dumps(cls._go_ontology_cache), timeout=86400)
            
            cls._last_cache_time = time.time()
        
        return cls._go_ontology_cache

    def __init__(self):
        self.go_ontology = self.get_go_ontology()

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

    def _generate_go_plot(self, results, category, max_terms=20):
        """生成GO富集分析结果的图表"""
        if not results:
            return None

        data = {
            'Description': [],
            'GeneRatio': [],
            'BgRatio': [],
            'pvalue': [],
            'p.adjust': [],
            'Count': []
        }
        
        for item in results[:max_terms]:
            data['Description'].append(item['description']['name'])
            data['GeneRatio'].append(item['gene_ratio'])
            data['BgRatio'].append(item['bg_ratio'])
            data['pvalue'].append(item['p_value'])
            data['p.adjust'].append(item.get('corrected_p_value', item['p_value']))
            data['Count'].append(len(item['genes'].split(',')))
        
        df = pd.DataFrame(data)
        
        if df.empty:
            return None

        fig = plt.figure(figsize=(20, 10))
        gs = GridSpec(1, 2, figure=fig, width_ratios=[1, 1.5])

        ax1 = fig.add_subplot(gs[0])
        colors = sns.color_palette("Reds_r", n_colors=len(df))
        # 修复palette警告：将y变量赋值给hue并设置legend=False
        sns.barplot(data=df, y='Description', x='Count', hue='Description', palette=colors, ax=ax1, legend=False)

        ax1.set_title(f'GO {category} - Count', pad=20, fontsize=14, fontweight='bold')
        ax1.set_ylabel('')
        ax1.set_xlabel('Gene Count', fontsize=12)
        ax1.tick_params(axis='y', labelsize=10)
        ax1.grid(axis='x', linestyle='--', alpha=0.7)

        y_labels = ['\n'.join(wrap(label, 40)) for label in df['Description']]
        # 修复set_ticklabels警告：先设置ticks再设置labels
        ax1.set_yticks(range(len(y_labels)))
        ax1.set_yticklabels(y_labels)

        ax2 = fig.add_subplot(gs[1])

        sizes = (df['Count'] / df['Count'].max() * 200 + 50)
        colors = -np.log10(df['p.adjust'])

        df['GeneRatio_val'] = df['GeneRatio'].apply(lambda x: eval(x.replace('/', '/')))
        
        scatter = ax2.scatter(
            x='GeneRatio_val', 
            y='Description', 
            s=sizes, 
            c=colors, 
            cmap='Reds_r', 
            data=df
        )

        ax2.set_title(f'GO {category} - Dotplot', pad=20, fontsize=14, fontweight='bold')
        ax2.set_ylabel('')
        ax2.set_xlabel('Gene Ratio', fontsize=12)
        ax2.tick_params(axis='y', labelsize=10)
        ax2.grid(axis='x', linestyle='--', alpha=0.7)
        # 修复set_ticklabels警告：先设置ticks再设置labels
        ax2.set_yticks(range(len(y_labels)))
        ax2.set_yticklabels(y_labels)

        cbar = plt.colorbar(scatter, ax=ax2, pad=0.01)
        cbar.set_label('-log10(p.adjust)', fontsize=10)

        plt.tight_layout()
        plt.subplots_adjust(wspace=0.3)

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return image_base64

    def perform_enrichment(self, gene_list):
        """优化后的富集分析主函数"""
        start_time = time.time()
        
        # 1. 查询输入基因的GO注释
        with connection.cursor() as cursor:
            # 使用更高效的IN查询，包含Description列
            cursor.execute(
                "SELECT Query, GO_ID, `Gene_Ontology`, Description FROM eg_go_enrichment "
                "WHERE Query IN %s AND GO_ID IS NOT NULL AND GO_ID != '-'",
                [tuple(gene_list)]
            )
            input_genes_go = cursor.fetchall()
            
            # 2. 获取背景统计信息
            cursor.execute("SELECT COUNT(*) FROM eg_go_enrichment")
            total_background_genes = cursor.fetchone()[0]
            
            # 3. 预计算背景GO频率和描述
            cursor.execute(
                "SELECT GO_ID, `Gene_Ontology`, Description FROM eg_go_enrichment "
                "WHERE GO_ID IS NOT NULL AND GO_ID != '-'"
            )
            background_counts = defaultdict(int)
            background_categories = {}
            background_descriptions = {}  # 存储GO术语的描述
            
            for go_id, go_type, description in cursor:
                for go in go_id.split(','):
                    go = go.strip()
                    if go:
                        background_counts[go] += 1
                        # 存储GO术语的类别
                        if go not in background_categories:
                            if go_type.upper() == 'BIOLOGICAL_PROCESS':
                                background_categories[go] = 'BP'
                            elif go_type.upper() == 'MOLECULAR_FUNCTION':
                                background_categories[go] = 'MF'
                            elif go_type.upper() == 'CELLULAR_COMPONENT':
                                background_categories[go] = 'CC'
                            else:
                                background_categories[go] = go_type
                        # 存储GO术语的描述
                        if go not in background_descriptions:
                            background_descriptions[go] = description
        
        # 4. 处理输入基因的GO项
        input_go_terms = defaultdict(list)
        input_genes = set()
        
        for gene, go_id, _, _ in input_genes_go:
            input_genes.add(gene)
            for go in go_id.split(','):
                go = go.strip()
                if go:
                    input_go_terms[go].append(gene)
        
        total_input_genes = len(input_genes)
        if total_input_genes == 0:
            return {
                'gene_list': gene_list,
                'results': {'MF': [], 'BP': [], 'CC': [], 'other': []},
                'input_gene_count': 0,
                'background_gene_count': total_background_genes
            }
        
        # 5. 并行计算富集结果
        enrichment_results = []
        for go_term, genes in input_go_terms.items():
            a = len(genes)
            b = total_input_genes - a
            c = background_counts.get(go_term, 0)
            d = total_background_genes - c
            
            if c == 0:
                continue
            
            metrics = self._calculate_enrichment(a, b, c, d)
            category = background_categories.get(go_term, 'other')
            
            enrichment_results.append({
                'go_id': go_term,
                'description': {
                    'name': background_descriptions.get(go_term, 'No description available'),
                    'definition': '' 
                },
                'gene_ratio': f"{a}/{total_input_genes}",
                'bg_ratio': f"{c}/{total_background_genes}",
                'rich_factor': a / c if c > 0 else 0,
                'fold_enrichment': metrics['fold_enrichment'],
                'z_score': metrics['z_score'],
                'p_value': metrics['p_value'],
                'genes': ', '.join(genes),
                'category': category
            })
        
        # 6. 多重检验校正
        if enrichment_results:
            p_values = [r['p_value'] for r in enrichment_results]
            _, corrected_p_values, _, _ = multipletests(p_values, method='fdr_bh')
            for i, p in enumerate(corrected_p_values):
                enrichment_results[i]['corrected_p_value'] = p
            
            # 按p值排序
            enrichment_results.sort(key=lambda x: x['p_value'])
        
        # 7. 按类别分类结果
        categorized_results = {
            'MF': [r for r in enrichment_results if r['category'] == 'MF'],
            'BP': [r for r in enrichment_results if r['category'] == 'BP'],
            'CC': [r for r in enrichment_results if r['category'] == 'CC'],
         
        }
        
        print(f"富集分析完成，总耗时: {time.time()-start_time:.2f}秒")
        return {
            'gene_list': gene_list,
            'results': categorized_results,
            'input_gene_count': total_input_genes,
            'background_gene_count': total_background_genes
        }

def go_enrichment(request):
    if request.method == 'GET':
        # 检查是否是分页请求
        if any(f"{cat}_page" in request.GET for cat in ['MF', 'BP', 'CC', 'other']):
            # 从session获取之前提交的基因列表
            gene_list = request.session.get('go_enrichment_gene_list', [])
            if not gene_list:
                return render(request, 'tools/go_enrichment/go_enrichment.html', {'error': '没有找到基因列表数据'})
            
            try:
                go_analysis = GOEnrichment()
                result_data = go_analysis.perform_enrichment(gene_list)
                per_page = int(request.GET.get('per_page', 5))
                
                paginated_results = {}
                plot_images = {} 
                
                for category, items in result_data['results'].items():
                    paginator = Paginator(items, per_page)
                    page_number = request.GET.get(f'{category}_page', 1)
                    paginated_results[category] = paginator.get_page(page_number)
                    
                    # 生成图表
                    plot_image = go_analysis._generate_go_plot(
                        items,
                        category='MF' if category == 'MF' else 
                                'BP' if category == 'BP' else 
                                'CC' if category == 'CC' else 'Other',
                        max_terms=20
                    )
                    if plot_image:
                        plot_images[category] = plot_image
                
                context = {
                    'results': paginated_results,
                    'input_gene_count': result_data['input_gene_count'],
                    'background_gene_count': result_data['background_gene_count'],
                    'per_page': per_page,
                    'gene_list': ', '.join(gene_list),
                    'plot_images': plot_images
                }
                return render(request, 'tools/go_enrichment/go_enrichment_result.html', context)
            except Exception as e:
                return render(request, 'tools/go_enrichment/go_enrichment.html', 
                            {'error': f'分页出错: {str(e)}'})
        
        # 普通GET请求，返回空表单
        return render(request, 'tools/go_enrichment/go_enrichment.html')
    
    elif request.method == 'POST':
        gene_list = request.POST.get('gene_list', '').strip().split()
        gene_list = [gene.strip().upper() for gene in gene_list if gene.strip()]
        
        if not gene_list:
            return render(request, 'tools/go_enrichment/go_enrichment.html', 
                         {'error': '请输入有效的基因列表'})
        
        # 保存基因列表到session
        request.session['go_enrichment_gene_list'] = gene_list
        
        try:
            go_analysis = GOEnrichment()
            result_data = go_analysis.perform_enrichment(gene_list)
            per_page = int(request.POST.get('per_page', 5))
            
            paginated_results = {}
            plot_images = {}
            
            for category, items in result_data['results'].items():
                paginator = Paginator(items, per_page)
                page_number = request.GET.get(f'{category}_page', 1)
                paginated_results[category] = paginator.get_page(page_number)
                
                # 生成图表
                plot_image = go_analysis._generate_go_plot(
                    items,
                    category='MF' if category == 'MF' else 
                            'BP' if category == 'BP' else 
                            'CC' if category == 'CC' else 'Other',
                    max_terms=20
                )
                if plot_image:
                    plot_images[category] = plot_image
            
            context = {
                'results': paginated_results,
                'input_gene_count': result_data['input_gene_count'],
                'background_gene_count': result_data['background_gene_count'],
                'per_page': per_page,
                'gene_list': ', '.join(gene_list),
                'plot_images': plot_images
            }
            return render(request, 'tools/go_enrichment/go_enrichment_result.html', context)
        except Exception as e:
            return render(request, 'tools/go_enrichment/go_enrichment.html', 
                         {'error': f'分析出错: {str(e)}'})
    

    return render(request, 'tools/go_enrichment/go_enrichment.html')