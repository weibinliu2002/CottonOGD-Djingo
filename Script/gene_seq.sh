#!/bin/bash
# 初始化变量
name=""
genome=""
mrna=""
cds=""
cdna=""
protein=""
gff=""
annoation=""
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
        -a|--annoation)
            annoation="$2"
            shift 2
            ;;
        -w|--workdir)
            workdir="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 -n <name> [-g <genome_file>] [-m <mrna_file>] [-c <cds_file>] [-d <cdna_file>] [-p <protein_file>] [-f <gff_file>] [-a <annoation_file>] -w <workdir>"
            echo "Note: All file parameters except name and workdir are optional and can be empty"
            exit 1
            ;;
    esac
done

# 检查必填参数是否完整
if [ -z "$name" ] || [ -z "$workdir" ]; then
    echo "Usage: $0 -n <name> [-g <genome_file>] [-m <mrna_file>] [-c <cds_file>] [-d <cdna_file>] [-p <protein_file>] [-f <gff_file>] [-a <annoation_file>] -w <workdir>"
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
jbrowse_path=$workdir/backend/static/jbrowse/data/$name
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

annoation_file=""
if [ -n "$annoation" ]; then
    annoation_file=$genome_path/$annoation
fi



#prepare genemaster
if  [ -n "$gff" ]; then
    echo '1 准备genemaster'
    echo "Rscript $Script_path/genemaster.R "$name" "$gff_file""
    Rscript $Script_path/genemaster.R "$name" "$gff_file"
    
    echo '1 genemaster准备完成'
fi

if  [ -n "$annoation" ]; then
#add annotation
    echo '1.2 添加注释'
    echo "$Script_path/add_annoation.R "$name" "$annoation_file""
    Rscript $Script_path/add_annoation.R "$name" "$annoation_file"
fi
#add jbrowes
if [ -n "$genome" ] && [ -n "$gff" ]; then
    echo '2 添加jbrowes'
    echo "$Script_path/add_jbrowes.sh "$name" "$genome" "$gff" "$genome_path" "$jbrowse_path" "$Script_path""
    #bash $Script_path/add_jbrowes.sh "$name" "$genome" "$gff" "$genome_path" "$jbrowse_path" "$Script_path"
    echo '2 jbrowes添加完成'
    new_gff_file=$genome_path/${name}.gff.gz
    new_genome_file=$genome_path/${name}.genome.fa.gz
fi

#prepare gene_seq database
echo '3 准备gene_seq数据库'

# 构建extract_seq.R命令，只包含存在的文件参数
extract_cmd="Rscript $Script_path/extract_seq.R -i \"$name\" -o \"$genome_path\""

# 检查并添加genome_file
if [ -n "$genome_file" ] && [ -f "$genome_file" ]; then
    extract_cmd="$extract_cmd -g \"$genome_file\""
fi

# 检查并添加gff_file
if [ -n "$gff_file" ] && [ -f "$gff_file" ]; then
    extract_cmd="$extract_cmd -f \"$gff_file\""
fi

# 检查并添加mrna_file
if [ -n "$mrna_file" ] && [ -f "$mrna_file" ]; then
    extract_cmd="$extract_cmd -m \"$mrna_file\""
fi

# 检查并添加cdna_file
if [ -n "$cdna_file" ] && [ -f "$cdna_file" ]; then
    extract_cmd="$extract_cmd -d \"$cdna_file\""
fi

# 检查并添加cds_file
if [ -n "$cds_file" ] && [ -f "$cds_file" ]; then
    extract_cmd="$extract_cmd -c \"$cds_file\""
fi

# 检查并添加protein_file
if [ -n "$protein_file" ] && [ -f "$protein_file" ]; then
    extract_cmd="$extract_cmd -p \"$protein_file\""
fi

echo "$extract_cmd"
#eval $extract_cmd
echo '3 gene_seq数据库准备完成'

#prepare longest protein sequence
echo '4 准备最长序列'
pro_longest_files=$genome_path/${name}.pro_longest.fasta
cds_longest_files=$genome_path/${name}.cds_longest.fasta
mran_longest_files=$genome_path/${name}.mrna_longest.fasta

if [ -n "$protein" ]; then
    protein_file=$protein_file
    echo $protein_file
    else 
   
    protein_file=$genome_path/${name}.pro.fa
     echo $protein_file
fi
Rscript $Script_path/longest.R $protein_file $pro_longest_files 
if [ -f "$pro_longest_files" ]; then
    echo '4 最长蛋白质序列准备完成'
fi


if [ -n "$cdna" ]; then
    cdna_file=$cdna_file        
    echo $cdna_file
    else 
    cdna_file=$genome_path/${name}.cdna.fa
    echo $cdna_file
fi
 Rscript $Script_path/longest.R $cdna_file $cds_longest_files 
    if [ -f "$cds_longest_files" ]; then
        echo '4 最长cds序列准备完成'
    fi



if [ -n "$mrna" ]; then     
    mrna_file=$mrna_file
    echo $mrna_file
    else 
    mrna_file=$genome_path/${name}.mrna.fa
    echo $mrna_file
fi
 Rscript $Script_path/longest.R $mrna_file $mran_longest_files  
    if [ -f "$mran_longest_files" ]; then
        echo '4 最长mrna序列准备完成'
    fi



echo '4 最长序列准备完成'

#prepare blastdb genome ,longest_mrna,longest_cds,longest_protein
echo '5 准备blastdb'
echo "$Script_path/add_blast_db.sh "$name" "$genome_file" "$mran_longest_files" "$cds_longest_files" "$pro_longest_files" "$blast_path" "$blastdb_path""
#bash $Script_path/add_blast_db.sh "$name" "$genome_file" "$mran_longest_files" "$cds_longest_files" "$pro_longest_files" "$blast_path" "$blastdb_path"
echo '5 blastdb准备完成'

#preapre TF_gene_family
if [ -n "$protein" ] && [ -n "$gff" ]; then
    echo '6 鉴定转录因子和转录响应因子家族 '
    pro_longest_blast=$blastdb_path/protein/${name}
    echo "Rscript $Script_path/TF.R "$protein_file" "$new_gff_file" "$name" "$TF_gene_family" "$pro_longest_blast" "$Script_path" "
    #Rscript $Script_path/TF.R "$protein_file" "$new_gff_file" "$name" "$TF_gene_family" "$pro_longest_blast" "$Script_path"
    echo '6 转录因子和转录响应因子家族鉴定完成'
fi