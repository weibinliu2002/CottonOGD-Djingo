# 导入所需的库
import pandas as pd
from sqlalchemy import create_engine 
import pymysql
pymysql.install_as_MySQLdb()
# 创建数据库连接
db = pymysql.connect(
   host="127.0.0.1",
   user="root",
   password="1234",
   port=3306,
   database="cottonogd-ortho"
)
# 创建游标对象，用于执行SQL查询
cursor = db.cursor()
cursor.execute("SET NAMES utf8mb4")
cursor.execute("SHOW tables;")
cursor.execute("USE cottonogd-ortho")
cursor.execute("SELECT * FROM genemaster")
# 打印查询结果
for row in cursor.fetchall():
    print(row)



with open('genemaster.csv', 'r') as f:
    reader = csv.reader(f)
    next(reader)  # 跳过表头
    for row in reader:
        cursor.execute("INSERT INTO genemaster (genome_id, geneid, alias, start, end, strand) VALUES (%s, %s, %s, %s, %s, %s)", row)
try:
    cursor.execute("SELECT * FROM genemaster")
    # 打印查询结果
    for row in cursor.fetchall():
        print(row)
except Exception as e:
    print(f"查询出错: {e}")



# 提交事务
db.commit()
# 关闭游标和数据库连接
cursor.close()
db.close()
