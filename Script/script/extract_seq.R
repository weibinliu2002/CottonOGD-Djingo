#!/usr/bin/env Rscript

library(optparse)
library(Biostrings)
library(rtracklayer)
library(plyr)
library(dplyr)

# 定义命令行选项
option_list <- list(
  make_option(c("-i", "--genome-id"), type="character", default=NULL, 
              help="Genome ID", metavar="character"),
  make_option(c("-g", "--genome"), type="character", default=NULL, 
              help="Genome fasta file", metavar="character"),
  make_option(c("-f", "--gff-file"), type="character", default=NULL, 
              help="GFF/GTF file", metavar="character"),
  make_option(c("-m", "--mrna-file"), type="character", default=NA, 
              help="mRNA fasta file (optional)", metavar="character"),
  make_option(c("-d", "--cdna-file"), type="character", default=NA, 
              help="cDNA fasta file (optional)", metavar="character"),
  make_option(c("-c", "--cds-file"), type="character", default=NA, 
              help="CDS fasta file (optional)", metavar="character"),
  make_option(c("-p", "--protein-file"), type="character", default=NA, 
              help="Protein fasta file (optional)", metavar="character"),
  make_option(c("-o", "--output-path"), type="character", default=NULL, 
              help="Output directory path", metavar="character")
)

# 解析命令行参数
opt_parser <- OptionParser(option_list=option_list)
opt <- parse_args(opt_parser)

# 检查必填参数
if (is.null(opt$`genome-id`) || is.null(opt$genome) || is.null(opt$`gff-file`) || is.null(opt$`output-path`)) {
  print_help(opt_parser)
  stop("Missing required arguments", call.=FALSE)
}

# 赋值参数
genome_id <- opt$`genome-id`
genome_files <- opt$genome
gff_files <- opt$`gff-file`
mrna_files <- opt$`mrna-file`
cdna_files <- opt$`cdna-file`
cds_files <- opt$`cds-file`
pro_files <- opt$`protein-file`
genome_path <- opt$`output-path`

print(gff_files)
print(genome_files)
print(mrna_files)
print(cdna_files)
print(cds_files)
print(pro_files)

# 处理空参数
if (is.na(mrna_files) || mrna_files == "") {
  mrna_files <- paste0(genome_path,'/', genome_id, ".mrna.fa")
  print(paste0("gffread ", gff_files, " -g ", genome_files, " -u ", mrna_files, ' --w-nocds'))
  system(paste0("gffread ", gff_files, " -g ", genome_files, " -u ", mrna_files, ' --w-nocds'))
}
if (is.na(cdna_files) || cdna_files == "") {
  cdna_files <- paste0(genome_path,'/', genome_id, ".cdna.fa")
  print(paste0("gffread ", gff_files, " -g ", genome_files, " -w ", cdna_files, " --w-nocds"))
  system(paste0("gffread ", gff_files, " -g ", genome_files, " -w ", cdna_files, " --w-nocds"))
}
if (is.na(cds_files) || cds_files == "") {
    cds_files <- paste0(genome_path,'/', genome_id, ".cds.fa")
    print(paste0("gffread ", gff_files, " -g ", genome_files, " -x ", cds_files, " --w-nocds"))
    system(paste0("gffread ", gff_files, " -g ", genome_files, " -x ", cds_files, " --w-nocds"))
}
if (is.na(pro_files) || pro_files == "") {
  pro_files <- paste0(genome_path,'/', genome_id, ".pro.fa")
  print(paste0("gffread ", gff_files, " -g ", genome_files, " -y ", pro_files, " --w-nocds"))
  system(paste0("gffread ", gff_files, " -g ", genome_files, " -y ", pro_files, " --w-nocds"))
}

# 修复work_dir和work_dir_base未定义的问题
work_dir <- genome_path
work_dir_base <- genome_id

gene_genome_files <- paste0(genome_path,'/', genome_id, ".gene_genome.fa")
if (!file.exists(gene_genome_files)){
    # 导入GFF文件并过滤基因记录
    gff_gr <- rtracklayer::import(gff_files)
    gene_gr <- gff_gr[gff_gr$type == 'gene']
    clean_genome_path <- gsub("//", "/", genome_files)
    print(clean_genome_path)
    # 读取基因组序列（修复拼写错误）
    genome_seq <- Rsamtools::FaFile(clean_genome_path[1])
    open(genome_seq)
    # 提取基因序列
    gene_seqs <- Biostrings::getSeq(genome_seq, gene_gr)
    close(genome_seq)
    # 设置序列名称
    if ("Name" %in% names(mcols(gene_gr))) {
        names(gene_seqs) <- gene_gr$Name
    } else if ("ID" %in% names(mcols(gene_gr))) {
        names(gene_seqs) <- gene_gr$ID
    } else {
        names(gene_seqs) <- paste(seqnames(gene_gr), start(gene_gr), end(gene_gr), sep="_")
    }
    print(gene_seqs)
    # 保存基因序列到FASTA文件
    Biostrings::writeXStringSet(gene_seqs, gene_genome_files)
    print(paste("Extracted", length(gene_seqs), "gene sequences to", gene_genome_files))

}
upstream_files <- paste0(genome_path,'/', genome_id, ".upstream20000.fa")
if (!file.exists(upstream_files)) {
    print(paste0("java -cp /data/wbliu/soft/TBtools-II-2.311/TBtools_JRE1.6.jar biocjava.bioIO.GFF.ExtractFeaturefromGFF3andGenome --inGtf ", gff_files, " --inGenome ", genome_files, " --outFile ", upstream_files, " --targetFeature CDS --targetIdTag Parent --upStreamBases 20000 --onlyCheck false --onlyRetainFlank true"))
  system(paste0("java -cp /data/wbliu/soft/TBtools-II-2.311/TBtools_JRE1.6.jar biocjava.bioIO.GFF.ExtractFeaturefromGFF3andGenome --inGtf ", gff_files, " --inGenome ", genome_files, " --outFile ", upstream_files, " --targetFeature CDS --targetIdTag Parent --upStreamBases 20000 --onlyCheck false --onlyRetainFlank true"))
}

downstream_files <- paste0(genome_path,'/', genome_id, ".downstream20000.fa")
if (!file.exists(downstream_files)) {
    print(paste0("java -cp /data/wbliu/soft/TBtools-II-2.311/TBtools_JRE1.6.jar biocjava.bioIO.GFF.ExtractFeaturefromGFF3andGenome --inGtf ", gff_files, " --inGenome ", genome_files, " --outFile ", downstream_files, " --targetFeature CDS --targetIdTag Parent --downStreamBases 20000 --onlyCheck false --onlyRetainFlank true"))
  system(paste0("java -cp /data/wbliu/soft/TBtools-II-2.311/TBtools_JRE1.6.jar biocjava.bioIO.GFF.ExtractFeaturefromGFF3andGenome --inGtf ", gff_files, " --inGenome ", genome_files, " --outFile ", downstream_files, " --targetFeature CDS --targetIdTag Parent --downStreamBases 20000 --onlyCheck false --onlyRetainFlank true"))
}


pre<-function(x){
    if (x!='pro_files'){
    fa<-Biostrings::readDNAStringSet(get(x))
    }else{
        fa<-Biostrings::readAAStringSet(get(x))
    }
    names(fa)<-sapply(names(fa), function(n) strsplit(n,'\t')[[1]][1])
    da<-data.frame(id=names(fa),seq=as.character(fa))
    names(da)<-c('mrna_id','sequence')
    if (x=='gene_genome_files'){
        da$gene_type<-paste0(gsub('_files','',x),'')
        da$gene_type<-paste0(da$gene_type,'gene_')
    }else{
        da$gene_type<-paste0(gsub('_files','',x),'')
    }
    print(x)
    print(str(da))
    fu<<-rbind(fu,da)
}
#te<-readDNAStringSet(mrna_files)
fu<-data.frame()
lis<-c('gene_genome_files','mrna_files','cdna_files','cds_files','upstream_files','downstream_files','pro_files')
for (i in lis) {
   pre(i)
}
fu$geneid_id<-gsub('\\.\\d+','',fu$mrna_id)
fu$genome_id<-genome_id
print(str(fu))
#dat<-data.frame(mrna_id=fu$id,mrna_seq=fu$mrna_seq,cds_seq=fu$cds_seq,upstream_seq=fu$upstream_seq,downstream_seq=fu$downstream_seq,protein_seq=fu$pro_seq,gene_id=gsub('\\.\\d+','',fu$id))
#print(str(dat))
print('连接数据库')
library(DBI)
library(RMySQL)
print('开始连接mysql数据库：')
con <- dbConnect(RMySQL::MySQL(),
                 dbname = "cottonogd-ortho",
                 host = "127.0.0.1",
                 PORT=3306,
                 user = "root",
                 password = "1234",
                 )
print(paste0('数据表：',dbListTables(con)))
genemaster<-dplyr::tbl(con,'genemaster')|>as.data.frame()
fu <- fu |>
  left_join(
    genemaster |> select(geneid, genome_id,id),
    by = c("geneid_id" = "geneid", "genome_id" = "genome_id")
  ) 
names(fu)[6]<-'id_id'
print('写入数据库')

dbWriteTable(con,"gene_seq",fu,overwrite=F,append=T,row.names=F)
print('断开数据库')
DBI::dbDisconnect(con)
print('断开数据库成功')
