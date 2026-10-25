#!/usr/bin/env python3
"""
通用注释数据库导入脚本
支持: UniProt, Pfam, SMART, eggNOG
"""

import os
import sys
import django

# 设置Django环境
sys.path.insert(0, '/data/web/CottonOGD/OGD/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from CottonOGD.models import AnnotationSource, AnnotationDetail
from django.db import transaction

def parse_pfam_dat(pfam_file):
    """解析Pfam的pfam_a.dat文件"""
    with open(pfam_file, 'r') as f:
        entry = {}
        for line in f:
            if line.startswith('#=GF '):
                parts = line[5:].split(None, 1)
                if len(parts) == 2:
                    key = parts[0]
                    value = parts[1].strip()
                    if key == 'ID':
                        entry['annotation_id'] = value
                    elif key == 'AC':
                        entry['accession'] = value
                    elif key == 'DE':
                        entry['description'] = value
                    elif key == 'TP':
                        entry['pfam_type'] = value
                    elif key == 'CL':
                        entry['clan'] = value
                    elif key == 'ML':
                        try:
                            entry['model_length'] = int(value)
                        except:
                            pass
                    elif key == 'GA':
                        try:
                            entry['gathering_threshold'] = float(value.split(';')[0])
                        except:
                            pass
            elif line.startswith('//') and entry:
                yield entry
                entry = {}

def parse_smart_hmms(smart_file):
    """解析SMART的HMM文件"""
    with open(smart_file, 'r') as f:
        entry = {}
        for line in f:
            if line.startswith('NAME  '):
                entry['annotation_id'] = line[6:].strip()
            elif line.startswith('ACC   '):
                entry['accession'] = line[6:].strip()
            elif line.startswith('DESC  '):
                entry['description'] = line[6:].strip()
            elif line.startswith('LENG  '):
                try:
                    entry['model_length'] = int(line[6:].strip())
                except:
                    pass
            elif line.startswith('HMM   '):
                if entry and 'annotation_id' in entry:
                    yield entry
                    entry = {}

def import_database(source_name, description, parser, file_path, batch_size=10000):
    """通用数据库导入函数"""
    print(f"\n===== 开始导入 {source_name} =====")
    print(f"文件: {file_path}")
    
    # 1. 创建或获取注释来源
    source, _ = AnnotationSource.objects.get_or_create(
        name=source_name,
        defaults={'description': description}
    )
    print(f"注释来源ID: {source.id}")
    
    # 2. 删除已有数据
    deleted = AnnotationDetail.objects.filter(source=source).delete()[0]
    print(f"已删除 {deleted} 条旧数据")
    
    # 3. 批量导入
    total_count = 0
    batch = []
    
    for i, data in enumerate(parser(file_path)):
        detail = AnnotationDetail(
            source=source,
            annotation_id=data.get('annotation_id', ''),
            description=data.get('description'),
            accession=data.get('accession'),
            pfam_type=data.get('pfam_type'),
            clan=data.get('clan'),
            model_length=data.get('model_length'),
            gathering_threshold=data.get('gathering_threshold'),
        )
        batch.append(detail)
        
        if len(batch) >= batch_size:
            with transaction.atomic():
                AnnotationDetail.objects.bulk_create(batch)
                total_count += len(batch)
            print(f"已处理 {i+1} 条记录...")
            batch = []
    
    if batch:
        with transaction.atomic():
            AnnotationDetail.objects.bulk_create(batch)
            total_count += len(batch)
        print(f"已处理 {i+1} 条记录...")
    
    print(f"导入完成！共插入 {total_count} 条数据")
    return total_count

if __name__ == '__main__':
    # 导入Pfam
    pfam_file = '/data/wbliu/soft/interproscan-5.77-108.0/data/pfam/38.1/pfam_a.dat'
    if os.path.exists(pfam_file):
        import_database(
            source_name='pfam',
            description='Pfam protein family database',
            parser=parse_pfam_dat,
            file_path=pfam_file
        )
    else:
        print(f"警告: Pfam文件不存在 {pfam_file}")
    
    # 导入SMART
    smart_file = '/data/wbliu/soft/interproscan-5.77-108.0/data/smart/9.0/smart.HMMs'
    if os.path.exists(smart_file):
        import_database(
            source_name='smart',
            description='SMART protein domain database',
            parser=parse_smart_hmms,
            file_path=smart_file
        )
    else:
        print(f"警告: SMART文件不存在 {smart_file}")
    
    print("\n===== 所有数据库导入完成 =====")
