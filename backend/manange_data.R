library(DBI)
library(RMySQL)
con <- dbConnect(RMySQL::MySQL(),
                 dbname = "CottonOGD-ortho",
                 host = "127.0.0.1",
                 PORT=3306,
                 user = "root",
                 password = "1234",
                 )
dbListTables(con)


seq<-read.csv('D:/Users/21023/Desktop/fpkm.csv',sep = ',')
seq<-data.table::fread('D:/Users/21023/Desktop/fpkm.csv')
dbWriteTable(con,"fpkm4",seq,overwrite=T,row.names=F)
DBI::dbDisconnect(con)