#!/usr/bin/env python3
"""
导入eggNOG生成的GO和KEGG注释到数据库
"""

import os
import sys
import django
import pymysql
import pandas as pd
from collections import defaultdict

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
sys.path.insert(0, '/data/web/CottonOGD/OGD/backend')
django.setup()

from CottonOGD.models import Species_info, GeneMaster, TranscriptMaster, gene_go, gene_kegg

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='1234',
        database='cottonogd-ortho',
        charset='utf8mb4'
    )

def load_genemaster_map(genome_id):
    """加载genemaster映射表"""
    genemaster_map = {}
    for gm in GeneMaster.objects.filter(genome_id=genome_id).values('geneid', 'id'):
        genemaster_map[gm['geneid']] = gm['id']
    return genemaster_map

def load_transcriptmaster_map(genome_id):
    """加载transcriptmaster映射表"""
    transcriptmaster_map = {}
    for tm in TranscriptMaster.objects.filter(genome_id=genome_id).values('transcriptid', 'id'):
        transcriptmaster_map[tm['transcriptid']] = tm['id']
    return transcriptmaster_map

def match_id(gene_id, genemaster_map, transcriptmaster_map):
    """
    匹配基因ID到id_id
    参考 import_itak_to_genefamily.py 的匹配逻辑
    """
    import re
    
    # 1. 直接从transcriptmaster查找
    if gene_id in transcriptmaster_map:
        return transcriptmaster_map[gene_id]
    
    # 2. 直接从genemaster查找
    if gene_id in genemaster_map:
        return genemaster_map[gene_id]
    
    # 3. 处理特殊格式：rna-gnl|WGS:xxx|GeneName-RA
    if '|' in gene_id:
        parts = gene_id.split('|')
        if len(parts) >= 3:
            clean_id = parts[-1]
            if clean_id in genemaster_map:
                return genemaster_map[clean_id]
            if clean_id in transcriptmaster_map:
                return transcriptmaster_map[clean_id]
            # 去掉 -RA, -RB 等后缀
            if '-' in clean_id:
                suffix = clean_id.rsplit('-', 1)[1]
                if suffix in ('RA', 'RB', 'RC', 'RD', 'RE', 'RF', 'RG', 'RH'):
                    base_id = clean_id.rsplit('-', 1)[0]
                    if base_id in genemaster_map:
                        return genemaster_map[base_id]
                    if base_id in transcriptmaster_map:
                        return transcriptmaster_map[base_id]
    
    # 4. 尝试去除前缀
    for prefix in ('gene:', 'mRNA:', 'transcript:', 'CDS:', 'exon:', 'transcript_id:', 'gene_id:'):
        if gene_id.startswith(prefix):
            gene_id_no_prefix = gene_id[len(prefix):]
            if gene_id_no_prefix in genemaster_map:
                return genemaster_map[gene_id_no_prefix]
            if gene_id_no_prefix in transcriptmaster_map:
                return transcriptmaster_map[gene_id_no_prefix]
    
    # 5. 尝试去除后缀版本号（如 .1, .2）
    if '.' in gene_id:
        parts = gene_id.split('.')
        for i in range(len(parts)-1, 0, -1):
            candidate = '.'.join(parts[:i])
            if candidate in genemaster_map:
                return genemaster_map[candidate]
            if candidate in transcriptmaster_map:
                return transcriptmaster_map[candidate]
    
    # 6. 尝试去除下划线后的部分
    if '_' in gene_id:
        parts = gene_id.split('_')
        for i in range(len(parts)-1, 0, -1):
            candidate = '_'.join(parts[:i])
            if candidate in genemaster_map:
                return genemaster_map[candidate]
            if candidate in transcriptmaster_map:
                return transcriptmaster_map[candidate]
    
    # 7. 尝试组合（先下划线，后点号）
    if '_' in gene_id:
        parts = gene_id.split('_')
        for i in range(len(parts)-1, 0, -1):
            candidate = '_'.join(parts[:i])
            if '.' in candidate:
                subparts = candidate.split('.')
                for j in range(len(subparts)-1, 0, -1):
                    sub_candidate = '.'.join(subparts[:j])
                    if sub_candidate in genemaster_map:
                        return genemaster_map[sub_candidate]
                    if sub_candidate in transcriptmaster_map:
                        return transcriptmaster_map[sub_candidate]
    
    # 8. 尝试提取数字部分进行匹配
    match = re.search(r'(\d+[A-Z]?\d+)', gene_id)
    if match:
        numeric_part = match.group(1)
        for key in genemaster_map:
            if numeric_part in key:
                return genemaster_map[key]
        for key in transcriptmaster_map:
            if numeric_part in key:
                return transcriptmaster_map[key]
    
    return None

def parse_go_annotation(annotation_file):
    """
    解析GO annotation文件
    文件格式：gene\tGO\tname\tnamespace
    """
    go_data = []
    
    if not os.path.exists(annotation_file):
        print(f"GO文件不存在: {annotation_file}")
        return go_data
    
    with open(annotation_file, 'r') as f:
        header = f.readline()  # 跳过header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            
            gene_id = parts[0]
            go_id = parts[1]
            
            if go_id and go_id.startswith('GO:'):
                go_data.append((gene_id, go_id))
    
    return go_data

def parse_kegg_annotation(annotation_file):
    """
    解析KEGG annotation文件
    文件格式：gene\tKO\tpathway\tdescription
    """
    kegg_data = []
    
    if not os.path.exists(annotation_file):
        print(f"KEGG文件不存在: {annotation_file}")
        return kegg_data
    
    with open(annotation_file, 'r') as f:
        header = f.readline()  # 跳过header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            
            gene_id = parts[0]
            ko_id = parts[1]
            pathway = parts[2] if len(parts) > 2 else None
            
            # 提取 pathway_id (如 "map00010: Glycolysis" -> "00010")
            pathway_id = None
            if pathway:
                # 先提取冒号前的部分
                if ':' in pathway:
                    pathway_part = pathway.split(':')[0].strip()
                else:
                    pathway_part = pathway.strip()
                # 去掉 map 前缀
                if pathway_part.startswith('map'):
                    pathway_id = pathway_part[3:]
                else:
                    pathway_id = pathway_part
            
            if ko_id and ko_id.startswith('K'):
                kegg_data.append((gene_id, ko_id, pathway_id))
    
    return kegg_data

def import_go_kegg_annotation(genome_name, annotation_dir):
    """
    导入GO和KEGG注释到数据库
    """
    print(f"\n===== 处理物种: {genome_name} =====")
    
    # 0. 检查是否已导入（只判断是否存在，不计数）
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 查询该物种是否已有GO注释
        cursor.execute("""
            SELECT 1 FROM gene_go 
            WHERE id_id IN (SELECT id FROM transcriptmaster WHERE genome_id = (SELECT id FROM species WHERE name = %s))
            LIMIT 1
        """, (genome_name,))
        go_exists = cursor.fetchone() is not None
        
        # 查询该物种是否已有KEGG注释
        cursor.execute("""
            SELECT 1 FROM gene_kegg 
            WHERE id_id IN (SELECT id FROM transcriptmaster WHERE genome_id = (SELECT id FROM species WHERE name = %s))
            LIMIT 1
        """, (genome_name,))
        kegg_exists = cursor.fetchone() is not None
    
    if go_exists or kegg_exists:
        print(f"该物种已有注释数据，跳过导入")
        conn.close()
        return 0, 0
    conn.close()
    
    # 1. 获取物种ID
    try:
        species_obj = Species_info.objects.get(name=genome_name)
        genome_id = species_obj.id
        print(f"物种ID: {genome_id}")
    except Species_info.DoesNotExist:
        print(f"物种不存在: {genome_name}")
        return 0, 0
    
    # 2. 加载映射表
    print("加载映射表...")
    genemaster_map = load_genemaster_map(genome_id)
    transcriptmaster_map = load_transcriptmaster_map(genome_id)
    print(f"genemaster: {len(genemaster_map)} 条")
    print(f"transcriptmaster: {len(transcriptmaster_map)} 条")
    
    # 3. 解析GO annotation文件
    go_file = os.path.join(annotation_dir, 'GOannotation.tsv')
    print(f"解析GO文件: {go_file}")
    go_data = parse_go_annotation(go_file)
    print(f"GO记录: {len(go_data)}")
    
    # 4. 解析KEGG annotation文件
    kegg_file = os.path.join(annotation_dir, 'KOannotation.tsv')
    print(f"解析KEGG文件: {kegg_file}")
    kegg_data = parse_kegg_annotation(kegg_file)
    print(f"KEGG记录: {len(kegg_data)}")
    
    # 4.1 获取有效的 pathway_id 映射
    conn = get_db_connection()
    pathway_id_map = {}
    with conn.cursor() as cursor:
        cursor.execute("SELECT pathway_id FROM metabolic_pathway")
        for row in cursor.fetchall():
            pathway_id_map[row[0]] = row[0]
    print(f"有效的 pathway_id 数: {len(pathway_id_map)}")
    
    # 5. 匹配并导入GO
    go_records = []
    go_matched = 0
    go_unmatched = 0
    for gene_id, go_id in go_data:
        id_id = match_id(gene_id, genemaster_map, transcriptmaster_map)
        if id_id is not None:
            go_records.append({
                'id_id': id_id,
                'go_id': go_id
            })
            go_matched += 1
        else:
            go_unmatched += 1
    
    print(f"GO匹配成功: {go_matched}, 失败: {go_unmatched}")
    
    # 6. 匹配并导入KEGG
    kegg_records = []
    kegg_matched = 0
    kegg_unmatched = 0
    kegg_pathway_invalid = 0
    for gene_id, ko_id, pathway_id in kegg_data:
        id_id = match_id(gene_id, genemaster_map, transcriptmaster_map)
        if id_id is not None:
            # 检查 pathway_id 是否有效
            valid_pathway_id = pathway_id if pathway_id in pathway_id_map else None
            if pathway_id and valid_pathway_id is None:
                kegg_pathway_invalid += 1
            kegg_records.append({
                'id_id': id_id,
                'kegg_id': ko_id,
                'pathway_id': valid_pathway_id
            })
            kegg_matched += 1
        else:
            kegg_unmatched += 1
    
    print(f"KEGG匹配成功: {kegg_matched}, 失败: {kegg_unmatched}, pathway无效: {kegg_pathway_invalid}")
    
    # 7. 批量插入数据库（复用已打开的连接）
    cursor = conn.cursor()
    
    # 禁用外键检查和唯一键检查以提高插入速度
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("SET UNIQUE_CHECKS = 0")
    
    # 插入GO - 使用executemany批量插入（分批处理）
    go_inserted = 0
    if go_records:
        batch_size = 100000
        total_records = len(go_records)
        go_values = [(r['id_id'], r['go_id']) for r in go_records]
        
        for i in range(0, total_records, batch_size):
            batch = go_values[i:i+batch_size]
            cursor.executemany(
                "INSERT IGNORE INTO gene_go (id_id, go_id) VALUES (%s, %s)",
                batch
            )
            go_inserted += cursor.rowcount
            conn.commit()
            print(f"  GO插入进度: {min(i + batch_size, total_records)}/{total_records}")
    
    print(f"GO实际插入: {go_inserted}")
    
    # 插入KEGG - 使用executemany批量插入（分批处理）
    kegg_inserted = 0
    if kegg_records:
        batch_size = 50000
        total_records = len(kegg_records)
        kegg_values = [(r['id_id'], r['kegg_id'], r['pathway_id']) for r in kegg_records]
        
        for i in range(0, total_records, batch_size):
            batch = kegg_values[i:i+batch_size]
            cursor.executemany(
                "INSERT IGNORE INTO gene_kegg (id_id, kegg_id, pathway_id) VALUES (%s, %s, %s)",
                batch
            )
            kegg_inserted += cursor.rowcount
            conn.commit()
            print(f"  KEGG插入进度: {min(i + batch_size, total_records)}/{total_records}")
    
    # 恢复设置
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    cursor.execute("SET UNIQUE_CHECKS = 1")
    cursor.close()
    conn.close()
    
    return go_inserted, kegg_inserted

def main():
    if len(sys.argv) < 3:
        print("用法: python import_eggnog_annotation.py <genome_name> <annotation_dir>")
        sys.exit(1)
    
    genome_name = sys.argv[1]
    annotation_dir = sys.argv[2]
    
    go_count, kegg_count = import_go_kegg_annotation(genome_name, annotation_dir)
    print(f"\n===== 完成 =====")
    print(f"GO: {go_count} 条")
    print(f"KEGG: {kegg_count} 条")

if __name__ == '__main__':
    main()
