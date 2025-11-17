library(DBI)
library(RMySQL)
con <- dbConnect(RMySQL::MySQL(),
                 dbname = "CottonOGD-ortho",
                 host = "localhost",
                 user = "root",
                 password = "1234")
dbListTables(con)
DBI::dbDisconnect(con)