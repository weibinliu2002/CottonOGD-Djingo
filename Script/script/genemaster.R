#!/usr/bin/Rscript
args <- commandArgs(trailingOnly = TRUE)
genome<-args[1]
gff_file<-args[2]
print(paste0('gff文件：',gff_file))
gffs<-rtracklayer::import(gff_file)
gffs<-gffs[gffs$type=='gene']
print(paste0('基因数：',length(gffs)))
data<-data.frame(
    geneid=ifelse(!(is.na(gffs$ID)),gffs$ID,ifelse(!(is.na(gffs$Name)),gffs$Name,gffs$NAME)),
    genome_id=genome
    )
data$alias<-paste(data$genome_id,data$geneid,sep = '_')
write.csv(data, paste0(genome,'_genemaster.csv'), row.names = FALSE,  quote = FALSE)
data<-read.csv(paste0(genome,'_genemaster.csv'),header = T)
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
dbWriteTable(con,'genemaster',data,overwrite=F,append=T,row.names=FALSE)
print('写入数据库成功')
DBI::dbDisconnect(con)
print('断开数据库连接')