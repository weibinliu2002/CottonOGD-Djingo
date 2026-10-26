"""
危险操作：删除并重建 family 索引（数据源：MySQL genefamily 表）。
必须提供 --confirm 才会真正执行。

索引文档结构（primaryKey=id）::

    {
      "id":         "<GeneMaster 主键>",       # 前端用于详情跳转
      "geneid":     "A01G00200",              # 规范化，取自 genemaster.geneid
      "geneid_raw": "A01G00200.mRNA1",        # genefamily.geneid 原值
      "alias":      "<物种名>::<geneid>",
      "genome_id":  "<物种名>",                # 与 genemaster 索引取值一致，便于统一 filter
      "TF_class":   "TF" | "TR" | "kinase",
      "class_name": "NAC" | ...,
      "TF_name":    "NAC" | ...
    }

取数方式：按主键区间分批（id_id > last_pk），不使用 JOIN，
避免外键约束关闭（settings 中 FOREIGN_KEY_CHECKS=0）导致关联行被静默丢弃。
"""
from __future__ import annotations
import sys
import time

from django.core.management.base import BaseCommand, CommandError

from CottonOGD.management.commands.rebuild_index import (
    as_dict, index_primary_key, list_index_uids, task_uid_of, wait_for_task,
)

INDEX_NAME = 'family'
FAMILY_FIELDS = ('id_id', 'geneid', 'genome_id', 'TF_class', 'class_name', 'TF_name')


class Command(BaseCommand):
    help = '危险操作：重建 family 索引（数据源 genefamily 表）。必须 --confirm。'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true',
                            help='显式确认后才会真正执行（必填）。')
        parser.add_argument('--batch-size', type=int, default=1000,
                            help='每批写入文档数 (1-10000)。')
        parser.add_argument('--workers', type=int, default=1,
                            help='暂未使用，保留并发扩展。上限 4。')
        parser.add_argument('--progress-every', type=int, default=50,
                            help='每多少批打印一次进度（默认 50 批）。')

    def handle(self, *args, **options):
        from CottonOGD.config.meilisearch_config import MeilisearchConfig
        from CottonOGD.models import Family, Species_info

        if not options['confirm']:
            self.stderr.write(self.style.ERROR(
                f'这是危险操作，会删除 {INDEX_NAME} 索引并全量重建。'
                ' 请确认后再次运行并加上 --confirm 参数。'))
            sys.exit(2)

        batch_size = max(1, min(options['batch_size'], 10000))
        workers = max(1, min(options['workers'], 4))
        progress_every = max(1, options['progress_every'])
        if workers > 1:
            self.stdout.write(self.style.WARNING(
                f'--workers={workers} 当前版本串行执行，保留语义以便未来启用线程池。'))

        meta = MeilisearchConfig.INDEX_META[INDEX_NAME]
        searchable = meta['searchable_attributes']
        filterable = meta['filterable_attributes']

        client = MeilisearchConfig.get_client(use_master=True)

        # 1) 删除已有索引（若存在）
        if INDEX_NAME in list_index_uids(client):
            self.stdout.write(f'[1/5] 删除已有索引 {INDEX_NAME} ...')
            try:
                task = client.delete_index(INDEX_NAME)
                wait_for_task(client, task_uid_of(task), label='delete_index')
            except Exception as exc:
                if 'index_not_found' not in str(exc):
                    raise CommandError(str(exc)) from exc
        else:
            self.stdout.write(f'[1/5] 索引 {INDEX_NAME} 不存在，跳过删除。')

        # 2) 创建索引
        self.stdout.write(f'[2/5] 创建索引 {INDEX_NAME} primaryKey=id ...')
        task = client.create_index(INDEX_NAME, {'primaryKey': 'id'})
        wait_for_task(client, task_uid_of(task), label='create_index')

        # 3) 更新 settings
        self.stdout.write('[3/5] 更新 settings: searchable/filterable attributes ...')
        task = client.index(INDEX_NAME).update_settings({
            'searchableAttributes': searchable,
            'filterableAttributes': filterable,
        })
        wait_for_task(client, task_uid_of(task), label='update_settings')

        # 4) 分批导入
        total = Family.objects.count()
        self.stdout.write(
            f'[4/5] 从 MySQL genefamily 导入 {total:,} 条 (batch={batch_size}) ...')
        if total == 0:
            self.stdout.write(self.style.WARNING('genefamily 为空，跳过导入。'))
            processed, missing_gene = 0, 0
        else:
            processed, missing_gene = self._import_all(
                client, batch_size, progress_every, total)

        # 5) 校验 settings
        self.stdout.write('[5/5] 校验索引 settings ...')
        primary_key = index_primary_key(client, INDEX_NAME)
        if primary_key != 'id':
            raise CommandError(f'primaryKey 异常: {primary_key}')
        settings = as_dict(client.index(INDEX_NAME).get_settings())
        if settings.get('searchableAttributes') != searchable:
            raise CommandError(
                f'searchableAttributes 异常: {settings.get("searchableAttributes")}')
        if settings.get('filterableAttributes') != filterable:
            raise CommandError(
                f'filterableAttributes 异常: {settings.get("filterableAttributes")}')

        if missing_gene:
            self.stdout.write(self.style.WARNING(
                f'注意：{missing_gene} 条记录的 id_id 在 genemaster 中不存在，'
                f'已回退使用 genefamily.geneid 作为 geneid。'))
        self.stdout.write(self.style.SUCCESS(
            f'rebuild_family_index 完成，共导入 {processed:,}/{total:,} 条。'))

    # ---------- helpers ----------
    def _import_all(self, client, batch_size, progress_every, total):
        """
        按主键区间分批导入，返回 (已处理条数, geneid 缺失条数)。
        """
        from CottonOGD.models import Family, GeneMaster, Species_info

        # 物种 id -> 物种名（仅数百条，一次性载入）
        genome_map = dict(Species_info.objects.values_list('id', 'name'))

        processed = 0
        missing_gene = 0
        last_pk = 0
        page = 0
        t0 = time.time()

        while True:
            rows = list(
                Family.objects.filter(id_id__gt=last_pk)
                .order_by('id_id')
                .values(*FAMILY_FIELDS)[:batch_size]
            )
            if not rows:
                break
            last_pk = rows[-1]['id_id']
            page += 1

            # 批量取规范化 geneid（genemaster.geneid），避免逐条查询
            pks = [r['id_id'] for r in rows]
            gm_map = dict(
                GeneMaster.objects.filter(id__in=pks).values_list('id', 'geneid'))

            batch = []
            for r in rows:
                geneid = gm_map.get(r['id_id'])
                if not geneid:
                    missing_gene += 1
                    geneid = r['geneid'] or ''  # 兜底，保证不丢行
                genome_name = genome_map.get(r['genome_id'], '')
                batch.append({
                    'id': str(r['id_id']),
                    'geneid': geneid,
                    'geneid_raw': r['geneid'] or '',
                    'alias': f'{genome_name}::{geneid}',
                    'genome_id': genome_name,
                    'TF_class': r['TF_class'] or '',
                    'class_name': r['class_name'] or '',
                    'TF_name': r['TF_name'] or '',
                })

            self._flush(batch, client)
            processed += len(batch)

            if page % progress_every == 0 or processed >= total:
                elapsed = time.time() - t0
                rate = processed / elapsed if elapsed else 0
                self.stdout.write(
                    f'    进度 {processed:,}/{total:,} '
                    f'({processed * 100.0 / total:.1f}%) '
                    f'用时 {elapsed:,.0f}s 速率 {rate:,.0f} docs/s')

        return processed, missing_gene

    @staticmethod
    def _flush(batch, client):
        """写入一批文档并等待任务完成。"""
        try:
            task = client.index(INDEX_NAME).add_documents(batch, primary_key='id')
            wait_for_task(client, task_uid_of(task), label='add_documents')
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f'写入批次失败: {exc}') from exc
