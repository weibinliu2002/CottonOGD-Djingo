#!/bin/bash
# 初始化变量
name=""
genome=""
mrna=""
cds=""
cdna=""
protein=""
gff=""
workdir=""

# 解析命名参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            name="$2"
            shift 2
            ;;
        -g|--genome)
            genome="$2"
            shift 2
            ;;
        -m|--mrna)
            mrna="$2"
            shift 2
            ;;
        -c|--cds)
            cds="$2"
            shift 2
            ;;
        -d|--cdna)
            cdna="$2"
            shift 2
            ;;
        -p|--protein)
            protein="$2"
            shift 2
            ;;
        -f|--gff)
            gff="$2"
            shift 2
            ;;
        -w|--workdir)
            workdir="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 -n <name> [-g <genome_file>] [-m <mrna_file>] [-c <cds_file>] [-d <cdna_file>] [-p <protein_file>] [-f <gff_file>] -w <workdir>"
            echo "Note: All file parameters except name and workdir are optional and can be empty"
            exit 1
            ;;
    esac
done

# 检查必填参数是否完整
if [ -z "$name" ] || [ -z "$workdir" ]; then
    echo "Usage: $0 -n <name> [-g <genome_file>] [-m <mrna_file>] [-c <cds_file>] [-d <cdna_file>] [-p <protein_file>] [-f <gff_file>] -w <workdir>"
    echo "Note: All file parameters except name and workdir are optional and can be empty"
    exit 1
fi

# 检查工作目录是否存在
if [ ! -d "$workdir" ]; then
    echo "Error: Workdir not found: $workdir"
    exit 1
fi

#PATH
genome_path=$workdir/backend/data/genome/$name
blastdb_path=$workdir/backend/data/blast_db/CottonOGD/${name}
jbrowse_path=$workdir/backend/startup/jbrowse/data/$name
Script_path=$workdir/Script/script
blast_path=$workdir/backend/soft/UNIX/blast+/bin
TF_gene_family=$workdir/backend/data/TF_family/$name
if [ ! -d "$TF_gene_family" ]; then
    mkdir -p $TF_gene_family
fi

if [ ! -d "$blastdb_path" ]; then
    mkdir -p $blastdb_path
fi

#file_path
genome_file=""
if [ -n "$genome" ]; then
    genome_file=$genome_path/$genome
fi

mrna_file=""
if [ -n "$mrna" ]; then
    mrna_file=$genome_path/$mrna
fi

cds_file=""
if [ -n "$cds" ]; then
    cds_file=$genome_path/$cds
fi

cdna_file=""
if [ -n "$cdna" ]; then
    cdna_file=$genome_path/$cdna
fi

protein_file=""
if [ -n "$protein" ]; then
    protein_file=$genome_path/$protein
fi

gff_file=""
if [ -n "$gff" ]; then
    gff_file=$genome_path/$gff
fi


#prepare genemaster
if [ -n "$genome" ] && [ -n "$gff" ]; then
    echo '1 准备genemaster'
    Rscript $Script_path/genemaster.R "$genome" "$gff_file"
    echo '1 genemaster准备完成'
fi

#add jbrowes
if [ -n "$genome" ] && [ -n "$gff" ]; then
    echo '2 添加jbrowes'
    bash $Script_path/add_jbrowes.sh "$name" "$genome" "$gff" "$genome_path" "$jbrowse_path" "$Script_path"
    echo '2 jbrowes添加完成'
    new_gff_file=$genome_path/${name}.gff.gz
    new_genome_file=$genome_path/${name}.genome.fa.gz
fi

#prepare gene_seq database
echo '3 准备gene_seq数据库'
Rscript $Script_path/extract_seq.R -i "$name" -g "$new_genome_file" -f "$new_gff_file" -m "$mrna_file" -d "$cdna_file" -c "$cds_file" -p "$protein_file" -o "$genome_path"
echo '3 gene_seq数据库准备完成'

#prepare longest protein sequence
echo '4 准备最长序列'
pro_longest_files=$genome_path/${name}.pro_longest.fasta
cds_longest_files=$genome_path/${name}.cds_longest.fasta
mran_longest_files=$genome_path/${name}.mrna_longest.fasta

if [ -n "$protein" ]; then
    Rscript $Script_path/longest.R $protein_file $pro_longest_files
    if [ -f "$pro_longest_files" ]; then
        echo '4 最长蛋白质序列准备完成'
    fi
fi

if [ -n "$cdna" ]; then
    Rscript $Script_path/longest.R $cdna_file $cds_longest_files
    if [ -f "$cds_longest_files" ]; then
        echo '4 最长cds序列准备完成'
    fi
fi

if [ -n "$mrna" ]; then
    Rscript $Script_path/longest.R $mrna_file $mran_longest_files
    if [ -f "$mran_longest_files" ]; then
        echo '4 最长mrna序列准备完成'
    fi
fi

echo '4 最长序列准备完成'

#prepare blastdb genome ,longest_mrna,longest_cds,longest_protein
echo '5 准备blastdb'
bash $Script_path/add_blast_db.sh "$name" "$new_genome_file" "$mran_longest_files" "$cds_longest_files" "$pro_longest_files" "$blast_path" "$blastdb_path"
echo '5 blastdb准备完成'

#preapre TF_gene_family
if [ -n "$protein" ] && [ -n "$gff" ]; then
    echo '6 鉴定转录因子和转录响应因子家族 '
    pro_longest_blast=$genome_path/${name}/protein/${name}
    Rscript $Script_path/TF.R "$protein_file" "$new_gff_file" "$name" "$TF_gene_family" "$pro_longest_blast" "$Script_path"
    echo '6 转录因子和转录响应因子家族鉴定完成'
fi