# cache_models.py

import pickle
import logging
from collections import defaultdict
from django.db import connection
from django.core.cache import caches

logger = logging.getLogger(__name__)

# ==========================================
# 1. 基础框架：缓存管理器和描述符
# ==========================================

class CacheManagerDescriptor:
    """
    描述符类，用于实现类似 Django Model.objects 的类级别访问
    支持子类隔离，确保每个 Model 都有自己的 Manager
    """
    def __init__(self):
        self._managers = {}  # 用字典缓存每个类的 Manager

    def __get__(self, instance, owner):
        # owner 是调用 objects 的类（比如 GenomeGenesetCache）
        if owner not in self._managers:
            self._managers[owner] = CacheManager(owner)
        return self._managers[owner]



class CacheManager:
    """
    缓存管理器，类似 Django 的 objects
    """
    cache_alias = 'default'  # 使用 settings.py 中的 default 缓存

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
        return self.model_class.key_format.format(version=version, **kwargs)

    def get(self, **kwargs):
        """获取缓存数据，如果 Redis 没有则触发构建"""
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
        
        return None

    def build_all(self):
        """触发全量构建，版本号 +1"""
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
        logger.info(f"构建完成！当前版本: {new_version}")


class CacheModelBase:
    """缓存模型基类"""
    version_key = None       
    key_format = None        
    
    # 使用描述符
    objects = CacheManagerDescriptor()

    def __init__(self, data, **kwargs):
        self._data = data
        for k, v in kwargs.items():
            setattr(self, k, v)


# ==========================================
# 2. 具体业务模型：基因集缓存
# ==========================================

class GenomeGenesetCache(CacheModelBase):
    """
    基因组基因集缓存模型
    """
    version_key = 'geneset_cache_version'
    key_format = 'geneset_v{version}_{suffix}'

    @staticmethod
    def build_data(version):
        """全量构建所有基因组的基因集"""
        genomes_data = {}

        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM species")
            genome_names = [row[0] for row in cursor.fetchall()]

            for genome_name in genome_names:
                data = GenomeGenesetCache._build_single_genome(cursor, genome_name)
                if data:
                    genomes_data[genome_name] = data

        return genomes_data

    @staticmethod
    def _build_single_genome(cursor, genome_name):
        """构建单个基因组的逻辑"""
        logger.info(f"正在构建基因组: {genome_name}")
        
        # 1. 获取 id_id 到 geneid 的映射及背景基因
        cursor.execute("SELECT id, geneid FROM genemaster WHERE genome_id = %s", [genome_name])
        id_to_geneid = {}
        background_genes = set()
        for pk, geneid in cursor.fetchall():
            id_to_geneid[pk] = geneid
            background_genes.add(geneid)
        
        if not background_genes:
            return None

        # 2. 构建 GO 基因集 (带 True Path Rule 传播)
        cursor.execute("""
            SELECT gg.id_id, gg.go_id 
            FROM gene_go gg
            JOIN genemaster gm ON gg.id_id = gm.id
            WHERE gm.genome_id = %s AND gg.go_id IS NOT NULL
        """, [genome_name])
        
        go2ids_direct = defaultdict(set)
        for id_id, go_id in cursor.fetchall():
            go2ids_direct[go_id].add(id_id)

        # 2.1 获取 is_a 关系并递归传播
        cursor.execute("SELECT subject_id, object_id FROM go_relationship WHERE relationship_type = 'is_a'")
        go_is_a = defaultdict(list)
        for sub, obj in cursor.fetchall():
            go_is_a[sub].append(obj)

        ancestor_cache = {}
        def get_go_ancestors(go_id):
            if go_id in ancestor_cache:
                return ancestor_cache[go_id]
            ancestors = set()
            for parent in go_is_a.get(go_id, []):
                ancestors.add(parent)
                ancestors |= get_go_ancestors(parent)
            ancestor_cache[go_id] = ancestors
            return ancestors

        go2ids_propagated = defaultdict(set)
        for go_id, id_set in go2ids_direct.items():
            all_gos = set([go_id])
            all_gos |= get_go_ancestors(go_id)
            for g in all_gos:
                go2ids_propagated[g] |= id_set

        # 2.2 获取 GO 名称和类型
        cursor.execute("SELECT id, name, namespace FROM go_term")
        go_info = {row[0]: {'name': row[1], 'namespace': row[2]} for row in cursor.fetchall()}

        go_genesets = {}
        go_type_map = {}
        for go_id, id_set in go2ids_propagated.items():
            gene_set = set()
            for id_id in id_set:
                if id_id in id_to_geneid:
                    gene_set.add(id_to_geneid[id_id])
            
            if not gene_set: continue
            
            info = go_info.get(go_id, {'name': '', 'namespace': ''})
            name = info.get('name', '')
            key = f"{go_id} {name}" if name else go_id
            go_genesets[key] = sorted(list(gene_set))
            
            ns = info.get('namespace', '')
            go_type_map[go_id] = 'BP' if 'biological' in ns else 'MF' if 'molecular' in ns else 'CC'

        # 3. 构建 KEGG 基因集
        cursor.execute("""
            SELECT gk.id_id, gk.kegg_id 
            FROM gene_kegg gk
            JOIN genemaster gm ON gk.id_id = gm.id
            WHERE gm.genome_id = %s AND gk.kegg_id IS NOT NULL
        """, [genome_name])
        
        gene2kos = defaultdict(set)
        for id_id, kegg_id in cursor.fetchall():
            for ko in str(kegg_id).split(','):
                ko = ko.strip().replace('ko:', '')
                if ko.startswith('K'):
                    gene2kos[id_id].add(ko)

        cursor.execute("""
            SELECT pe.enzyme_id, mp.pathway_id 
            FROM pathway_enzyme pe
            JOIN metabolic_pathway mp ON pe.pathway_id = mp.pathway_id
        """)
        ko2pathways = defaultdict(list)
        for ko_id, pathway_id in cursor.fetchall():
            ko2pathways[ko_id].append(pathway_id)

        cursor.execute("SELECT pathway_id, name FROM metabolic_pathway")
        pathway2name = {row[0]: row[1] for row in cursor.fetchall()}

        pathway2ids = defaultdict(set)
        for id_id, kos in gene2kos.items():
            for ko in kos:
                for pathway_id in ko2pathways.get(ko, []):
                    pathway2ids[pathway_id].add(id_id)

        kegg_genesets = {}
        for pathway_id, id_set in pathway2ids.items():
            gene_set = set()
            for id_id in id_set:
                if id_id in id_to_geneid:
                    gene_set.add(id_to_geneid[id_id])
            
            if not gene_set: continue
            
            name = pathway2name.get(pathway_id, '')
            key = f"{pathway_id} {name}" if name else pathway_id
            kegg_genesets[key] = sorted(list(gene_set))

        # 4. 返回当前基因组构建好的数据
        logger.info(f"基因组 {genome_name} 构建完成: GO集={len(go_genesets)}, KEGG集={len(kegg_genesets)}")
        return {
            'go_genesets': go_genesets,
            'kegg_genesets': kegg_genesets,
            'go_type_map': go_type_map,
            'background_genes': background_genes
        }

    # ==========================================
    # 实例方法：像 Model 一样访问属性
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
