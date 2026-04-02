"""
Meilisearch 配置和客户端
"""
import meilisearch

class MeilisearchConfig:
    MEILISEARCH_URL = 'http://172.28.226.114:7700'
    MEILISEARCH_API_KEY = '29IHoDlQOMKL0URlVIh7lb2McyxoaArhNPQJa0V9HoY'
    
    @classmethod
    def get_client(cls):
        return meilisearch.Client(
            cls.MEILISEARCH_URL,
            cls.MEILISEARCH_API_KEY
        )

# 创建全局客户端实例
meilisearch_client = MeilisearchConfig.get_client()