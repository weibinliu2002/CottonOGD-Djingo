args <- commandArgs(trailingOnly = TRUE)
id<-args[1]
fasta <- args[2]
gff<-args[3]
out <- args[4]
id<-read.table(id, header = FALSE, sep = "\t",fill = TRUE, comment.char = "#")|>as.data.frame()
names(id)<-'transcript_id'
fasta<-Biostrings::readAAStringSet(fasta)
#print(id)
fasta<-fasta[id$transcript_id]
gff<-rtracklayer::import.gff3(gff)|>as.data.frame()
#print(0)
gff1<-gff[gff$ID %in% names(fasta)| gff$Parent %in% names(fasta),]
#print(1)
str_gene<-gff1[gff1$type=='gene',]
#print(str_gene)
str_mRNA<-gff1[gff1$type=='mRNA',]
#print(str_mRNA)
str_exon<-gff1[gff1$type=='exon',]
#print(2)
str_intron<-gff1[gff1$type=='intron',]
#print(str_intron)
str_cds<-gff1[gff1$type=='CDS',]
#print(3)
##print(str(gff1))
infos<-data.frame()
info_list<-sapply(names(fasta),function(x){
    #print(x)

  dat2<-str_mRNA[str_mRNA$ID==x,]
  #print(dat2)
    chr<-dat2$seqnames
  start<-dat2$start
  end<-dat2$end
  lenbg<-dat2$width
  dat3<-str_exon[str_exon$Parent==x,]
  #print(dat3)
  exon_num<-nrow(dat3)
  exon_len<-sum(dat3$width)
  intron_num<-exon_num-1
  intron_len<-lenbg-exon_len
  dat5<-str_cds[str_cds$Parent==x,]
  #print(dat5)
  cds_num<-nrow(dat5)
  cds_len<-sum(dat5$width)
  protein_len<-fasta[x]@ranges@width
  #print(protein_len)
  info<-data.frame(gene_id=gsub('\\.\\d+','',x),transcript_id=x,chr,start,end,lenbg, protein_len, exon_num, exon_len, intron_num, intron_len, cds_num, cds_len)
  infos<<-rbind(infos,info)
})

#print(str(infos))
write.table(infos, file = out, sep = "\t", quote = FALSE, row.names = FALSE, col.names = TRUE)
# 将结果写入输出文件
#write.table(info_df, file = out, sep = "\t", quote = FALSE, row.names = FALSE, col.names = TRUE)
