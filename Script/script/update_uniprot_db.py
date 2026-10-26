#!/usr/bin/env python3
"""
导入UniProt数据到数据库，使用完整字段
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

def parse_uniprot_fasta(fasta_file):
    """解析UniProt FASTA文件，提取ID和详细描述"""
    with open(fasta_file, 'r') as f:
        for line in f:
            if line.startswith('>'):
                header = line[1:].strip()  # 去掉 >
                
                # 解析头部，获取Accession ID
                # 格式: sp|Q9FG91|BLH1_ARATH BELL-like homeodomain protein 1 OS=Arabidopsis thaliana OX=3702 GN=BLH1 PE=1 SV=1
                parts = header.split("|")
                if len(parts) >= 3:
                    acc_id = parts[1]  # 取中间的Accession ID作为主要ID
                    
                    data = {
                        'annotation_id': acc_id,
                        'full_header': header,
                        'description': None,
                        'protein_name': None,
                        'gene_name': None,
                        'species': None,
                        'ox': None,
                        'pe': None,
                        'sv': None
                    }
                    
                    # 提取蛋白名/功能描述 (在 OS= 之前，去掉第一个ID部分)
                    if " OS=" in header:
                        before_os = header.split(" OS=")[0]
                        if " " in before_os:
                            # 只保留功能描述部分
                            data['protein_name'] = before_os.split(" ", 1)[1]
                            data['description'] = data['protein_name']  # description只保留功能描述
                    
                    # 提取物种 (在 OS= 和 OX= 之间)
                    if "OS=" in header and "OX=" in header:
                        data['species'] = header.split("OS=")[1].split(" OX=")[0]
                    
                    # 提取基因名 (在 GN= 和 PE= 之间)
                    if "GN=" in header and "PE=" in header:
                        data['gene_name'] = header.split("GN=")[1].split(" PE=")[0]
                    
                    # 提取其他标签
                    for tag in ['OX=', 'PE=', 'SV=']:
                        if tag in header:
                            key = tag.replace('=', '').lower()
                            value = header.split(tag)[1].split(' ')[0]
                            try:
                                data[key] = int(value)
                            except ValueError:
                                data[key] = None
                    
                    yield data

def import_uniprot(fasta_file, source_name='uniprot', batch_size=10000):
    """导入UniProt数据到数据库"""
    print(f"开始导入 UniProt 数据...")
    print(f"文件: {fasta_file}")
    
    # 1. 创建或获取注释来源
    source, created = AnnotationSource.objects.get_or_create(
        name=source_name,
        defaults={'description': 'UniProt/Swiss-Prot 蛋白质注释数据库'}
    )
    print(f"注释来源: {source.name} (ID: {source.id})")
    
    # 2. 批量导入数据
    total_count = 0
    batch = []
    
    for i, data in enumerate(parse_uniprot_fasta(fasta_file)):
        batch.append(AnnotationDetail(
            source=source,
            annotation_id=data['annotation_id'],
            description=data['description'],
            protein_name=data['protein_name'],
            gene_name=data['gene_name'],
            species=data['species'],
            ox=data['ox'],
            pe=data['pe'],
            sv=data['sv'],
            full_header=data['full_header'],
            other_info=None
        ))
        
        if len(batch) >= batch_size:
            with transaction.atomic():
                # 直接 bulk_create 更快
                AnnotationDetail.objects.bulk_create(batch)
                total_count += len(batch)
            
            print(f"已处理 {i+1} 条记录，已插入 {total_count} 条...")
            batch = []
    
    # 处理剩余的记录
    if batch:
        with transaction.atomic():
            AnnotationDetail.objects.bulk_create(batch)
            total_count += len(batch)
        print(f"已处理 {i+1} 条记录，已插入 {total_count} 条...")
    
    print(f"\n导入完成！共插入 {total_count} 条数据")
    
    # 打印统计
    total_in_db = AnnotationDetail.objects.filter(source=source).count()
    print(f"数据库中 {source_name} 共有 {total_in_db} 条记录")

if __name__ == '__main__':
    fasta_file = '/public2/wbliu/data/pfam_data/uniprot/uniprot_sprot.fasta'
    
    if not os.path.exists(fasta_file):
        print(f"错误: 文件不存在 {fasta_file}")
        sys.exit(1)
    
    import_uniprot(fasta_file)
