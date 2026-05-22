#!/usr/bin/bash
Ref_genoeme=$1
query_genome=$2
prefix=$3
work_dir=$PWD
temp_dir=$work_dir/temp
if [ ! -d $temp_dir ]; then
    mkdir -p $temp_dir
fi
if [ ! -d syri_out ]; then
    mkdir -p syri_out
fi
mkdir -p $temp_dir/$prefix
Rscript pre_fasta.R $Ref_genoeme $query_genome $temp_dir/$prefix
# fa1_sorted.fa fa2_sorted.fa
# fa1_sorted.fa fa2_sorted.fa
# fa1_sorted.fa fa2_sorted.fa
# fa1_sorted.fa fa2_sorted.fa
#echo "===== Start minimap2 at $(date) ====="
time mm2plus -ax asm5 --eqx -t 64 $temp_dir/$prefix/fa1_sorted.fa $temp_dir/$prefix/fa2_sorted.fa | samtools sort -@ 64  > $temp_dir/$prefix/$prefix.bam
#echo "===== Finish minimap2 at $(date) ====="
#echo "===== Start SyRI at $(date) ====="
time syri -c $temp_dir/$prefix/$prefix.bam -r $temp_dir/$prefix/fa1_sorted.fa -q $temp_dir/$prefix/fa2_sorted.fa -F B --dir syri_out --prefix $prefix
#echo "===== Finish SyRI at $(date) ====="
