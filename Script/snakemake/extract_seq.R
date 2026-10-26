#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)
genome_path <- args[1]
gff_file <- args[2]
output <- args[3]
gff_gr <- rtracklayer::import(gff_file)
gene_gr <- gff_gr[gff_gr$type == 'gene']
if(length(gene_gr)==0){
    gene_gr <- gff_gr[gff_gr$type == 'mRNA']
}
genome_fai <- paste0(genome_path, ".fai")
genome_fai<-read.table(genome_fai,header=F,sep='\t',quote='')
names(genome_fai)<-c('chr','start','end','len','seq')
gene_gr<-gene_gr[as.character(GenomicRanges::seqnames(gene_gr)) %in% genome_fai$chr]
genome_seq <- Rsamtools::FaFile(genome_path)
open(genome_seq)
# 提取基因序列
gene_seqs <- Biostrings::getSeq(genome_seq, gene_gr)
close(genome_seq)
# 设置序列名称
if ("Name" %in% names(rtracklayer::mcols(gene_gr))) {
  names(gene_seqs) <- gene_gr$Name
} else if ("ID" %in% names(rtracklayer::mcols(gene_gr))) {
    names(gene_seqs) <- gene_gr$ID
} else if ("Parent" %in% names(rtracklayer::mcols(gene_gr))) {
    names(gene_seqs) <- gsub('\\.\\d+','',gene_gr$Parent)
} else {
  names(gene_seqs) <- paste(as.character(GenomicRanges::seqnames(gene_gr)), GenomicRanges::start(gene_gr), GenomicRanges::end(gene_gr), sep="_")
}

# 写入文件
 Biostrings::writeXStringSet(gene_seqs, output)

