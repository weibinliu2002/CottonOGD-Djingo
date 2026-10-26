#!/bin/bash

# 修复 GFF 文件：确保 start <= end，并按位置排序
# 使用方法：fix_gff.sh <input_gff> <output_gff>

input_gff="$1"
output_gff="$2"

cat "$input_gff" | awk -F'\t' -v OFS='\t' '/^#/{print;next} $4>$5{temp=$4;$4=$5;$5=temp} {print}' | LC_ALL=C sort -k1,1 -k4,4n -t$'\t' | bgzip > "$output_gff"
tabix "$output_gff"