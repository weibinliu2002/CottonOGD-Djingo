"""
危险操作：删除并重建 genemaster 索引，从 MySQL 全量重写 Meilisearch。
必须提供 --confirm 才会真正执行。
"""
from __future__ import annotations
import sys
import time
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

INDEX_NAME = 'genemaster'


def _quote_filter_value(value):
    """仅在 verify 环节使用，避免循环依赖。"""
    return str(value).replace('\\', '\\\\').replace('"', '\\"')


def as_dict(obj):
    """
    把 meilisearch 客户端返回值统一成 dict。

    meilisearch >= 0.40 的 create_index / add_documents / get_task 等返回
    pydantic 模型（TaskInfo / Task），不能用 .get() 访问，必须先转换。
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    if hasattr(obj, 'dict'):
        return obj.dict()
    return {}


def task_uid_of(task):
    """从 TaskInfo / Task（pydantic 或 dict）中取任务 uid。"""
    data = as_dict(task)
    return data.get('task_uid') or data.get('uid')


def _index_items(client):
    """取 GET /indexes 的 results 列表（元素为 Index 包装对象或 dict）。"""
    res = client.get_indexes()
    if isinstance(res, dict):
        return list(res.get('results') or [])
    return list(getattr(res, 'results', None) or [])


def list_index_uids(client):
    """列出 Meilisearch 现有索引 uid。"""
    uids = []
    for item in _index_items(client):
        if isinstance(item, dict):
            uids.append(item.get('uid') or item.get('name'))
        else:
            uids.append(getattr(item, 'uid', None))
    return [u for u in uids if u]


def index_primary_key(client, uid):
    """
    读取索引主键名。

    注意：primaryKey 不在 GET /indexes/{uid}/settings 的返回里，
    必须从索引对象（GET /indexes/{uid}）读取，否则永远读到 None。
    """
    for item in _index_items(client):
        if isinstance(item, dict):
            if (item.get('uid') or item.get('name')) == uid:
                return item.get('primaryKey') or item.get('primary_key')
        elif getattr(item, 'uid', None) == uid:
            return getattr(item, 'primary_key', None)
    return None


def wait_for_task(client, task_uid, timeout=1800, poll=1.0, label=''):
    """
    轮询 Meilisearch 任务直到 succeeded / failed / timeout。

    Returns:
        最终 task dict。
    Raises:
        CommandError：失败或超时。
    """
    if not task_uid:
        raise CommandError(f'Task#{task_uid}({label}) 未取到有效 task_uid。')

    start = time.time()
    while True:
        try:
            task = as_dict(client.get_task(task_uid))
        except Exception as exc:
            raise CommandError(f'获取 task#{task_uid}({label}) 失败: {exc}') from exc

        status = task.get('status')
        if status == 'succeeded':
            return task
        if status == 'failed':
            err = task.get('error') or {}
            raise CommandError(
                f'Task#{task_uid}({label}) failed: '
                f'code={err.get("code")} type={err.get("type")} message={err.get("message")}'
            )
        if time.time() - start > timeout:
            raise CommandError(f'Task#{task_uid}({label}) 等待超时 ({timeout}s)。')
        time.sleep(poll)


class Command(BaseCommand):
    help = '危险操作：重建 genemaster 索引。必须 --confirm。'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true',
                            help='显式确认后才会真正执行（必填）。')
        parser.add_argument('--batch-size', type=int, default=1000,
                            help='每批写入文档数 (1-10000)。')
        parser.add_argument('--workers', type=int, default=1,
                            help='暂未使用，保留并发扩展。上限 4。')

    def handle(self, *args, **options):
        from CottonOGD.models import GeneMaster
        from CottonOGD.config.meilisearch_config import MeilisearchConfig

        if not options['confirm']:
            self.stderr.write(self.style.ERROR(
                '这是危险操作，会删除 genemaster 索引并全量重建。'
                ' 请确认后再次运行并加上 --confirm 参数。'))
            sys.exit(2)

        batch_size = max(1, min(options['batch_size'], 10000))
        workers = max(1, min(options['workers'], 4))
        if workers > 1:
            self.stdout.write(self.style.WARNING(
                f'--workers={workers} 当前版本串行执行，保留语义以便未来启用线程池。'))

        client = MeilisearchConfig.get_client(use_master=True)

        # 1) 删除索引（若存在）
        try:
            index_names = list_index_uids(client)
        except Exception as exc:
            raise CommandError(f'无法列出 Meilisearch 索引: {exc}') from exc

        if INDEX_NAME in index_names:
            self.stdout.write(f'[1/5] 删除已有索引 {INDEX_NAME} ...')
            try:
                task = client.delete_index(INDEX_NAME)
                wait_for_task(client, task_uid_of(task), label='delete_index')
            except Exception as exc:
                # 404 忽略
                if 'index_not_found' not in str(exc):
                    raise CommandError(str(exc)) from exc

        # 2) 创建索引
        self.stdout.write(f'[2/5] 创建索引 {INDEX_NAME} primaryKey=id ...')
        task = client.create_index(INDEX_NAME, {'primaryKey': 'id'})
        wait_for_task(client, task_uid_of(task), label='create_index')

        # 3) 更新 settings
        self.stdout.write('[3/5] 更新 settings: searchable/filterable attributes ...')
        task = client.index(INDEX_NAME).update_settings({
            'searchableAttributes': ['geneid', 'alias'],
            'filterableAttributes': ['genome_id'],
        })
        wait_for_task(client, task_uid_of(task), label='update_settings')

        # 4) 分批导入
        total = GeneMaster.objects.count()
        self.stdout.write(f'[4/5] 从 MySQL 导入 {total} 条 GeneMaster (batch={batch_size}) ...')
        if total == 0:
            self.stdout.write(self.style.WARNING('MySQL 中 GeneMaster 为空，跳过导入。'))
        else:
            processed = 0
            qs = GeneMaster.objects.all().order_by('pk').only(
                'id', 'geneid', 'genome_id', 'alias', 'created_at')
            batch = []
            t0 = time.time()
            for obj in qs.iterator(chunk_size=batch_size):
                created_at_iso = (obj.created_at.isoformat()
                                  if isinstance(obj.created_at, datetime) else
                                  (obj.created_at.isoformat() if obj.created_at else None))
                batch.append({
                    'id': str(obj.id),
                    'geneid': obj.geneid,
                    'genome_id': obj.genome_id,
                    'alias': obj.alias,  # 必须从 ORM 读（bulk_create 不会走 save）
                    'created_at': created_at_iso,
                })
                if len(batch) >= batch_size:
                    processed = self._flush(batch, processed, total, client, label='import')
                    batch = []
            if batch:
                processed = self._flush(batch, processed, total, client, label='import-last')

            elapsed = time.time() - t0
            self.stdout.write(self.style.SUCCESS(
                f'[4/5] 导入完成 {processed}/{total} 条，用时 {elapsed:,.1f}s。'))

        # 5) 校验 settings
        self.stdout.write('[5/5] 校验索引 settings ...')
        primary_key = index_primary_key(client, INDEX_NAME)
        if primary_key != 'id':
            raise CommandError(f'primaryKey 异常: {primary_key}')
        settings = as_dict(client.index(INDEX_NAME).get_settings())
        if settings.get('searchableAttributes') != ['geneid', 'alias']:
            raise CommandError(f'searchableAttributes 异常: {settings.get("searchableAttributes")}')
        if settings.get('filterableAttributes') != ['genome_id']:
            raise CommandError(f'filterableAttributes 异常: {settings.get("filterableAttributes")}')
        self.stdout.write(self.style.SUCCESS('rebuild_index 完成。'))

    # ---------- helpers ----------
    def _flush(self, batch, processed, total, client, label=''):
        try:
            task = client.index(INDEX_NAME).add_documents(batch, primary_key='id')
            wait_for_task(client, task_uid_of(task), label=f'add_documents::{label}')
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f'写入 Meili 批次失败({label}): {exc}') from exc
        processed += len(batch)
        pct = 100 * processed / max(1, total)
        self.stdout.write(f'  -> {processed}/{total} ({pct:5.1f}%) batch={len(batch)}')
        return processed
