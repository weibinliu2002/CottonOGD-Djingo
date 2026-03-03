#!/usr/bin/Rscript
Args<-commandArgs(trailingOnly = TRUE )
dat<-read.table(Args[1],header = F,sep = '\t')
print(str(dat))
busco<-function(x){
  name<-dat[x,1]
  if(name %in% paste0('N',seq(200,306)))
    name<-paste0('G.hirsutumAD1_',name,'_CRI_v1')
fa<-Biostrings::readDNAStringSet(paste('genome',name,dat[x,2],sep = '/'))  
fa@ranges|>as.data.frame() -> dat
 total_size<-data.frame(name,dat$width|>sum())
 write.table(total_size,paste0('Genome_size.txt'),quote = F,row.names =F,sep='\t',col.names = F,append = T)
}
if(!file.exists('Genome_size.txt'))
write.table(data.frame('name','size',paste0('Genome_size.txt'),quote = F,row.names =F,sep='\t' )
pre_dat<-read.table('Genome_size.txt',header = F,sep = '\t')
los<-dat[!(dat$V1 %in% pre_dat$V1),]
a<-sapply(1:length(los$V1), busco)

#write.table(total_size,paste0('Genome_size.txt'),quote = F,row.names =F,sep='\t' )