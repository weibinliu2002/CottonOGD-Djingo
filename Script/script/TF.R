#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)

# 设置文件路径

#read.table('seq/G.raimondii_(D5)_JGI_v2_a2.1.fa', header=F, sep='\t')
TM_1.pro.fa = args[1]
TM_1.gff = args[2]
hmm_path = '/public2/wbliu/data/pfam_data/pfamdb/Pfam-A.hmm'
sample = args[3]
output = args[4]
blastdb=args[5]
sc=args[6]
TF_list = paste0(sc,'../data/Ath_TF_list.txt')
TF_domain = paste0(sc,'../data/TF-domain.txt')
At.pro.fa = paste0(sc,'../data/seq/AT.pro.fa')
# 读取TF列表
TF_LIST <- read.table(TF_list, header=F, sep='\t', skip=1)  # 跳过表头行
print(str(TF_LIST))
TF_domain <- read.table(TF_domain, header=F, sep='\t', skip=1)  # 跳过表头行
names(TF_domain)<-c('V1','V2','num')
TF_domain$num<-as.numeric(TF_domain$num)
# 读取拟南芥蛋白质序列并提取基因ID
At.pro.fa <- Biostrings::readAAStringSet(At.pro.fa)
names(At.pro.fa) <- sapply(names(At.pro.fa), function(x) strsplit(x, " ")[[1]][1])

base_out<-paste0(output,'/TF_result')

if (file.exists(base_out)){
  system(paste0('rm -rf ',base_out))
}



dir.create(base_out, showWarnings = FALSE)
dir.create(paste0(base_out,'/TF_pro'), showWarnings = FALSE)
dir.create(paste0(base_out,'/TF_id'), showWarnings = FALSE)
dir.create(paste0(base_out,'/TF_info'), showWarnings = FALSE)



# 定义最长转录本选择函数
longest <- function(fa) {
  old_name <- names(fa)
  new_name <- gsub('\\.\\d+', '', old_name)
  long <- data.frame(old_name, new_name, width = fa@ranges@width)
  max_widths <- long |>
    dplyr::group_by(new_name) |>
    dplyr::summarize(max_width = max(width)) |>
    dplyr::ungroup()
  result <- long |>
    dplyr::left_join(max_widths, by = "new_name") |>
    dplyr::filter(width == max_width) |>
    dplyr::group_by(new_name) |>
    dplyr::slice_head(n = 1) |>
    dplyr::ungroup()
  return(result)
}

filter_domain<-function(TF_name){
    domain_num<-TF_domain[TF_domain$V1==TF_name,]
    domain.id<-domain_num$V2
    hmm_result <- paste0(TF_name, '/', TF_name, '.hmm.result')
    system(paste0('sed -i \'s/  / /g\' ', hmm_result))
    system(paste0('sed -i \'s/  / /g\' ', hmm_result))
    system(paste0('sed -i \'s/  / /g\' ', hmm_result))
    system(paste0('sed -i \'s/  / /g\' ', hmm_result))
    system(paste0('sed -i \'s/  / /g\' ', hmm_result))
    #filter_name<-paste0(TF_name, '/', TF_name, '.hmm.result.filter')
    hmm_file<-read.table(hmm_result, header = FALSE, sep = " ",fill = TRUE, comment.char = "#")|>as.data.frame()
    names(hmm_file) = c('target name','accession1' ,'tlen', 'query name', 'accession2', 'qlen', 'E-value' , 'score','bias' , 'from','to','from','to','from','to','acc','description of target')
    hmm_file<-hmm_file[,1:9]
    #print(str(hmm_file))
    hmm_file<-table(hmm_file$`target name`,hmm_file$`accession2`)|>as.data.frame()
    names(hmm_file)<-c('id','domain','num')
    hmm_file$domain<-gsub('\\.\\d+','',hmm_file$domain)
    #print(str(hmm_file))
    ids<-hmm_file$id|>unique()|>as.character()
    for(i in domain.id){
        domain_num<-TF_domain[TF_domain$V1==TF_name & TF_domain$V2==i,]
        #print(paste0(TF_name,':',i))
        #print(domain_num)
        if(is.na(domain_num$num)){
            # 处理NA值情况
            selected<-hmm_file[hmm_file$domain==i & hmm_file$num>=1,]
        }else if(domain_num$num==1){
            selected<-hmm_file[hmm_file$domain==i & hmm_file$num==1,]
        }else if(domain_num$num==-1){
            selected<-hmm_file[hmm_file$domain!=i ,]
        }else if(domain_num$num==2){
            selected<-hmm_file[hmm_file$domain==i & hmm_file$num >=2,]
        }else{
            selected<-hmm_file[hmm_file$domain==i & hmm_file$num>=1 ,]
        }
        #print(selected)
        id<-selected$id|>unique()|>as.character()
         if (TF_name=='C3H'){
        ids<-ids
        }else {
            ids<-ids[ids %in% id]
        }
       
    }
   
    #print(ids)
    return(ids)
}

# TF分析函数
TF <- function(TF_name, At.id, domain.id = NULL) {
  # 创建输出目录
  system(paste0('rm -rf ', paste0(base_out,'/TF_pro/',TF_name)))
  dir.create(paste0(base_out,'/TF_pro/',TF_name), showWarnings = FALSE)
  
  # 提取拟南芥TF序列并选择最长转录本
  TF_AT.pro.fa <- At.pro.fa[At.id]
  if (length(TF_AT.pro.fa) > 0) {
    TF_AT.pro.fa <- TF_AT.pro.fa[longest(TF_AT.pro.fa)$old_name]
    
    # 输出拟南芥TF序列
    output_file <- paste0(base_out,'/TF_pro/',TF_name, '/', TF_name, '_AT.pro.fa')
    Biostrings::writeXStringSet(TF_AT.pro.fa, output_file)
    
    # BLAST分析
    blast_output <- paste0(base_out,'/TF_pro/',TF_name, '/', TF_name, '_AT.pro.fa.blastp')
    system(paste0('blastp -query ', output_file, ' -db seq/',sample,'/TM_1 -outfmt 6 -num_threads 40 -out ', blast_output))
    
    # 过滤BLAST结果
    blast_filtered <- paste0(base_out,'/TF_pro/',TF_name, '/', TF_name, '_AT.pro.fa.blastp.1')
    if(TF_name != 'OFP'){
        system(paste0('grep -v "#" ', blast_output, ' | awk \'$3>25 && $11<1e-5 {print $2}\'' ,' | sort | uniq >', blast_filtered))
    }else{
        system(paste0('grep -v "#" ', blast_output, ' | awk \'{print $2}\'' ,' | sort | uniq >', blast_filtered))
    }
    
    # 提取棉花同源序列
    cotton_output <- paste0(base_out,'/TF_pro/',TF_name, '/', TF_name, '_TM_1.pro.fa')
    system(paste0('seqkit grep -f ', blast_filtered, ' ', TM_1.pro.fa, ' -o ', cotton_output))
    
    # HMM分析（如果提供了domain.id）
    if (!is.null(domain.id) && length(domain.id) > 0) {
      # 获取HMM模型
      hmm_file <- paste0(base_out,'/TF_pro/',TF_name, '/', TF_name, '.hmm')
      for (i in domain.id) {
        id_name <- system(paste0('grep -i ', i, ' ', hmm_path, ' | cut -f 2'), intern = TRUE)
        #print(id_name)
        id_name <- gsub('ACC   ', '', id_name)
         #print(id_name)
        system(paste0('hmmfetch ', hmm_path, ' ', id_name, ' >> ', hmm_file))
      }
      
      # 运行HMM搜索
      hmm_result <- paste0(base_out,'/TF_pro/',TF_name, '/', TF_name, '.hmm.result')
      system(paste0('hmmsearch --domtblout ', hmm_result, ' -E 1e-5 ', hmm_file, ' ', cotton_output,' > /dev/null'))
      hmm_filtered <- paste0(base_out,'/TF_pro/',TF_name, '/', TF_name, '.hmm.result1')
      #system(paste0('grep -v "#" ', hmm_result, ' | awk \'$4>$7 {print $1}\'' ,' | sort | uniq >', hmm_filtered))
      if(TF_name == 'SAP'){
        # 修复print语句语法错误
        #print(c(blast_filtered, hmm_filtered))
        # 使用引号确保路径中有空格时也能正确处理
        system(paste0('cp "', blast_filtered, '" "', hmm_filtered, '"'))
      }else {
         ids<-filter_domain(TF_name)
     # print(ids)
      # 过滤HMM结果
     
      write.table(ids, hmm_filtered, row.names = FALSE, col.names = FALSE, quote = FALSE)
      }
      # 提取最终结果序列
      final_output <- paste0(base_out,'/TF_pro/',TF_name, '/', TF_name, '.hmm.result.fa')
      system(paste0('seqkit grep -f ', hmm_filtered, ' ', cotton_output, ' -o ', final_output))
    
    
      # 提取最长转录本
      final_output_longest <- paste0(base_out,'/TF_pro/',TF_name, '/', TF_name, '.hmm.result.longest.fa')
      system(paste0('Rscript longest.R ', final_output, ' ', final_output_longest))
      id_name<-paste0(base_out,'/TF_pro/',TF_name, '/', TF_name,'.id')
      system(paste0('grep ">" ', final_output_longest, '| cut -f 1 | sed "s/>//" > ', id_name))
     
    
    #提取gff

    system(paste0('Rscript info.R ',id_name,' ', final_output_longest,' ', TM_1.gff, ' ', base_out,'/TF_pro/',TF_name,'/',TF_name))
    }
    #final_output_longest <- paste0(TF_name, '/', TF_name, '.hmm.result.longest.fa')
    geneid<-read.table(id_name,header = F)$V1
    cla<-TF_LIST[TF_LIST$V3 == TF_name, 4]
    TF_dat<-data.frame(TF_name=TF_name,
                       geneid=geneid,
                       TF_class=cla[1],
                       genome_id=sample)
    write.csv(TF_dat, paste0(base_out,'/TF_pro/',TF_name, '/', TF_name,'_TF.csv'), row.names = FALSE, col.names = TRUE, quote = FALSE)
    if (file.exists(final_output_longest)==T){
      #system(paste0('ln -fs ../../',final_output_longest, ' TF_result/TF_pro/'))
      system(paste0('ln -fs ../../',base_out,'/TF_pro/',TF_name,'/',TF_name,'_TF.csv', ' TF_result/TF_id/'))
      system(paste0('ln -fs ../../',base_out,'/TF_pro/',TF_name, '/',TF_name,  ' TF_result/TF_info/'))
    }else{
      system(paste0('ln -fs ../../',base_out,'/TF_pro/',TF_name, '/',TF_name, '_TM_1.pro.fa', ' /TF_result/TF_pro/'))
    }
    
  }
}
merge_TF<-function(x){
  CSV<-list.files(paste0(x, '/'), pattern = '_TF.csv', full.names = T)
  TF_dat<-do.call(rbind, lapply(CSV, function(x) read.csv(x)))
  write.csv(TF_dat, paste0(base_out,'/',sample,'_TF.csv'), row.names = FALSE, col.names = TRUE, quote = FALSE)
}

# 示例运行：CPP家族的TF分析
print("Running TF analysis...")


# 使用parallel包实现多线程运行
library(parallel)

# 获取可用CPU核心数
n_cores <- detectCores()
print(paste0("Using ", n_cores, " cores for parallel processing..."))

# 获取唯一的TF家族列表
tf_families <- unique(TF_LIST$V3)

# 使用mclapply进行多线程处理
run_TF<-function(x){ mclapply(x, function(x) {
  # 获取domain ID，如果没有找到则返回NULL
  domain_id <- TF_domain[TF_domain$V1 == x, 2]
  # 过滤掉NA值和空字符串
  domain_id <- domain_id[!is.na(domain_id) & domain_id != ""]
 # # 如果没有有效domain ID，设置为NULL
  if (length(domain_id) == 0) {
    domain_id <- NULL
  }
  TF(x, TF_LIST[TF_LIST$V3 == x, 1], domain_id)

}, mc.cores = n_cores)
merge_TF(x)
}


clean_TF<-function(x){ mclapply(x, function(x) {
  system(paste0('rm -rf ', x))
}, mc.cores = n_cores)}

#TEST <- TF('SAP', TF_LIST[TF_LIST$V3 == 'SAP', 1], domain.id =TF_domain[TF_domain$V1 == 'SAP', 2])
#clean_TF(tf_families)
run_TF(tf_families)
#sapply(tf_families, function(x) {  TF(x, TF_LIST[TF_LIST$V3 == x, 1], domain.id = TF_domain[TF_domain$V1 == x, 2])})



print("Analysis completed successfully!")

family<-read.csv(paste0(base_out,'/',sample,'_TF.csv'),header = T)

print(str(family))
print('连接数据库')
library(DBI)
library(RMySQL)
con <- dbConnect(RMySQL::MySQL(),
                 dbname = "CottonOGD-ortho",
                 host = "127.0.0.1",
                 port=3306,
                 user = "root",
                 password = "1234",
                 #client.flag = CLIENT_MULTI_STATEMENTS | CLIENT_LOCAL_FILES
                 )
print('列出数据库')
dbListTables(con)
genemaster<-dplyr::tbl(con,'genemaster')|>as.data.frame()
family <- family %>%
  left_join(
    genemaster %>% select(geneid, genome_id,id),
    by = c("geneid" = "geneid", "genome_id" = "genome_id")
  ) 
names(family)[5]<-'id_id'
print('写入数据库')

dbWriteTable(con,"genefamily",family,overwrite=F,,append=T,row.names=F)
print('断开数据库')
DBI::dbDisconnect(con)
print('断开数据库成功')
