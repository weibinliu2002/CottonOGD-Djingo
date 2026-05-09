args <- commandArgs(trailingOnly = TRUE)
input <- args[1]

# 加载parallel包用于多线程处理
library(parallel)

# 读取数据
data <- read.table(input, header=F, col.names=c('name','genome','gff'))

# 获取系统核心数，设置并行计算的线程数
num_cores <- 2
if (num_cores > 1) {
  num_cores <- num_cores - 1  # 保留一个核心给系统
}
cat(paste0('Using ', num_cores, ' cores for parallel processing\n'))

# 定义处理函数
process_row <- function(i) {
  cmd <- paste0('Script/gene_seq.sh -n ', data$name[i], ' -f ', data$gff[i], ' -g ', data$genome[i] ,' -w .')
  print(cmd)
  system(cmd, wait=TRUE)
}

# 使用mclapply进行并行处理
mclapply(1:nrow(data), process_row, mc.cores=num_cores)
