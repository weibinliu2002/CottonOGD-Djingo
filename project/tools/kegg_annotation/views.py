from django.shortcuts import render
from django.db import connection
from django.core.paginator import Paginator
from collections import Counter

def kegg_annotation(request):
    if request.method == 'POST':
        gene_input = request.POST.get('gene_id', '').strip()
        per_page = int(request.POST.get('per_page', 10))
        
        gene_list = [gene.strip() for gene in gene_input.replace(',', '\n').split() if gene.strip()]
        
        results = []
        if gene_list:
            with connection.cursor() as cursor:
                for gene_id in gene_list:
                    cursor.execute("""
                        SELECT Chr, Start, End, ID 
                        FROM `eg_go_annotation` 
                        WHERE ID = %s
                    """, [gene_id])
                    annotation_data = cursor.fetchall()

                    cursor.execute("""
                        SELECT  Query, `match` ,Description
                        FROM `eg_kegg` 
                        WHERE Query = %s
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

            match_counts = Counter([result['match'] for result in results if result['match']])
            chart_data = {
                'labels': list(match_counts.keys()),
                'data': list(match_counts.values()),
            }

            request.session['annotation_results'] = results
            request.session['searched_ids'] = gene_input
            request.session['per_page'] = per_page
            request.session['chart_data'] = chart_data

            paginator = Paginator(results, per_page)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            
            return render(request, 'tools/kegg_annotation_result.html', {
                'page_obj': page_obj,
                'gene_list': gene_list,
                'searched_ids': gene_input,
                'per_page': per_page,
                'chart_data': chart_data,
            })
    
    elif request.method == 'GET' and 'page' in request.GET:
        results = request.session.get('annotation_results', [])
        gene_input = request.session.get('searched_ids', '')
        per_page = request.session.get('per_page', 10)
        chart_data = request.session.get('chart_data', {})
        
        if not results:
            return render(request, 'tools/kegg_annotation.html')
        
        paginator = Paginator(results, per_page)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'tools/kegg_annotation_result.html', {
            'page_obj': page_obj,
            'gene_list': gene_input.split(),
            'searched_ids': gene_input,
            'per_page': per_page,
            'chart_data': chart_data,
        })
    
    return render(request, 'tools/kegg_annotation.html')