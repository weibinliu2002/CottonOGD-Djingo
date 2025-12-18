from django.views import View
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import pandas as pd
from io import TextIOWrapper

# 导入模型
from .models import gene_info, gene_annotation

# 工具函数
def normalize_gene_id(id_str: str) -> str:
    """去掉括号、引号、转录本后缀，只保留合法字符"""
    import re
    id_str = re.sub(r'[()\[\]"\'\s]', '', id_str.strip())
    id_str = re.sub(r'[^a-zA-Z0-9_:.-]', '', id_str)

    # 1. 去掉数字型版本号  .1  .2  ...
    id_str = re.sub(r'\.\d+$', '', id_str)
    # 2. 去掉转录本后缀    .t1  .T01  .txxx（大小写不敏感）
    id_str = re.sub(r'\.[tT]\d+$', '', id_str)

    if not re.match(r'^[a-zA-Z0-9_:.-]+$', id_str):
        id_str = f"ID_{id_str}"
    return id_str

def build_jbrowse_url(seqid: str, start: int, end: int) -> str:
    """拼装 JBrowse 单基因视图地址（适合在iframe中嵌入）"""
    genome_name = 'Ghirsutum_genome_HAU_v1.0'
    gff_name = 'TM-1.gff'
    loc = f"{seqid}:{max(0, start-1000)}-{end+1000}"
    # 直接访问静态文件，确保JBrowse能正确加载配置
    return f"/assets/jbrowse/index.html?assembly={genome_name}&loc={loc}&tracks={gff_name}"

class IdSearchResults(View):
    """基因 ID 搜索：直接从数据库获取序列"""

    # -------------------- 公开入口 --------------------
    def get(self, request):
        annotation_dict = {}
        gene_id = self._extract_gene_id(request)
        if not gene_id:
            return self._error_response(request, '未提供基因ID或ID为空')

        up, down = self._extract_flank_lengths(request)

        # 查询数据库
        genes_qs = gene_info.objects.filter(IDs=gene_id)
        normalized_gene_id = normalize_gene_id(gene_id)

        if not genes_qs and normalized_gene_id != gene_id:
            genes_qs = gene_info.objects.filter(IDs=normalized_gene_id)

        if not genes_qs:
            return self._error_response(request, f'未找到ID为 {gene_id} 的基因信息', [gene_id])

        original_id_mapping = {normalized_gene_id: gene_id}
        enriched = self._enrich_with_sequence(genes_qs, up, down, original_id_mapping)
        # 不过滤type字段，直接使用所有结果
        gene_records = enriched

        if not gene_records:
            return self._error_response(request, f'未找到ID为 {gene_id} 的基因信息', [gene_id])

        jbrowse_url = IdSearchResults._build_jbrowse_link(gene_records[0])
        has_seq = IdSearchResults._any_sequence_present(gene_records)

        # 注释字典
        annotations = gene_annotation.objects.filter(Gene_ID=normalized_gene_id)
        for annotation in annotations:
            annotation_dict.setdefault('GO_annotation', []).append(annotation.GO_annotation)
            annotation_dict.setdefault('KEGG_annotation', []).append(annotation.KEGG_annotation)
            annotation_dict.setdefault('Swissprot_annotation', []).append(annotation.Swissprot_annotation)
            annotation_dict.setdefault('KOG_class_annotation', []).append(annotation.KOG_class_annotation)
            annotation_dict.setdefault('Pfam_annotation', []).append(annotation.Pfam_annotation)
            annotation_dict.setdefault('TrEMBL_annotation', []).append(annotation.TrEMBL_annotation)
            annotation_dict.setdefault('nr_annotation', []).append(annotation.nr_annotation)

        # 提取 mRNA 转录本
        mrna_transcripts = []
        for gene in genes_qs:
            if getattr(gene, 'type', '') == 'mRNA':
                transcript_id = getattr(gene, 'IDs', '')
                gene_seq = getattr(gene, 'gene_seq', {}) or {}
                mrna_transcripts.append({
                    'id': transcript_id,
                    'original_id': transcript_id,
                    'mrna_seq': gene_seq.get('mrna_seq'),
                    'cds_seq': gene_seq.get('cds_seq'),
                    'protein_seq': gene_seq.get('protein_seq'),
                    'upstream_seq': gene_seq.get('upstream_seq'),
                    'downstream_seq': gene_seq.get('downstream_seq'),
                    'cdna_seq': gene_seq.get('cdna_seq'),
                    'seqid': getattr(gene, 'seqid', ''),
                    'start': getattr(gene, 'start', 0),
                    'end': getattr(gene, 'end', 0),
                    'strand': getattr(gene, 'strand', '+'),
                })

        context = {
            'results': gene_records,
            'searched_ids': [gene_id],
            'jbrowse_url': jbrowse_url,
            'total_genes': len(gene_records),
            'has_sequences': has_seq,
            'annotation_dict': annotation_dict,
            'gene_records': genes_qs,
            'mrna_transcripts': mrna_transcripts
        }

        return render(request, 'tools/id_search/id_search_results.html', context)

    # -------------------- 私有工具 --------------------
    def _extract_gene_id(self, request):
        return request.GET.get('id', '').strip()

    def _extract_flank_lengths(self, request):
        def clamp(x, d=2000):
            return max(1, min(int(x or d), 10000))
        return clamp(request.GET.get('upstream_length')), \
               clamp(request.GET.get('downstream_length'))

    def _error_response(self, request, err_msg, searched_ids=None):
        return render(request, 'tools/id_search/id_search_results.html', {
            'error': err_msg,
            'searched_ids': searched_ids or [],
            'jbrowse_url': '/static/jbrowse/index.html',
            'total_genes': 0,
            'has_sequences': False,
        })

    def _enrich_with_sequence(self, genes_qs, upstream=None, downstream=None, original_id_mapping=None):
        """直接从数据库获取序列信息"""
        enriched_records = []
        
        # 批量获取所有基因ID
        gene_ids = [gene.IDs for gene in genes_qs]
        normalized_ids = [normalize_gene_id(gene_id) for gene_id in gene_ids]
        all_gene_ids = list(set(gene_ids + normalized_ids))
        
        # 批量查询序列信息，优化查询效率
        from .models import gene_seq, genome_seq
        
        # 预加载所有基因序列
        gene_seq_dict = {}
        for seq in gene_seq.objects.filter(gene_id__in=all_gene_ids):
            gene_seq_dict[seq.gene_id] = {
                'mrna_seq': seq.mrna_seq,
                'cds_seq': seq.cds_seq,
                'protein_seq': seq.protein_seq,
            }
        
        # 预加载所有基因组序列
        genome_seq_dict = {}
        for seq in genome_seq.objects.filter(gene_id__in=all_gene_ids):
            genome_seq_dict[seq.gene_id] = seq.seq
        
        for gene in genes_qs:
            gene_id = gene.IDs
            normalized_gid = normalize_gene_id(gene_id)
            
            record = {
                'IDs': gene_id,
                'original_id': original_id_mapping.get(normalized_gid, gene_id) if original_id_mapping else gene_id,
                'normalized_id': normalized_gid,
                'seqid': getattr(gene, 'seqid', ''),
                'start': getattr(gene, 'start', 0),
                'end': getattr(gene, 'end', 0),
                'strand': getattr(gene, 'strand', '+'),
                'type': getattr(gene, 'type', 'gene'),
                'attributes': getattr(gene, 'attributes', ''),
                'species': getattr(gene, 'species', ''),
                # 添加mrna_transcripts字段，用于full模式下的序列展示
                'mrna_transcripts': [],
            }
            
            # 获取基因序列信息
            seq_info = gene_seq_dict.get(gene_id, {})
            if not seq_info:
                seq_info = gene_seq_dict.get(normalized_gid, {})
            
            # 获取基因组序列
            genome_seq_val = genome_seq_dict.get(gene_id)
            if not genome_seq_val:
                genome_seq_val = genome_seq_dict.get(normalized_gid)
            
            # 构建序列信息
            gene_seq_info = {
                'gene_seq': genome_seq_val,
                'mrna_seq': seq_info.get('mrna_seq'),
                'cds_seq': seq_info.get('cds_seq', '未找到CDS序列'),
                'protein_seq': seq_info.get('protein_seq', '未找到蛋白序列'),
                'upstream_seq': '',
                'downstream_seq': '',
                'cdna_seq': '',
            }
            
            record.update(gene_seq_info)
            
            # 添加转录本信息到mrna_transcripts数组，用于full模式下的序列展示
            if seq_info or genome_seq_val:
                transcript = {
                    'id': gene_id,
                    'mrna_seq': seq_info.get('mrna_seq'),
                    'cds_seq': seq_info.get('cds_seq', '未找到CDS序列'),
                    'protein_seq': seq_info.get('protein_seq', '未找到蛋白序列'),
                    'upstream_seq': '',
                    'downstream_seq': '',
                    'cdna_seq': '',
                    'seqid': getattr(gene, 'seqid', ''),
                    'start': getattr(gene, 'start', 0),
                    'end': getattr(gene, 'end', 0),
                    'strand': getattr(gene, 'strand', '+'),
                }
                record['mrna_transcripts'].append(transcript)
            enriched_records.append(record)
        return enriched_records

    @staticmethod
    def _build_jbrowse_link(rec):
        return build_jbrowse_url(rec['seqid'], int(rec['start']), int(rec['end']))

    @staticmethod
    def _any_sequence_present(records):
        return any(
            g.get('gene_seq') or g.get('mrna_seq') or g.get('cds_seq') != '未找到CDS序列'
            for g in records
        )


# ============================================
# JSON API 接口
# ============================================
class IdSearchAPIView(View):
    """基因ID搜索 JSON API，直接从数据库获取序列"""

    def get(self, request):
        gene_id = request.GET.get('id', '').strip()
        action = request.GET.get('action', 'results')

        if not gene_id:
            return JsonResponse({'error': '未提供基因ID或ID为空', 'status': 'error'}, status=400)

        search_results_view = IdSearchResults()

        try:
            if action == 'summary':
                return self._handle_summary_request(request, gene_id, search_results_view)
            else:
                return self._handle_single_result_request(request, gene_id, search_results_view)
        except Exception as e:
            return JsonResponse({'error': f'处理请求时发生错误: {str(e)}', 'status': 'error'}, status=500)

    def _handle_single_result_request(self, request, gene_id, search_results_view):
        up, down = search_results_view._extract_flank_lengths(request)

        normalized_gene_id = normalize_gene_id(gene_id)
        
        # 使用Q对象进行高效查询，一次性获取所有匹配的基因
        from django.db.models import Q
        genes_qs = gene_info.objects.filter(
            Q(IDs=gene_id) | Q(IDs=normalized_gene_id)
        )
        
        if not genes_qs:
            return JsonResponse({'error': f'未找到ID为 {gene_id} 的基因信息', 'status': 'not_found', 'searched_id': gene_id}, status=404)

        original_id_mapping = {normalized_gene_id: gene_id}
        enriched = search_results_view._enrich_with_sequence(genes_qs, up, down, original_id_mapping)
        # 不过滤type字段，直接使用所有结果
        gene_records = enriched
        
        # 如果没有找到匹配的基因，返回原始ID的空结果
        if not gene_records:
            gene_records = [{
                'IDs': gene_id,
                'original_id': gene_id,
                'normalized_id': normalized_gene_id,
                'species': '未知',
                'type': 'gene',
                'seqid': '',
                'start': 0,
                'end': 0,
                'strand': '+',
                'attributes': '',
                'gene_seq': '',
                'mrna_seq': '',
                'cds_seq': '未找到CDS序列',
                'protein_seq': '未找到蛋白序列',
                'upstream_seq': '',
                'downstream_seq': '',
                'cdna_seq': '',
                'mrna_transcripts': []
            }]

        annotation_dict = {}
        annotations = gene_annotation.objects.filter(Gene_ID=normalized_gene_id)
        for annotation in annotations:
            annotation_dict.setdefault('GO_annotation', []).append(annotation.GO_annotation)
            annotation_dict.setdefault('KEGG_annotation', []).append(annotation.KEGG_annotation)
            annotation_dict.setdefault('Swissprot_annotation', []).append(annotation.Swissprot_annotation)
            annotation_dict.setdefault('KOG_class_annotation', []).append(annotation.KOG_class_annotation)
            annotation_dict.setdefault('Pfam_annotation', []).append(annotation.Pfam_annotation)
            annotation_dict.setdefault('TrEMBL_annotation', []).append(annotation.TrEMBL_annotation)
            annotation_dict.setdefault('nr_annotation', []).append(annotation.nr_annotation)

        jbrowse_url = IdSearchResults._build_jbrowse_link(gene_records[0])

        # GFF 数据
        gff_data = []
        for record in gene_records:
            gff_data.append({
                'seqid': record.get('seqid', ''),
                'source': record.get('source', 'OGD'),
                'type': record.get('type', 'gene'),
                'start': record.get('start', 0),
                'end': record.get('end', 0),
                'score': '.',
                'strand': record.get('strand', '.'),
                'phase': '.',
                'attributes': record.get('attributes', f'ID={record.get("IDs", "")}')
            })

        # 添加相关 feature
        gene = gene_records[0]
        related_features = gene_info.objects.filter(seqid=gene.get('seqid'), start__lte=gene.get('end'), end__gte=gene.get('start'))
        for feature in related_features:
            if feature.type == 'gene':
                continue
            gff_data.append({
                'seqid': feature.seqid,
                'source': feature.source,
                'type': feature.type,
                'start': feature.start,
                'end': feature.end,
                'score': '.',
                'strand': feature.strand,
                'phase': '.',
                'attributes': feature.attributes or f'ID={feature.IDs}'
            })

        # 检查是否有序列信息
        has_sequences = any(
            record.get('gene_seq') or 
            record.get('mrna_seq') or 
            (record.get('cds_seq') and record.get('cds_seq') != '未找到CDS序列') or
            (record.get('protein_seq') and record.get('protein_seq') != '未找到蛋白序列') 
            for record in gene_records
        )

        return JsonResponse({
            'status': 'success',
            'result': gene_records[0],
            'jbrowse_url': jbrowse_url,
            'annotations': annotation_dict,
            'searched_id': gene_id,
            'gff_data': gff_data,
            'has_sequences': has_sequences
        })

    def _handle_summary_request(self, request, gene_id, search_results_view):
        try:
            query_ids = [gid.strip() for gid in gene_id.split(',') if gid.strip()]
            if not query_ids:
                return JsonResponse({'error': '未提供有效的基因ID', 'status': 'error'}, status=400)

            # 批量处理，构建所有可能的基因ID列表
            all_gene_ids = []
            original_id_mapping = {}
            
            for gid in query_ids:
                normalized_gid = normalize_gene_id(gid)
                all_gene_ids.append(gid)
                all_gene_ids.append(normalized_gid)
                original_id_mapping[normalized_gid] = gid
            
            # 使用Q对象进行高效查询，一次性获取所有匹配的基因
            from django.db.models import Q
            
            # 构建查询条件
            query = Q()
            for gene_id_val in all_gene_ids:
                query |= Q(IDs=gene_id_val)
            
            # 一次性查询所有基因
            all_genes_qs = gene_info.objects.filter(query)
            
            # 构建基因查询集列表
            enriched_results = []
            
            # 调用_enrich_with_sequence处理所有基因，直接使用已创建的original_id_mapping
            enriched = search_results_view._enrich_with_sequence(all_genes_qs, 2000, 2000, original_id_mapping)
            enriched_results.extend(enriched)
            
            # 对结果进行去重处理，确保每个基因ID只出现一次
            seen_ids = set()
            unique_results = []
            
            for result in enriched_results:
                gene_id = result.get('IDs')
                if gene_id not in seen_ids:
                    seen_ids.add(gene_id)
                    unique_results.append(result)
            
            # 不过滤type字段，返回去重后的结果
            gene_results = unique_results
            
            # 如果没有找到匹配的基因，返回原始ID的空结果
            if not gene_results:
                for gid in query_ids:
                    if gid not in seen_ids:
                        seen_ids.add(gid)
                        gene_results.append({
                            'IDs': gid,
                            'original_id': gid,
                            'normalized_id': normalize_gene_id(gid),
                            'species': '未知',
                            'type': 'gene',
                            'seqid': '',
                            'start': 0,
                            'end': 0,
                            'strand': '+',
                            'attributes': '',
                            'gene_seq': '',
                            'mrna_seq': '',
                            'cds_seq': '未找到CDS序列',
                            'protein_seq': '未找到蛋白序列',
                            'upstream_seq': '',
                            'downstream_seq': '',
                            'cdna_seq': '',
                            'mrna_transcripts': []
                        })
            
            # 安全检查has_sequences
            has_sequences = False
            try:
                has_sequences = any(r.get('gene_seq') or r.get('mrna_seq') or 
                                 (r.get('cds_seq') and r.get('cds_seq') != '未找到CDS序列') for r in gene_results)
            except Exception as e:
                print(f"检查序列存在性时出错: {str(e)}")

            return JsonResponse({
                'status': 'success',
                'results': gene_results,
                'searched_ids': query_ids,
                'has_sequences': has_sequences,
                'total_genes': len(gene_results)
            })
        except Exception as e:
            print(f"处理摘要请求时出错: {str(e)}")
            return JsonResponse({'error': f'处理请求时发生错误: {str(e)}', 'status': 'error'}, status=500)


# ============================================
# 表单提交 API
# ============================================
@method_decorator(csrf_exempt, name='dispatch')
class IdSearchFormAPIView(View):
    """处理基因ID搜索表单提交的API"""

    def post(self, request):
        try:
            request_id = request.POST.get('request_id') or request.headers.get('X-Request-ID')
            gene_ids_text = request.POST.get('gene_ids', '')
            file = request.FILES.get('gene_file')

            query_ids = []

            if gene_ids_text.strip():
                query_ids.extend([line.strip() for line in gene_ids_text.split('\n') if line.strip()])

            if file:
                if file.name.endswith('.csv'):
                    df = pd.read_csv(TextIOWrapper(file, encoding='utf-8'))
                    query_ids.extend(df.iloc[:, 0].astype(str).tolist())
                else:
                    content = file.read().decode('utf-8')
                    query_ids.extend([line.strip() for line in content.split('\n') if line.strip()])

            query_ids = list(set([gid for gid in query_ids if gid]))
            if not query_ids:
                response_data = {'error': '未提供有效的基因ID', 'status': 'error'}
                if request_id:
                    response_data['request_id'] = request_id
                return JsonResponse(response_data, status=400)

            response_data = {
                'status': 'success',
                'query_ids': query_ids,
                'message': f'成功解析{len(query_ids)}个基因ID',
                'request_id': request_id
            }
            return JsonResponse(response_data)

        except Exception as e:
            response_data = {'error': f'处理请求时发生错误: {str(e)}', 'status': 'error'}
            request_id = request.POST.get('request_id') or request.headers.get('X-Request-ID')
            if request_id:
                response_data['request_id'] = request_id
            return JsonResponse(response_data, status=500)
