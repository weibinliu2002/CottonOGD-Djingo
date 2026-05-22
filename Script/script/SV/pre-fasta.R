
#/usr/bin/Rscript
args<-commandArgs(trailingOnly = TRUE)
file1<-args[1]
file2<-args[2]
prefix_dir<-args[3]
print(file1)
fa1<-Biostrings::readAAStringSet(file1)
print(file1)
fa2<-Biostrings::readAAStringSet(file2)
print(file2)
fa1_name<-names(fa1)
fa1_nam<-grep('sca|tig',fa1_name,invert = TRUE, value = TRUE,ignore.case = TRUE)
fa1<-fa1[fa1_nam]
fa1 <- fa1[gtools::mixedorder(names(fa1))]
fa2_name<-names(fa2)
fa2_nam<-grep('sca|tig',fa2_name,invert = TRUE, value = TRUE,ignore.case = TRUE)
fa2<-fa2[fa2_nam]
fa2 <- fa2[gtools::mixedorder(names(fa2))]
Biostrings::writeXStringSet(fa1, paste0(prefix_dir,"/fa1_sorted.fa"))
Biostrings::writeXStringSet(fa2, paste0(prefix_dir,"/fa2_sorted.fa"))
