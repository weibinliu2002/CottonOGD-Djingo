#!/bin/bash
set -e

genome_name=$1
genome_dir="/data/web/CottonOGD/OGD/backend/data/genome"

if [ -z "$genome_name" ]; then
    echo "Usage: $0 <genome_name>"
    exit 1
fi

cd "$genome_dir/$genome_name"

prefix="$genome_name"
workdir="tmp/$prefix"
resultdir="result/$prefix"

mkdir -p "$workdir"
cd "$workdir"

if [ -f "../../$prefix.fa" ]; then
    genome_file="../../$prefix.fa"
elif [ -f "../../$prefix.genome.fa" ]; then
    genome_file="../../$prefix.genome.fa"
elif [ -f "../../$prefix.genome.fa.gz" ]; then
    genome_file="../../$prefix.genome.fa.gz"
else
    genome_file=$(ls -1 ../../*.fa ../../*.fa.gz 2>/dev/null | head -1)
fi

if [ ! -f "$genome_file" ]; then
    echo "Error: Cannot find genome FASTA file for $genome_name"
    exit 1
fi

filename=$(basename "$genome_file")

[ -f "$filename" ] && rm "$filename"
ln -fs "../$genome_file" .

newfilename=rename_genome.fa
grep '>' "$filename" | sed 's/>//' > original_ids.txt
awk 'NR>=1{print $0 "\t" "seq" NR}' original_ids.txt > id_map.txt
awk -F'\t' '
NR==FNR {
    map[$1]=$2
    next
}
$0 ~ /^>/ {
    id = substr($0, 2)
    if (id in map) {
        print ">" map[id]
        next
    }
}
{ print }
' id_map.txt "$filename" > "$newfilename"

LTR_FINDER_parallel -seq "$newfilename" -threads 7 -harvest_out -size 1000000 -time 300 &

(
    gt suffixerator -db "$newfilename" -indexname "$newfilename" -tis -suf -lcp -des -ssp -sds -dna &&
    gt ltrharvest -index "$newfilename" -minlenltr 100 -maxlenltr 7000 -mintsd 4 -maxtsd 6 -motif TGCA -motifmis 1 -similar 85 -vic 10 -seed 20 -seqids yes > "$newfilename.harvest.scn"
) &

wait

if [ -f "$newfilename.finder.combine.scn" ]; then
    cat "$newfilename.harvest.scn" "$newfilename.finder.combine.scn" > "$prefix.rawLTR.scn"
else
    cp "$newfilename.harvest.scn" "$prefix.rawLTR.scn"
fi

LTR_retriever -genome "$newfilename" -inharvest "$prefix.rawLTR.scn" -threads 35
LAI -genome "$newfilename" -intact "$newfilename.pass.list" -all "$newfilename.out" -t 20

cd ../..

mkdir -p "result/$prefix"
mv "tmp/$prefix/"* "result/$prefix/"
mv "result/$prefix/$newfilename.out.LAI" "result/$prefix/$prefix.out.LAI"

rm -rf tmp/

echo "Finished $prefix"
