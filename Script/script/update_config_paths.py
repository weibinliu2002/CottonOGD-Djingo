#!/usr/bin/env python3
import json
import os
import sys

# 检查是否提供了正确的参数
if len(sys.argv) != 2:
    print("用法: python update_config_paths.py <genome_config_dir>")
    sys.exit(1)

# 获取基因组配置文件目录
genome_config_dir = sys.argv[1]

# 构建配置文件路径
config_file = os.path.join(genome_config_dir, 'config.json')

# 检查配置文件是否存在
if not os.path.exists(config_file):
    print(f'错误: 配置文件 {config_file} 不存在')
    sys.exit(1)

# 获取基因组名称（目录名称）
genome_name = os.path.basename(genome_config_dir)

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

print(f'配置文件 {config_file} 更新完成')
print('所有配置文件更新完成！')
