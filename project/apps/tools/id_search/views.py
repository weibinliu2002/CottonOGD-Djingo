import re, os
from io import TextIOWrapper
from django.views import View
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
import pyfaidx

from Browse.Species.models import Species
from .models import gene_info, gene_seq, gene_annotation    # Genome_Assembly 未在本文件使用，可保留模型


# -------------------- 工具函数 --------------------
def normalize_gene_id(id_str: str) -> str:
    """去掉括号、引号、转录本后缀，只保留合法字符"""
    id_str = re.sub(r'[()\[\]"\'\s]', '', id_str.strip())
    id_str = re.sub(r'[^a-zA-Z0-9_:.-]', '', id_str)

    # 1. 去掉数字型版本号  .1  .2  ...
    id_str = re.sub(r'\.\d+$', '', id_str)
    # 2. 去掉转录本后缀    .t1  .T01  .txxx（大小写不敏感）
    id_str = re.sub(r'\.[tT]\d+$', '', id_str)

    if not re.match(r'^[a-zA-Z0-9_:.-]+$', id_str):
        id_str = f"ID_{id_str}"
    return id_str


def extract_seq_from_fasta(fasta: pyfaidx.Fasta, seqid: str, start: int, end: int, strand: str) -> str:
    """从 fasta 提取指定区间，负链自动反向互补"""
    seq = str(fasta[seqid][start:end])
    if strand == '-':
        comp = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 'N': 'N'}
        seq = ''.join([comp.get(b, b) for b in reversed(seq)])
    return seq


def build_jbrowse_url(seqid: str, start: int, end: int) -> str:
    """拼装 JBrowse 单基因视图地址"""
    genome_name = 'Ghirsutum_genome_HAU_v1.0'
    gff_name = 'TM-1.gff'
    loc = f"{seqid}:{max(0, start-1000)}-{end+1000}"
    return f"/static/jbrowse/index.html?config=config.json&assembly={genome_name}&loc={loc}&type=LinearGenomeView&tracks={gff_name}"


def parse_attributes(attributes_str):
    """解析GFF格式的attributes字符串，返回字典"""
    if not attributes_str:
        return {}
    
    result = {}
    # 分割多个属性
    attributes = attributes_str.split(';')
    for attr in attributes:
        if '=' in attr:
            key_value = attr.strip().split('=')
            if len(key_value) == 2:
                key, value = key_value
                result[key.strip()] = value.strip().strip('"')
    return result

def generate_gene_structure_data(gene_record):
    """生成基因结构图所需的数据
    
    Args:
        gene_record: gene_info模型记录或包含基因信息的字典
    
    Returns:
        dict: 包含基因结构信息的字典，适合前端可视化
    """
    # 基础位置信息
    gene_data = {
        'seqid': gene_record.get('seqid') or gene_record.seqid,
        'start': gene_record.get('start') or gene_record.start,
        'end': gene_record.get('end') or gene_record.end,
        'strand': gene_record.get('strand') or gene_record.strand,
        'gene_id': gene_record.get('IDs') or gene_record.IDs,
        'original_id': gene_record.get('original_id', ''),
        'exons': [],
        'introns': [],
        'cds_regions': []
    }
    
    # 解析attributes获取可能的结构信息
    attributes_str = gene_record.get('attributes') or getattr(gene_record, 'attributes', '')
    if attributes_str:
        attributes = parse_attributes(attributes_str)
        gene_data.update(attributes)
    
    # 注意：这里简化处理，实际项目中可能需要从更详细的注释数据中获取外显子/内含子信息
    # 以下是一个基本示例，真实情况下可能需要查询额外的数据库表或解析更复杂的数据
    
    # 如果没有详细的外显子信息，我们可以假设有一个完整的外显子（整个基因）
    gene_data['exons'].append({
        'start': gene_data['start'],
        'end': gene_data['end'],
        'phase': 0
    })
    
    return gene_data

def populate_sequence_data(gene_records, fasta: pyfaidx.Fasta,
                           upstream_length: int = 2000,
                           downstream_length: int = 2000,
                           original_id_mapping: dict = None):
    """
    给 gene_records (list[dict]) 填入 gene/mRNA/up/down/cds/protein 序列
    返回 enriched_results list[dict]
    """
    upstream_length = max(1, min(upstream_length, 10000))
    downstream_length = max(1, min(downstream_length, 10000))

    DNA_comp = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 'N': 'N'}
    DNA_to_RNA = {'A': 'A', 'T': 'U', 'G': 'G', 'C': 'C', 'N': 'N'}
    RNA_comp = {'A': 'U', 'U': 'A', 'G': 'C', 'C': 'G', 'N': 'N'}

    enriched_results = []
    for rec in gene_records:
        # 只处理gene类型的记录，提高处理效率
        if getattr(rec, 'type', '') != 'gene':
            continue
            
        normalized_id = normalize_gene_id(rec.IDs)
        original_id = original_id_mapping.get(normalized_id, rec.IDs) if original_id_mapping else rec.IDs
        gene_dict = {
            'IDs': rec.IDs,
            'original_id': original_id,
            'normalized_id': normalized_id,  # 添加规范化的ID
            'source': getattr(rec, 'source', ''),
            'seqid': getattr(rec, 'seqid', ''),
            'start': getattr(rec, 'start', ''),
            'end': getattr(rec, 'end', ''),
            'strand': getattr(rec, 'strand', ''),
            'type': getattr(rec, 'type', ''),
            'species': getattr(rec, 'species', ''),
            'gene_seq': '',
            'mrna_seq': '',
            'transcript_seq': '',
            'upstream_seq': '',
            'downstream_seq': '',
            'cds_seq': '未找到CDS序列',
            'protein_seq': '未找到蛋白序列',
            'mrna_transcripts': [],
            'mrna_count': 0,
        }
       
        enriched_results.append(gene_dict)

    # ---- gene / mRNA 序列 ----
    for gene in enriched_results:
        if gene['type'] != 'gene':
            continue
        seqid, start, end, strand = gene['seqid'], int(gene['start']) - 1, int(gene['end']), gene['strand']
        if seqid not in fasta:
            continue
        gene['gene_seq'] = extract_seq_from_fasta(fasta, seqid, start, end, strand)

        # mRNA 及上下游 - 处理mRNA ID后缀匹配
        gene_id_base = re.sub(r'\.[tT]?\d+$', '', gene['IDs'])  # 移除基因ID可能的后缀
        mrna_recs = []
        for r in gene_records:
            if r.type == 'mRNA':
                mrna_id_base = re.sub(r'\.[tT]?\d+$', '', r.IDs)  # 移除mRNA ID可能的后缀
                if mrna_id_base == gene_id_base:
                    mrna_recs.append(r)
        for mr in mrna_recs:
            m_start, m_end = int(mr.start) - 1, int(mr.end)
            up_s = max(0, m_start - upstream_length)
            up_e = m_start
            down_s = m_end
            down_e = min(len(fasta[seqid]), m_end + downstream_length)
            mrna_seq = extract_seq_from_fasta(fasta, seqid, m_start, m_end, strand)
            up_seq = extract_seq_from_fasta(fasta, seqid, up_s, up_e, strand)
            down_seq = extract_seq_from_fasta(fasta, seqid, down_s, down_e, strand)

            # T→U 转录本
            transcript_seq = ''.join([DNA_to_RNA.get(b, b) for b in mrna_seq])

            gene['mrna_seq'] = mrna_seq
            gene['transcript_seq'] = transcript_seq
            gene['upstream_seq'] = up_seq
            gene['downstream_seq'] = down_seq

    # ---- CDS / protein ----
    # 使用规范化的基因ID进行查询，确保能匹配到CDS和蛋白序列
    gene_ids = [normalize_gene_id(g['IDs']) for g in enriched_results]
    seq_entries = gene_seq.objects.filter(gene_id__in=gene_ids)
    seq_map = {}
    mrna_map = {}
    for s in seq_entries:
        if s.gene_id not in seq_map:
            seq_map[s.gene_id] = {'cds_seq': s.cds_seq or '', 'protein_seq': s.protein_seq or ''}
            mrna_map[s.gene_id] = []
        if s.mrna_id and s.mrna_seq:
            mrna_map[s.gene_id].append({
                'mrna_id': s.mrna_id, 'mrna_seq': s.mrna_seq,
                'cds_id': s.cds_id, 'cds_seq': s.cds_seq,
                'protein_id': s.protein_id, 'protein_seq': s.protein_seq
            })

    for g in enriched_results:
        gid = normalize_gene_id(g['IDs'])  # 使用规范化的ID进行映射
        if gid in seq_map:
            g['cds_seq'] = seq_map[gid]['cds_seq'] or '未找到CDS序列'
            g['protein_seq'] = seq_map[gid]['protein_seq'] or '未找到蛋白序列'
        if gid in mrna_map:
            g['mrna_transcripts'] = mrna_map[gid]
            g['mrna_count'] = len(mrna_map[gid])

    return enriched_results


# -------------------- 视图 --------------------
class IDSearchView(View):

    def get_genome_categories(self):
        categories = {}
        for sp in Species.objects.all():
            categories.setdefault(sp.name, []).append(sp.name)
        return categories

    def get(self, request):
        return render(request, 'tools/id_search/id_search.html',
                      {'genome_categories': self.get_genome_categories()})

    def post(self, request):
        def extract_ids(text):
            return re.findall(r'[a-zA-Z0-9_:.-]+', text)

        # 1. 收集输入ID
        raw_query = request.POST.get('query_ids', '').strip()
        query_ids = [q.strip() for q in re.split(r'[,;\n]', raw_query) if q.strip()]

        uploaded_file = request.FILES.get('gene_file')
        if uploaded_file:
            try:
                content = TextIOWrapper(uploaded_file.file, encoding='utf-8').read()
                query_ids.extend(extract_ids(content))
            except Exception as e:
                return render(request, 'tools/id_search/id_search_results.html',
                              {'error': f'文件解析错误: {str(e)}'})

        # 2. 规范化
        original_query_ids = [qid for qid in query_ids if qid.strip()]
        id_mapping = {normalize_gene_id(qid): qid for qid in original_query_ids}
        query_ids = list(set(id_mapping.values()))
        if not query_ids:
            return render(request, 'tools/id_search/id_search_results.html',
                          {'error': '没有提供有效的基因ID'})

        # 3. 数据库查询
        # 使用规范化的ID进行数据库查询，确保能匹配到所有相关记录
        normalized_ids = [normalize_gene_id(qid) for qid in query_ids]
        genes_info = gene_info.objects.filter(IDs__in=normalized_ids)   
        genes_annotation = gene_annotation.objects.filter(Gene_ID__in=normalized_ids)
        
        # 创建注释ID映射字典以便于快速查找
        annotation_dict = {}
        for annotation in genes_annotation:
            if annotation.Gene_ID not in annotation_dict:
                annotation_dict[annotation.Gene_ID] = []
            annotation_dict[annotation.Gene_ID].append(annotation)
        print(1)
        print(annotation_dict)
        print(2)
        if not genes_info:
            return render(request, 'tools/id_search/id_search_results.html',
                          {'error': '数据库未找到匹配记录'})

        # 4. 序列提取参数
        upstream_length = max(1, min(int(request.POST.get('upstream_length', 2000)), 10000))
        downstream_length = max(1, min(int(request.POST.get('downstream_length', 2000)), 10000))

        genome_path = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'genomes', 'Ghirsutum_genome_HAU_v1.0.fasta'))
        fasta = pyfaidx.Fasta(genome_path)

        # 5. 填充序列
        enriched_results = populate_sequence_data(genes_info, fasta, upstream_length, downstream_length, id_mapping)

        # 6. 路由分流
        if len(query_ids) == 1:
            gid = normalize_gene_id(query_ids[0])  # 使用规范化的ID进行重定向
            jbrowse_url = build_jbrowse_url(enriched_results[0]['seqid'],
                                            int(enriched_results[0]['start']),
                                            int(enriched_results[0]['end']))
            return HttpResponseRedirect(reverse('id_search:id_search_results') + f'?id={gid}&upstream_length={upstream_length}&downstream_length={downstream_length}')
        else:
            # 只筛选type为gene的记录用于summary界面展示
            gene_results = [result for result in enriched_results if result.get('type') == 'gene']
            # 检查是否有序列信息可用于展示
            has_sequences = any(
                result.get('gene_seq') or result.get('mrna_seq') or result.get('cds_seq') != '未找到CDS序列'
                for result in gene_results
            )
            return render(request, 'tools/id_search/id_search_summary.html',
                          {'results': gene_results,
                           'searched_ids': query_ids,
                           'has_sequences': has_sequences,
                           'annotation_dict': annotation_dict})


class IdSearchResults(View):
    """基因 ID 搜索：返回序列、JBrowse 链接及错误提示。"""

    # -------------------- 公开入口 --------------------
    def get(self, request):
        gene_id = self._extract_gene_id(request)
        if not gene_id:
            return self._error_response(request, '未提供基因ID或ID为空')

        up, down = self._extract_flank_lengths(request)
        # 使用规范化的ID进行数据库查询，但保留原始ID用于显示
        normalized_gene_id = normalize_gene_id(gene_id)
        genes_qs = gene_info.objects.filter(IDs=normalized_gene_id)
        if not genes_qs:
            return self._error_response(request, f'未找到ID为 {gene_id} 的基因信息', [gene_id])

        # 创建原始ID映射，确保显示用户输入的原始ID
        original_id_mapping = {normalized_gene_id: gene_id}
        enriched = self._enrich_with_sequence(genes_qs, up, down, original_id_mapping)
        gene_records = [g for g in enriched if g.get('type') == 'gene']
        if not gene_records:
            return self._error_response(request, f'未找到ID为 {gene_id} 的基因信息', [gene_id])
        
        # 为每个基因记录生成结构图数据
        for gene_record in gene_records:
            gene_record['structure_data'] = generate_gene_structure_data(gene_record)

        jbrowse_url = self._build_jbrowse_link(gene_records[0])
        has_seq = self._any_sequence_present(gene_records)

        # 准备上下文数据，添加基因结构图相关信息
        context = {
            'results': gene_records,
            'searched_ids': [gene_id],
            'jbrowse_url': jbrowse_url,
            'total_genes': len(gene_records),
            'has_sequences': has_seq,
        }
        
        return render(request, 'tools/id_search/id_search_results.html', context)

    # -------------------- 私有工具 --------------------
    @staticmethod
    def _extract_gene_id(request):
        """提取基因ID，返回原始ID"""
        return request.GET.get('id', '').strip()

    @staticmethod
    def _extract_flank_lengths(request):
        """返回规范化的上下游长度，默认 2000，范围 1-10000。"""
        def clamp(x, d=2000):
            return max(1, min(int(x or d), 10000))
        return clamp(request.GET.get('upstream_length')), \
               clamp(request.GET.get('downstream_length'))

    @staticmethod
    def _error_response(request, err_msg, searched_ids=None):
        """统一渲染“查不到/出错”页面。"""
        return render(request, 'tools/id_search/id_search_results.html', {
            'error': err_msg,
            'searched_ids': searched_ids or [],
            'jbrowse_url': '/static/jbrowse/index.html',
            'total_genes': 0,
            'has_sequences': False,
        })

    @staticmethod
    def _genome_fasta():
        """单例模式缓存 Fasta 对象，避免重复打开。"""
        if not hasattr(IdSearchResults, '_fasta'):
            path = os.path.abspath(
                os.path.join(settings.BASE_DIR, '..', 'genomes', 'Ghirsutum_genome_HAU_v1.0.fasta')
            )
            IdSearchResults._fasta = pyfaidx.Fasta(path)
        return IdSearchResults._fasta

    @classmethod
    def _enrich_with_sequence(cls, genes_qs, upstream, downstream, original_id_mapping=None):
        """把序列信息挂到每条记录上。"""
        fasta = cls._genome_fasta()
        return populate_sequence_data(genes_qs, fasta, upstream, downstream, original_id_mapping)

    @staticmethod
    def _build_jbrowse_link(rec):
        """根据第一条记录生成 JBrowse 定位链接。"""
        return build_jbrowse_url(rec['seqid'], int(rec['start']), int(rec['end']))

    @staticmethod
    def _any_sequence_present(records):
        """只要有一条记录含任意序列即返回 True。"""
        return any(
            g.get('gene_seq') or g.get('mrna_seq') or g.get('cds_seq') != '未找到CDS序列'
            for g in records
)
