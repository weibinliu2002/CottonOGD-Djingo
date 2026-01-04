#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)
name_path<-args[1]

paths<-args[2]

namess<-list.files(name_path,full.names = FALSE)
#print(namess)

print(namess)
app<-function(name1){
    path<-paste0(paths,"/",name1)
    #print(path)
    fil<-list.files(path,full.names = FALSE)
    #print(fil)
    grep("genom|chr",fil)
    genome<-grep("geno|chr",fil,value = TRUE)
    genome<-grep("a$",genome,value = TRUE)
    gff<-fil[grep("gff",fil)]
    gff<-grep("gff|gff3$",gff,value = TRUE)
    print(name1)
    #name1<-sub('(', "\\(", name1, fixed = TRUE)
    #name1<-sub(')', "\\)", name1, fixed = TRUE)
    print(genome)
    print(gff)
    print(name1)
   system(paste0("bash add_jbrowes.sh \"",name1,"\" \"",path,"\" \"",genome,"\" \"",gff,"\""))
}
sapply(namess,app)
