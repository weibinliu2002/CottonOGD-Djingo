#! /bin/bash
name=$1
genome=$2
mrna=$3
cds=$4
protein=$5
blast_path=$6
output=$7
# 检查必填参数是否完整
if [ -z "$name" ] || [ -z "$blast_path" ] || [ -z "$output" ]; then
    echo "Usage: $0 <name> [genome_file] [mrna_file] [cds_file] [protein_file] <blast_path> <output_path>"
    echo "Note: File parameters can be empty if the file doesn't exist"
    exit 1
fi


mkdir -p $output

# 检查makeblastdb命令是否存在
MAKEBLASTDB=$blast_path/makeblastdb

# 仅当文件参数非空时创建blast数据库
if [ -n "$genome" ]; then
    $MAKEBLASTDB -in "$genome" -dbtype nucl -out "$output/genome/${name}" &
fi
if [ -n "$mrna" ]; then
    $MAKEBLASTDB -in "$mrna" -dbtype nucl -out "$output/mrna/${name}" &
fi
if [ -n "$cds" ]; then
    $MAKEBLASTDB -in "$cds" -dbtype nucl -out "$output/cds/${name}" &
fi
if [ -n "$protein" ]; then
    $MAKEBLASTDB -in "$protein" -dbtype prot -out "$output/protein/${name}" &
fi

# 等待所有后台进程完成
wait

echo "Blast database creation completed for $name"
