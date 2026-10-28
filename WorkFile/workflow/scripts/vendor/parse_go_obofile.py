# -*- coding: utf-8 -*-
# @Time : 2019/10/21 10:49
# @Author : Zhongyi Hua
# @FileName: parse_go_obofile.py
# @Usage: 解析 GO OBO 文件，基于层级关系剔除 disease 分支及动物特有/obsolete term
# @E-mail: njbxhzy@hotmail.com
import pandas as pd
import argparse
import re
from collections import defaultdict, deque

def main(input_path, output_path):
    lev_dict = {'molecular_function': 'MF', 'biological_process': 'BP', 'cellular_component': 'CC'}
    dict_list = []
    
    # --- 第一步：构建 GO 层级关系图，找出 disease 的所有后代 ---
    # 记录父子关系：key是父节点，value是子节点列表
    is_a_dict = defaultdict(list)
    all_terms_data = {}  # 临时存储所有 term 的基本信息
    
    with open(input_path, 'r') as f:
        current_id = None
        for line in f:
            line = line.strip()
            if line == '[Term]':
                current_id = None
            elif line.startswith('id: GO:'):
                current_id = line.split('id: ', 1)[1]
                all_terms_data[current_id] = {'GO': current_id}
            elif current_id and line.startswith('name:'):
                all_terms_data[current_id]['Description'] = line.split('name: ', 1)[1]
            elif current_id and line.startswith('namespace:'):
                ns = line.split('namespace: ', 1)[1]
                all_terms_data[current_id]['level'] = lev_dict.get(ns)
            elif current_id and line.startswith('is_a:'):
                # is_a 格式: is_a: GO:0008150 ! biological_process
                parent_id = line.split('is_a: ', 1)[1].split(' ')[0]
                is_a_dict[parent_id].append(current_id)

    # 广度优先搜索 (BFS) 找到 disease 及其所有子节点
    disease_root = "GO:0042221"
    disease_descendants = set()
    
    if disease_root in all_terms_data:
        queue = deque([disease_root])
        while queue:
            current = queue.popleft()
            if current not in disease_descendants:
                disease_descendants.add(current)
                # 将当前节点的所有子节点加入队列
                for child in is_a_dict.get(current, []):
                    if child not in disease_descendants:
                        queue.append(child)

    # --- 第二步：关键词黑名单（用于兜底过滤名称中含有动物特异词汇的 term）---
    blacklist = r'cancer|tumor|tumour|carcinoma|inflammation|inflammatory|immune|immunity|antibody|antigen|lymphocyte|macrophage|phagocytosis|virus|viral|infection|sepsis|nerve|neural|brain|synapse|hormone|endocrine|leukemia|melanoma|obsolete'

    # --- 第三步：再次遍历文件，生成最终过滤后的 DataFrame ---
    with open(input_path, 'r') as f:
        current_term = {}
        for line in f:
            line = line.strip()
            
            if line == '[Term]':
                # 判断上一个 term 是否有效并存入列表
                if current_term.get('GO') and current_term.get('Description') and current_term.get('level'):
                    go_id = current_term['GO']
                    desc = current_term['Description']
                    
                    # 核心过滤逻辑：ID在disease后代中 或 名称命中黑名单 则跳过
                    if go_id not in disease_descendants and not re.search(blacklist, desc, re.IGNORECASE):
                        dict_list.append(current_term)
                current_term = {}
                
            elif line.startswith('id: GO:'):
                current_term['GO'] = line.split('id: ', 1)[1]
            elif line.startswith('name:'):
                current_term['Description'] = line.split('name: ', 1)[1]
            elif line.startswith('namespace:'):
                ns = line.split('namespace: ', 1)[1]
                current_term['level'] = lev_dict.get(ns)
            elif line.startswith('alt_id: GO:'):
                # 处理 alt_id
                alt_id = line.split('alt_id: ', 1)[1]
                alt_term = {
                    "GO": alt_id,
                    "Description": current_term.get('Description'),
                    "level": current_term.get('level')
                }
                if alt_term['Description'] and alt_id not in disease_descendants and not re.search(blacklist, alt_term['Description'], re.IGNORECASE):
                    dict_list.append(alt_term)
                    
        # 处理文件最后一个 term
        if current_term.get('GO') and current_term.get('Description') and current_term.get('level'):
            go_id = current_term['GO']
            desc = current_term['Description']
            if go_id not in disease_descendants and not re.search(blacklist, desc, re.IGNORECASE):
                dict_list.append(current_term)

    # 输出结果
    go_annotation = pd.DataFrame(dict_list)[["GO", "Description", "level"]]
    go_annotation.dropna().to_csv(output_path, sep="\t", index=False)
    print(f"Done! Parsed {len(go_annotation)} valid GO terms.")
    print(f"Filtered out {len(disease_descendants)} disease-related terms and keyword-matched terms.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Parse GO OBO file, filter disease hierarchy & animal terms, save as TSV")
    parser.add_argument('-i', '--input_file', required=True,
                        help='<filepath>  The GO database file in OBO format (go-basic.obo)')
    parser.add_argument('-o', '--output_file', required=True,
                        help='<filepath>  The result TSV path (e.g., gp.tb)')
    args = parser.parse_args()
    main(args.input_file, args.output_file)

