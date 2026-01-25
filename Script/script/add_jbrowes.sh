#!/bin/bash

name=$1
genome=$2
gff=$3
genome_path=$4
jbrowse_path=$5
Script_path=$6

# 检查必填参数是否完整
if [ -z "$name" ] || [ -z "$genome" ] || [ -z "$gff" ] || [ -z "$genome_path" ] || [ -z "$jbrowse_path" ]; then
    echo "Usage: $0 <name> <genome_file> <gff_file> <genome_path> <jbrowse_path> [script_path]"
    echo "Note: script_path is optional for updating config paths"
    exit 1
fi

# 检查必要的命令是否存在
for cmd in bgzip samtools jbrowse; do
    if ! command -v $cmd &> /dev/null; then
        echo "Error: $cmd command not found"
        exit 1
    fi
done

printf "name: %s\ngenome: %s\ngff: %s\ngenome_path: %s\njbrowse_path: %s\n" "$name" "$genome" "$gff" "$genome_path" "$jbrowse_path"

# 压缩基因组文件并创建索引
bgzip -c "$genome_path/$genome" > "$genome_path/$name.genome.fa.gz" -@ 100
samtools faidx "$genome_path/$name.genome.fa.gz" 

# 排序并压缩GFF文件，创建索引
jbrowse sort-gff "$genome_path/$gff" | bgzip > "$genome_path/$name.gff.gz"
tabix "$genome_path/$name.gff.gz"

# 添加组装和轨道到jbrowse
jbrowse add-assembly "$genome_path/$name.genome.fa.gz" --load symlink -n "$name" --out "$jbrowse_path" --force
jbrowse add-track "$genome_path/$name.gff.gz" --load symlink -n "$name" --out "$jbrowse_path" --trackId GFF --force

# 仅当提供了script_path时更新配置路径
if [ -n "$Script_path" ]; then
    python "$Script_path/update_config_paths.py" "$jbrowse_path"
fi
