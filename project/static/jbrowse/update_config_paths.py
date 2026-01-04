#!/usr/bin/env python3
import json
import os
import glob

# 获取所有配置文件
config_files = glob.glob('data/**/config.json', recursive=True)

for config_file in config_files:
    # 获取基因组名称（父目录名称）
    genome_name = os.path.basename(os.path.dirname(config_file))
    if genome_name == 'data':
        continue  # 跳过根目录的配置文件
    
    print(f'更新配置文件: {config_file}')
    print(f'基因组名称: {genome_name}')
    
    # 读取配置文件
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # 更新assemblies中的路径
    if 'assemblies' in config:
        for assembly in config['assemblies']:
            if 'sequence' in assembly and 'adapter' in assembly['sequence']:
                adapter = assembly['sequence']['adapter']
                
                # 更新BgzipFastaAdapter的路径
                if adapter['type'] == 'BgzipFastaAdapter':
                    if 'fastaLocation' in adapter:
                        adapter['fastaLocation']['uri'] = f'/jbrowse/large/{genome_name}/{genome_name}.genome.fa.gz'
                    if 'faiLocation' in adapter:
                        adapter['faiLocation']['uri'] = f'/jbrowse/large/{genome_name}/{genome_name}.genome.fa.gz.fai'
                    if 'gziLocation' in adapter:
                        adapter['gziLocation']['uri'] = f'/jbrowse/large/{genome_name}/{genome_name}.genome.fa.gz.gzi'
    
    # 更新tracks中的路径
    if 'tracks' in config:
        for track in config['tracks']:
            if 'adapter' in track:
                adapter = track['adapter']
                
                # 更新Gff3TabixAdapter的路径
                if adapter['type'] == 'Gff3TabixAdapter':
                    if 'gffGzLocation' in adapter:
                        adapter['gffGzLocation']['uri'] = f'/jbrowse/large/{genome_name}/{genome_name}.gff.gz'
                    if 'index' in adapter and 'location' in adapter['index']:
                        adapter['index']['location']['uri'] = f'/jbrowse/large/{genome_name}/{genome_name}.gff.gz.tbi'
    
    # 写回配置文件
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f'配置文件 {config_file} 更新完成\n')

print('所有配置文件更新完成！')
