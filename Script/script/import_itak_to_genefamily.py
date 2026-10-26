#!/usr/bin/env python3
import os
import pymysql
import glob

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

def get_genemaster_map_by_genome(conn, genome_name):
    """根据genome_name获取该物种的基因ID到id的映射，支持多种匹配方式"""
    genemaster_map = {}
    with conn.cursor() as cursor:
        # 获取genemaster中的基因ID映射（支持geneid和alias）
        cursor.execute("SELECT geneid, id, alias FROM genemaster WHERE genome_id = %s", (genome_name,))
        for row in cursor.fetchall():
            geneid, id_val, alias = row[0], row[1], row[2]
            # 直接用geneid建立映射
            genemaster_map[geneid] = id_val
            # 用alias建立映射（去掉物种名前缀）
            if alias:
                if alias.startswith(genome_name + '_'):
                    genemaster_map[alias[len(genome_name) + 1:]] = id_val
                else:
                    genemaster_map[alias] = id_val
        
        # 获取transcriptmaster中的转录本ID映射
        cursor.execute("""
            SELECT tm.transcriptid, tm.id_id 
            FROM transcriptmaster tm
            JOIN species s ON tm.genome_id = s.id
            WHERE s.name = %s
        """, (genome_name,))
        for row in cursor.fetchall():
            transcriptid, id_id = row[0], row[1]
            genemaster_map[transcriptid] = id_id
    return genemaster_map

def get_matched_id(gene_id, genemaster_map):
    """参考GFF导入脚本的匹配逻辑，支持多种ID匹配方式"""
    # 1. 直接匹配
    if gene_id in genemaster_map:
        return genemaster_map[gene_id]
    
    # 2. 处理特殊格式：rna-gnl|WGS:xxx|GeneName-RA
    if '|' in gene_id:
        parts = gene_id.split('|')
        if len(parts) >= 3:
            clean_id = parts[-1]  # 获取最后一个部分，如 Godav_00000027-RA
            if clean_id in genemaster_map:
                return genemaster_map[clean_id]
            # 去掉 -RA, -RB 等后缀
            if '-' in clean_id:
                suffix = clean_id.rsplit('-', 1)[1]
                if suffix in ('RA', 'RB', 'RC', 'RD', 'RE', 'RF', 'RG', 'RH'):
                    base_id = clean_id.rsplit('-', 1)[0]
                    if base_id in genemaster_map:
                        return genemaster_map[base_id]
    
    # 3. 尝试去除前缀
    for prefix in ('gene:', 'mRNA:', 'transcript:', 'CDS:', 'exon:', 'transcript_id:', 'gene_id:'):
        if gene_id.startswith(prefix):
            gene_id_no_prefix = gene_id[len(prefix):]
            if gene_id_no_prefix in genemaster_map:
                return genemaster_map[gene_id_no_prefix]
    
    # 3. 尝试去除后缀版本号（如 .1, .2）
    if '.' in gene_id:
        parts = gene_id.split('.')
        for i in range(len(parts)-1, 0, -1):
            candidate = '.'.join(parts[:i])
            if candidate in genemaster_map:
                return genemaster_map[candidate]
    
    # 4. 尝试去除下划线后的部分（如 _exon, _CDS）
    if '_' in gene_id:
        parts = gene_id.split('_')
        for i in range(len(parts)-1, 0, -1):
            candidate = '_'.join(parts[:i])
            if candidate in genemaster_map:
                return genemaster_map[candidate]
    
    # 5. 尝试组合（先下划线，后点号）
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
    
    # 6. 尝试提取数字部分进行匹配（如 Gobar.1Z001700.1 -> 1Z001700）
    import re
    # 提取类似 1Z001700 的模式
    match = re.search(r'(\d+[A-Z]?\d+)', gene_id)
    if match:
        numeric_part = match.group(1)
        # 在映射中查找包含这个数字部分的键
        for key in genemaster_map:
            if numeric_part in key:
                return genemaster_map[key]
    
    # 7. 处理前导零问题（如 Godav_00000027 vs Godav_000001）
    # 提取基因ID中的数字部分，去除前导零后进行匹配
    match = re.search(r'_(\d+)', gene_id)
    if match:
        numeric_str = match.group(1)
        # 去除前导零
        numeric_value = str(int(numeric_str)) if numeric_str else None
        if numeric_value:
            for key in genemaster_map:
                key_match = re.search(r'_(\d+)', key)
                if key_match:
                    key_numeric = str(int(key_match.group(1)))
                    if key_numeric == numeric_value:
                        return genemaster_map[key]
    
    return None

def parse_tf_classification(filepath):
    """解析tf_classification.txt - 正确区分TF/TR类别"""
    records = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 4:
                gene_id = parts[0]
                class_name = parts[1]      # 类别名称（如 C3H, C2C2-GATA）
                tf_class = parts[2]        # TF/TR（转录因子/转录调节因子）
                tf_name = parts[3]         # 详细名称
                records.append({
                    'gene_id': gene_id,
                    'TF_class': tf_class,
                    'TF_name': tf_name,
                    'class_name': class_name
                })
    return records

def parse_shiu_classification(filepath):
    """解析shiu_classification.txt - 激酶分类"""
    records = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                gene_id = parts[0]
                tf_name = parts[1]           # 激酶名称
                tf_class = 'kinase'          # 激酶类别
                class_name = tf_name.split('_')[0] if '_' in tf_name else tf_name  # 主类别
                records.append({
                    'gene_id': gene_id,
                    'TF_class': tf_class,
                    'TF_name': tf_name,
                    'class_name': class_name
                })
    return records

def main():
    base_dir = '/data/wbliu/data/CottonOGD/iTAK/iTAK_result'
    
    # 连接数据库
    conn = pymysql.connect(**get_db_config())
    
    try:
        # 获取物种映射
        species_map = get_species_map(conn)
        print(f"已加载 {len(species_map)} 个物种")
        
        # 清空表
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE genefamily")
            conn.commit()
            print("已清空 genefamily 表")
        
        # 统计
        total_inserted = 0
        total_skipped = 0
        
        # 遍历所有物种目录
        for species_dir in glob.glob(os.path.join(base_dir, '*.pro')):
            if not os.path.isdir(species_dir):
                continue
            
            # 从目录名提取基因组名称（去掉 .pro 后缀）
            genome_name = os.path.basename(species_dir).replace('.pro', '')
            
            # 检查物种是否存在
            if genome_name not in species_map:
                print(f"警告：物种 {genome_name} 不在数据库中，跳过")
                continue
            
            print(f"处理物种: {genome_name}")
            species_id = species_map[genome_name]
            
            # 获取该物种的基因映射
            genemaster_map = get_genemaster_map_by_genome(conn, genome_name)
            print(f"  加载了 {len(genemaster_map)} 个基因/转录本")
            
            # 收集该物种的所有记录
            all_records = []
            
            # 处理 tf_classification.txt
            tf_file = os.path.join(species_dir, 'tf_classification.txt')
            if os.path.exists(tf_file):
                records = parse_tf_classification(tf_file)
                all_records.extend(records)
                print(f"  tf_classification.txt: {len(records)} 条")
            
            # 处理 shiu_classification.txt
            shiu_file = os.path.join(species_dir, 'shiu_classification.txt')
            if os.path.exists(shiu_file):
                records = parse_shiu_classification(shiu_file)
                all_records.extend(records)
                print(f"  shiu_classification.txt: {len(records)} 条")
            
            # 插入数据库
            inserted = 0
            skipped = 0
            
            with conn.cursor() as cursor:
                # 禁用外键检查加速导入
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                
                for record in all_records:
                    gene_id = record['gene_id']
                    
                    # 使用改进的匹配逻辑获取 id_id
                    id_id = get_matched_id(gene_id, genemaster_map)
                    
                    if id_id is not None:
                        sql = """
                            INSERT IGNORE INTO genefamily (id_id, TF_class, TF_name, geneid, genome_id, class_name)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(sql, (id_id, record['TF_class'], record['TF_name'], gene_id, species_id, record['class_name']))
                        inserted += 1
                    else:
                        skipped += 1
                
                conn.commit()
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            print(f"  导入完成: 成功 {inserted} 条, 跳过 {skipped} 条")
            total_inserted += inserted
            total_skipped += skipped
        
        print(f"\n总计导入: 成功 {total_inserted} 条, 跳过 {total_skipped} 条")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()