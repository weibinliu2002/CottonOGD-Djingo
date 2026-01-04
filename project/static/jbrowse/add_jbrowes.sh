#!/bin/bash
name=$1
path=$2
genome=$3
gff=$4
#static=$PWD/../../static/jbrowse/
printf "name: %s\npath: %s\ngenome: %s\ngff: %s\n" $name $path $genome $gff
bgzip -c $path/$genome > $path/$name.genome.fa.gz -@ 100
samtools faidx $path/$name.genome.fa.gz 
jbrowse sort-gff $path/$gff | bgzip > $path/$name.gff.gz
tabix $path/$name.gff.gz
jbrowse add-assembly $path/$name.genome.fa.gz --load symlink -n $name --out data/$name 
jbrowse add-track $path/$name.gff.gz --load symlink -n $name --out data/$name --trackId GFF
