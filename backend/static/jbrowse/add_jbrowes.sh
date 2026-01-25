#!/bin/bash
name=$1
genome=$2
gff=$3
path=../../data/genome/${name}

# 检查参数是否存在
if [ -z "$name" ] || [ -z "$genome" ] || [ -z "$gff" ]; then
  echo "Usage: $0 <name> <genome_file> <gff_file>"
  exit 1
fi

# 检查文件是否存在
if [ ! -f "$path/$name.genome.fa.gz" ]; then
  echo "Error: Genome file not found: $path/$name.genome.fa.gz"
  exit 1
fi

if [ ! -f "$path/$name.gff.gz" ]; then
  echo "Error: GFF file not found: $path/$name.gff.gz"
  exit 1
fi

# 执行 jbrowse 命令
echo "Adding assembly for $name..."
jbrowse add-assembly "$path/$name.genome.fa.gz" --load symlink --name "$name" --out "data/$name" --force
echo "Adding track for $name..."
jbrowse add-track "$path/$name.gff.gz" --load symlink --name "$name" --out "data/$name" --trackId "GFF" --force
