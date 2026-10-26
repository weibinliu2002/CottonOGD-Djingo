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
bgzip -c "$genome" > "$genome_path/$name.genome.fa.gz" -@ 100
samtools faidx "$genome_path/$name.genome.fa.gz" 

# 排序并压缩GFF文件，创建索引
if [[ "{input.gff_file}" == *.gz ]]; then
    CAT_CMD="zcat"
else
    CAT_CMD="cat"
fi

# 提取头部


$CAT_CMD $gff | awk -F'\t' -v OFS='\t' '/^#/{print;next} $4>$5{temp=$4;$4=$5;$5=temp} {print}' | LC_ALL=C sort -k1,1 -k4,4n -t$'\t' | bgzip > "$genome_path/$name.gff.gz"



tabix "$genome_path/$name.gff.gz"

# 添加组装和轨道到jbrowse
if [ -f "$jbrowse_path/config.json" ]; then
    # config.json 存在，说明之前成功过，什么都不做，直接跳过
    true 
else
    # config.json 不存在，说明从未成功添加过，或者上次失败了
    # 既然走到这里，就要执行，但执行前先清理可能残留的失败文件，防止报错
    rm -f "$jbrowse_path/$name.genome.fa.gz" "$jbrowse_path/$name.genome.fa.gz.fai" "$jbrowse_path/$name.genome.fa.gz.gzi"
    
    jbrowse add-assembly "$genome_path/$name.genome.fa.gz" \
        --load symlink \
        -n "$name" \
        --out "$jbrowse_path" \
        --force
fi


jbrowse add-track "$genome_path/$name.gff.gz" --load symlink -n "$name" --out "$jbrowse_path" --trackId GFF --force

# 仅当提供了script_path时更新配置路径
if [ -n "$Script_path" ]; then
    python "$Script_path/update_config_paths.py" "$jbrowse_path"
fi
