"""
GeneMaster post_save/post_delete -> Meilisearch 实时同步。
所有 Meili 异常必须吞掉，不得影响 Django 主事务写入。
"""
from __future__ import annotations
import logging
from datetime import datetime

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from CottonOGD.models import GeneMaster
from CottonOGD.config.meilisearch_config import MeilisearchConfig

logger = logging.getLogger(__name__)
INDEX_NAME = 'genemaster'


def _doc_from_obj(obj: GeneMaster) -> dict:
    created_at_iso = None
    if isinstance(obj.created_at, datetime):
        ca = obj.created_at
        if ca.tzinfo is None:
            ca = ca.replace(tzinfo=None)  # noqa: PLW0104  保留 naive
        created_at_iso = ca.isoformat()
    return {
        'id': str(obj.id),
        'geneid': obj.geneid,
        'genome_id': obj.genome_id,
        'alias': obj.alias,
        'created_at': created_at_iso,
    }


def _upsert_doc_to_meili(obj: GeneMaster) -> None:
    """单条 upsert 到 Meili；异常吞掉，不影响数据库事务。"""
    try:
        client = MeilisearchConfig.get_client(use_master=False)
        client.index(INDEX_NAME).add_documents([_doc_from_obj(obj)], primary_key='id')
    except Exception as exc:  # noqa: BLE001  必须吞掉
        logger.error(
            'Meili post_save upsert 失败 %s id=%s: %s',
            type(exc).__name__, obj.id, exc, exc_info=True)


def _delete_doc_from_meili(obj: GeneMaster) -> None:
    """单条删除 Meili 文档；异常吞掉。"""
    try:
        client = MeilisearchConfig.get_client(use_master=False)
        client.index(INDEX_NAME).delete_document(str(obj.id))
    except Exception as exc:  # noqa: BLE001  必须吞掉
        logger.error(
            'Meili post_delete 删除失败 %s id=%s: %s',
            type(exc).__name__, obj.id, exc, exc_info=True)


@receiver(post_save, sender=GeneMaster, weak=False)
def _on_gene_saved(sender, instance: GeneMaster, **kwargs) -> None:  # noqa: ARG001
    _upsert_doc_to_meili(instance)


@receiver(post_delete, sender=GeneMaster, weak=False)
def _on_gene_deleted(sender, instance: GeneMaster, **kwargs) -> None:  # noqa: ARG001
    _delete_doc_from_meili(instance)
