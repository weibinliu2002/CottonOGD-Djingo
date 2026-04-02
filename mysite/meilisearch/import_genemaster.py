import pymysql
import meilisearch
import time
import sys
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor

# 添加父目录到路径以导入配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meilisearch_config import MeilisearchConfig

# Meilisearch 连接配置
client = MeilisearchConfig.get_client()

# MySQL 数据库连接配置
db_config = {
    'host': '172.28.226.114',
    'user': 'root',
    'password': '1234',
    'port': 3306,
    'database': 'cottonogd-ortho',
    'charset': 'utf8mb4'
}

# 线程安全的计数器
class Counter:
    def __init__(self):
        self.value = 0
        self.lock = threading.Lock()
    
    def increment(self):
        with self.lock:
            self.value += 1
            return self.value
    
    def get(self):
        with self.lock:
            return self.value

def clean_document_id(doc_id):
    """
    清理文档标识符，确保符合 Meilisearch 的要求
    Meilisearch 文档标识符只能包含：字母数字字符 (a-z A-Z 0-9)、连字符 (-) 和下划线 (_)
    """
    # 将点号和其他无效字符替换为下划线
    cleaned_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(doc_id))
    # 确保长度不超过 511 字节
    if len(cleaned_id.encode('utf-8')) > 511:
        # 截断并添加哈希值以确保唯一性
        truncated = cleaned_id[:490]
        hash_value = hash(cleaned_id) % 10000
        cleaned_id = f"{truncated}_{hash_value}"
    return cleaned_id

def import_batch(batch, batch_num, total_batches, success_counter, failure_counter):
    """
    导入单个批次的数据到 Meilisearch
    
    Args:
        batch: 要导入的文档批次
        batch_num: 批次编号
        total_batches: 总批次数
        success_counter: 成功计数器
        failure_counter: 失败计数器
    """
    print(f"线程 {threading.current_thread().name} 正在处理批次 {batch_num}/{total_batches} ({len(batch)} 条记录)...")
    
    try:
        task = client.index('genemaster').add_documents(batch)
        print(f"批次 {batch_num} 已提交，任务 ID: {task.task_uid}")
        
        # 等待任务完成
        while True:
            task_info = client.get_task(task.task_uid)
            if task_info['status'] in ['succeeded', 'failed']:
                break
            time.sleep(0.5)
        
        if task_info['status'] == 'succeeded':
            success_counter.increment()
            print(f"批次 {batch_num} 导入成功")
        else:
            failure_counter.increment()
            error_msg = task_info.get('error', '未知错误')
            print(f"批次 {batch_num} 导入失败: {error_msg}")
            
    except Exception as e:
        failure_counter.increment()
        print(f"批次 {batch_num} 导入时出错: {e}")

def import_genemaster_to_meilisearch():
    try:
        # 连接到 MySQL 数据库
        print("正在连接到 MySQL 数据库...")
        db = pymysql.connect(**db_config)
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SET NAMES utf8mb4")
        
        # 获取 Meilisearch 中已存在的基因 ID
        print("正在获取 Meilisearch 中已存在的基因 ID...")
        existing_geneids = set()
        
        # 分批获取已存在的基因 ID
        batch_size = 1000
        offset = 0
        while True:
            documents = client.index('genemaster').get_documents({
                'limit': batch_size,
                'offset': offset,
                'fields': ['geneid']
            })
            
            if not documents.results:
                break
            
            for doc in documents.results:
                existing_geneids.add(doc.geneid)
            
            offset += batch_size
            if len(documents.results) < batch_size:
                break
        
        print(f"Meilisearch 中已存在 {len(existing_geneids)} 个基因")
        
        # 查询 genemaster 表中不在 Meilisearch 中的数据
        print("正在查询 genemaster 表中未导入的数据...")
        
        # 构建不在子查询
        if existing_geneids:
            # 构建单个值列表的 NOT IN 查询
            placeholders = ','.join(['%s'] * len(existing_geneids))
            values = list(existing_geneids)
            query = f"SELECT * FROM genemaster WHERE geneid NOT IN ({placeholders})"
            cursor.execute(query, values)
        else:
            # 如果 Meilisearch 中没有数据，查询所有
            cursor.execute("SELECT * FROM genemaster")
        
        rows = cursor.fetchall()
        
        print(f"找到 {len(rows)} 条未导入的记录")
        
        # 转换数据为 Meilisearch 文档格式
        documents = []
        for row in rows:
            # 清理 geneid 以符合 Meilisearch 文档标识符要求
            cleaned_geneid = clean_document_id(row['geneid'])
            documents.append({
                'geneid': cleaned_geneid,
                'original_geneid': row['geneid'],  # 保留原始 geneid
                'alias': row['alias'],
                'genome_id': row['genome_id'],
                'id': row['id'],
            })
        
        # 批量添加文档到 Meilisearch
        if documents:
            print("正在导入数据到 Meilisearch...")
            batch_size = 1000
            total_batches = (len(documents) + batch_size - 1) // batch_size
            
            # 创建批次列表
            batches = []
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_num = i // batch_size + 1
                batches.append((batch, batch_num))
            
            # 线程安全的计数器
            success_counter = Counter()
            failure_counter = Counter()
            
            # 使用线程池并行处理
            max_workers = min(4, os.cpu_count())  # 使用最多 4 个线程
            print(f"使用 {max_workers} 个线程进行并行导入")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有批次任务
                futures = []
                for batch, batch_num in batches:
                    future = executor.submit(
                        import_batch,
                        batch,
                        batch_num,
                        total_batches,
                        success_counter,
                        failure_counter
                    )
                    futures.append(future)
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
            
            print(f"数据导入完成！成功: {success_counter.get()}, 失败: {failure_counter.get()}")
        else:
            print("所有数据已存在于 Meilisearch 中，无需导入")
        
        cursor.close()
        db.close()
        
    except Exception as e:
        print(f"导入过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import_genemaster_to_meilisearch()
