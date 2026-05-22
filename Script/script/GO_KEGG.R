#!/usr/bin/Rscript
print('连接数据库')
library(DBI)
library(RMySQL)
library(dplyr)
print('开始连接mysql数据库：')
con <- dbConnect(RMySQL::MySQL(),
                 dbname = "cottonogd-ortho",
                 host = "127.0.0.1",
                 PORT=3306,
                 user = "root",
                 password = "1234",
                 )
print(paste0('数据表：',dbListTables(con)))

args<-commandArgs(trailingOnly = TRUE)
file_path<-args[1]
genomes_path<-args[2]
genomes<-read.table(genomes_path,header=F,sep='\t',quote='')
genomes<-genomes$V1
file_list<-list.files(file_path,full.names = TRUE)
file_analyse<-function(genome,type,genemaster){
    files<-grep(genome,file_list,value = TRUE)
    files<-grep(type,files,value = TRUE)
    #print(files)
    data<-data.frame()
    for (i in files){
        print(i)
        dat<-read.table(i,header=F,sep='\t',quote='')
        data<-rbind(data,dat)|>unique()
    }
    if(ncol(data)!=2){
        data<-data.frame('gene_id','id_id')
    }else{
        names(data)<-c('gene_id','go_id')
    }
    
    data$gene_id<-gsub('\\.\\d+','',data$gene_id)
    data <- data |>
    left_join(
    genemaster |> select(geneid,id),
    by = c("gene_id" = "geneid")
    ) 
    names(data)[3]<-'id_id'
    return(data[,-1])
}

main<-function(genome){
    print(genome)
    species_id<-dplyr::tbl(con,'species')|>filter(name==genome)|>pull(id)
    genemaster<-dplyr::tbl(con,'genemaster')|>filter(genome_id==genome)|>select(geneid,id)|>as.data.frame()
    GO<-file_analyse(genome,'GO',genemaster)
    
    if(nrow(GO)==0| any(is.na(GO$id_id)|length(GO)!=2)){
        loss<-c(loss,genome)|>unique()
        
    }else{
        print('写入数据库')
        names(GO)<-c('go_id','id_id')
        dbWriteTable(con,"gene_go",GO,overwrite=F,append=T,row.names=F)
    }
    kegg<-file_analyse(genome,'KEGG',genemaster)
    
    if(nrow(kegg)==0| any(is.na(kegg$id_id))|length(kegg)!=2){
        loss<-c(loss,genome)|>unique()
    }else{
        print('写入数据库')
        names(kegg)<-c('kegg_id','id_id')
        dbWriteTable(con,"gene_kegg",kegg,overwrite=F,append=T,row.names=F)
    }
}
loss<-c()
sapply(genomes,main)
write.table(loss,'loss.txt',row.names=F,sep='\t',quote=F,'')
DBI::dbDisconnect(con)
print('断开数据库成功')
