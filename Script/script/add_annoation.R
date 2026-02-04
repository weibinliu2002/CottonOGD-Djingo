args <- commandArgs(trailingOnly = TRUE)
genome<-args[1]
annoaion<-args[2]
annoaion<-readLines(annoaion)
annoaion|>Biostrings::strsplit('\t')-> anno
anno_df <- as.data.frame(do.call(rbind, anno), stringsAsFactors = FALSE)
colnames(anno_df) <- anno_df[1, ]
names(anno_df)
anno_df <- anno_df[-1, ]
anno_df$genome_id<-genome
anno_df$GeneID<-gsub('\\.\\d+','',anno_df$GeneID)
anno_df <- anno_df %>%
  left_join(
    genemaster %>% select(geneid, genome_id,id),
    by = c("GeneID" = "geneid", "genome_id" = "genome_id")
  ) 
names(anno_df)[11]<-c('id_id')
str(anno_df)
names(anno_df)[2:9]
long<-tidyr::gather(anno_df,key = 'annoation_source',value = 'annoation',names(anno_df)[2:9])
names(long)
dbReadTable(con,'gene_annotation')|>str()
names(long)<-c('geneid_id','genome_id','id_id','annoation_source','annotation')
dbWriteTable(con,'gene_annotation',long,overwrite=F,append=T,row.names=FALSE)
print('写入数据库成功')
DBI::dbDisconnect(con)
print('断开数据库连接')