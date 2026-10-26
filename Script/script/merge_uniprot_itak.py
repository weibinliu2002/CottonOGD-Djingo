#!/usr/bin/env python3
"""
将 UniProt 注释与 iTAK 结果合并的脚本

功能：
1. 加载 total_uniprot.csv 数据
2. 加载 SpeciesIDs.txt 物种映射
3. 为每个基因组的 TF/TR/Kinase 添加 UniProt 注释
4. 从 uniprot_sprot.fasta 解析 description

输入文件：
- /data/wbliu/data/CottonOGD/Function/uniprot/total_uniprot.csv
- /data/wbliu/data/CottonOGD/pandagma/work3/00_data/SpeciesIDs.txt
- /data/wbliu/data/CottonOGD/iTAK/iTAK_result/{物种}.pro/tf_classification.txt
- /data/wbliu/data/CottonOGD/iTAK/iTAK_result/{物种}.pro/shiu_classification.txt
- /public2/wbliu/data/pfam_data/uniprot/uniprot_sprot.fasta

输出：
- 每个物种目录下生成带 UniProt 注释的文件
"""

import os
import pandas as pd
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

def load_species_ids(filepath):
    """加载物种ID映射"""
    species_num_map = {}  # 物种编号 -> 物种名称
    species_name_map = {}  # 物种名称 -> 物种编号
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    num = parts[0].strip()
                    name = parts[1].strip()
                    species_num_map[num] = name
                    species_name_map[name] = num
    return species_num_map, species_name_map

def load_uniprot_data(filepath):
    """加载 UniProt 数据"""
    df = pd.read_csv(filepath)
    print(f"加载 UniProt 数据: {len(df)} 条")
    return df

def parse_fasta_descriptions(filepath):
    """解析 FASTA 文件中的 description"""
    descriptions = {}
    with open(filepath, 'r') as f:
        current_id = None
        for line in f:
            if line.startswith('>'):
                # 解析描述行: >sp|Q6GZX4|001R_FRG3G description...
                parts = line[1:].strip().split('|', 2)
                if len(parts) >= 3:
                    uniprot_id = parts[1]
                    description = parts[2].split(' OS=')[0] if ' OS=' in parts[2] else parts[2]
                    descriptions[uniprot_id] = description.strip()
    print(f"解析 FASTA description: {len(descriptions)} 条")
    return descriptions

def process_species_wrapper(args):
    """多进程包装函数"""
    species_name, species_num, uniprot_data, descriptions_dict, itak_dir = args
    # 在子进程中重新创建 DataFrame
    uniprot_df = pd.DataFrame(uniprot_data)
    descriptions = descriptions_dict
    return process_species(species_name, species_num, uniprot_df, descriptions, itak_dir)

def process_species(species_name, species_num, uniprot_df, descriptions, itak_dir):
    """处理单个物种"""
    species_dir = os.path.join(itak_dir, f"{species_name}.pro")
    if not os.path.exists(species_dir):
        print(f"  跳过: {species_name} (目录不存在)")
        return False
    
    # 输出目录固定为 iTAK 结果目录
    out_dir = species_dir
    
    # 筛选该物种的 UniProt 数据
    species_uniprot = uniprot_df[uniprot_df['species'] == int(species_num)]
    print(f"  物种 {species_name}: {len(species_uniprot)} 条 UniProt 记录")
    
    # 收集所有基因数据
    all_genes = []
    
    # 1. 读取 tf_classification.txt (TF/TR)
    tf_file = os.path.join(species_dir, 'tf_classification.txt')
    if os.path.exists(tf_file):
        tf_df = pd.read_csv(tf_file, sep='\t', header=None, 
                           names=['gene_id', 'class', 'type', 'subclass'])
        tf_df['family'] = tf_df['class']  # family 列
        tf_df['gene_type'] = 'TF'  # 标记类型
        all_genes.append(tf_df)
        print(f"    TF/TR: {len(tf_df)} 条")
    
    # 2. 读取 shiu_classification.txt (Kinase)
    kinase_file = os.path.join(species_dir, 'shiu_classification.txt')
    if os.path.exists(kinase_file):
        kinase_df = pd.read_csv(kinase_file, sep='\t', header=None,
                               names=['gene_id', 'family'])
        kinase_df['class'] = kinase_df['family']  # class 列
        kinase_df['type'] = 'kinase'  # 标记类型
        kinase_df['subclass'] = ''  # 空列
        kinase_df['gene_type'] = 'kinase'  # 标记类型
        all_genes.append(kinase_df)
        print(f"    Kinase: {len(kinase_df)} 条")
    
    # 3. 合并所有基因数据
    if all_genes:
        merged_df = pd.concat(all_genes, ignore_index=True)
        
        # 4. 与 UniProt 数据合并（保留所有在 iTAK 或 UniProt 中存在的基因）
        final_df = merged_df.merge(species_uniprot, left_on='gene_id', right_on='V2', how='outer')
        
        # 5. 添加 description
        final_df['uniprot_description'] = final_df['uniprotid'].map(descriptions)
        
        # 6. 保存到新文件
        out_file = os.path.join(out_dir, 'tf_tr_kinase_with_uniprot.txt')
        final_df.to_csv(out_file, sep='\t', index=False, na_rep='')
        print(f"    合并后总计: {len(final_df)} 条")
    else:
        print(f"    未找到任何基因数据")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='合并 UniProt 注释与 iTAK 结果')
    parser.add_argument('--species', '-s', help='只处理指定物种（逗号分隔）')
    args = parser.parse_args()
    
    # 文件路径
    uniprot_file = '/data/wbliu/data/CottonOGD/Function/uniprot/total_uniprot.csv'
    species_ids_file = '/data/wbliu/data/CottonOGD/pandagma/work3/00_data/SpeciesIDs.txt'
    itak_dir = '/data/wbliu/data/CottonOGD/iTAK/iTAK_result'
    fasta_file = '/public2/wbliu/data/pfam_data/uniprot/uniprot_sprot.fasta'
    
    print("===== 加载数据 =====")
    
    # 加载物种映射
    species_num_map, species_name_map = load_species_ids(species_ids_file)
    print(f"加载物种映射: {len(species_num_map)} 个物种")
    
    # 加载 UniProt 数据
    uniprot_df = load_uniprot_data(uniprot_file)
    
    # 加载 FASTA description
    descriptions = parse_fasta_descriptions(fasta_file)
    
    print("\n===== 处理物种 =====")
    
    # 获取要处理的物种列表
    if args.species:
        species_list = args.species.split(',')
    else:
        species_list = sorted(species_name_map.keys())
    
    # 准备多进程参数
    # 将 DataFrame 和 dict 转换为可序列化的格式
    uniprot_data = uniprot_df.to_dict('records')
    
    process_args = []
    for species_name in species_list:
        if species_name not in species_name_map:
            print(f"警告: 物种 {species_name} 不在映射表中，跳过")
            continue
        
        species_num = species_name_map[species_name]
        process_args.append((species_name, species_num, uniprot_data, descriptions, itak_dir))
    
    # 使用多进程处理
    total_processed = 0
    max_workers = min(len(process_args), os.cpu_count() or 4)
    
    print(f"使用 {max_workers} 个进程处理 {len(process_args)} 个物种")
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_species_wrapper, args): args[0] for args in process_args}
        
        for future in as_completed(futures):
            species_name = futures[future]
            try:
                future.result()
                total_processed += 1
                print(f"完成: {species_name} ({total_processed}/{len(process_args)})")
            except Exception as e:
                print(f"错误处理 {species_name}: {e}")
    
    print(f"\n===== 完成 =====")
    print(f"处理物种数: {total_processed}")

if __name__ == '__main__':
    main()