#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)
genome<-args[1]
pattern<-args[2]
workdir<-args[3]

genego<-paste0(workdir,'/',pattern,'_genes2Go.xlsx')
geneIPR<-paste0(workdir,'/',pattern,'_genes2IPR.xlsx')
kegg_ortho<-paste0(workdir,'/',pattern,'_KEGG-orthologs.xlsx')
kegg_path<-paste0(workdir,'/',pattern,'_KEGG-pathways.xlsx')
library(DBI)
library(RMySQL)
library(dplyr)
print('开始连接mysql数据库：')
con <- dbConnect(RMySQL::MySQL(),
                 dbname = "cottonogd-ortho",
                 #host = "172.28.226.114",
                 #PORT=3306,
                 user = "root",
                 password = "1234",
)
genemaster<-dbReadTable(con,'genemaster')|>filter(genome_id==genome)|>select(geneid,genome_id,id)
# 定义函数：读取并合并xlsx文件中的所有数据表
read_and_merge_xlsx <- function(file_path, skip = 2) {
  if(!file.exists(file_path)) {
    cat(file_path, "文件不存在，跳过处理\n")
    return(NULL)
  }
  
  # 检查xlsx文件中有几个数据表
  sheet_names <- readxl::excel_sheets(file_path)

  
  # 读取所有数据表并合并
  tryCatch({
    data_list <- lapply(sheet_names, function(sheet) {
      readxl::read_excel(file_path, sheet = sheet, skip = skip,)
    })
    merged_data <- do.call(rbind, data_list)
    cat("合并后", file_path, "数据表行数:", nrow(merged_data), "\n")
    names(merged_data)<-c('geneid_id','kegg_id','kegg_description')
    merged_data$geneid<-gsub('\\.\\d+','',merged_data$geneid_id)
dat<-merged_data
    dat$geneid<-gsub('gnl\\|WGS:VKDL\\|','',dat$geneid)
dat$geneid<-gsub('\\.\\d+$','',dat$geneid)
dat$geneid<-gsub('-\\d+$','',dat$geneid)
dat$geneid<-gsub('-v1.0.a2','',dat$geneid)
dat$geneid<-gsub('XR_','LOC',dat$geneid)
dat$geneid<-gsub('evm\\.model\\.','',dat$geneid)
dat$geneid<-gsub('gene-','',dat$geneid)
dat$geneid<-gsub('-RA','',dat$geneid)
dat$geneid<-gsub('-mRNA-\\d+','',dat$geneid)
dat$geneid<-gsub(':cds','',dat$geneid)
dat$geneid<-gsub(':cds:\\d+','',dat$geneid)
dat$geneid<-gsub(':exon','',dat$geneid)
dat$geneid<-gsub(':exon:\\d+','',dat$geneid)
dat$geneid<-gsub(':\\d+$','',dat$geneid)
dat$geneid<-gsub('^cds\\d+\\.','',dat$geneid)
dat$geneid<-gsub('\\.exon\\d+','',dat$geneid)
dat$geneid<-gsub('\\.utr\\dp\\d+','',dat$geneid)i
dat$geneid<-gsub('rna-gnl\\|WGS:VKGE\\|','',dat$geneid)
dat$geneid<-gsub('rna-gnl\\|WGS:JABEZW\\|','',dat$geneid)

dat$geneid<-gsub('\\.mRNA\\d+$','',dat$geneid)
dat$geneid<-gsub('\\.m\\d+$','',dat$geneid)
dat$geneid<-gsub('-RA','',dat$geneid)
dat$geneid<-gsub('\\.t\\d+$','',dat$geneid)
dat$geneid<-gsub('\\.\\d+$','',dat$geneid)
dat$geneid<-gsub('-JGI_221_v2.1','',dat$geneid)
dat$geneid<-gsub("^rna-gnl\\|WGS:[A-Za-z0-9]+\\|", "",dat$geneid)
dat$geneid<-gsub('-RA$','',dat$geneid)
dat$geneid<-gsub('\\.\\d+$','',dat$geneid)
#genemaster<-dplyr::tbl(con,'genemaster')|>dplyr::filter(genome_id ==genome)|>dplyr::collect()

    return(dat)
  }, error = function(e) {
    cat("读取", file_path, "文件失败:", e$message, "\n")
    return(NULL)
  })
}
print(kegg_path)
# 处理KEGG pathways文件
if(file.exists(kegg_path)){
  print(kegg_path)
	kegg_path <- read_and_merge_xlsx(kegg_path)
  if(!is.null(kegg_path)) {
    names(kegg_path)[1:3] <- c('geneid_id', 'kegg_id', 'kegg_description')
    kegg_path$genome_id <- genome
    kegg_path$kegg_type <- 'pathway'
    kegg_path <- kegg_path |> 
      left_join(
        genemaster %>% select(geneid, genome_id,id),
        by = c("geneid" = "geneid", "genome_id" = "genome_id")
      ) 
      names(kegg_path)[-1]<-'id_id'
      if (any(is.na(kegg_path$id_id))) {
        cat("警告：KEGG pathways 文件中存在缺失的基因ID对应关系，可能需要检查数据\n")
      }
      dbWriteTable(con,'kegg_pathway',kegg_path,geneIPR[,-geneid],overwrite=F,append=T,row.names=FALSE)
  }
}

# 处理KEGG orthologs文件
if(file.exists(kegg_ortho)){
  kegg_ortho <- read_and_merge_xlsx(kegg_ortho)
  if(!is.null(kegg_ortho)) {
    names(kegg_ortho)[1:3] <- c('geneid_id', 'kegg_id', 'kegg_description')
    kegg_ortho$genome_id <- genome
    kegg_ortho$kegg_type <- 'protein'
    kegg_ortho <- kegg_ortho |> 
      left_join(
        genemaster %>% select(geneid, genome_id,id),
        by = c("geneid_id" = "geneid", "genome_id" = "genome_id")
      ) 
      names(kegg_ortho)[-1]<-'id_id'
      if (any(is.na(kegg_ortho$id_id))) {
        cat("警告：KEGG orthologs 文件中存在缺失的基因ID对应关系，可能需要检查数据\n")
      }
      dbWriteTable(con,'kegg_ortholog',kegg_ortho,geneIPR[,-geneid],overwrite=F,append=T,row.names=FALSE)
  }
}

# 处理genes2Go文件
if(file.exists(genego)){
  genego <- read_and_merge_xlsx(genego)
  if(!is.null(genego)) {
    names(genego)[1:3] <- c('geneid_id', 'go_id', 'go_description')
    genego$genome_id <- genome
    genego <- genego |> 
      tidyr::separate(go_description, into = c('go_type', 'go_description'), sep = ':')
    genego$go_type <- gsub('Molecular Function', 'MF', genego$go_type)
    genego$go_type <- gsub('Biological Process', 'BP', genego$go_type)
    genego$go_type <- gsub('Cellular Component', 'CC', genego$go_type)
    genego <- genego |> 
      left_join(
        genemaster %>% select(geneid, genome_id,id),
        by = c("geneid_id" = "geneid", "genome_id" = "genome_id")
      ) 
      names(genego)[-1]<-'id_id'
      if (any(is.na(genego$id_id))) {
        cat("警告：genes2Go 文件中存在缺失的基因ID对应关系，可能需要检查数据\n")
      }
      dbWriteTable(con,'gene_go',genego,geneIPR[,-geneid],overwrite=F,append=T,row.names=FALSE)
  }
}

# 处理genes2IPR文件
if(file.exists(geneIPR)){
  geneIPR <- read_and_merge_xlsx(geneIPR)
  if(!is.null(geneIPR)) {
    names(geneIPR)[1:3] <- c('geneid_id', 'annoation_id', 'annoation')
    geneIPR$annoation_source <- 'InterProScan'
    geneIPR$genome_id <- genome
    geneIPR <- geneIPR |> 
      left_join(
        genemaster %>% select(geneid, genome_id,id),
        by = c("geneid_id" = "geneid", "genome_id" = "genome_id")
      ) 
      names(geneIPR)[-1]<-'id_id'
      if (any(is.na(geneIPR$id_id))) {
        cat("警告：genes2IPR 文件中存在缺失的基因ID对应关系，可能需要检查数据\n")
      }
      dbWriteTable(con,'gene_annotation',geneIPR[,-geneid],overwrite=F,append=T,row.names=FALSE)
  }
}
dbDisconnect(con)
