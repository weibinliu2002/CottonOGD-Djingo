#!/usr/bin/env python3
"""
导入 eggNOG 数据库
"""

import os
import sys
import sqlite3
import django

# 设置Django环境
sys.path.insert(0, '/data/web/CottonOGD/OGD/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from CottonOGD.models import AnnotationSource, AnnotationDetail
from django.db import transaction

def import_eggnog(eggnog_db, batch_size=10000):
    """导入eggNOG数据库"""
    print("\n===== 开始导入 eggNOG =====")
    print(f"文件: {eggnog_db}")
    
    # 1. 创建或获取注释来源
    source, _ = AnnotationSource.objects.get_or_create(
        name='eggnog',
        defaults={'description': 'eggNOG orthologous groups database'}
    )
    print(f"注释来源ID: {source.id}")
    
    # 2. 删除已有数据
    deleted = AnnotationDetail.objects.filter(source=source).delete()[0]
    print(f"已删除 {deleted} 条旧数据")
    
    # 3. 连接SQLite数据库并导入
    conn = sqlite3.connect(eggnog_db)
    cursor = conn.cursor()
    
    # 获取数据总数
    cursor.execute("SELECT COUNT(*) FROM og")
    total_rows = cursor.fetchone()[0]
    print(f"总记录数: {total_rows}")
    
    # 分批读取
    offset = 0
    total_count = 0
    
    while True:
        cursor.execute("SELECT og, level, description, COG_categories FROM og LIMIT ? OFFSET ?", 
                      (batch_size, offset))
        rows = cursor.fetchall()
        
        if not rows:
            break
        
        batch = []
        for og, level, description, cog_categories in rows:
            detail = AnnotationDetail(
                source=source,
                annotation_id=og,
                description=description,
                eggnog_og=og,
                cog_category=level,
                cog_class=cog_categories,
            )
            batch.append(detail)
        
        with transaction.atomic():
            AnnotationDetail.objects.bulk_create(batch)
            total_count += len(batch)
        
        print(f"已处理 {total_count}/{total_rows} 条记录...")
        offset += batch_size
    
    conn.close()
    print(f"导入完成！共插入 {total_count} 条数据")
    return total_count

if __name__ == '__main__':
    eggnog_db = '/public2/wbliu/data/pfam_data/eggnog/eggnog.db'
    
    if os.path.exists(eggnog_db):
        import_eggnog(eggnog_db)
    else:
        print(f"警告: eggNOG文件不存在 {eggnog_db}")
    
    print("\n===== eggNOG导入完成 =====")
