"""
构建 OrthoFinder 直系同源索引（数据源：<ORTHOFINDER_RESULTS_DIR>/Orthogroups/Orthogroups.tsv）。

把约 290 万条「基因↔直系同源组(OG)」成员关系导入 MySQL：
  - orthofinder_orthogroup  (OG 元数据)
  - orthofinder_og_gene     (核心成员表，含 species FK -> Species_info.name)

物种列已 100% 对齐 Species_info.name（前置校验，缺失即报错）。
基因 id 即 TranscriptMaster.transcriptid，查询时再按需 join 到 GeneMaster。

用法：
  python manage.py build_orthofinder_index            # 清空后全量重建
  python manage.py build_orthofinder_index --results-dir /path/to/Results_xxx
  python manage.py build_orthofinder_index --append   # 不清空，幂等 upsert（靠唯一约束跳过重复）

性能：分块 bulk_create，2.9M 行约 1~3 分钟。
"""
from __future__ import annotations

import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

BATCH = 50_000  # 每批写入行数


class Command(BaseCommand):
    help = '构建 OrthoFinder 直系同源索引（OG 元数据 + 基因成员表）。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--results-dir', default=None,
            help='OrthoFinder 结果目录（含 Orthogroups/ 子目录）。'
                 '默认取 settings.ORTHOFINDER_RESULTS_DIR。')
        parser.add_argument(
            '--append', action='store_true',
            help='不清空旧数据，依赖唯一约束跳过重复行（用于增量）。')
        parser.add_argument(
            '--batch-size', type=int, default=BATCH,
            help='每批 bulk_create 行数（默认 50000）。')

    def handle(self, *args, **options):
        from CottonOGD.models import (
            Species_info, OrthofinderOrthogroup, OrthofinderOgGene,
        )

        results_dir = options['results_dir'] or getattr(
            settings, 'ORTHOFINDER_RESULTS_DIR', None)
        if not results_dir:
            raise CommandError('未配置 ORTHOFINDER_RESULTS_DIR，请用 --results-dir 指定。')
        results_dir = os.path.abspath(results_dir)

        tsv_path = os.path.join(results_dir, 'Orthogroups', 'Orthogroups.tsv')
        if not os.path.isfile(tsv_path):
            alt = os.path.join(results_dir, 'Orthogroups', 'Orthogroups.txt')
            if os.path.isfile(alt):
                tsv_path = alt
            else:
                raise CommandError(f'找不到 Orthogroups.tsv：{tsv_path}')

        batch_size = max(1, options['batch_size'])
        self.stdout.write(f'数据源：{tsv_path}')

        # ---- 1) 读表头，校验物种列 ----
        with open(tsv_path, 'r', encoding='utf-8') as fh:
            header = fh.readline().rstrip('\n').split('\t')
        if not header or header[0] != 'Orthogroup':
            raise CommandError('表头首列应为 Orthogroup。')
        species_cols = header[1:]
        self.stdout.write(f'检测到 {len(species_cols)} 个物种列。')

        existing = set(Species_info.objects.values_list('name', flat=True))
        missing = [s for s in species_cols if s not in existing]
        if missing:
            raise CommandError(
                f'{len(missing)} 个物种列不在 Species_info 表中（前 10 个）：'
                f'{missing[:10]}')
        n_species = len(species_cols)

        # ---- 2) 清空旧数据（除非 --append）----
        if not options['append']:
            self.stdout.write('清空旧索引 orthofinder_og_gene / orthofinder_orthogroup ...')
            OrthofinderOgGene.objects.all().delete()
            OrthofinderOrthogroup.objects.all().delete()

        # ---- 3) 逐行解析 + 分块 bulk_create ----
        og_gene_rows: list[OrthofinderOgGene] = []
        og_stats: dict[str, list] = {}  # og_code -> [gene_count, species_count]
        n_genes = 0
        n_ogs = 0
        t0 = time.time()

        with open(tsv_path, 'r', encoding='utf-8') as fh:
            fh.readline()  # 跳过表头
            for line in fh:
                line = line.rstrip('\n')
                if not line:
                    continue
                parts = line.split('\t')
                og_code = parts[0].strip()
                if not og_code:
                    continue
                n_ogs += 1
                gcount = 0
                scount = 0
                for idx, col in enumerate(parts[1:], start=1):
                    if not col.strip():
                        continue
                    species = species_cols[idx - 1]
                    scount += 1
                    for gid in col.split(','):
                        gid = gid.strip()
                        if not gid:
                            continue
                        gcount += 1
                        og_gene_rows.append(OrthofinderOgGene(
                            og_code=og_code, species_id=species, geneid=gid))
                        n_genes += 1
                        if len(og_gene_rows) >= batch_size:
                            self._flush(OrthofinderOgGene, og_gene_rows)
                            og_gene_rows = []
                stats = og_stats.get(og_code)
                if stats is None:
                    og_stats[og_code] = [gcount, scount]
                else:
                    stats[0] += gcount
                    stats[1] += scount

                if n_ogs % 5000 == 0:
                    self._progress(n_ogs, n_genes, t0)

        if og_gene_rows:
            self._flush(OrthofinderOgGene, og_gene_rows)
            og_gene_rows = []

        # ---- 4) 写入 OG 元数据 ----
        self.stdout.write(f'写入 OG 元数据（{len(og_stats):,} 个）...')
        og_objs = [
            OrthofinderOrthogroup(
                og_code=og, gene_count=s[0], species_count=s[1],
                is_single_copy=(s[1] == n_species),
            )
            for og, s in og_stats.items()
        ]
        for i in range(0, len(og_objs), batch_size):
            OrthofinderOrthogroup.objects.bulk_create(
                og_objs[i:i + batch_size], ignore_conflicts=True)

        elapsed = time.time() - t0
        self.stdout.write(self.style.SUCCESS(
            f'完成：OG={n_ogs:,}  基因关系={n_genes:,}  '
            f'用时 {elapsed:,.0f}s'))

    # ---------- helpers ----------
    @staticmethod
    def _flush(model, rows):
        model.objects.bulk_create(rows, ignore_conflicts=True)

    def _progress(self, n_ogs, n_genes, t0):
        elapsed = time.time() - t0
        rate = n_genes / elapsed if elapsed else 0
        self.stdout.write(
            f'    进度 OG={n_ogs:,}  基因关系={n_genes:,}  '
            f'用时 {elapsed:,.0f}s 速率 {rate:,.0f} 行/s')
