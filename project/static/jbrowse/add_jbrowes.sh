#!/bin/bash
name=$1
path=$2
genome=$3
gff=$4
#static=$PWD/../../static/jbrowse/
bgzip -c $path/$genome > $path/$name.genome.fa.gz -@ 12
samtools faidx $path/$name.genome.fa.gz 
jbrowse sort-gff $path/$gff | bgzip > $path/$name.gff.gz
tabix $path/$name.gff.gz
jbrowse add-assembly $path/$name.genome.fa.gz --load copy -n $name --out data/$name 
jbrowse add-track $path/$name.gff.gz --load copy -n $name --out data/$name --trackId GFF
