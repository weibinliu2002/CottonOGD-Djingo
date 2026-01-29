#!/usr/bin/Rscript
args <- commandArgs(trailingOnly = TRUE)
genome<-args[1]
gff_file<-args[2]
print(paste0('gff文件：',gff_file))
gffs<-rtracklayer::import(gff_file)
gffs_gene<-gffs[gffs$type=='gene']
print(paste0('基因数：',length(gffs_gene)))
data<-data.frame(
    geneid=ifelse(!(is.na(gffs_gene$ID)),gffs_gene$ID,ifelse(!(is.na(gffs_gene$Name)),gffs_gene$Name,gffs_gene$NAME)),
    genome_id=genome
    )
data$alias<-paste(data$genome_id,data$geneid,sep = '_')

gffss<-read.table(gff_file,header = F,sep = '\t')
gffss<-dplyr::arrange(gffss,V1,V4,V5)
gffs<-as.data.frame(gffs)|>dplyr::arrange(seqnames,start,end)

data2<-data.frame(
    
    seqid=gffss$V1,
    start=gffss$V4,
    end=gffss$V5,
    strand=gffss$V7,
    source=gffss$V2,
    type=gffss$V3,
    value=gffss$V8,
    phase=gffss$V6,
    attribute=gffss$V9,
    geneid=ifelse(!(is.na(gffs$ID)),gffs$ID,ifelse(!(is.na(gffs$Name)),gffs$Name,gffs$NAME)),
    genome_id=genome
    )
    names(data2)<-c('seqid','start','end','strand','source','type','value','phase','attributes','geneid_id','genome_id')
data2$geneid_id<-gsub('\\.\\d+\\..*$','',data2$geneid_id)
data2$geneid_id<-gsub('\\.\\d+$','',data2$geneid_id)
data$alias<-paste(data$genome_id,data$geneid,sep = '_')

print(str(data))
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
#dbWriteTable(con,'genemaster',data,overwrite=F,append=T,row.names=FALSE)
print('写入数据库成功')
genemaster<-dbReadTable(con,'genemaster',filter = paste0('genome_id="',genome,'"'))

data2 <- data2 |>
  dplyr::left_join(
    genemaster |> dplyr::select(geneid, genome_id,id),
    by = c("geneid_id" = "geneid", "genome_id" = "genome_id")
  ) 
names(data2)[12]<-c('id_id')
str(data2)  
dbWriteTable(con,'gene_assembly',data2,overwrite=F,append=T,row.names=FALSE)

DBI::dbDisconnect(con)
print('断开数据库连接')

