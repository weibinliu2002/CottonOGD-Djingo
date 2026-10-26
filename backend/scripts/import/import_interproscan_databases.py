#!/usr/bin/env python3
"""
导入 InterProScan 各数据库到 annotation_detail 表（表2）
包括: Gene3D, CDD, PANTHER, ProSite, HAMAP, PRINTS, SFLD, PIRSF 等
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

INTERPROSCAN_DATA = '/data/wbliu/soft/interproscan-5.77-108.0/data'

def get_or_create_source(source_name, description):
    """获取或创建注释来源"""
    source, _ = AnnotationSource.objects.get_or_create(
        name=source_name,
        defaults={'description': description}
    )
    return source

def parse_gene3d_hmm(hmm_file):
    """解析 Gene3D HMM 文件"""
    with open(hmm_file, 'r') as f:
        entry = {}
        for line in f:
            if line.startswith('NAME  '):
                entry['annotation_id'] = line[6:].strip()
            elif line.startswith('LENG  '):
                try:
                    entry['model_length'] = int(line[6:].strip())
                except:
                    pass
            elif line.startswith('DESC  '):
                entry['description'] = line[6:].strip()
            elif line.startswith('HMM') and entry and 'annotation_id' in entry:
                yield entry
                entry = {}

def parse_cdd_tbl(tbl_file):
    """解析 CDD cddid.tbl 文件"""
    with open(tbl_file, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                yield {
                    'annotation_id': parts[1],  # CDD ID
                    'description': parts[3],  # description
                    'accession': parts[1],
                    'gene_name': parts[2] if len(parts) > 2 else None,  # short name
                    'model_length': int(parts[4]) if len(parts) > 4 else None
                }

def parse_panther_hmm(hmm_dir):
    """解析 PANTHER HMM 文件"""
    for filename in os.listdir(hmm_dir):
        if filename.endswith('.hmm'):
            filepath = os.path.join(hmm_dir, filename)
            with open(filepath, 'r') as f:
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
                    elif line.startswith('HMM') and entry and 'annotation_id' in entry:
                        yield entry
                        entry = {}

def parse_prosite_dat(dat_file):
    """解析 ProSite dat 文件"""
    with open(dat_file, 'r') as f:
        entry = {}
        for line in f:
            if line.startswith('ID   '):
                entry['annotation_id'] = line[5:].split(';')[0].strip()
            elif line.startswith('AC   '):
                entry['accession'] = line[5:].split(';')[0].strip()
            elif line.startswith('DE   '):
                entry['description'] = line[5:].split(';')[0].strip()
            elif line.startswith('//') and entry and 'annotation_id' in entry:
                yield entry
                entry = {}

def parse_pirsf_dat(dat_file):
    """解析 PIRSF dat 文件"""
    with open(dat_file, 'r') as f:
        entry = {}
        for line in f:
            if line.startswith('>PIRSF'):
                if entry and 'annotation_id' in entry:
                    yield entry
                entry = {'annotation_id': line[1:].strip()}
            elif 'annotation_id' in entry and not line.startswith('>') and not line.startswith('BLAST'):
                if 'description' not in entry:
                    entry['description'] = line.strip()
                    yield entry
                    entry = {}

def parse_hamap_prf(prf_file):
    """解析 HAMAP prf 文件"""
    with open(prf_file, 'r') as f:
        entry = {}
        for line in f:
            if line.startswith('ID   '):
                entry['annotation_id'] = line[5:].split(';')[0].strip()
            elif line.startswith('AC   '):
                entry['accession'] = line[5:].split(';')[0].strip()
            elif line.startswith('DE   '):
                entry['description'] = line[5:].split(';')[0].strip()
            elif line.startswith('//') and entry and 'annotation_id' in entry:
                yield entry
                entry = {}

def parse_hamap_hmm_lib(hmm_file):
    """解析 HAMAP hmm.lib 文件"""
    with open(hmm_file, 'r') as f:
        entry = {}
        for line in f:
            if line.startswith('NAME '):
                entry['annotation_id'] = line[5:].strip()
            elif line.startswith('ACC  '):
                entry['accession'] = line[5:].strip()
            elif line.startswith('DESC '):
                entry['description'] = line[5:].strip()
            elif line.startswith('LENG '):
                try:
                    entry['model_length'] = int(line[5:].strip())
                except:
                    pass
            elif line.startswith('HMM') and entry and 'annotation_id' in entry:
                yield entry
                entry = {}

def parse_superfamily_model(model_file):
    """解析 SUPERFAMILY model.tab 文件
    格式: ID  length  sunid  rep_id  description
    """
    with open(model_file, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                yield {
                    'annotation_id': parts[2].strip(),  # sunid 列
                    'description': parts[4].strip() if len(parts) > 4 else None,  # description 列
                    'model_length': int(parts[1].strip()) if parts[1].strip().isdigit() else None,
                }

def parse_sfld_hmm(hmm_file):
    """解析 SFLD HMM 文件"""
    with open(hmm_file, 'r') as f:
        entry = {}
        for line in f:
            if line.startswith('NAME '):
                entry['annotation_id'] = line[5:].strip()
            elif line.startswith('ACC  '):
                entry['accession'] = line[5:].strip()
            elif line.startswith('DESC '):
                entry['description'] = line[5:].strip()
            elif line.startswith('LENG '):
                try:
                    entry['model_length'] = int(line[5:].strip())
                except:
                    pass
            elif line.startswith('HMM') and entry and 'annotation_id' in entry:
                yield entry
                entry = {}

def import_database(source_name, description, parser, file_path, batch_size=10000):
    """通用数据库导入函数"""
    print(f"\n===== 开始导入 {source_name} =====")
    print(f"文件: {file_path}")
    
    source = get_or_create_source(source_name, description)
    print(f"注释来源ID: {source.id}")
    
    # 删除已有数据
    deleted = AnnotationDetail.objects.filter(source=source).delete()[0]
    print(f"已删除 {deleted} 条旧数据")
    
    total_count = 0
    batch = []
    
    for i, data in enumerate(parser(file_path)):
        detail = AnnotationDetail(
            source=source,
            annotation_id=data.get('annotation_id', ''),
            description=data.get('description'),
            accession=data.get('accession'),
            gene_name=data.get('gene_name'),
            model_length=data.get('model_length'),
        )
        batch.append(detail)
        
        if len(batch) >= batch_size:
            with transaction.atomic():
                AnnotationDetail.objects.bulk_create(batch, ignore_conflicts=True)
                total_count += len(batch)
            print(f"已处理 {i+1} 条记录...")
            batch = []
    
    if batch:
        with transaction.atomic():
            AnnotationDetail.objects.bulk_create(batch, ignore_conflicts=True)
            total_count += len(batch)
        print(f"已处理 {i+1} 条记录...")
    
    print(f"导入完成！共插入 {total_count} 条数据")
    return total_count

if __name__ == '__main__':
    total_imported = 0
    
    # 1. Gene3D
    gene3d_file = os.path.join(INTERPROSCAN_DATA, 'gene3d', '4.3.0', 'gene3d_main.hmm')
    if os.path.exists(gene3d_file):
        total_imported += import_database(
            'gene3d', 'Gene3D structural classification',
            parse_gene3d_hmm, gene3d_file
        )
    
    # 2. CDD
    cdd_file = os.path.join(INTERPROSCAN_DATA, 'cdd', '3.21', 'data', 'cddid.tbl')
    if os.path.exists(cdd_file):
        total_imported += import_database(
            'cdd', 'Conserved Domain Database',
            parse_cdd_tbl, cdd_file
        )
    
    # 3. ProSite Patterns
    prosite_file = os.path.join(INTERPROSCAN_DATA, 'prosite', '2025_01', 'prosite_patterns.dat')
    if os.path.exists(prosite_file):
        total_imported += import_database(
            'prosite', 'ProSite patterns database',
            parse_prosite_dat, prosite_file
        )
    
    # 4. PIRSF
    pirsf_file = os.path.join(INTERPROSCAN_DATA, 'pirsf', '3.10', 'pirsf.dat')
    if os.path.exists(pirsf_file):
        total_imported += import_database(
            'pirsf', 'PIR SuperFamily',
            parse_pirsf_dat, pirsf_file
        )
    
    # 5. HAMAP (使用复制的 hmm.lib 文件)
    hamap_file = '/data/web/CottonOGD/OGD/backend/data/hamap.hmm.lib'
    if os.path.exists(hamap_file):
        total_imported += import_database(
            'hamap', 'High-quality Automated and Manual Annotation of Proteins',
            parse_hamap_hmm_lib, hamap_file
        )
    
    # 6. SUPERFAMILY
    superfamily_file = os.path.join(INTERPROSCAN_DATA, 'superfamily', '1.75', 'model.tab')
    if os.path.exists(superfamily_file):
        total_imported += import_database(
            'superfamily', 'SUPERFAMILY database',
            parse_superfamily_model, superfamily_file
        )
    
    # 7. SFLD
    sfld_file = os.path.join(INTERPROSCAN_DATA, 'sfld', '4', 'sfld.hmm')
    if os.path.exists(sfld_file):
        total_imported += import_database(
            'sfld', 'SFLD protein families',
            parse_sfld_hmm, sfld_file
        )
    
    print(f"\n===== 所有数据库导入完成 =====")
    print(f"总计导入: {total_imported} 条数据")