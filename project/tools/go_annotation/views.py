from django.shortcuts import render
from django.db import connection
from django.core.paginator import Paginator
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

def go_annotation(request):
    if request.method == 'POST':
        gene_input = request.POST.get('gene_id', '').strip()
        per_page = int(request.POST.get('per_page', 10))
        
        gene_list = [gene.strip() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        results = []
        if gene_list:
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

            request.session['annotation_results'] = results
            request.session['searched_ids'] = gene_input
            request.session['per_page'] = per_page
            request.session['chart'] = chart

            paginator = Paginator(results, per_page)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            
            return render(request, 'tools/go_annotation_result.html', {
                'page_obj': page_obj,
                'gene_list': gene_list,
                'searched_ids': gene_input,
                'per_page': per_page,
                'chart': chart
            })

    elif request.method == 'GET' and 'page' in request.GET:
        results = request.session.get('annotation_results', [])
        gene_input = request.session.get('searched_ids', '')
        per_page = request.session.get('per_page', 10)
        chart = request.session.get('chart', None)
        
        if not results:
            return render(request, 'tools/go_annotation.html')

        paginator = Paginator(results, per_page)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'tools/go_annotation_result.html', {
            'page_obj': page_obj,
            'gene_list': gene_input.split(),
            'searched_ids': gene_input,
            'per_page': per_page,
            'chart': chart
        })
    
    return render(request, 'tools/go_annotation.html')