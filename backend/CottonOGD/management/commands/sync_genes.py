"""
增量同步 GeneMaster 到 Meilisearch（以 created_at 为游标）。
同时消费 cursor.json 中的 pending_deletes 队列。
"""
from __future__ import annotations
import json
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError

from CottonOGD.config.meilisearch_config import MeilisearchConfig
from CottonOGD.management.commands.rebuild_index import (
    wait_for_task, task_uid_of, INDEX_NAME,
)

logger = logging.getLogger(__name__)
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class Command(BaseCommand):
    help = '增量同步新增/删除的 GeneMaster 到 Meilisearch。'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=1000)
        parser.add_argument('--retry', type=int, default=3,
                            help='每批失败重试次数（指数退避 1/2/4s）。')
        parser.add_argument('--reset-cursor', action='store_true',
                            help='忽略已存游标，从 epoch 开始重跑一次全增量（不会删索引）。')

    def handle(self, *args, **options):
        from django.conf import settings
        from CottonOGD.models import GeneMaster

        cursor_path: Path = settings.MEILISEARCH_CURSOR_PATH
        cursor_path.parent.mkdir(parents=True, exist_ok=True)

        batch_size = max(1, min(options['batch_size'], 10000))
        retry_times = max(0, int(options['retry']))

        cursor = self._load_cursor(cursor_path)
        if options['reset_cursor']:
            self.stdout.write(self.style.WARNING('--reset-cursor：游标已重置到 epoch。'))
            cursor = {}

        last_created_at = self._parse_iso(
            cursor.get('indexes', {}).get(INDEX_NAME, {}).get('last_created_at_iso')
        ) or EPOCH
        pending_deletes = list(cursor.get('pending_deletes') or [])

        client = MeilisearchConfig.get_client(use_master=True)

        batches_run = 0
        max_created = last_created_at

        # ------ 1) upsert 新增/更新 ------
        self.stdout.write(f'[1/2] 筛选 created_at > {last_created_at.isoformat()} 的 GeneMaster ...')
        qs = GeneMaster.objects.filter(created_at__gt=last_created_at).order_by(
            'created_at', 'pk').only('id', 'geneid', 'genome_id', 'alias', 'created_at')

        batch = []
        for obj in qs.iterator(chunk_size=batch_size):
            created_at = obj.created_at
            if created_at and (created_at.tzinfo is None):
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at and created_at > max_created:
                max_created = created_at
            batch.append({
                'id': str(obj.id),
                'geneid': obj.geneid,
                'genome_id': obj.genome_id,
                'alias': obj.alias,
                'created_at': created_at.isoformat() if created_at else None,
            })
            if len(batch) >= batch_size:
                self._send_with_retry(batch, client, retry_times)
                batches_run += 1
                batch = []
        if batch:
            self._send_with_retry(batch, client, retry_times)
            batches_run += 1
        self.stdout.write(f'  upsert 批次：{batches_run}（游标起点：{last_created_at.isoformat()}）')

        # ------ 2) 消费 pending_deletes ------
        if pending_deletes:
            self.stdout.write(f'[2/2] 消费待删队列：{len(pending_deletes)} 条 ...')
            # 字符串化去重
            ids = list({str(i) for i in pending_deletes if i is not None})
            for start in range(0, len(ids), batch_size):
                chunk = ids[start:start + batch_size]
                attempt = 0
                while True:
                    try:
                        task = client.index(INDEX_NAME).delete_documents(chunk)
                        wait_for_task(client, task_uid_of(task), label='delete_documents')
                        break
                    except CommandError:
                        raise
                    except Exception as exc:
                        attempt += 1
                        if attempt > retry_times:
                            raise CommandError(f'删除 Meili 文档失败: {exc}') from exc
                        self.stdout.write(
                            self.style.WARNING(f'  删除重试 {attempt}/{retry_times}: {exc}'))
                        time.sleep(2 ** attempt)
        else:
            self.stdout.write('[2/2] 无待删队列。')

        # ------ 写回游标 ------
        cursor['pending_deletes'] = []
        cursor.setdefault('indexes', {}).setdefault(INDEX_NAME, {})
        if max_created and max_created.tzinfo is None:
            max_created = max_created.replace(tzinfo=timezone.utc)
        cursor['indexes'][INDEX_NAME]['last_created_at_iso'] = max_created.isoformat()
        cursor['indexes'][INDEX_NAME]['last_sync_run_at'] = (
            datetime.now(timezone.utc).isoformat())
        self._dump_cursor(cursor_path, cursor)
        self.stdout.write(self.style.SUCCESS(
            f'sync_genes 完成。游标已保存到 {cursor_path}'))

    # ---------- helpers ----------
    def _send_with_retry(self, batch, client, retry_times):
        attempt = 0
        while True:
            try:
                task = client.index(INDEX_NAME).add_documents(batch, primary_key='id')
                wait_for_task(client, task_uid_of(task), label='sync_upsert')
                return
            except CommandError:
                raise
            except Exception as exc:
                attempt += 1
                if attempt > retry_times:
                    raise CommandError(f'add_documents 连续失败: {exc}') from exc
                self.stdout.write(self.style.WARNING(
                    f'  写入重试 {attempt}/{retry_times}: {exc}'))
                time.sleep(2 ** attempt)

    def _load_cursor(self, cursor_path: Path) -> dict:
        if not cursor_path.exists():
            return {}
        try:
            return json.loads(cursor_path.read_text(encoding='utf-8'))
        except Exception as exc:
            logger.warning('读取 meili 游标失败（将从头开始）：%s', exc)
            return {}

    def _dump_cursor(self, cursor_path: Path, data: dict):
        cursor_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _parse_iso(self, s):
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
