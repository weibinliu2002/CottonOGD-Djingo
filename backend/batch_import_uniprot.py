#!/usr/bin/env python3
"""
按物种分批导入 UniProt 注释数据
一个物种导入完成后再导入下一个，使用 LOAD DATA 快速导入
"""

import os
import sys
import argparse
import pymysql

def load_species_ids(filepath):
    """加载物种ID映射"""
    species_num_map = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    species_num_map[parts[0].strip()] = parts[1].strip()
    return species_num_map

def main():
    parser = argparse.ArgumentParser(description='按物种分批导入UniProt注释')
    parser.add_argument('--seq-uniprot', required=True, help='sequenceid_to_uniprot.txt 文件路径')
    parser.add_argument('--gene-mapping', required=True, help='gene_mapping.txt 文件路径')
    parser.add_argument('--output-dir', '-o', default='/tmp/uniprot_batch', help='批处理输出目录')
    parser.add_argument('--species', '-s', help='只处理指定物种编号（逗号分隔）')
    parser.add_argument('--start-from', help='从指定物种编号开始（用于断点续传）')
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 加载物种映射
    species_num_map = load_species_ids('/data/wbliu/data/CottonOGD/pandagma/work3/00_data/SpeciesIDs.txt')
    
    # 加载 seq_uniprot 到内存
    print("加载 sequenceid_to_uniprot.txt...")
    seq_uniprot = {}
    with open(args.seq_uniprot, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    seq_uniprot[parts[0]] = parts[1]
    
    print(f"  共 {len(seq_uniprot)} 条映射")
    
    # 按物种分组加载 gene_mapping
    print("\n加载 gene_mapping.txt...")
    gene_map_by_species = {}
    with open(args.gene_mapping, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split('\t')
                if len(parts) >= 4:
                    species_num = parts[1]
                    seq_id = parts[0]
                    species_name = parts[2]
                    gene_id = parts[3]
                    
                    # 如果指定了物种，只处理这些物种
                    if args.species and species_num not in args.species.split(','):
                        continue
                    
                    if species_num not in gene_map_by_species:
                        gene_map_by_species[species_num] = []
                    gene_map_by_species[species_num].append({
                        'seq_id': seq_id,
                        'species_name': species_name,
                        'gene_id': gene_id
                    })
    
    print(f"  涉及 {len(gene_map_by_species)} 个物种")
    
    # 获取要处理的物种列表
    species_list = sorted(gene_map_by_species.keys())
    
    # 如果指定了起始物种，跳过之前的
    if args.start_from:
        start_idx = species_list.index(args.start_from)
        species_list = species_list[start_idx:]
    
    print(f"\n准备处理 {len(species_list)} 个物种")
    
    # 连接数据库
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='cottonogd',
        password='1234',
        database='cottonogd-ortho',
        charset='utf8mb4',
        autocommit=False,
        local_infile=True
    )
    
    try:
        # 获取 UniProt 来源ID
        uniprot_source_id = None
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM annotation_source WHERE name = 'uniprot'")
            result = cursor.fetchone()
            if result:
                uniprot_source_id = result[0]
        
        if uniprot_source_id is None:
            print("错误：未找到 uniprot 来源记录")
            return
        
        # 获取物种ID映射
        db_species_map = {}
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM species")
            for row in cursor.fetchall():
                db_species_map[row[1]] = row[0]
        
        # 获取已存在的 annotation_detail
        uniprot_detail_map = {}
        with conn.cursor() as cursor:
            cursor.execute("SELECT annotation_id, id FROM annotation_detail WHERE source_id = %s", (uniprot_source_id,))
            for row in cursor.fetchall():
                uniprot_detail_map[row[0]] = row[1]
        
        # 统计变量
        total_inserted = 0
        species_processed = 0
        
        # 逐个物种处理
        for species_num in species_list:
            species_name = species_num_map.get(species_num, '未知')
            species_data = gene_map_by_species[species_num]
            
            print(f"\n{'='*60}")
            print(f"处理物种 {species_num}: {species_name}")
            print(f"  待处理基因数: {len(species_data)}")
            
            # 获取物种ID
            if species_name not in db_species_map:
                print(f"  警告: 物种 {species_name} 不在数据库中，跳过")
                continue
            
            species_id = db_species_map[species_name]
            
            # 获取该物种的 transcriptmaster 和 genemaster
            tm_genes = {}
            gm_genes = {}
            
            with conn.cursor() as cursor:
                # 获取 transcriptmaster
                cursor.execute("SELECT transcriptid, id_id FROM transcriptmaster WHERE genome_id = %s", (species_id,))
                for row in cursor.fetchall():
                    tm_genes[row[0]] = row[1]
                
                # 获取 genemaster
                cursor.execute("SELECT geneid, id FROM genemaster WHERE genome_id = %s", (species_name,))
                for row in cursor.fetchall():
                    gm_genes[row[0]] = row[1]
            
            print(f"  数据库中 transcriptmaster: {len(tm_genes)} 条")
            print(f"  数据库中 genemaster: {len(gm_genes)} 条")
            
            # 收集需要的 UniProt ID
            needed_uniprot_ids = set()
            for item in species_data:
                if item['seq_id'] in seq_uniprot:
                    needed_uniprot_ids.add(seq_uniprot[item['seq_id']])
            
            # 检查缺失的 annotation_detail 并插入
            missing_uniprot = [uid for uid in needed_uniprot_ids if uid not in uniprot_detail_map]
            
            if missing_uniprot:
                print(f"  需要插入 {len(missing_uniprot)} 个 annotation_detail")
                with conn.cursor() as cursor:
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                    insert_data = [(uniprot_source_id, uid) for uid in missing_uniprot]
                    cursor.executemany("INSERT INTO annotation_detail (source_id, annotation_id) VALUES (%s, %s)", insert_data)
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                    conn.commit()
                
                # 更新映射
                with conn.cursor() as cursor:
                    placeholders = ','.join(['%s'] * len(missing_uniprot))
                    cursor.execute(f"SELECT annotation_id, id FROM annotation_detail WHERE source_id = %s AND annotation_id IN ({placeholders})",
                                (uniprot_source_id,) + tuple(missing_uniprot))
                    for row in cursor.fetchall():
                        uniprot_detail_map[row[0]] = row[1]
            
            # 生成该物种的导入文件
            output_file = os.path.join(args.output_dir, f'uniprot_{species_num}.txt')
            with open(output_file, 'w') as out:
                for item in species_data:
                    seq_id = item['seq_id']
                    gene_id = item['gene_id']
                    
                    if seq_id not in seq_uniprot:
                        continue
                    
                    uniprot_id = seq_uniprot[seq_id]
                    detail_id = uniprot_detail_map.get(uniprot_id)
                    
                    if detail_id is None:
                        continue
                    
                    # 获取 id_id
                    id_id = None
                    if gene_id in tm_genes:
                        id_id = tm_genes[gene_id]
                    elif gene_id in gm_genes:
                        id_id = gm_genes[gene_id]
                    
                    if id_id is None:
                        continue
                    
                    out.write(f"{id_id}\t{species_id}\t{uniprot_source_id}\t{detail_id}\n")
            
            # 统计文件行数
            with open(output_file, 'r') as f:
                line_count = sum(1 for _ in f)
            
            print(f"  生成导入文件: {line_count} 条")
            
            # 使用 LOAD DATA 导入
            if line_count > 0:
                with conn.cursor() as cursor:
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                    cursor.execute(f"""
                        LOAD DATA LOCAL INFILE '{output_file}' INTO TABLE gene_annotation
                        FIELDS TERMINATED BY '\t'
                        (id_id, genome_id, source_id, annotation_detail_id)
                    """)
                    inserted = cursor.rowcount
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                    conn.commit()
                
                print(f"  成功插入 {inserted} 条")
                total_inserted += inserted
            
            species_processed += 1
            print(f"  进度: {species_processed}/{len(species_list)}")
        
        print(f"\n{'='*60}")
        print(f"完成！")
        print(f"处理物种数: {species_processed}")
        print(f"总插入记录数: {total_inserted}")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()