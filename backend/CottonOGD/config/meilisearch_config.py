"""
Meilisearch 客户端配置。
- 从 Django settings 读取 URL 与 keys；
- master key 只在管理命令（setup_meili_keys / rebuild_index / sync_genes）中使用；
- 前端只可使用 search-only API key，禁止将 master/admin key 暴露给前端。
"""
from __future__ import annotations
from typing import Optional
import meilisearch


class MeilisearchConfig:
    """集中存放 Meilisearch 配置与客户端工厂方法。"""

    # 业务常量（视图不应硬编码）
    INDEX_NAME = 'genemaster'
    FAMILY_INDEX_NAME = 'family'
    MAX_LIMIT = 100        # 单次最多返回条数
    MAX_OFFSET = 9900      # Meilisearch 默认 maxTotalHits=1000，
                           # 如需更深的分页，需在索引设置中调大 pagination.maxTotalHits
    RETRIEVE_FIELDS = ['geneid', 'alias', 'genome_id', 'id']

    # ---------------------------------------------------------------------
    # 索引注册表：统一管理「可用索引」的元数据。
    # - 检索代理（/search/）据此校验 index 白名单；
    # - /get_search_indexes/ 据此返回给前端渲染库选择器。
    # 新增索引只需在此登记 + 建好索引，前端无需改代码。
    # ---------------------------------------------------------------------
    INDEX_META = {
        'genemaster': {
            'label': '基因主表',
            'description': '全部基因组基因 ID / 检索名（genemaster）',
            'searchable_attributes': ['geneid', 'alias'],
            'filterable_attributes': ['genome_id'],
            'default_attributes_to_retrieve': ['id', 'geneid', 'alias', 'genome_id'],
            'default_attributes_to_highlight': ['geneid', 'alias'],
        },
        'family': {
            'label': '基因家族',
            'description': 'TF / TR / kinase 家族分类（genefamily）',
            # 全部字段均可搜、可筛
            'searchable_attributes': [
                'geneid', 'geneid_raw', 'alias', 'genome_id',
                'TF_class', 'class_name', 'TF_name',
            ],
            'filterable_attributes': [
                'geneid', 'geneid_raw', 'alias', 'genome_id',
                'TF_class', 'class_name', 'TF_name',
            ],
            'default_attributes_to_retrieve': [
                'id', 'geneid', 'geneid_raw', 'alias', 'genome_id',
                'TF_class', 'class_name', 'TF_name',
            ],
            'default_attributes_to_highlight': [
                'geneid', 'geneid_raw', 'alias', 'genome_id',
                'TF_class', 'class_name', 'TF_name',
            ],
        },
    }

    @classmethod
    def allowed_indexes(cls):
        """可选索引白名单（注册表中的 uid 集合）。"""
        return frozenset(cls.INDEX_META)

    @classmethod
    def _get_settings(cls):
        """延迟导入 settings，避免 Django 未初始化时触发 import 错误。"""
        from django.conf import settings  # noqa: WPS433
        return settings

    @classmethod
    @property
    def MEILISEARCH_URL(cls) -> str:
        return cls._get_settings().MEILISEARCH_URL

    @classmethod
    def get_client(cls, use_master: bool = False) -> meilisearch.Client:
        """
        构造 Meilisearch 客户端。

        Args:
            use_master: True 时强制使用 master key（管理命令）。
                        False 时优先 frontend key，frontend key 为空时回退 master。

        Returns:
            meilisearch.Client 实例（snake_case 参数）。
        """
        settings = cls._get_settings()
        url = settings.MEILISEARCH_URL
        master_key: str = getattr(settings, 'MEILISEARCH_MASTER_KEY', '') or ''
        frontend_key: str = getattr(settings, 'MEILISEARCH_FRONTEND_API_KEY', '') or ''

        if use_master:
            api_key = master_key
        else:
            api_key = frontend_key or master_key

        # meilisearch python 客户端 0.40.x 接收 (url, api_key)
        return meilisearch.Client(url, api_key)


# 模块级客户端实例（懒加载）。
# 禁止在 import 时立即调用，保留此符号用于向后兼容。
meilisearch_client: Optional[meilisearch.Client] = None
