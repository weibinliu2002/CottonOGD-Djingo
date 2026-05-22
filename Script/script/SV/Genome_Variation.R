#/usr/bin<-commandArgs(trailingOnly = TRUE)
ref<-args[1]
query<-args[2]
file_path<-args[3]
print('连接数据库')
library(DBI)
library(dplyr)
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
ref_id<-tbl(con,'species') |>filter(name==ref)|>pull(id)
query_id<-tbl(con,'species') |>filter(name==query)|>pull(id)
tb<-data.table::fread(file_path)
names(tb)<-c('Ref_genome_chr','Ref_genome_start','Ref_genome_end','Ref_seq','Alt_seq','Query_genome_chr','Query_genome_start','Query_genome_end','Variation_type','Parent_Variation','son_type','copygain')
tb$Ref_genome<-ref_id
tb$Query_genome<-query_id
dbWriteTable(con,"genome_synteny",tb,overwrite=F,append=T,row.names=F)
disconnect(con)