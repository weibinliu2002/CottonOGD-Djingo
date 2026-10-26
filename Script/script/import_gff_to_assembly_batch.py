#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GFF批量导入工具 - 增量导入
只导入不存在的物种数据
"""

import os
import sys
import gzip
import time
import tempfile

sys.path.append('/data/web/CottonOGD/OGD/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

import django
django.setup()

from CottonOGD.models import Species_info
from django.db import connection, connections


def get_db_config():
    """获取数据库配置"""
    from django.db import connections
    db_params = connections['default'].get_connection_params()
    return {
        'host': db_params.get('HOST', 'localhost'),
        'user': db_params.get('USER', 'cottonogd'),
        'password': db_params.get('PASSWORD', '1234'),
        'database': db_params.get('NAME', 'cottonogd-ortho'),
        'port': db_params.get('PORT', 3306),
        'charset': 'utf8mb4',
        'connect_timeout': 60,
        'read_timeout': 120,
        'write_timeout': 120,
    }


def get_species_mapping():
    """获取所有物种名称到ID的映射"""
    return {sp.name: sp.id for sp in Species_info.objects.all()}


def get_existing_genome_ids():
    """获取gene_assembly中已存在的genome_id"""
    import pymysql

    db_config = get_db_config()
    for attempt in range(3):
        try:
            conn = pymysql.connect(**db_config)
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT DISTINCT genome_id FROM gene_assembly")
                    return set(row[0] for row in cursor.fetchall())
            finally:
                conn.close()
        except Exception as e:
            if attempt < 2:
                print(f" 查询超时，重试... ({attempt+1}/3)")
                time.sleep(3)
            else:
                print(f" 查询失败: {e}")
                return set()
    return set()


def get_genemaster_mapping(species_name, species_id):
    """获取GeneMaster映射，支持geneid和alias双字段匹配"""
    import pymysql

    db_config = get_db_config()
    result = {}

    for attempt in range(3):
        try:
            conn = pymysql.connect(**db_config)
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SET SESSION innodb_lock_wait_timeout = 60")

                    # 用名称查询，获取geneid和alias两个字段
                    cursor.execute("""
                        SELECT geneid, id, alias FROM genemaster WHERE genome_id = %s
                    """, [species_name])
                    rows = cursor.fetchall()

                    if not rows:
                        # 用整数ID查询
                        cursor.execute("""
                            SELECT geneid, id, alias FROM genemaster WHERE genome_id = %s
                        """, [species_id])
                        rows = cursor.fetchall()

                    for row in rows:
                        geneid, gid, alias = row
                        # 用geneid建立映射
                        result[geneid] = gid
                        # 用alias建立映射（去掉物种名前缀）
                        if alias:
                            if alias.startswith(species_name + '_'):
                                result[alias[len(species_name) + 1:]] = gid

                    return result

            finally:
                conn.close()

        except Exception as e:
            if attempt < 2:
                print(f" 查询超时，重试... ({attempt+1}/3)")
                time.sleep(3)
            else:
                print(f" 查询失败: {e}")
                return {}

    return result


def parse_gff_fast(gff_path, species_id, geneid_to_master):
    """解析单个GFF文件并准备插入数据"""
    features = []

    opener = gzip.open(gff_path, 'rt', encoding='utf-8') if gff_path.endswith('.gz') else open(gff_path, 'r', encoding='utf-8')

    # 第一遍：收集所有ID和Parent关系，以及ID到Name的映射
    id_map = {}
    id_to_name = {}
    with opener as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) != 9:
                continue
            attrs_str = parts[8].strip()
            feature_id = ''
            parent = ''
            feature_name = ''
            for attr in attrs_str.split(';'):
                if '=' in attr:
                    idx = attr.find('=')
                    key = attr[:idx].strip()
                    value = attr[idx+1:].strip()
                    if key == 'ID':
                        feature_id = value
                    elif key == 'Parent' or key == 'Derives_from':
                        parent = value
                    elif key == 'Name':
                        feature_name = value
            if feature_id:
                id_map[feature_id] = parent
            if feature_id and feature_name:
                id_to_name[feature_id] = feature_name

    # 第二遍：构建完整的gene映射链
    def get_gene_id(feature_id_or_parent, visited=None):
        """递归获取最终的gene id，带循环检测"""
        if visited is None:
            visited = set()
        
        # 检测循环引用
        if feature_id_or_parent in visited:
            return None
        visited.add(feature_id_or_parent)
        
        if not feature_id_or_parent:
            return None
        # 直接检查这个ID是否在geneid_to_master中（可能是gene ID）
        if feature_id_or_parent in geneid_to_master:
            return feature_id_or_parent
        if feature_id_or_parent in id_to_name and id_to_name[feature_id_or_parent] in geneid_to_master:
            return id_to_name[feature_id_or_parent]
        # 获取这个ID的Parent
        parent = id_map.get(feature_id_or_parent)
        if parent:
            # 递归检查Parent
            result = get_gene_id(parent, visited.copy())
            if result:
                return result
            # 如果没有结果，尝试去掉前缀再检查
            for prefix in ('gene:', 'mRNA:', 'transcript:', 'CDS:', 'exon:'):
                if parent.startswith(prefix):
                    parent_no_prefix = parent[len(prefix):]
                    result = get_gene_id(parent_no_prefix, visited.copy())
                    if result:
                        return result
        # 如果没有Parent或者Parent没找到，尝试从ID中推断（针对没有Parent属性的GFF）
        # 例如：Chr01000010.1_exon_14 -> Chr01000010.1 -> Chr01000010
        # 或者：Chr01000010.1_cds_14 -> Chr01000010.1 -> Chr01000010
        # 或者：Chr01000010.1 -> Chr01000010
        for separator in ('.', '_'):
            if separator in feature_id_or_parent:
                parts = feature_id_or_parent.split(separator)
                # 尝试逐步去掉后面的部分
                for i in range(len(parts)-1, 0, -1):
                    candidate = separator.join(parts[:i])
                    if candidate in geneid_to_master:
                        return candidate
                    # 检查这个候选ID在id_map中是否有Parent
                    if candidate in id_map:
                        result = get_gene_id(candidate, visited.copy())
                        if result:
                            return result
        return None

    # 第三遍：解析所有特征
    opener = gzip.open(gff_path, 'rt', encoding='utf-8') if gff_path.endswith('.gz') else open(gff_path, 'r', encoding='utf-8')
    with opener as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) != 9:
                continue

            seqid = parts[0]
            source = parts[1] if len(parts) > 1 else '.'
            feature_type = parts[2]
            start = parts[3]
            end = parts[4]
            score = parts[5] if len(parts) > 5 else '.'
            strand = parts[6]
            phase = parts[7] if len(parts) > 7 else '.'
            attrs_str = parts[8].strip()

            attrs = {}
            for attr in attrs_str.split(';'):
                if '=' in attr:
                    idx = attr.find('=')
                    key = attr[:idx].strip()
                    value = attr[idx+1:].strip()
                    attrs[key] = value

            feature_id = attrs.get('ID', '')
            feature_name = attrs.get('Name', '')
            parent = attrs.get('Parent', '')

            # 确定gene_id：尝试多种匹配方式
            gene_id = None
            feature_type_lower = feature_type.lower()

            # 直接尝试feature_id匹配（很多GFF没有Name）
            if feature_id and feature_id in geneid_to_master:
                gene_id = feature_id
            elif feature_name and feature_name in geneid_to_master:
                gene_id = feature_name
            elif feature_type_lower in ('gene',):
                gene_id = feature_id if feature_id else feature_name
            elif feature_type_lower in ('mrna', 'transcript'):
                # mRNA/transcript的Parent是gene ID
                gene_id = get_gene_id(parent) if parent else (feature_name if feature_name else feature_id)
            else:
                # 其他特征（exon, CDS等），直接用Parent追溯
                gene_id = get_gene_id(parent) if parent else get_gene_id(feature_id)

            genemaster_id = None
            if gene_id:
                # 尝试直接匹配
                genemaster_id = geneid_to_master.get(gene_id)
                # 如果没有匹配到，尝试去掉可能的前缀
                if genemaster_id is None and gene_id:
                    for prefix in ('gene:', 'mRNA:', 'transcript:', 'CDS:', 'exon:'):
                        if gene_id.startswith(prefix):
                            gene_id_no_prefix = gene_id[len(prefix):]
                            genemaster_id = geneid_to_master.get(gene_id_no_prefix)
                            if genemaster_id is not None:
                                break

            # 只有匹配到genemaster的记录才保留（因为数据库id_id字段不允许为空）
            if genemaster_id is not None:
                features.append((
                    str(genemaster_id),
                    feature_id or '',
                    str(species_id),
                    seqid,
                    source,
                    feature_type,
                    start,
                    end,
                    strand,
                    phase,
                    score,
                    attrs_str
                ))

    return features


def import_all_gff(merge_file):
    """批量导入所有GFF"""
    print("=" * 60)
    print("GFF批量导入（增量）")
    print("=" * 60)

    # 读取配置文件
    print("\n读取配置文件...")
    species_config = []
    with open(merge_file, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                species_name = parts[0]
                gff_file = f"/data/web/CottonOGD/OGD/backend/data/genome/{species_name}/{parts[2]}"
                if os.path.exists(gff_file):
                    species_config.append((species_name, gff_file))
                else:
                    print(f"警告：文件不存在: {gff_file}")

    print(f"找到 {len(species_config)} 个物种")

    # 获取物种映射
    species_map = get_species_mapping()
    valid_species = []
    for name, gff_file in species_config:
        if name in species_map:
            valid_species.append((name, gff_file, species_map[name]))

    print(f"有效物种: {len(valid_species)} 个")

    # 跳过耗时的已存在检查，直接处理所有物种
    # 如需增量导入，请编辑merge.txt只保留需要导入的物种
    need_import = valid_species
    print(f"将处理: {len(need_import)} 个物种")

    if not need_import:
        print("\n没有需要导入的物种！")
        return

    # 第一步：解析需要导入的GFF文件
    print("\n第一步：解析GFF文件...")
    all_features = []
    failed_species = []
    total_time = time.time()

    for species_name, gff_file, species_id in need_import:
        print(f"  解析: {species_name}...", end="", flush=True)

        # 获取该物种的GeneMaster映射
        geneid_to_master = get_genemaster_mapping(species_name, species_id)

        if not geneid_to_master:
            print(f" 无GeneMaster数据，跳过")
            failed_species.append(species_name)
            continue

        # 解析GFF
        start_time = time.time()
        features = parse_gff_fast(gff_file, species_id, geneid_to_master)
        all_features.extend(features)
        print(f" {len(features)} 条有效记录 ({time.time() - start_time:.1f}s)")

    parse_time = time.time() - total_time
    print(f"\n解析完成！共 {len(all_features)} 条记录，耗时 {parse_time:.2f} 秒")

    if failed_species:
        print(f"跳过物种: {len(failed_species)} 个")

    if not all_features:
        print("没有记录可导入")
        return

    # 第二步：写入临时CSV文件
    print("\n第二步：准备CSV文件...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        # 写入header行
        tmp.write('\t'.join(['id_id', 'genome_id', 'seqid', 'source', 'type', 'start', 'end', 'strand', 'phase', 'value', 'attributes']) + '\n')
        for feature in all_features:
            tmp.write('\t'.join(feature) + '\n')
        csv_path = tmp.name

    print(f"CSV文件: {csv_path}")
'''
    # 第三步：批量导入
    print("\n第三步：批量导入数据库...")
    start_time = time.time()

    # 使用pymysql直接连接以支持LOCAL INFILE
    import pymysql
    db_config = get_db_config()
    db_config['local_infile'] = True
    
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("SET autocommit = 0")

            sql = f"""
                LOAD DATA LOCAL INFILE '{csv_path}'
                INTO TABLE gene_assembly
                FIELDS TERMINATED BY '\\t'
                LINES TERMINATED BY '\\n'
                IGNORE 1 LINES
                (id_id, geneid_id, genome_id, seqid, source, type, start, end, strand, phase, value, attributes)
            """
            cursor.execute(sql)
            inserted = cursor.rowcount

            cursor.execute("COMMIT")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    finally:
        conn.close()

    insert_time = time.time() - start_time

    # 清理
    os.unlink(csv_path)

    print("\n" + "=" * 60)
    print(f"导入完成！")
    print(f"  导入物种: {len(need_import) - len(failed_species)} 个")
    print(f"  跳过物种: {len(failed_species)} 个")
    print(f"  插入记录: {inserted}")
    print(f"  导入耗时: {insert_time:.2f} 秒")
    print(f"  总耗时: {(time.time() - total_time):.2f} 秒")

'''
def main():
    import argparse
    parser = argparse.ArgumentParser(description="批量导入GFF文件")
    parser.add_argument("--merge", default="/data/web/CottonOGD/OGD/backend/data/genome/merge.txt",
                        help="merge.txt配置文件路径")
    args = parser.parse_args()

    import_all_gff(args.merge)


if __name__ == "__main__":
    main()
