#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将物种信息导入到Species_info表中
支持从CSV文件或命令行参数导入
"""

import os
import sys
import csv
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

def import_species_info(data):
    """
    导入物种信息到数据库
    data: 字典，包含物种信息
    """
    conn = pymysql.connect(**get_db_config())
    
    try:
        with conn.cursor() as cursor:
            # 检查物种是否已存在
            cursor.execute("SELECT id FROM species WHERE name = %s", (data['name'],))
            if cursor.fetchone():
                # 更新现有记录
                update_fields = []
                update_values = []
                for key, value in data.items():
                    if key != 'name' and value is not None:
                        update_fields.append(f"{key} = %s")
                        update_values.append(value)
                
                if update_fields:
                    update_sql = f"UPDATE species SET {', '.join(update_fields)} WHERE name = %s"
                    update_values.append(data['name'])
                    cursor.execute(update_sql, update_values)
                    conn.commit()
                    print(f"更新物种: {data['name']}")
                else:
                    print(f"物种已存在，无需更新: {data['name']}")
            else:
                # 插入新记录
                fields = []
                values = []
                placeholders = []
                for key, value in data.items():
                    if value is not None:
                        fields.append(key)
                        values.append(value)
                        placeholders.append('%s')
                
                insert_sql = f"INSERT INTO species ({', '.join(fields)}) VALUES ({', '.join(placeholders)}"
                cursor.execute(insert_sql, values)
                conn.commit()
                print(f"插入新物种: {data['name']}")
        
        return True
    
    except Exception as e:
        print(f"导入失败: {str(e)}")
        conn.rollback()
        return False
    
    finally:
        conn.close()

def import_from_csv(csv_file):
    """从CSV文件导入物种信息"""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 清理空值
            data = {}
            for key, value in row.items():
                if value == '' or value == 'NULL':
                    data[key] = None
                else:
                    data[key] = value
            
            import_species_info(data)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='导入物种信息到数据库')
    parser.add_argument('--csv', help='CSV文件路径')
    parser.add_argument('--name', required=True, help='物种名称')
    parser.add_argument('--cotton_species', help='棉花物种')
    parser.add_argument('--genome_type', help='基因组类型')
    parser.add_argument('--category', help='类别')
    parser.add_argument('--accession', help='登录号')
    parser.add_argument('--ploidy', help='倍性')
    parser.add_argument('--assembling_institution', help='组装机构')
    parser.add_argument('--website', help='网站')
    parser.add_argument('--article', help='文章')
    parser.add_argument('--lai_value', help='LAI值')
    parser.add_argument('--busco', help='BUSCO值')
    parser.add_argument('--genome_size', type=int, help='基因组大小')
    parser.add_argument('--description', help='描述')
    parser.add_argument('--alias', help='实际显示名')
    
    args = parser.parse_args()
    
    if args.csv:
        import_from_csv(args.csv)
    else:
        data = {
            'name': args.name,
            'Cotton_Species': args.cotton_species,
            'Genome_type': args.genome_type,
            'Category': args.category,
            'Accession': args.accession,
            'Ploidy': args.ploidy,
            'Assembling_institution': args.assembling_institution,
            'Website': args.website,
            'Article': args.article,
            'LAI_value': args.lai_value,
            'Busco': args.busco,
            'Genome_size': args.genome_size,
            'description': args.description,
            'alias': args.alias
        }
        import_species_info(data)

if __name__ == "__main__":
    main()