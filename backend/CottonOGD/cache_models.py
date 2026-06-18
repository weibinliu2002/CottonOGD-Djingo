# cache_models.py

import pickle
import logging
from collections import defaultdict
from django.db import connection
from django.core.cache import caches

logger = logging.getLogger(__name__)

# ==========================================
# 1. 基础框架：缓存管理器和基类 (类似 ORM 的 Manager 和 Model)
# ==========================================

class CacheManager:
    """
    缓存管理器，类似 Django 的 objects
    负责处理 Redis 连接、序列化、版本控制和读取
    """
    cache_alias = 'geneset'  # 指向 settings.py 中配置的专用 Redis

    def __init__(self, model_class):
        self.model_class = model_class

    @property
    def _cache(self):
        return caches[self.cache_alias]

    def _get_version(self):
        return int(self._cache.get(self.model_class.version_key, 0) or 0)

    def _make_key(self, **kwargs):
        """生成带版本号的 Redis Key"""
        version = self._get_version()
        # 子类可以重写 key_format
        return self.model_class.key_format.format(version=version, **kwargs)

    def get(self, **kwargs):
        """
        获取缓存数据，如果 Redis 没有则触发构建
        类似 Model.objects.get()
        """
        key = self._make_key(**kwargs)
        raw = self._cache.get(key)
        
        if raw is not None:
            return self.model_class(data=pickle.loads(raw), **kwargs)
        
        # 缓存未命中，触发构建
        logger.warning(f"Cache miss for {key}, building...")
        self.build_all()
        
        # 重新获取
        key = self._make_key(**kwargs)
        raw = self._cache.get(key)
        if raw is not None:
            return self.model_class(data=pickle.loads(raw), **kwargs)
        
        return None # 构建后仍没有（可能是无效的 genome_name）

    def build_all(self):
        """
        触发全量构建，类似 makemigrations/migrate
        版本号 +1，保证旧数据自动失效
        """
        new_version = self._get_version() + 1
        logger.info(f"开始构建 {self.model_class.__name__}，新版本: {new_version}")
        
        # 调用具体 Model 类定义的构建逻辑
        all_data = self.model_class.build_data(new_version)
        
        # 批量写入 Redis
        for key_suffix, data in all_data.items():
            key = self.model_class.key_format.format(version=new_version, suffix=key_suffix)
            self._cache.set(key, pickle.dumps(data), timeout=None)
            
        # 更新版本号
        self._cache.set(self.model_class.version_key, new_version, timeout=None)
        
        # 清理上一个版本的数据（可选）
        old_version = new_version - 1
        if old_version > 0:
            # 这里为了简化，没有自动清理旧版本，Redis 内存够用可以忽略
            pass


class CacheModelBase:
    """
    缓存模型基类，类似 django.db.models.Model
    子类必须定义：version_key, key_format, build_data()
    """
    version_key = None       # 版本号的 Redis Key
    key_format = None        # 数据的 Redis Key 格式
    
    # 注入 Manager
    objects = None 

    def __init__(self, data, **kwargs):
        self._data = data
        # 将 kwargs 作为实例属性（如 genome_name）
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def get_manager(cls):
        if cls.objects is None:
            cls.objects = CacheManager(cls)
        return cls.objects

    # 语法糖，让子类可以直接调用 GenomeGenesetCache.objects.get()
    objects = property(lambda cls: cls.get_manager())

    @staticmethod
    def build_data(version):
        """
        纯数据构建逻辑（查库、计算等），必须由子类实现
        返回字典：{ 'key_suffix': data }
        """
        raise NotImplementedError


# ==========================================
# 2. 具体业务模型：基因集缓存
# ==========================================

class GenomeGenesetCache(CacheModelBase):
    """
    基因组基因集缓存模型
    将之前那堆复杂的 SQL 和 GO 传播逻辑封装在里面
    """
    version_key = 'geneset_cache_version'
    key_format = 'geneset_v{version}_{suffix}'  # suffix 可以是基因组名

    @staticmethod
    def build_data(version):
        """全量构建所有基因组的基因集"""
        genomes_data = {}

        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM species")
            genome_names = [row[0] for row in cursor.fetchall()]

            for genome_name in genome_names:
                # 这里放之前那堆复杂的查库和 GO 传播逻辑
                # 为了简洁，我简化了代码，你把之前的逻辑搬进来即可
                data = GenomeGenesetCache._build_single_genome(cursor, genome_name)
                if data:
                    genomes_data[genome_name] = data

        return genomes_data

    @staticmethod
    def _build_single_genome(cursor, genome_name):
        """构建单个基因组的逻辑（封装内部实现）"""
        logger.info(f"正在构建基因组: {genome_name}")
        
        cursor.execute("SELECT id, geneid FROM genemaster WHERE genome_id = %s", [genome_name])
        id_to_geneid = {}
        background_genes = set()
        for pk, geneid in cursor.fetchall():
            id_to_geneid[pk] = geneid
            background_genes.add(geneid)
        
        if not background_genes:
            return None

        # --- GO 逻辑 (搬运你之前的代码) ---
        # ... cursor.execute(...) 
        # ... True Path Rule 传播 ...
        # go_genesets = {...}
        # go_type_map = {...}

        # --- KEGG 逻辑 (搬运你之前的代码) ---
        # ... cursor.execute(...) 
        # kegg_genesets = {...}

        # 模拟返回结果
        return {
            'go_genesets': {}, # 替换为真实计算结果
            'kegg_genesets': {}, # 替换为真实计算结果
            'go_type_map': {}, # 替换为真实计算结果
            'background_genes': background_genes
        }

    # ==========================================
    # 3. 实例方法：像 Model 一样访问属性
    # ==========================================
    @property
    def go_genesets(self):
        return self._data.get('go_genesets', {})

    @property
    def kegg_genesets(self):
        return self._data.get('kegg_genesets', {})

    @property
    def go_type_map(self):
        return self._data.get('go_type_map', {})

    @property
    def background_genes(self):
        return self._data.get('background_genes', set())
        
    def is_valid_gene(self, gene_name):
        """便捷方法：检查基因是否在背景集中"""
        return gene_name in self.background_genes

