#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量导入所有缺少transcript数据的物种的transcript信息
"""

import os
import subprocess
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

def get_species_without_transcript():
    """获取所有缺少transcript数据的物种"""
    conn = pymysql.connect(**get_db_config())
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT s.name 
                FROM species s 
                LEFT JOIN transcriptmaster tm ON s.id = tm.genome_id 
                WHERE tm.id IS NULL
            """)
            return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

def find_gff_file(species_name):
    """查找物种的GFF文件"""
    base_path = f'/data/web/CottonOGD/OGD/backend/data/genome/{species_name}'
    if not os.path.exists(base_path):
        return None
    
    # 优先查找包含transcripts的GFF文件
    for filename in sorted(os.listdir(base_path)):
        if 'transcript' in filename.lower() and (filename.endswith('.gff.gz') or filename.endswith('.gff')):
            return os.path.join(base_path, filename)
    
    # 查找以物种名开头的GFF文件（优先gz压缩版）
    for filename in sorted(os.listdir(base_path)):
        if filename.startswith(species_name):
            if filename.endswith('.gff.gz'):
                return os.path.join(base_path, filename)
            elif filename.endswith('.gff'):
                return os.path.join(base_path, filename)
    
    # 查找其他GFF文件（优先gz压缩版）
    for filename in sorted(os.listdir(base_path)):
        if filename.endswith('.gff.gz'):
            return os.path.join(base_path, filename)
        elif filename.endswith('.gff'):
            return os.path.join(base_path, filename)
    
    return None

def main():
    print("获取缺少transcript的物种列表...")
    species_list = get_species_without_transcript()
    print(f"找到 {len(species_list)} 个物种缺少transcript数据")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for species_name in species_list:
        gff_file = find_gff_file(species_name)
        if not gff_file:
            print(f"跳过 {species_name}: 未找到GFF文件")
            skipped_count += 1
            continue
        
        print(f"\n处理物种: {species_name}")
        print(f"  GFF文件: {gff_file}")
        
        # 调用导入脚本
        cmd = [
            'python', '/data/web/CottonOGD/OGD/Script/script/import_transcripts_from_gff.py',
            gff_file, species_name
        ]
        
        try:
            result = subprocess.run(cmd, cwd='/data/web/CottonOGD/OGD/backend', 
                                  capture_output=True, text=True, timeout=3600)
            if result.returncode == 0:
                print(result.stdout.strip())
                success_count += 1
            else:
                print(f"  导入失败: {result.stderr.strip()}")
                failed_count += 1
        except subprocess.TimeoutExpired:
            print(f"  导入超时")
            failed_count += 1
        except Exception as e:
            print(f"  导入异常: {str(e)}")
            failed_count += 1
    
    print("\n" + "=" * 60)
    print(f"批量导入完成！")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print(f"  跳过: {skipped_count}")

if __name__ == "__main__":
    main()
