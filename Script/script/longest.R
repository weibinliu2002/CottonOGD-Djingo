args <- commandArgs(trailingOnly = TRUE)
input <- args[1]
out <- args[2]

fa<-Biostrings::readAAStringSet(input)
old_name<-names(fa)
new_name<-gsub('\\.\\d+','',old_name)
#print(old_name)
#print(new_name)
long<-data.frame(old_name, new_name, width = fa@ranges@width)
#print(str(long))
# 找到每个new_name对应的最大宽度
max_widths<-long|>dplyr::group_by(new_name)|>dplyr::summarize(max_width=max(width))|>dplyr::ungroup()

# 合并回原始数据，保留old_name信息，当有多个相同最大值时只取第一个
result<-long|>dplyr::left_join(max_widths, by="new_name")|>dplyr::filter(width == max_width)|>dplyr::group_by(new_name)|>dplyr::slice_head(n=1)|>dplyr::ungroup()


# 输出结果  
#print(result)
#write.table(result, file = out, sep = "\t", quote = FALSE, row.names = FALSE, col.names = TRUE)
fa2<-fa[result$old_name]
#print(fa2)
Biostrings::writeXStringSet(fa2, out)
