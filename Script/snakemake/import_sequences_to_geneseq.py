#!/usr/bin/env python3
import os
import pymysql
import glob
import argparse
from Bio import SeqIO

def get_db_config():
    return {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'cottonogd',
        'password': '1234',
        'database': 'cottonogd-ortho',
        'charset': 'utf8mb4'
    }

def get_species_map(conn):
    """获取物种名称到ID的映射"""
    species_map = {}
    with conn.cursor() as cursor:
        cursor.execute("SELECT name, id FROM species")
        for row in cursor.fetchall():
            species_map[row[0]] = row[1]
    return species_map

def get_genemaster_map(conn, genome_name):
    """获取genemaster中的基因ID到id的映射"""
    genemaster_map = {}
    with conn.cursor() as cursor:
        cursor.execute("SELECT geneid, id, alias FROM genemaster WHERE genome_id = %s", (genome_name,))
        for row in cursor.fetchall():
            geneid, id_val, alias = row[0], row[1], row[2]
            genemaster_map[geneid] = id_val
            if alias:
                if alias.startswith(genome_name + '_'):
                    genemaster_map[alias[len(genome_name) + 1:]] = id_val
                else:
                    genemaster_map[alias] = id_val
    return genemaster_map

def get_transcriptmaster_map(conn, genome_name):
    """获取transcriptmaster中的转录本ID到id的映射"""
    transcriptmaster_map = {}
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT tm.transcriptid, tm.id, tm.id_id 
            FROM transcriptmaster tm
            JOIN species s ON tm.genome_id = s.id
            WHERE s.name = %s
        """, (genome_name,))
        for row in cursor.fetchall():
            transcriptid, tr_id, id_id = row[0], row[1], row[2]
            transcriptmaster_map[transcriptid] = {'tr_id': tr_id, 'id_id': id_id}
    return transcriptmaster_map

def get_existing_gene_types(conn, species_id):
    """获取该物种已存在的gene_type列表"""
    existing_types = set()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT gene_type FROM gene_seq WHERE genome_id = %s
        """, (species_id,))
        for row in cursor.fetchall():
            existing_types.add(row[0])
    return existing_types

def get_matched_gene_id(gene_id, genemaster_map):
    """匹配基因ID，返回genemaster的id"""
    if gene_id in genemaster_map:
        return genemaster_map[gene_id]
    
    if '.' in gene_id:
        parts = gene_id.split('.')
        for i in range(len(parts)-1, 0, -1):
            candidate = '.'.join(parts[:i])
            if candidate in genemaster_map:
                return genemaster_map[candidate]
    
    for prefix in ('gene:', 'mRNA:', 'transcript:', 'CDS:', 'exon:'):
        if gene_id.startswith(prefix):
            gene_id_no_prefix = gene_id[len(prefix):]
            if gene_id_no_prefix in genemaster_map:
                return genemaster_map[gene_id_no_prefix]
    
    return None

def get_matched_transcript_id(gene_id, transcriptmaster_map):
    """匹配转录本ID，返回{'tr_id': ..., 'id_id': ...}"""
    if gene_id in transcriptmaster_map:
        return transcriptmaster_map[gene_id]
    
    if '.' in gene_id:
        parts = gene_id.split('.')
        for i in range(len(parts)-1, 0, -1):
            candidate = '.'.join(parts[:i])
            if candidate in transcriptmaster_map:
                return transcriptmaster_map[candidate]
    
    if '-' in gene_id:
        parts = gene_id.rsplit('-', 1)
        if len(parts) == 2 and parts[1] in ('RA', 'RB', 'RC', 'RD', 'RE'):
            if parts[0] in transcriptmaster_map:
                return transcriptmaster_map[parts[0]]
    
    for prefix in ('gene:', 'mRNA:', 'transcript:', 'CDS:', 'exon:'):
        if gene_id.startswith(prefix):
            gene_id_no_prefix = gene_id[len(prefix):]
            if gene_id_no_prefix in transcriptmaster_map:
                return transcriptmaster_map[gene_id_no_prefix]
    
    return None

def load_fasta_file(filepath):
    """读取FASTA文件，返回字典{gene_id: sequence}"""
    sequences = {}
    for record in SeqIO.parse(filepath, 'fasta'):
        gene_id = str(record.id).split()[0]
        sequences[gene_id] = str(record.seq)
    return sequences

def process_species(conn, species_map, genome_name):
    """处理单个物种的序列导入"""
    base_dir = '/data/web/CottonOGD/OGD/backend/data/genome'
    
    # 序列文件类型定义
    seq_types = {
        'gene_genome': {'suffix': '.gene_genome.fa', 'gene_type': 'genome', 'level': 'gene'},
        'mrna': {'suffix': '.mrna.fa', 'gene_type': 'mrna', 'level': 'transcript'},
        'cdna': {'suffix': '.cdna.fa', 'gene_type': 'cdna', 'level': 'transcript'},
        'cds': {'suffix': '.cds.fa', 'gene_type': 'cds', 'level': 'transcript'},
        'upstream': {'suffix': '.upstream20000.fa', 'gene_type': 'upstream', 'level': 'gene'},
        'downstream': {'suffix': '.downstream20000.fa', 'gene_type': 'downstream', 'level': 'gene'},
        'pro': {'suffix': '.pro.fa', 'gene_type': 'pro', 'level': 'transcript'}
    }
    
    if genome_name not in species_map:
        print(f"警告：物种 {genome_name} 不在数据库中")
        return 0, 0
    
    print(f"处理物种: {genome_name}")
    species_id = species_map[genome_name]
    
    species_dir = os.path.join(base_dir, genome_name)
    if not os.path.isdir(species_dir):
        print(f"警告：物种目录不存在: {species_dir}")
        return 0, 0
    
    # 获取该物种已存在的gene_type
    existing_types = get_existing_gene_types(conn, species_id)
    #print(f"  已存在的序列类型: {existing_types}")
    
    # 检查是否有需要处理的序列类型
    required_types = set(seq_info['gene_type'] for seq_info in seq_types.values())
    missing_types = required_types - existing_types
    
    if not missing_types:
        print(f"  所有序列类型都已存在，跳过处理")
        return 0, 0
    
    print(f"  需要处理的序列类型: {missing_types}")
    
    # 获取基因和转录本映射
    genemaster_map = get_genemaster_map(conn, genome_name)
    transcriptmaster_map = get_transcriptmaster_map(conn, genome_name)
    print(f"  加载了 {len(genemaster_map)} 个基因, {len(transcriptmaster_map)} 个转录本")
    
    total_inserted = 0
    total_skipped = 0
    
    # 处理每种序列类型
    with conn.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        for seq_key, seq_info in seq_types.items():
            seq_file = os.path.join(species_dir, f"{genome_name}{seq_info['suffix']}")
            
            if not os.path.exists(seq_file):
                print(f"  跳过 {seq_key}: 文件不存在")
                continue
            
            # 检查该gene_type是否已存在
            if seq_info['gene_type'] in existing_types:
                print(f"  跳过 {seq_key}: {seq_info['gene_type']} 类型数据已存在")
                continue
            
            print(f"  处理 {seq_key}...")
            
            sequences = load_fasta_file(seq_file)
            print(f"    读取到 {len(sequences)} 条序列")
            
            inserted = 0
            skipped = 0
            
            # 批量插入数据
            batch_size = 10000
            batch_data = []
            
            for gene_id, sequence in sequences.items():
                id_id = None
                tr_id = None
                
                if seq_info['level'] == 'gene':
                    # 基因级别：使用 genemaster 的 id
                    id_id = get_matched_gene_id(gene_id, genemaster_map)
                else:
                    # 转录本级：使用 transcriptmaster 的 id
                    result = get_matched_transcript_id(gene_id, transcriptmaster_map)
                    if result:
                        tr_id = result['tr_id']
                        id_id = result['id_id']
                
                if id_id is not None:
                    batch_data.append((id_id, tr_id, species_id, gene_id, seq_info['gene_type'], sequence))
                    inserted += 1
                    
                    # 达到批量大小，执行批量插入
                    if len(batch_data) >= batch_size:
                        sql = """
                            INSERT IGNORE INTO gene_seq (id_id, tr_id, genome_id, mrna_id, gene_type, sequence)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.executemany(sql, batch_data)
                        batch_data = []
                else:
                    skipped += 1
            
            # 处理剩余的数据
            if len(batch_data) > 0:
                sql = """
                    INSERT IGNORE INTO gene_seq (id_id, tr_id, genome_id, mrna_id, gene_type, sequence)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.executemany(sql, batch_data)
            
            print(f"    导入完成: 成功 {inserted} 条, 跳过 {skipped} 条")
            total_inserted += inserted
            total_skipped += skipped
        
        conn.commit()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    return total_inserted, total_skipped

def main():
    parser = argparse.ArgumentParser(description='导入序列数据到 gene_seq 表')
    parser.add_argument('--species', type=str, help='指定要处理的物种名称')
    args = parser.parse_args()
    
    base_dir = '/data/web/CottonOGD/OGD/backend/data/genome'
    
    # 连接数据库
    conn = pymysql.connect(**get_db_config())
    
    try:
        # 获取物种映射
        species_map = get_species_map(conn)
        print(f"已加载 {len(species_map)} 个物种")
        
        total_inserted = 0
        total_skipped = 0
        
        if args.species:
            # 处理单个物种
            inserted, skipped = process_species(conn, species_map, args.species)
            total_inserted += inserted
            total_skipped += skipped
        else:
            # 处理所有物种
            for species_dir in glob.glob(os.path.join(base_dir, '*')):
                if not os.path.isdir(species_dir):
                    continue
                
                genome_name = os.path.basename(species_dir)
                inserted, skipped = process_species(conn, species_map, genome_name)
                total_inserted += inserted
                total_skipped += skipped
        
        print(f"\n总计导入: 成功 {total_inserted} 条, 跳过 {total_skipped} 条")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()