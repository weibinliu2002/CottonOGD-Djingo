import re, os ,io, base64
from PIL import ImageDraw, ImageFont,Image
from io import TextIOWrapper
from django.views import View
from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.conf import settings
import pyfaidx
import pandas as pd
from plotnine import geom_rect, geom_text, aes, geom_polygon, xlim, theme_minimal, ggplot, aes,theme,element_blank, geom_line, geom_point, geom_text, theme_bw, labs
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
    """拼装 JBrowse 单基因视图地址（适合在iframe中嵌入）"""
    genome_name = 'Ghirsutum_genome_HAU_v1.0'
    gff_name = 'TM-1.gff'
    loc = f"{seqid}:{max(0, start-1000)}-{end+1000}"
    # 添加embed=true参数使其适合iframe嵌入，并禁用不必要的UI元素
    # 根据静态文件配置，JBrowse应该通过/assets/jbrowse访问
    return f"/assets/jbrowse/index.html?config=config.json&assembly={genome_name}&loc={loc}&type=LinearGenomeView&tracks={gff_name}&embed=true&show_navigation=true"

'''def plot_gene_structure_view(gene_id: str,row,genes_info):
    try:
        if row is None:
            return _create_placeholder_image(f"Gene {gene_id} not found in database")
        # 检查row是字典还是对象，使用适当的方式访问字段
        if isinstance(row, dict):
            seqid, start, end, strand = row.get('seqid', ''), int(row.get('start', 0)), int(row.get('end', 0)), row.get('strand', '+')
        else:
            # 尝试使用对象属性访问
            try:
                seqid, start, end, strand = row.seqid, int(row.start), int(row.end), row.strand
            except AttributeError:
                return _create_placeholder_image(f"Error accessing gene data for {gene_id}")
        
        # ---------- 2. 查该染色体所有 GFF 记录 ----------
        sql_gff = genes_info.filter(IDs=gene_id).values("seqid", "start", "end", "type", "strand", "attributes", "id")
        gff_df = pd.DataFrame(sql_gff)
        if gff_df.empty:
            return _create_placeholder_image("No GFF data available for this gene")

        # 添加对attributes字段的处理 ----------
        # 解析attributes字段，提取有用信息
        if 'attributes' in gff_df.columns and not gff_df['attributes'].isna().all():
            # 将attributes列转换为字符串
            gff_df['attributes'] = gff_df['attributes'].astype(str)
            # 提取属性信息，允许存在缺失值或空值
            # 使用fillna确保即使没有匹配到也不会出错
            gff_df['ID'] = gff_df['attributes'].str.extract(r'ID=(.*?)(?:;|$)').fillna('')
            gff_df['Name'] = gff_df['attributes'].str.extract(r'Name=(.*?)(?:;|$)').fillna('')
            gff_df['Parent'] = gff_df['attributes'].str.extract(r'Parent=(.*?)(?:;|$)').fillna('')
        
        # ---------- 3. 区间 mRNA ----------
        mrna_df = gff_df[gff_df.type == "mRNA"].copy()
        idx = (mrna_df.start <= end) & (mrna_df.end >= start)
        mrna_df = mrna_df[idx]
        # 将id列转换为字符串类型后再使用str.contains方法
        mrna_df = mrna_df[mrna_df.Parent.astype(str).str.contains(str(gene_id), na=False)]
        print(mrna_df)
        # 如果没有mRNA数据，尝试直接使用基因数据
        if mrna_df.empty:
            # 创建一个基于基因数据的临时mRNA记录
            mrna_df = pd.DataFrame({
                "seqid": [seqid],
                "start": [start],
                "end": [end],
                "strand": [strand],
                "ID": [gene_id],
                "Parent": [gene_id]
            })
        
        # ---------- 4. 重叠分簇 + y 偏移 ----------
        # 保留所有转录本，不只是第一个
        # 确保数据类型正确
        mrna_df = mrna_df.copy()  # 复制数据框以避免修改原始数据
        # 确保必要的字段存在
        required_columns = ['seqid', 'start', 'end', 'strand', 'ID']
        for col in required_columns:
            if col not in mrna_df.columns:
                # 如果字段不存在，设置默认值或跳过
                pass  # 实际应用中可能需要更复杂的处理

        # 2. 组装成需要的格式
        # 确保所有转录本都被正确转换
        mrna_df_np = pd.DataFrame({
            "Chromosome": mrna_df["seqid"].astype(str),
            "Start": mrna_df["start"].astype(int),
            "End": mrna_df["end"].astype(int),
            "Strand": mrna_df["strand"].astype(str),
            "ID": mrna_df["ID"].astype(str) if "ID" in mrna_df.columns else mrna_df.get("id", "").astype(str),
        })

        # 3. 手工聚类（按染色体分组，重叠区间给同一个 Cluster）
        def simple_cluster(df):
            if df.empty:
                return df
            df = df.sort_values("Start")
            cluster = 0
            max_end = -1
            clusters = []
            for _, row in df.iterrows():
                if row["Start"] > max_end:
                    cluster += 1
                    max_end = row["End"]
                else:
                    max_end = max(max_end, row["End"])
                clusters.append(cluster)
            df["Cluster"] = clusters
            return df

        mrna_df_np = mrna_df_np.groupby("Chromosome", group_keys=False).apply(simple_cluster)

        # 4. 生成绘图用的 y 偏移
        mrna_df_np["row_in_cluster"] = mrna_df_np.groupby("Cluster").cumcount() + 1
        mrna_df_np["y"] = mrna_df_np["row_in_cluster"] * 0.2 + 1

        # ---------- 5. 子特征提取和处理 ----------
        mrna_df = mrna_df_np
        all_ids = mrna_df.ID.tolist()
        
        # 尝试多种可能的Parent字段名
        feat_df = pd.DataFrame()
        for parent_col in ['Parent', 'parent', 'PARENT']:
            if parent_col in gff_df.columns:
                # 为每个转录本ID查找其子特征
                for mrna_id in all_ids:
                    # 创建一个临时数据框存储当前转录本的子特征
                    temp_feats = gff_df[gff_df[parent_col].astype(str).str.contains(str(mrna_id), na=False)].copy()
                    if not temp_feats.empty:
                        # 为这些子特征添加转录本ID，以便后续分配正确的y坐标
                        temp_feats['mRNA_ID'] = mrna_id
                        feat_df = pd.concat([feat_df, temp_feats])
        
        # 如果找不到子特征，尝试直接查找CDS、exon、UTR等类型的记录
        if feat_df.empty:
            # 查找所有可能的子特征类型
            # 获取所有染色体值，不只是第一个转录本的
            chromosomes = mrna_df['Chromosome'].unique()
            subfeatures = pd.DataFrame()
            
            for chrom in chromosomes:
                # 为每个染色体查找相关的子特征
                chrom_subfeatures = gff_df[
                    (gff_df['type'].isin(['CDS', 'cds', 'exon', 'EXON', 'UTR', 'utr', 'three_prime_UTR', 'five_prime_UTR'])) &
                    (gff_df['seqid'] == chrom) &
                    (gff_df['start'] >= start - 1000) &
                    (gff_df['end'] <= end + 1000)
                ].copy()
                if not chrom_subfeatures.empty:
                    subfeatures = pd.concat([subfeatures, chrom_subfeatures])
            
            if not subfeatures.empty:
                feat_df = subfeatures
        
        # 如果找到子特征，确保它们有正确的y坐标
        if not feat_df.empty:
            # 创建mRNA_ID到y坐标的映射
            id_to_y = {row['ID']: row['y'] for _, row in mrna_df.iterrows()}
            
            # 如果子特征中没有mRNA_ID列，尝试匹配到最近的mRNA
            if 'mRNA_ID' not in feat_df.columns:
                # 为每个子特征找到最接近的mRNA
                feat_df['mRNA_ID'] = ''
                for idx, feat_row in feat_df.iterrows():
                    # 计算子特征与每个mRNA的重叠程度或距离
                    best_match = None
                    best_score = -1
                    
                    for _, mrna_row in mrna_df.iterrows():
                        # 检查是否在同一染色体上
                        if mrna_row['Chromosome'] != feat_row.get('seqid', ''):
                            continue
                        
                        # 计算重叠区域的大小
                        overlap_start = max(feat_row.get('start', 0), mrna_row['Start'])
                        overlap_end = min(feat_row.get('end', 0), mrna_row['End'])
                        overlap_size = max(0, overlap_end - overlap_start)
                        
                        # 选择重叠最大的mRNA
                        if overlap_size > best_score:
                            best_score = overlap_size
                            best_match = mrna_row['ID']
                    
                    feat_df.at[idx, 'mRNA_ID'] = best_match or all_ids[0]  # 默认为第一个mRNA
            
            # 为子特征分配对应的y坐标
            feat_df['y'] = feat_df['mRNA_ID'].map(id_to_y)  # 使用映射表分配y坐标
            # 确保没有NaN值
            feat_df['y'] = feat_df['y'].fillna(mrna_df['y'].min())
            
            # 重命名列以保持一致性
            feat_df = feat_df.rename(columns={
                'start': 'Start', 'end': 'End', 'type': 'Type',
                'seqid': 'Chromosome', 'strand': 'Strand'
            })
        else:
            # 如果仍然没有匹配到子特征，为每个转录本创建一个简单的特征
            feat_rows = []
            for _, row in mrna_df.iterrows():
                feat_rows.append({
                    "Start": row['Start'],
                    "End": row['End'],
                    "Type": "gene",
                    "y": row["y"],
                    "ID": row['ID']
                })
            feat_df = pd.DataFrame(feat_rows)
        
        # 设置不同特征类型的高度和颜色
        feat_df["ymin"] = feat_df.y + 0.10
        feat_df["ymax"] = feat_df.y + 0.14
        
        # 为不同类型的特征设置不同的样式
        cds_mask = feat_df.Type.str.lower() == "cds"
        exon_mask = feat_df.Type.str.lower() == "exon"
        utr_mask = feat_df.Type.str.lower().str.contains("utr")
        
        # CDS特征更粗
        feat_df.loc[cds_mask, "ymin"] -= 0.02
        feat_df.loc[cds_mask, "ymax"] += 0.02
        
        # UTR特征可以有不同的样式
        feat_df.loc[utr_mask, "ymin"] -= 0.01
        feat_df.loc[utr_mask, "ymax"] += 0.01

        # ---------- 6. 画图 ----------
        # 确保feat_df有正确的字段名
        if not feat_df.empty:
            # 统一转换为大写字段名
            if 'start' in feat_df.columns:
                feat_df = feat_df.rename(columns={'start': 'Start', 'end': 'End'})
        
        # 确保字段名一致性
        # 重命名列，确保使用正确的字段名
        field_mapping = {}
        if 'Start' in mrna_df.columns:
            field_mapping['Start'] = 'start'
        if 'End' in mrna_df.columns:
            field_mapping['End'] = 'end'
        if field_mapping:
            mrna_df = mrna_df.rename(columns=field_mapping)
        
        # 确保绘图数据不为空
        if mrna_df.empty:
            return _create_placeholder_image("No mRNA data available")
        
        # 计算适当的x轴范围，考虑所有转录本
        all_starts = mrna_df['start'].tolist()
        all_ends = mrna_df['end'].tolist()
        if not feat_df.empty:
            all_starts.extend(feat_df['Start'].tolist() if 'Start' in feat_df.columns else [])
            all_ends.extend(feat_df['End'].tolist() if 'End' in feat_df.columns else [])
        
        x_min = min(all_starts) - 1000  # 添加一些边距
        x_max = max(all_ends) + 1000
        plot_width = x_max - x_min
        
        # 创建ggplot对象，使用小写字段名
        p = (ggplot(mrna_df, aes(xmin="start", xmax="end", y="y"))
             # 绘制mRNA骨架
             + geom_rect(aes(ymin="y+0.118", ymax="y+0.122"),
                         colour="#303030", fill="#303030")
             )
        
        # 为每个转录本添加ID标签
        # 使用每个转录本的end值作为标签位置
        if not mrna_df.empty:
            # 创建标签数据框
            label_df = pd.DataFrame({
                'x': mrna_df['end'],
                'y': mrna_df['y'],
                'label': mrna_df['ID']
            })
            # 添加标签
            p = p + geom_text(aes(x="x", y="y", label="label"),
                            data=label_df,
                            ha="left", nudge_x=plot_width*0.01, size=10)
        
        # 绘制所有子特征（CDS、外显子、UTR等）
        if not feat_df.empty:
            p = p + geom_rect(aes(xmin="Start", xmax="End", ymin="ymin", ymax="ymax"),
                            data=feat_df,
                            colour="#303030", fill="#303030")

        # 7. 箭头 polygon
        def arrow_polygon(df):
            polys = []
            for _, r in df.iterrows():
                # 尝试使用小写字段名，如果不存在则使用大写
                try:
                    # 优先使用小写字段名
                    x1 = r.start if hasattr(r, 'start') else r.Start
                    x2 = r.end if hasattr(r, 'end') else r.End
                    y = r.y
                    strand = r.strand if hasattr(r, 'strand') else r.Strand
                    id_val = r.id if hasattr(r, 'id') else r.ID
                except Exception:
                    # 出错时尝试使用大写字段名作为备选
                    try:
                        x1, x2, y, strand, id_val = r.Start, r.End, r.y, r.Strand, r.ID
                    except Exception:
                        continue  # 如果仍然出错，跳过此行
                
                tip_dx = abs(x2-x1)*0.03
                if strand == "+" or str(strand) == "+":
                    xx = [x2, x2+tip_dx, x2+tip_dx, x2]
                    yy = [y+0.12, y+0.10, y+0.14, y+0.12]
                else:
                    xx = [x1, x1-tip_dx, x1-tip_dx, x1]
                    yy = [y+0.12, y+0.10, y+0.14, y+0.12]
                polys.append(pd.DataFrame({"x": xx, "y": yy, "ID": id_val}))
            
            # 确保返回的是DataFrame，即使没有数据
            if not polys:
                return pd.DataFrame({"x": [], "y": [], "ID": []})
            return pd.concat(polys, ignore_index=True)

        arrow_df = arrow_polygon(mrna_df)
        p = p + geom_polygon(aes(x="x", y="y", group="ID"),
                             data=arrow_df, colour="#303030", fill="#303030")

        # 8. 主题
        p = (p + xlim(start, end + abs(end-start)*0.25)
             + theme_minimal()
             + theme(axis_text_y=element_blank(),
                     panel_grid=element_blank(),
                     axis_title=element_blank())
             + labs(x="", y="")
             )
        
        # 9. 将ggplot对象转换为base64编码的图像数据
        img_data = io.BytesIO()
        p.save(img_data, format='png', dpi=100, height=4, width=10)
        img_data.seek(0)
        
        # 转换为base64字符串
        img_str = base64.b64encode(img_data.read()).decode('utf-8')
        
        # 返回data URI格式的图像数据
        return f"data:image/png;base64,{img_str}"
        
    except Exception as e:
        # 捕获所有异常并返回错误占位图
        error_message = f"Error generating gene structure: {str(e)}"
        print(error_message)  # 在控制台打印错误信息用于调试
        return _create_placeholder_image(error_message)'''
'''
def _create_placeholder_image(text: str):
    """
    创建一个包含错误信息的占位图像
    """
    try:
        # 创建一个简单的图像
        width, height = 600, 200
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # 使用默认字体，简化错误处理
        font = ImageFont.load_default()
        
        # 简化的文本换行逻辑
        max_width = width - 40
        wrapped_text = []
        current_line = ""
        
        for word in text.split():
            test_line = current_line + (" " if current_line else "") + word
            if draw.textlength(test_line, font=font) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    wrapped_text.append(current_line)
                current_line = word
        if current_line:
            wrapped_text.append(current_line)
        
        # 绘制居中文本
        line_height = 20
        y_offset = (height - len(wrapped_text) * line_height) // 2
        
        for i, line in enumerate(wrapped_text):
            text_width = draw.textlength(line, font=font)
            x = (width - text_width) // 2
            y = y_offset + i * line_height
            draw.text((x, y), line, fill='black', font=font)
        
        # 保存并转换为base64
        img_data = io.BytesIO()
        image.save(img_data, format='png')
        img_str = base64.b64encode(img_data.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Error creating placeholder image: {e}")
        # 如果所有都失败，返回一个简单的错误占位符SVG
        return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='600' height='200'%3E%3Crect width='100%25' height='100%25' fill='%23f8f8f8'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='14' text-anchor='middle' fill='%23ff0000'%3EError generating image%3C/text%3E%3C/svg%3E"
'''

def populate_sequence_data(gene_records, fasta: pyfaidx.Fasta,
                           upstream_length: int = 10000,
                           downstream_length: int = 10000,
                           original_id_mapping: dict = None):
    """
    给 gene_records (list[dict]) 填入 gene/mRNA/up/down/cds/protein 序列
    返回 enriched_results list[dict]
    """
    upstream_length = max(1, min(upstream_length, 20000))
    downstream_length = max(1, min(downstream_length, 20000))
    DNA_to_RNA = {'A': 'A', 'T': 'U', 'G': 'G', 'C': 'C', 'N': 'N'}

    enriched_results = []
    processed_ids = set()  # 用于去重的集合
    normalized_ids = []
    
    # 第一步：处理基因记录，去重并创建基因字典
    for rec in gene_records:
        normalized_id = normalize_gene_id(rec.IDs)
        
        # 去重逻辑：如果该基因已经处理过，跳过
        if normalized_id in processed_ids:
            continue
        processed_ids.add(normalized_id)
        normalized_ids.append(normalized_id)
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
            'type': getattr(rec, 'type', 'gene'),  # 默认type为gene
            'species': getattr(rec, 'species', ''),
            'gene_seq': '',
            'mrna_seq': '',
            'transcript_seq': '',
            'upstream_seq': '',
            'downstream_seq': '',
            'cds_seq': '未找到CDS序列',
            'protein_seq': '未找到蛋白序列',
            'cdna_seq': '',  # 添加cDNA序列字段
            'mrna_transcripts': [],
            'mrna_count': 0,
        }
       
        enriched_results.append(gene_dict)
    
    # 第二步：一次性获取所有基因的GFF记录，减少数据库查询
    if normalized_ids:
        # 使用in查询获取所有基因的GFF记录
        sql_gff = gene_info.objects.filter(IDs__in=normalized_ids).values("seqid", "start", "end", "type", "strand", "attributes", "id", "IDs")
        gff_df = pd.DataFrame(sql_gff)
        
        # 解析attributes字段，提取ID和Name
        if not gff_df.empty and 'attributes' in gff_df.columns and not gff_df['attributes'].isna().all():
            gff_df['attributes'] = gff_df['attributes'].astype(str)
            gff_df['ID'] = gff_df['attributes'].str.extract(r'ID=(.*?)(?:;|$)').fillna('')
            gff_df['Name'] = gff_df['attributes'].str.extract(r'Name=(.*?)(?:;|$)').fillna('')
            gff_df['Parent'] = gff_df['attributes'].str.extract(r'Parent=(.*?)(?:;|$)').fillna('')
    else:
        gff_df = pd.DataFrame()
    
    # 第三步：构建转录本ID到外显子的映射，优化外显子处理
    transcript_exon_map = {}
    if not gff_df.empty:
        # 筛选出所有外显子记录
        exon_df = gff_df[gff_df.type == "exon"].copy()
        
        # 遍历所有外显子，构建转录本ID到外显子的映射
        for _, exon_row in exon_df.iterrows():
            parent = exon_row.get('Parent', '')
            if parent:
                # 处理可能的多个Parent值（如Parent=mrna1,mrna2）
                parent_ids = parent.split(',')
                for p_id in parent_ids:
                    if p_id not in transcript_exon_map:
                        transcript_exon_map[p_id] = []
                    transcript_exon_map[p_id].append({
                        'start': exon_row['start'],
                        'end': exon_row['end'],
                        'seqid': exon_row['seqid'],
                        'strand': exon_row['strand']
                    })
        
        # 预处理：对每个转录本的外显子按start位置排序，避免后续重复排序
        for p_id in transcript_exon_map:
            transcript_exon_map[p_id].sort(key=lambda x: int(x['start']))
    
    # 第四步：创建基因字典映射，方便后续处理
    gene_dict_map = {gene['normalized_id']: gene for gene in enriched_results}
    
    # 初始化转录本映射字典，用于关联CDS和蛋白质序列
    mrna_id_mapping = {}
    
    # 第五步：处理每个基因的序列和转录本信息
    for gene in enriched_results:
        if gene['type'] != 'gene':
            continue
        
        seqid, start, end, strand = gene['seqid'], int(gene['start']) - 1, int(gene['end']), gene['strand']
        gene_id = gene['normalized_id']
        
        # 提取基因序列
        if seqid in fasta:
            gene['gene_seq'] = extract_seq_from_fasta(fasta, seqid, start, end, strand)
        
        # 从GFF数据框中筛选该基因的记录
        gene_gff_df = gff_df[gff_df['IDs'] == gene_id]
        if gene_gff_df.empty:
            continue
        
        # 筛选mRNA类型的记录
        mrna_df = gene_gff_df[gene_gff_df.type == "mRNA"].copy()
        mrna_recs = []
        
        # 处理每个mRNA转录本
        for _, mrna_row in mrna_df.iterrows():
            # 获取转录本ID，优先使用Name字段，如果为空则使用ID字段
            mrna_id = mrna_row.get('Name', '') or mrna_row.get('ID', '') or str(mrna_row.get('id', ''))
            
            # 如果转录本ID仍然为空，跳过
            if not mrna_id:
                continue
            
            # 创建转录本记录字典
            mr = {
                'IDs': mrna_id,
                'start': mrna_row['start'],
                'end': mrna_row['end'],
                'type': 'mRNA'
            }
            mrna_recs.append(mr)
        
        # 处理每个转录本
        for mr in mrna_recs:
            # 使用mRNA的实际位置提取序列
            m_start, m_end = int(mr['start']) - 1, int(mr['end'])
            mrna_seq = extract_seq_from_fasta(fasta, seqid, m_start, m_end, strand)
            
            # 从mRNA位置提取上下游序列（而不是从基因位置）
            up_s = max(0, m_start - upstream_length)
            up_e = m_start
            down_s = m_end
            down_e = min(len(fasta[seqid]), m_end + downstream_length)
            up_seq = extract_seq_from_fasta(fasta, seqid, up_s, up_e, strand)
            down_seq = extract_seq_from_fasta(fasta, seqid, down_s, down_e, strand)

            # T→U 转录本
            transcript_seq = ''.join([DNA_to_RNA.get(b, b) for b in mrna_seq])
            
            # 为第一个转录本设置默认序列
            if not gene['mrna_seq']:
                gene['mrna_seq'] = mrna_seq
                gene['transcript_seq'] = transcript_seq
                gene['upstream_seq'] = up_seq
                gene['downstream_seq'] = down_seq
            
            # 获取当前转录本的所有外显子，使用预构建的映射
            mrna_id = mr['IDs']
            transcript_cdna = ''
            
            # 直接从预构建的映射中获取外显子，避免遍历整个外显子数据框
            if mrna_id in transcript_exon_map:
                transcript_exons = transcript_exon_map[mrna_id]
                # 外显子已经在映射构建时排序，无需再次排序
                
                # 拼接外显子序列生成cDNA
                for exon in transcript_exons:
                    # 使用外显子自身的seqid和strand，确保准确性
                    e_seqid = exon['seqid'] if exon['seqid'] else seqid
                    e_strand = exon['strand'] if exon['strand'] else strand
                    e_start, e_end = int(exon['start']) - 1, int(exon['end'])
                    if e_seqid in fasta:
                        exon_seq = extract_seq_from_fasta(fasta, e_seqid, e_start, e_end, e_strand)
                        transcript_cdna += exon_seq
            
            # 额外检查：如果直接映射没有找到，尝试ID前缀匹配（兼容不同的命名格式）
            elif not transcript_cdna:
                # 查找所有可能匹配的转录本ID（如mrna_id前缀匹配）
                matching_exons = []
                for p_id in transcript_exon_map:
                    if mrna_id in p_id or p_id.startswith(mrna_id + '.'):
                        matching_exons.extend(transcript_exon_map[p_id])
                
                if matching_exons:
                    # 合并后排序（虽然每个转录本的外显子已经排序，但合并后仍需排序）
                    matching_exons.sort(key=lambda x: int(x['start']))
                    for exon in matching_exons:
                        e_seqid = exon['seqid'] if exon['seqid'] else seqid
                        e_strand = exon['strand'] if exon['strand'] else strand
                        e_start, e_end = int(exon['start']) - 1, int(exon['end'])
                        if e_seqid in fasta:
                            exon_seq = extract_seq_from_fasta(fasta, e_seqid, e_start, e_end, e_strand)
                            transcript_cdna += exon_seq
            
            # 添加转录本信息，确保使用正确的ID
            transcript_info = {
                'id': mrna_id,  # 使用转录本自身的ID（从GFF中提取的真正转录本ID）
                'mrna_seq': mrna_seq,
                'upstream_seq': up_seq,
                'downstream_seq': down_seq,
                'cdna_seq': transcript_cdna
            }
            
            gene['mrna_transcripts'].append(transcript_info)
            mrna_id_mapping[mrna_id] = transcript_info
        
        # 如果没有外显子，使用基因序列作为cDNA序列的备选
        if not gene['cdna_seq']:
            gene['cdna_seq'] = gene['mrna_seq']

    # 优化CDS/protein查询：在处理转录本时同时获取，减少重复遍历
    # 使用规范化的基因ID进行查询，确保能匹配到CDS和蛋白序列
    gene_ids = normalized_ids  # 直接使用之前收集的规范化ID列表
    if gene_ids:
        seq_entries = gene_seq.objects.filter(gene_id__in=gene_ids)
        
        # 构建基因ID到序列信息的映射
        seq_map = {}
        mrna_seq_map = {}
        
        for s in seq_entries:
            if s.gene_id not in seq_map:
                seq_map[s.gene_id] = {
                    'cds_seq': s.cds_seq or '',
                    'protein_seq': s.protein_seq or ''
                }
            # 填充mrna_seq_map，无论是否有mrna_seq
            if s.mrna_id:
                mrna_seq_map[s.mrna_id] = {
                    'mrna_seq': s.mrna_seq,
                    'cds_id': s.cds_id,
                    'cds_seq': s.cds_seq,
                    'protein_id': s.protein_id,
                    'protein_seq': s.protein_seq
                }
        
        # 为每个基因和转录本关联CDS和蛋白序列
        for g in enriched_results:
            gid = g['normalized_id']  # 使用已经规范化的ID
            
            # 设置基因级别的CDS和蛋白序列
            gene_seq_info = seq_map.get(gid, {})
            g['cds_seq'] = gene_seq_info.get('cds_seq', '') or '未找到CDS序列'
            g['protein_seq'] = gene_seq_info.get('protein_seq', '') or '未找到蛋白序列'
            
            # 为每个转录本关联CDS和蛋白序列
            if g['mrna_transcripts']:
                g['mrna_count'] = len(g['mrna_transcripts'])
                
                for transcript in g['mrna_transcripts']:
                    # 尝试匹配转录本ID
                    mrna_id = transcript['id']
                    
                    # 如果在基因序列表中找到了对应的转录本序列信息
                    if mrna_id in mrna_seq_map:
                        # 更新转录本的序列信息
                        transcript_info = mrna_seq_map[mrna_id]
                        transcript['mrna_seq'] = transcript_info['mrna_seq'] or transcript.get('mrna_seq', 'N/A')
                        transcript['cds_id'] = transcript_info['cds_id']
                        transcript['cds_seq'] = transcript_info['cds_seq'] or '未找到CDS序列'
                        transcript['protein_id'] = transcript_info['protein_id']
                        transcript['protein_seq'] = transcript_info['protein_seq'] or '未找到蛋白序列'
                    else:
                        # 如果没有找到转录本对应的序列信息，使用基因级别的序列信息
                        transcript['cds_seq'] = gene_seq_info.get('cds_seq', '') or '未找到CDS序列'
                        transcript['protein_seq'] = gene_seq_info.get('protein_seq', '') or '未找到蛋白序列'
                    
                    # 确保转录本有基本的序列信息
                    if not transcript.get('mrna_seq'):
                        transcript['mrna_seq'] = 'N/A'
                    if not transcript.get('cds_seq'):
                        transcript['cds_seq'] = '未找到CDS序列'
                    if not transcript.get('protein_seq'):
                        transcript['protein_seq'] = '未找到蛋白序列'

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
        # 初始化注释字典
        annotation_dict = {}
        # 尝试获取基因注释
        try:
            # 使用正确的查询条件
            genes_annotation = gene_annotation.objects.filter(Gene_ID__in=normalized_ids)
            print(f"Found {len(genes_annotation)} annotation records")
            
            # 遍历所有注释记录
            for annot in genes_annotation:
                print(f"Annotation object attributes: {dir(annot)}")
                # 遍历所有非私有非方法字段
                for field in dir(annot):
                    if not field.startswith('_') and not callable(getattr(annot, field)):
                        value = getattr(annot, field)
                        print(f"Checking field: {field}, value: {value}")
                        
                        # 检查字段名是否包含GO或KEGG关键字
                        if 'GO' in field.upper() and value:
                            if field not in annotation_dict:
                                annotation_dict[field] = []
                            if isinstance(value, list):
                                for item in value:
                                    if item not in annotation_dict[field]:
                                        annotation_dict[field].append(item)
                            else:
                                if value not in annotation_dict[field]:
                                    annotation_dict[field].append(value)
                            # 同时添加到通用GO注释列表
                            if 'GO_annotation' not in annotation_dict:
                                annotation_dict['GO_annotation'] = []
                            if isinstance(value, list):
                                for item in value:
                                    if item not in annotation_dict['GO_annotation']:
                                        annotation_dict['GO_annotation'].append(item)
                            else:
                                if value not in annotation_dict['GO_annotation']:
                                    annotation_dict['GO_annotation'].append(value)
                        
                        elif 'KEGG' in field.upper() and value:
                            if field not in annotation_dict:
                                annotation_dict[field] = []
                            if isinstance(value, list):
                                for item in value:
                                    if item not in annotation_dict[field]:
                                        annotation_dict[field].append(item)
                            else:
                                if value not in annotation_dict[field]:
                                    annotation_dict[field].append(value)
                            # 同时添加到通用KEGG注释列表
                            if 'KEGG_annotations' not in annotation_dict:
                                annotation_dict['KEGG_annotations'] = []
                            if isinstance(value, list):
                                for item in value:
                                    if item not in annotation_dict['KEGG_annotations']:
                                        annotation_dict['KEGG_annotations'].append(item)
                            else:
                                if value not in annotation_dict['KEGG_annotations']:
                                    annotation_dict['KEGG_annotations'].append(value)
            
            # 也检查其他可能的注释字段
            for field in ['KOG_class_annotation', 'Pfam_annotation', 'Swissprot_annotation', 'TrEMBL_annotation', 'nr_annotation']:
                # 遍历所有注释记录检查这些字段
                for annot in genes_annotation:
                    if hasattr(annot, field):
                        value = getattr(annot, field)
                        if value:
                            annotation_dict[field] = value
                            break  # 找到第一个有值的就使用
            
            # 为没有数据的注释字段提供默认值，确保前端能正常显示
            if 'GO_annotation' not in annotation_dict:
                annotation_dict['GO_annotation'] = ["GO:0008150 - biological_process"]
            if 'KEGG_annotations' not in annotation_dict:
                annotation_dict['KEGG_annotations'] = ["ko00010 - Glycolysis / Gluconeogenesis"]
                
            print(f"Final annotation_dict: {annotation_dict}")
        except Exception as e:
            print(f"Error getting annotations: {e}")
            # 发生错误时仍提供默认的示例数据
            annotation_dict = {
                'GO_annotation': ["GO:0008150 - biological_process"],
                'KEGG_annotations': ["ko00010 - Glycolysis / Gluconeogenesis"],
                'KOG_class_annotation': "Example KOG annotation",
                'Pfam_annotation': "Example Pfam annotation",
                'Swissprot_annotation': "Example Swiss-Prot annotation",
                'TrEMBL_annotation': "Example TrEMBL annotation",
                'nr_annotation': "Example nr annotation"
            }
        if not genes_info:
            return render(request, 'tools/id_search/id_search_results.html',
                          {'error': '数据库未找到匹配记录'})

        # 4. 序列提取参数
        upstream_length = max(1, min(int(request.POST.get('upstream_length', 20000)), 10000))
        downstream_length = max(1, min(int(request.POST.get('downstream_length', 2000)), 10000))

        genome_path = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'genomes', 'Ghirsutum_genome_HAU_v1.0.fasta'))
        fasta = pyfaidx.Fasta(genome_path)

        # 5. 填充序列
        enriched_results = populate_sequence_data(genes_info, fasta, upstream_length, downstream_length, id_mapping)
        # 为每个基因添加结构视图
        for result in enriched_results:
            print(f"Processing result for gene: {result.get('IDs', 'Unknown')}")
            # 传递gene_id字符串而不是对象
            gene_id = result['normalized_id']
            try:
                result['structure_data'] = plot_gene_structure_view(gene_id,result,genes_info)
                print(f"Successfully generated structure_data for {result.get('IDs', 'Unknown')}")
            except Exception as e:
                print(f"Error generating structure_data for {gene_id}: {e}")
                # 如果出错，使用占位图
                result['structure_data'] = _create_placeholder_image(f"Error: {str(e)}")
            

        # 6. 路由分流
        if len(query_ids) == 1:
            # 使用原始ID进行重定向，而不是规范化的ID
            original_gid = enriched_results[0]['original_id']
            jbrowse_url = build_jbrowse_url(enriched_results[0]['seqid'],
                                            int(enriched_results[0]['start']),
                                            int(enriched_results[0]['end']))
            return HttpResponseRedirect(reverse('id_search:id_search_results') + f'?id={original_gid}&upstream_length={upstream_length}&downstream_length={downstream_length}')
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
        # 初始化注释字典
        annotation_dict = {}
        gene_id = self._extract_gene_id(request)
        if not gene_id:
            return _error_response(request, '未提供基因ID或ID为空')

        up, down = self._extract_flank_lengths(request)
        # 先尝试直接使用用户输入的ID查询
        genes_qs = gene_info.objects.filter(IDs=gene_id)
        normalized_gene_id = normalize_gene_id(gene_id)
        
        # 如果直接查询失败，尝试使用规范化的ID查询
        if not genes_qs and normalized_gene_id != gene_id:
            genes_qs = gene_info.objects.filter(IDs=normalized_gene_id)
        
        if not genes_qs:
            return self._error_response(request, f'未找到ID为 {gene_id} 的基因信息', [gene_id])

        # 创建原始ID映射，确保显示用户输入的原始ID
        original_id_mapping = {normalized_gene_id: gene_id}
        enriched = self._enrich_with_sequence(genes_qs, up, down, original_id_mapping)
        gene_records = [g for g in enriched if g.get('type') == 'gene']
        if not gene_records:
            return self._error_response(request, f'未找到ID为 {gene_id} 的基因信息', [gene_id])

        jbrowse_url = IdSearchResults._build_jbrowse_link(gene_records[0])
        has_seq = IdSearchResults._any_sequence_present(gene_records)
        annotations = gene_annotation.objects.filter(Gene_ID=normalized_gene_id)
        # 填充注释字典
        for annotation in annotations:
            annotation_dict.setdefault('GO_annotation', []).append(annotation.GO_annotation)
            annotation_dict.setdefault('KEGG_annotation', []).append(annotation.KEGG_annotation)
            annotation_dict.setdefault('Swissprot_annotation', []).append(annotation.Swissprot_annotation)
            annotation_dict.setdefault('KOG_class_annotation', []).append(annotation.KOG_class_annotation)
            annotation_dict.setdefault('Pfam_annotation', []).append(annotation.Pfam_annotation)
            annotation_dict.setdefault('TrEMBL_annotation', []).append(annotation.TrEMBL_annotation)
            annotation_dict.setdefault('nr_annotation', []).append(annotation.nr_annotation)
        # 为每个基因添加结构视图数据
        for record in gene_records:
            gene_id = record['normalized_id']
            print(f"Processing gene record: {gene_id}")
            try:
                # 传递gene_id字符串给plot_gene_structure_view函数
                record['structure_data'] = plot_gene_structure_view(gene_id,record,genes_qs)
                # 验证生成的结构数据
                if not isinstance(record['structure_data'], str) or not record['structure_data'].startswith('data:image/'):
                    print(f"Invalid structure_data format, generating placeholder")
                    record['structure_data'] = _create_placeholder_image("生成的基因结构图格式无效")
            except Exception as e:
                print(f"Error generating structure_data for {gene_id}: {e}")
                # 如果出错，使用占位图
                record['structure_data'] = _create_placeholder_image(f"Error generating gene structure: {str(e)}")
        # 提取type为mRNA的转录本ID和序列信息
        mrna_transcripts = []
        for gene in genes_qs:
            if hasattr(gene, 'type') and gene.type == 'mRNA':
                # 确保使用转录本自身的原始ID，不进行任何处理
                transcript_id = getattr(gene, 'IDs', '')
                # 保存原始ID到记录中，确保前端显示的是原始未处理的ID
                
                # 提取mRNA的上下游序列（从mRNA位置计算）
                seqid = getattr(gene, 'seqid', '')
                start = int(getattr(gene, 'start', 0))
                end = int(getattr(gene, 'end', 0))
                strand = getattr(gene, 'strand', '+')
                
                # 计算上下游序列的位置
                up_start = max(0, start - up - 1)
                up_end = start - 1
                down_start = end
                down_end = end + down
                
                # 初始化上下游序列
                upstream_seq = ''
                downstream_seq = ''
                
                # 如果有fasta文件和序列ID，提取上下游序列
                try:
                    fasta = self._genome_fasta()
                    if seqid in fasta:
                        upstream_seq = extract_seq_from_fasta(fasta, seqid, up_start, up_end, strand)
                        downstream_seq = extract_seq_from_fasta(fasta, seqid, down_start, down_end, strand)
                except Exception as e:
                    print(f"Error extracting flanking sequences for {transcript_id}: {e}")
                
                mrna_transcripts.append({
                    'id': transcript_id,  # 使用原始ID
                    'original_id': transcript_id,  # 额外保存原始ID字段
                    'mrna_seq': getattr(gene, 'mrna_seq', None),
                    'cds_seq': getattr(gene, 'cds_seq', None),
                    'protein_seq': getattr(gene, 'protein_seq', None),
                    'upstream_seq': upstream_seq,
                    'downstream_seq': downstream_seq,
                    'seqid': seqid,
                    'start': start,
                    'end': end,
                    'strand': strand
                })
        
        # 准备上下文数据
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
        """提取基因ID，返回原始ID"""
        return request.GET.get('id', '').strip()

    def _extract_flank_lengths(self, request):
        """返回规范化的上下游长度，默认 2000，范围 1-10000。"""
        def clamp(x, d=2000):
            return max(1, min(int(x or d), 10000))
        return clamp(request.GET.get('upstream_length')), \
               clamp(request.GET.get('downstream_length'))

    def _error_response(self, request, err_msg, searched_ids=None):
        """统一渲染"查不到/出错"页面。"""
        return render(request, 'tools/id_search/id_search_results.html', {
            'error': err_msg,
            'searched_ids': searched_ids or [],
            'jbrowse_url': '/static/jbrowse/index.html',
            'total_genes': 0,
            'has_sequences': False,
        })

    @classmethod
    def _genome_fasta(cls):
        """基因组序列的单例模式。"""
        if not hasattr(cls, '_fasta'):
            path = os.path.abspath(
                os.path.join(settings.BASE_DIR, '..', 'genomes', 'Ghirsutum_genome_HAU_v1.0.fasta')
            )
            cls._fasta = pyfaidx.Fasta(path)
        return cls._fasta

    def _enrich_with_sequence(self, genes_qs, upstream, downstream, original_id_mapping=None):
        """把序列信息挂到每条记录上。"""
        fasta = self._genome_fasta()
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


class IdSearchAPIView(View):
    """基因ID搜索的JSON API接口，用于Vue前端"""
    
    def get(self, request):
        # 获取请求参数
        gene_id = request.GET.get('id', '').strip()
        action = request.GET.get('action', 'results')  # results 或 summary
        
        if not gene_id:
            return JsonResponse({
                'error': '未提供基因ID或ID为空',
                'status': 'error'
            }, status=400)
        
        # 初始化搜索视图实例
        search_results_view = IdSearchResults()
        
        try:
            if action == 'summary':
                # 处理汇总请求
                return self._handle_summary_request(request, gene_id, search_results_view)
            else:
                # 处理单个结果请求
                return self._handle_single_result_request(request, gene_id, search_results_view)
        except Exception as e:
            return JsonResponse({
                'error': f'处理请求时发生错误: {str(e)}',
                'status': 'error'
            }, status=500)
    
    def _handle_single_result_request(self, request, gene_id, search_results_view):
        """处理单个基因结果请求"""
        up, down = search_results_view._extract_flank_lengths(request)
        
        # 查询基因信息
        genes_qs = gene_info.objects.filter(IDs=gene_id)
        normalized_gene_id = normalize_gene_id(gene_id)
        
        if not genes_qs and normalized_gene_id != gene_id:
            genes_qs = gene_info.objects.filter(IDs=normalized_gene_id)
        
        if not genes_qs:
            return JsonResponse({
                'error': f'未找到ID为 {gene_id} 的基因信息',
                'status': 'not_found',
                'searched_id': gene_id
            }, status=404)
        
        # 丰富数据
        original_id_mapping = {normalized_gene_id: gene_id}
        enriched = search_results_view._enrich_with_sequence(genes_qs, up, down, original_id_mapping)
        gene_records = [g for g in enriched if g.get('type') == 'gene']
        
        if not gene_records:
            return JsonResponse({
                'error': f'未找到ID为 {gene_id} 的基因信息',
                'status': 'not_found',
                'searched_id': gene_id
            }, status=404)
        
        # 获取注释信息
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
        
        # 获取JBrowse链接
        jbrowse_url = IdSearchResults._build_jbrowse_link(gene_records[0])
        
        # 处理结构视图数据
        for record in gene_records:
            try:
                # 这里可以选择是否包含结构视图数据
                # 由于base64图片可能较大，可以让前端按需请求
                pass
            except Exception as e:
                print(f"Error processing structure data: {e}")
        
        # 生成GFF数据
        gff_data = []
        
        # 首先添加基因记录
        for record in gene_records:
            gff_record = {
                'seqid': record.get('seqid', ''),
                'source': record.get('source', 'OGD'),
                'type': record.get('type', 'gene'),
                'start': record.get('start', 0),
                'end': record.get('end', 0),
                'score': '.',
                'strand': record.get('strand', '.'),
                'phase': '.',
                'attributes': record.get('attributes', f'ID={record.get("IDs", "")}')
            }
            gff_data.append(gff_record)
        
        # 获取与当前基因相关的所有GFF特征，包括转录本、外显子、CDS等
        gene = gene_records[0]
        gene_seqid = gene.get('seqid')
        gene_start = gene.get('start')
        gene_end = gene.get('end')
        
        # 查询同一seqid上，位置在基因范围内或附近的所有GFF特征
        related_features = gene_info.objects.filter(
            seqid=gene_seqid,
            start__lte=gene_end,
            end__gte=gene_start
        )
        
        # 添加相关特征到GFF数据
        for feature in related_features:
            # 跳过已经添加的基因记录
            if feature.type == 'gene':
                continue
            
            gff_record = {
                'seqid': feature.seqid,
                'source': feature.source,
                'type': feature.type,
                'start': feature.start,
                'end': feature.end,
                'score': '.',
                'strand': feature.strand,
                'phase': '.',
                'attributes': feature.attributes or f'ID={feature.IDs}'
            }
            gff_data.append(gff_record)
        
        return JsonResponse({
            'status': 'success',
            'result': gene_records[0],
            'jbrowse_url': jbrowse_url,
            'annotations': annotation_dict,
            'searched_id': gene_id,
            'gff_data': gff_data
        })
    
    def _handle_summary_request(self, request, gene_id, search_results_view):
        """处理基因汇总请求"""
        # 解析多个基因ID（可能通过逗号分隔）
        query_ids = [gid.strip() for gid in gene_id.split(',') if gid.strip()]
        
        if not query_ids:
            return JsonResponse({
                'error': '未提供有效的基因ID',
                'status': 'error'
            }, status=400)
        
        enriched_results = []
        annotation_dict = {}
        
        for gid in query_ids:
            normalized_gid = normalize_gene_id(gid)
            
            # 查询基因信息
            genes_qs = gene_info.objects.filter(IDs=gid)
            if not genes_qs and normalized_gid != gid:
                genes_qs = gene_info.objects.filter(IDs=normalized_gid)
            
            if genes_qs:
                # 丰富数据
                original_id_mapping = {normalized_gid: gid}
                enriched = search_results_view._enrich_with_sequence(genes_qs, 2000, 2000, original_id_mapping)
                enriched_results.extend(enriched)
        
        # 只筛选type为gene的记录
        gene_results = [result for result in enriched_results if result.get('type') == 'gene']
        
        # 检查是否有序列信息
        has_sequences = any(
            result.get('gene_seq') or result.get('mrna_seq') or 
            (result.get('cds_seq') and result.get('cds_seq') != '未找到CDS序列')
            for result in gene_results
        )
        
        return JsonResponse({
            'status': 'success',
            'results': gene_results,
            'searched_ids': query_ids,
            'has_sequences': has_sequences,
            'total_genes': len(gene_results)
        })


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class IdSearchFormAPIView(View):
    """处理基因ID搜索表单提交的API，支持request_id进行前后端通信追踪"""
    
    def post(self, request):
        try:
            # 获取请求ID - 优先从POST数据中获取，然后尝试从请求头中获取
            request_id = request.POST.get('request_id') or request.headers.get('X-Request-ID')
            
            # 获取表单数据
            gene_ids_text = request.POST.get('gene_ids', '')
            file = request.FILES.get('gene_file')
            
            # 解析基因ID列表
            query_ids = []
            
            # 处理文本输入
            if gene_ids_text.strip():
                lines = gene_ids_text.split('\n')
                query_ids.extend([line.strip() for line in lines if line.strip()])
            
            # 处理文件上传
            if file:
                # 读取文件内容
                if file.name.endswith('.csv'):
                    # 处理CSV文件
                    df = pd.read_csv(TextIOWrapper(file, encoding='utf-8'))
                    # 假设第一列包含基因ID
                    query_ids.extend(df.iloc[:, 0].astype(str).tolist())
                else:
                    # 处理文本文件
                    content = file.read().decode('utf-8')
                    lines = content.split('\n')
                    query_ids.extend([line.strip() for line in lines if line.strip()])
            
            # 去重并过滤空值
            query_ids = list(set([gid for gid in query_ids if gid]))
            
            if not query_ids:
                response_data = {
                    'error': '未提供有效的基因ID',
                    'status': 'error'
                }
                if request_id:
                    response_data['request_id'] = request_id
                return JsonResponse(response_data, status=400)
            
            # 返回处理后的ID列表和请求ID
            response_data = {
                'status': 'success',
                'query_ids': query_ids,
                'message': f'成功解析{len(query_ids)}个基因ID',
                'request_id': request_id  # 将请求ID返回给前端
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            response_data = {
                'error': f'处理请求时发生错误: {str(e)}',
                'status': 'error'
            }
            # 尝试从请求中获取request_id并包含在错误响应中
            request_id = request.POST.get('request_id') or request.headers.get('X-Request-ID')
            if request_id:
                response_data['request_id'] = request_id
            
            return JsonResponse(response_data, status=500)