"""
重建 Meilisearch `Orthologs` 索引（数据源：MySQL orthofinder_og_gene 表）。

文档粒度：每条 gene↔OG 成员关系一个文档（约 286 万条），
主键 id = "{og_code}|{species}|{geneid}"。

字段：
  - geneid            OrthoFinder transcript id（可搜）
  - genemaster_geneid 经 TranscriptMaster 解析到 GeneMaster.geneid（可搜，可能为 null）
  - species           物种名（对齐 Species_info.name，可过滤）
  - og_code           直系同源组 id（可搜、可过滤）

用途：用户通过基因 id（带/不带版本号）快速检索其所属 OG。

用法：
  python manage.py rebuild_orthologs_index --confirm
  python manage.py rebuild_orthologs_index --confirm --batch-size 5000
"""
from __future__ import annotations

import re
import sys
import time

from django.core.management.base import BaseCommand, CommandError

INDEX_NAME = 'Orthologs'
_VERSION_RE = re.compile(r'\.\d+$')
BATCH = 5000

# 复用 genemaster 重建命令的 Meilisearch 辅助函数（避免重复实现）
from CottonOGD.management.commands.rebuild_index import (
    as_dict, task_uid_of, list_index_uids, index_primary_key, wait_for_task,
)


def _strip_version(gid: str) -> str:
    return _VERSION_RE.sub('', gid) if gid else gid


# Meilisearch 文档 id 只允许字母数字/连字符/下划线；其余字符（. + 等）替换为 _
_ID_SAFE_RE = re.compile(r'[^A-Za-z0-9_-]')


def _safe_id(*parts: str) -> str:
    return '__'.join(_ID_SAFE_RE.sub('_', p) for p in parts)


class Command(BaseCommand):
    help = '重建 Meilisearch Orthologs 索引（基因->OG 成员检索）。必须 --confirm。'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true',
                            help='显式确认后才会真正执行（必填）。')
        parser.add_argument('--batch-size', type=int, default=BATCH,
                            help='每批写入文档数 (1-10000)。')

    def handle(self, *args, **options):
        from CottonOGD.config.meilisearch_config import MeilisearchConfig
        from CottonOGD.models import (
            Species_info, TranscriptMaster, GeneMaster, OrthofinderOgGene,
        )

        if not options['confirm']:
            self.stderr.write(self.style.ERROR(
                '这是危险操作，会删除 Orthologs 索引并全量重建。'
                ' 请确认后再次运行并加上 --confirm 参数。'))
            sys.exit(2)

        batch_size = max(1, min(options['batch_size'], 10000))
        client = MeilisearchConfig.get_client(use_master=True)

        # 1) 删除已有索引
        try:
            index_names = list_index_uids(client)
        except Exception as exc:
            raise CommandError(f'无法列出 Meilisearch 索引: {exc}') from exc
        if INDEX_NAME in index_names:
            self.stdout.write(f'[1/4] 删除已有索引 {INDEX_NAME} ...')
            try:
                task = client.delete_index(INDEX_NAME)
                wait_for_task(client, task_uid_of(task), label='delete_index')
            except Exception as exc:
                if 'index_not_found' not in str(exc):
                    raise CommandError(str(exc)) from exc
        else:
            self.stdout.write(f'[1/4] 索引 {INDEX_NAME} 不存在，跳过删除。')

        # 2) 创建索引
        self.stdout.write(f'[2/4] 创建索引 {INDEX_NAME} primaryKey=id ...')
        task = client.create_index(INDEX_NAME, {'primaryKey': 'id'})
        wait_for_task(client, task_uid_of(task), label='create_index')

        # 3) 更新 settings
        meta = MeilisearchConfig.INDEX_META[INDEX_NAME]
        self.stdout.write('[3/4] 更新 settings: searchable/filterable attributes ...')
        task = client.index(INDEX_NAME).update_settings({
            'searchableAttributes': meta['searchable_attributes'],
            'filterableAttributes': meta['filterable_attributes'],
        })
        wait_for_task(client, task_uid_of(task), label='update_settings')

        # 4) 分批导入
        total = OrthofinderOgGene.objects.count()
        self.stdout.write(
            f'[4/4] 从 MySQL orthofinder_og_gene 导入 {total:,} 条 (batch={batch_size}) ...')

        # 预载 TranscriptMaster -> GeneMaster.geneid 的解析映射（按物种分批，避免 N+1）
        species_names = list(
            Species_info.objects.filter(name__in=set(
                OrthofinderOgGene.objects.values_list('species', flat=True).distinct()))
            .values_list('name', flat=True))

        # 逐物种处理，便于批量 join 解析 genemaster_geneid
        processed = 0
        t0 = time.time()
        for sp in species_names:
            # 该物种下全部 (ortho_geneid, og_code)
            rows = list(
                OrthofinderOgGene.objects.filter(species=sp)
                .values_list('og_code', 'geneid')
            )
            if not rows:
                continue
            geneids = {r[1] for r in rows}
            bases = {_strip_version(g): g for g in geneids}
            tr_map = {
                tr['transcriptid']: tr['id_id']
                for tr in TranscriptMaster.objects.filter(genome__name=sp)
                .filter(transcriptid__in=geneids | set(bases.keys()))
                .values('transcriptid', 'id_id')
            }
            gm_ids = set(tr_map.values())
            gm_map = dict(GeneMaster.objects.filter(id__in=gm_ids)
                          .values_list('id', 'geneid'))

            batch = []
            # Meilisearch 文档 id 只允许字母数字/连字符/下划线，其余字符转义
            for og_code, gid in rows:
                pk = tr_map.get(gid) or tr_map.get(_strip_version(gid))
                gm_geneid = gm_map.get(pk) if pk else None
                batch.append({
                    'id': _safe_id(og_code, sp, gid),
                    'geneid': gid,
                    'genemaster_geneid': gm_geneid,
                    'species': sp,
                    'og_code': og_code,
                })
                if len(batch) >= batch_size:
                    processed = self._flush(batch, processed, total, client)
                    batch = []
            if batch:
                processed = self._flush(batch, processed, total, client)

        elapsed = time.time() - t0
        self.stdout.write(self.style.SUCCESS(
            f'[4/4] 导入完成 {processed:,}/{total:,} 条，用时 {elapsed:,.1f}s。'))

        # 5) 校验 settings
        primary_key = index_primary_key(client, INDEX_NAME)
        if primary_key != 'id':
            raise CommandError(f'primaryKey 异常: {primary_key}')
        settings = as_dict(client.index(INDEX_NAME).get_settings())
        if settings.get('searchableAttributes') != meta['searchable_attributes']:
            raise CommandError(
                f'searchableAttributes 异常: {settings.get("searchableAttributes")}')
        if settings.get('filterableAttributes') != meta['filterable_attributes']:
            raise CommandError(
                f'filterableAttributes 异常: {settings.get("filterableAttributes")}')
        self.stdout.write(self.style.SUCCESS('rebuild_orthologs_index 完成。'))

    # ---------- helpers ----------
    def _flush(self, batch, processed, total, client):
        try:
            task = client.index(INDEX_NAME).add_documents(batch, primary_key='id')
            wait_for_task(client, task_uid_of(task), label='add_documents')
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f'写入 Meili 批次失败: {exc}') from exc
        processed += len(batch)
        pct = 100 * processed / max(1, total)
        self.stdout.write(f'  -> {processed:,}/{total:,} ({pct:5.1f}%)')
        return processed
