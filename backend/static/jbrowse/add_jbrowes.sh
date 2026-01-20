#!/bin/bash
name=$1
#name="name"
#$path=$2
genome=$2
gff=$3
path=../../data/genome/${name}
#static=$PWD/../../static/jbrowse/
printf "name: %s\npath: %s\ngenome: %s\ngff: %s\n" $name $path $genome $gff
#bgzip -c $path/$genome > $path/$name.genome.fa.gz -@ 100
#samtools faidx $path/$name.genome.fa.gz 
jbrowse sort-gff $path/$gff | bgzip > $path/$name.gff.gz
tabix $path/$name.gff.gz
jbrowse add-assembly $path/$name.genome.fa.gz --load symlink -n $name --out data/$name --force
jbrowse add-track $path/$name.gff.gz --load symlink -n $name --out data/$name --trackId GFF --force
python update_config_paths.py
