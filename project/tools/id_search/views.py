import re
from io import TextIOWrapper
from django.views import View
from django.shortcuts import render
from django.db import connection
class IDSearchView(View):
    def get(self, request):
        return render(request, 'tools/id_search.html')
    def post(self, request):
        def extract_ids(text):
            return re.findall(r'[a-zA-Z0-9_:.-]+', text)
        
        query_ids = []
        
        # 1. 处理文本输入
        raw_query = request.POST.get('query_ids', '').strip()
        if raw_query:
            query_ids.extend([q.strip() for q in re.split(r'[,;\n]', raw_query) if q.strip()])
        
        # 2. 处理文件上传 - 统一作为文本处理
        uploaded_file = request.FILES.get('gene_file')
        if uploaded_file:
            try:
                content = TextIOWrapper(uploaded_file.file, encoding='utf-8').read()
                extracted_ids = extract_ids(content)
                query_ids.extend(extracted_ids)
            except Exception as e:
                return render(request, 'tools/id_search_results.html', {
                    'error': f'文件解析错误: {str(e)}'
                })
        
        # 去重并过滤空值
        query_ids = list(set([qid.strip() for qid in query_ids if qid.strip()]))
        
        if not query_ids:
            return render(request, 'tools/id_search_results.html', {
                'error': '没有提供有效的基因ID'
            })
        
        results = []
        found_ids = set()
        
        with connection.cursor() as cursor:
            # 1. 获取数据结构
            cursor.execute("SELECT * FROM orthogroups LIMIT 100")
            all_data = cursor.fetchall()
            db_columns = [desc[0] for desc in cursor.description]
            
            if not all_data:
                return render(request, 'tools/id_search_results.html', 
                           {'error': '数据库为空'})
            
            # 2. 第一行作为列名行
            display_column_names = all_data[0]
            
            # 3. 搜索逻辑
            found_in_same_cell = {}
            
            for row in all_data[1:]:
                row_data = dict(zip(db_columns, row))
                row_name = row_data[db_columns[0]]
                
                for col_index, col_name in enumerate(db_columns):
                    cell_value = str(row[col_index])
                    cell_ids = [id.strip() for id in cell_value.split(',') if id.strip()]
                    
                    # 查找当前单元格包含的查询ID
                    matched_ids = [qid for qid in query_ids if qid in cell_ids]
                    
                    if matched_ids:
                        # 记录同一单元格的多个ID
                        cell_key = f"{row_name}|{display_column_names[col_index]}"
                        found_in_same_cell[cell_key] = found_in_same_cell.get(cell_key, {
                            'row_name': row_name,
                            'column_name': str(display_column_names[col_index]),
                            'all_ids': cell_value,
                            'matched_ids': []
                        })
                        found_in_same_cell[cell_key]['matched_ids'].extend(matched_ids)
            
            # 4. 整理结果
            processed_ids = set()
            for cell_data in found_in_same_cell.values():
                if len(cell_data['matched_ids']) > 1:
                    # 多个ID在同一单元格
                    results.append({
                        'query_id': ", ".join(cell_data['matched_ids']),
                        'row_name': cell_data['row_name'],
                        'column_name': cell_data['column_name'],
                        'all_ids': cell_data['all_ids'],
                        'is_combined': True
                    })
                    processed_ids.update(cell_data['matched_ids'])
                else:
                    # 单个ID匹配
                    results.append({
                        'query_id': cell_data['matched_ids'][0],
                        'row_name': cell_data['row_name'],
                        'column_name': cell_data['column_name'],
                        'all_ids': cell_data['all_ids'],
                        'is_combined': False
                    })
                    processed_ids.add(cell_data['matched_ids'][0])
            
            # 5. 添加未找到的ID
            for qid in query_ids:
                if qid not in processed_ids:
                    results.append({
                        'query_id': qid,
                        'row_name': '未找到',
                        'column_name': '',
                        'all_ids': '',
                        'is_combined': False
                    })
        
        return render(request, 'tools/id_search_results.html', {
            'results': sorted(results, key=lambda x: x['query_id']),
            'searched_ids': query_ids
        })