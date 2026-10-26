#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：解析GFF文件中的mRNA/transcript信息，导入到TranscriptMaster模型中
Parent字段对应GeneMaster的geneid，支持多种匹配方式
"""

import os
import sys
import gzip
import re
import pymysql

def get_db_config():
    """获取数据库配置"""
    return {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'cottonogd',
        'password': '1234',
        'database': 'cottonogd-ortho',
        'charset': 'utf8mb4'
    }


def parse_gff_attributes(attrs_str):
    """解析GFF属性字符串"""
    attributes = {}
    parts = attrs_str.split(';')
    for part in parts:
        part = part.strip()
        if '=' in part:
            key, value = part.split('=', 1)
            attributes[key.strip()] = value.strip()
    return attributes


def get_attribute_value(attrs_str, keys):
    """获取属性值，支持多个可能的key"""
    attrs = parse_gff_attributes(attrs_str)
    for key in keys:
        if key in attrs:
            return attrs[key]
    return None


def get_matched_gene(parent_gene_id, gene_id_map, genome_name):
    """
    参考GFF导入脚本的匹配逻辑，支持多种ID匹配方式
    返回匹配到的基因ID（整数），否则返回None
    """
    # 1. 直接匹配
    if parent_gene_id in gene_id_map:
        return gene_id_map[parent_gene_id]
    
    # 2. 尝试去除前缀（包括gene-前缀）
    for prefix in ('gene:', 'mRNA:', 'transcript:', 'CDS:', 'exon:', 'ID=', 'gene-'):
        if parent_gene_id.startswith(prefix):
            gene_id_no_prefix = parent_gene_id[len(prefix):]
            if gene_id_no_prefix in gene_id_map:
                return gene_id_map[gene_id_no_prefix]
    
    # 3. 尝试去除后缀版本号（如 .1, .2）
    if '.' in parent_gene_id:
        parts = parent_gene_id.split('.')
        for i in range(len(parts)-1, 0, -1):
            candidate = '.'.join(parts[:i])
            if candidate in gene_id_map:
                return gene_id_map[candidate]
    
    # 4. 尝试去除下划线后的部分
    if '_' in parent_gene_id:
        parts = parent_gene_id.split('_')
        for i in range(len(parts)-1, 0, -1):
            candidate = '_'.join(parts[:i])
            if candidate in gene_id_map:
                return gene_id_map[candidate]
    
    # 5. 尝试组合（先下划线，后点号）
    if '_' in parent_gene_id:
        parts = parent_gene_id.split('_')
        for i in range(len(parts)-1, 0, -1):
            candidate = '_'.join(parts[:i])
            if '.' in candidate:
                subparts = candidate.split('.')
                for j in range(len(subparts)-1, 0, -1):
                    sub_candidate = '.'.join(subparts[:j])
                    if sub_candidate in gene_id_map:
                        return gene_id_map[sub_candidate]
    
    # 6. 尝试提取数字部分进行匹配（如 Gobar.1Z001700.1 -> 1Z001700）
    match = re.search(r'(\d+[A-Z]?\d+)', parent_gene_id)
    if match:
        numeric_part = match.group(1)
        # 在映射中查找包含这个数字部分的键
        for key in gene_id_map:
            if numeric_part in key:
                return gene_id_map[key]
    
    # 7. 处理前导零问题（如 Godav_00000027 vs Godav_000001）
    match = re.search(r'_(\d+)', parent_gene_id)
    if match:
        numeric_str = match.group(1)
        numeric_value = str(int(numeric_str)) if numeric_str else None
        if numeric_value:
            for key in gene_id_map:
                key_match = re.search(r'_(\d+)', key)
                if key_match:
                    key_numeric = str(int(key_match.group(1)))
                    if key_numeric == numeric_value:
                        return gene_id_map[key]
    
    return None


def parse_gff_file(gff_path):
    """
    解析GFF文件，提取mRNA/transcript信息
    返回列表: [(transcript_id, parent_gene_id, seqid, start, end, strand), ...]
    """
    transcripts = []
    
    if gff_path.endswith('.gz'):
        opener = gzip.open(gff_path, 'rt')
    else:
        opener = open(gff_path, 'r')
    
    with opener as f:
        for line in f:
            if line.startswith('#'):
                continue
            
            line = line.rstrip('\n\r')
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) != 9:
                continue
            
            seqid = parts[0]
            feature_type = parts[2].lower()
            start = int(parts[3])
            end = int(parts[4])
            strand = parts[6]
            attrs_str = parts[8]
            
            # 只处理mRNA或transcript类型
            if feature_type not in ('mrna', 'transcript'):
                continue
            
            # 获取transcript ID
            transcript_id = get_attribute_value(attrs_str, ['ID', 'Name', 'id', 'name'])
            if not transcript_id:
                continue
            
            # 获取Parent（对应的基因ID）
            parent_id = get_attribute_value(attrs_str, ['Parent', 'parent'])
            
            # 如果没有Parent字段，通过ID推断基因ID
            if not parent_id:
                # mRNA ID格式通常是 gene_id.version，如 Chr01000010.1
                if '.' in transcript_id:
                    parent_id = transcript_id.rsplit('.', 1)[0]
                else:
                    # 如果ID中没有点号，直接使用transcript_id作为基因ID
                    # 这适用于某些GFF格式，其中mRNA ID就是基因ID
                    parent_id = transcript_id
            
            # 清理Parent值（可能包含多个parent，取第一个）
            if ',' in parent_id:
                parent_id = parent_id.split(',')[0]
            
            transcripts.append({
                'transcript_id': transcript_id,
                'parent_gene_id': parent_id,
                'seqid': seqid,
                'start': start,
                'end': end,
                'strand': strand
            })
    
    return transcripts


def import_transcripts_to_db(genome_name, transcripts):
    """
    将解析的transcript数据导入数据库
    genome_name: 物种名称（对应Species_info的name字段）
    transcripts: 解析的transcript列表
    """
    conn = pymysql.connect(**get_db_config())
    
    try:
        # 获取物种ID
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM species WHERE name = %s", (genome_name,))
            row = cursor.fetchone()
            if not row:
                print(f"错误：物种 '{genome_name}' 不存在于数据库中")
                return {'success': False, 'error': f"Species '{genome_name}' not found"}
            species_id = row[0]
        
        # 获取该物种所有基因的映射（支持geneid和alias）
        gene_id_map = {}
        with conn.cursor() as cursor:
            cursor.execute("SELECT geneid, id, alias FROM genemaster WHERE genome_id = %s", (genome_name,))
            for row in cursor.fetchall():
                geneid, id_val, alias = row[0], row[1], row[2]
                # 用geneid建立映射
                gene_id_map[geneid] = id_val
                # 用alias建立映射（去掉物种名前缀）
                if alias:
                    if alias.startswith(genome_name + '_'):
                        gene_id_map[alias[len(genome_name) + 1:]] = id_val
                    else:
                        gene_id_map[alias] = id_val
        
        print(f"找到 {len(gene_id_map)} 个基因用于匹配")
        
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        with conn.cursor() as cursor:
            # 先删除该物种已有的transcript记录
            cursor.execute("DELETE FROM transcriptmaster WHERE genome_id = %s", (species_id,))
            conn.commit()
            print(f"已清除该物种现有的transcript记录")
            
            # 禁用外键检查加速导入
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            for transcript in transcripts:
                parent_gene_id = transcript['parent_gene_id']
                
                # 使用增强的匹配逻辑
                gene_master_id = get_matched_gene(parent_gene_id, gene_id_map, genome_name)
                
                if gene_master_id is None:
                    skipped_count += 1
                    continue
                
                try:
                    cursor.execute(
                        "INSERT INTO transcriptmaster (transcriptid, genome_id, id_id) VALUES (%s, %s, %s)",
                        (transcript['transcript_id'], species_id, gene_master_id)
                    )
                    imported_count += 1
                except Exception as e:
                    print(f"导入transcript {transcript['transcript_id']} 失败: {str(e)}")
                    error_count += 1
            
            conn.commit()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        return {
            'success': True,
            'total_parsed': len(transcripts),
            'imported': imported_count,
            'skipped': skipped_count,
            'errors': error_count,
            'species': genome_name
        }
    
    finally:
        conn.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="解析GFF文件中的mRNA/transcript信息并导入到TranscriptMaster模型"
    )
    parser.add_argument("gff_file", help="GFF文件路径（支持.gz压缩）")
    parser.add_argument("genome_name", help="物种名称（必须存在于Species_info表中）")
    parser.add_argument("--dry-run", action="store_true", 
                        help="仅解析GFF文件，不实际导入数据库")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.gff_file):
        print(f"错误：GFF文件不存在: {args.gff_file}")
        sys.exit(1)
    
    print(f"正在解析GFF文件: {args.gff_file}")
    transcripts = parse_gff_file(args.gff_file)
    print(f"解析完成，共找到 {len(transcripts)} 条mRNA/transcript记录")
    
    if len(transcripts) > 0:
        print("\n前5条记录示例:")
        for i, t in enumerate(transcripts[:5]):
            print(f"  {i+1}. transcript_id={t['transcript_id']}, parent_gene={t['parent_gene_id']}, "
                  f"location={t['seqid']}:{t['start']}-{t['end']}({t['strand']})")
    
    if args.dry_run:
        print("\nDry-run模式，跳过数据库导入")
        return
    
    print(f"\n正在导入到数据库，物种: {args.genome_name}")
    result = import_transcripts_to_db(args.genome_name, transcripts)
    
    if result['success']:
        print("\n导入完成！")
        print(f"  解析总数: {result['total_parsed']}")
        print(f"  成功导入: {result['imported']}")
        print(f"  跳过（基因未找到）: {result['skipped']}")
        print(f"  错误: {result['errors']}")
    else:
        print(f"\n导入失败: {result['error']}")


if __name__ == "__main__":
    main()
