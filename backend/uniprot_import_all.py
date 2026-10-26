#!/usr/bin/env python3
"""
UniProt 注释导入整合脚本
一步完成：生成映射 + 按物种分批导入
"""

import os
import sys
import argparse
import pymysql

class UnionFind:
    """并查集数据结构"""
    def __init__(self):
        self.parent = {}
    
    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            if root_x < root_y:
                self.parent[root_y] = root_x
            else:
                self.parent[root_x] = root_y

def load_species_ids(filepath):
    species_num_map = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    species_num_map[parts[0].strip()] = parts[1].strip()
    return species_num_map

def load_sequence_ids(filepath, species_filter=None):
    species_genes = {}
    seqid_to_geneid = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    seq_id = parts[0].strip()
                    gene_id = parts[1].strip()
                    seqid_to_geneid[seq_id] = gene_id
                    if '_' in seq_id:
                        sn = seq_id.split('_')[0]
                        if species_filter and sn not in species_filter:
                            continue
                        if sn not in species_genes:
                            species_genes[sn] = {}
                        species_genes[sn][seq_id] = gene_id
    return species_genes, seqid_to_geneid

def load_unique_proteins_map(filepath):
    uf = UnionFind()
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    uf.union(parts[0].strip(), parts[1].strip())
    
    result = {}
    for id_val in uf.parent:
        result[id_val] = uf.find(id_val)
    return result

def load_best_hits(filepath):
    best_hits = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    best_hits[parts[0].strip()] = parts[1].strip()
    return best_hits

def main():
    parser = argparse.ArgumentParser(description='UniProt注释导入整合脚本')
    parser.add_argument('--species', '-s', help='只处理指定物种编号（逗号分隔）')
    parser.add_argument('--start-from', help='从指定物种编号开始（断点续传）')
    parser.add_argument('--output-dir', '-o', default='/tmp/uniprot_import', help='临时输出目录')
    args = parser.parse_args()
    
    best_hits_file = '/data/wbliu/data/CottonOGD/Function/uniprot/best_hits.m8'
    map_file = '/data/wbliu/data/CottonOGD/Function/data/unique_proteins_map.txt'
    seq_ids_file = '/data/wbliu/data/CottonOGD/pandagma/work3/00_data/SequenceIDs.txt'
    species_ids_file = '/data/wbliu/data/CottonOGD/pandagma/work3/00_data/SpeciesIDs.txt'
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 解析物种筛选
    species_filter = None
    if args.species:
        species_filter = set(args.species.split(','))
    
    print("===== 阶段1: 生成映射文件 =====")
    
    # 加载映射表
    print("加载数据...")
    species_num_map = load_species_ids(species_ids_file)
    species_genes, seqid_to_geneid = load_sequence_ids(seq_ids_file, species_filter)
    unique_map = load_unique_proteins_map(map_file)
    best_hits = load_best_hits(best_hits_file)
    
    print(f"  SequenceIDs: {len(seqid_to_geneid)} 条")
    print(f"  Unique proteins map: {len(unique_map)} 条")
    print(f"  Best hits: {len(best_hits)} 条")
    
    # 构建反向映射
    rep_to_ids = {}
    for id_val, rep_id in unique_map.items():
        if rep_id not in rep_to_ids:
            rep_to_ids[rep_id] = []
        rep_to_ids[rep_id].append(id_val)
    
    # 生成映射数据（直接存储在内存中）
    print("\n生成映射...")
    seq_uniprot = {}  # seq_id -> uniprot_id
    gene_map_by_species = {}  # species_num -> list of {seq_id, species_name, gene_id}
    
    for seq_id, uniprot_id in best_hits.items():
        # 直接映射
        if seq_id in seqid_to_geneid:
            seq_uniprot[seq_id] = uniprot_id
            species_num = seq_id.split('_')[0]
            species_name = species_num_map.get(species_num, '')
            gene_id = seqid_to_geneid[seq_id]
            
            if species_num not in gene_map_by_species:
                gene_map_by_species[species_num] = []
            gene_map_by_species[species_num].append({
                'seq_id': seq_id,
                'species_name': species_name,
                'gene_id': gene_id
            })
        
        # 通过unique_map扩展
        if seq_id in unique_map:
            rep_id = unique_map[seq_id]
            if rep_id in rep_to_ids:
                for mapped_seq_id in rep_to_ids[rep_id]:
                    if mapped_seq_id in seqid_to_geneid and mapped_seq_id != seq_id:
                        seq_uniprot[mapped_seq_id] = uniprot_id
                        species_num = mapped_seq_id.split('_')[0]
                        species_name = species_num_map.get(species_num, '')
                        gene_id = seqid_to_geneid[mapped_seq_id]
                        
                        if species_num not in gene_map_by_species:
                            gene_map_by_species[species_num] = []
                        gene_map_by_species[species_num].append({
                            'seq_id': mapped_seq_id,
                            'species_name': species_name,
                            'gene_id': gene_id
                        })
    
    print(f"  扩展后映射: {len(seq_uniprot)} 条")
    print(f"  涉及物种: {len(gene_map_by_species)} 个")
    
    print("\n===== 阶段2: 按物种分批导入 =====")
    
    # 获取要处理的物种列表
    species_list = sorted(gene_map_by_species.keys())
    
    if args.start_from:
        start_idx = species_list.index(args.start_from)
        species_list = species_list[start_idx:]
    
    print(f"准备处理 {len(species_list)} 个物种")
    
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
        
        # 获取已导入的物种列表（通过 gene_annotation 表检查）
        imported_species = set()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT genome_id FROM gene_annotation 
                WHERE source_id = %s
            """, (uniprot_source_id,))
            for row in cursor.fetchall():
                imported_species.add(row[0])
        
        print(f"已导入物种数: {len(imported_species)}")
        
        total_inserted = 0
        species_processed = 0
        species_skipped = 0
        
        # 逐个物种处理
        for species_num in species_list:
            species_name = species_num_map.get(species_num, '未知')
            species_data = gene_map_by_species[species_num]
            
            print(f"\n{'='*60}")
            print(f"处理物种 {species_num}: {species_name}")
            print(f"  待处理基因数: {len(species_data)}")
            
            if species_name not in db_species_map:
                print(f"  警告: 物种 {species_name} 不在数据库中，跳过")
                continue
            
            species_id = db_species_map[species_name]
            
            # 检查是否已导入
            if species_id in imported_species:
                print(f"  该物种已导入 UniProt 注释，跳过")
                species_skipped += 1
                continue
            
            # 获取该物种的基因数据
            tm_genes = {}
            gm_genes = {}
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT transcriptid, id_id FROM transcriptmaster WHERE genome_id = %s", (species_id,))
                for row in cursor.fetchall():
                    tm_genes[row[0]] = row[1]
                
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
            
            # 检查缺失的 annotation_detail
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
            
            # 生成临时导入文件
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
                    
                    id_id = None
                    if gene_id in tm_genes:
                        id_id = tm_genes[gene_id]
                    elif gene_id in gm_genes:
                        id_id = gm_genes[gene_id]
                    
                    if id_id is None:
                        continue
                    
                    out.write(f"{id_id}\t{species_id}\t{uniprot_source_id}\t{detail_id}\n")
            
            # 统计并导入
            with open(output_file, 'r') as f:
                line_count = sum(1 for _ in f)
            
            print(f"  生成导入文件: {line_count} 条")
            
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
        print(f"跳过物种数: {species_skipped} (已导入)")
        print(f"总插入记录数: {total_inserted}")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()