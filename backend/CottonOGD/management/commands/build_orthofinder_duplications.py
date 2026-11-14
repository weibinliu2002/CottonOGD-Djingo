"""
构建 OrthoFinder 基因复制事件索引（数据源：
<ORTHOFINDER_RESULTS_DIR>/Gene_Duplication_Events/Duplications.tsv）。

把约 24 万条复制事件导入 MySQL 表 orthofinder_duplication，按 og_code 建索引，
供 tandem / wgd 端点 O(log n) 查询（避免每请求全量扫描 427MB 的 TSV）。

行格式（TSV，表头跳过）：
  Orthogroup  Species Tree Node  Gene Tree Node  Support  Type  Genes 1  Genes 2
  OG0000000   G.anomalumB1_HAU_v1  n1022  1.0  Terminal  <Sp_Gene,...>  <Sp_Gene,...>

注：列 2 名为 "Species Tree Node" 但值是物种名（如 G.anomalumB1_HAU_v1），
列 3 才是基因树节点（如 n1022）。Genes 1/2 形如 <物种名_.>_<基因id>（逗号聚合），
经 _clean_dup_gene 去除物种前缀还原为基因 id。

用法：
  python manage.py build_orthofinder_duplications            # 清空后全量重建
  python manage.py build_orthofinder_duplications --results-dir /path/to/Results_xxx
  python manage.py build_orthofinder_duplications --append   # 不清空，靠唯一约束跳过重复
"""
from __future__ import annotations

import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

BATCH = 20_000


class Command(BaseCommand):
    help = '构建 OrthoFinder 基因复制事件索引（orthofinder_duplication）。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--results-dir', default=None,
            help='OrthoFinder 结果目录。默认 settings.ORTHOFINDER_RESULTS_DIR。')
        parser.add_argument(
            '--append', action='store_true',
            help='不清空旧数据，依赖唯一约束跳过重复行。')
        parser.add_argument(
            '--batch-size', type=int, default=BATCH,
            help='每批 bulk_create 行数（默认 20000）。')

    def handle(self, *args, **options):
        from CottonOGD.models import OrthofinderDuplication
        from CottonOGD.views.orthofinder import _clean_dup_gene

        results_dir = options['results_dir'] or getattr(
            settings, 'ORTHOFINDER_RESULTS_DIR', None)
        if not results_dir:
            raise CommandError('未配置 ORTHOFINDER_RESULTS_DIR，请用 --results-dir 指定。')
        results_dir = os.path.abspath(results_dir)

        tsv_path = os.path.join(
            results_dir, 'Gene_Duplication_Events', 'Duplications.tsv')
        if not os.path.isfile(tsv_path):
            raise CommandError(f'找不到 Duplications.tsv：{tsv_path}')

        batch_size = max(1, options['batch_size'])
        if not options['append']:
            self.stdout.write('清空旧索引 orthofinder_duplication ...')
            OrthofinderDuplication.objects.all().delete()

        rows: list[OrthofinderDuplication] = []
        n_rows = 0
        t0 = time.time()

        def _split_genes(cell):
            return [g.strip() for g in cell.split(',') if g.strip()]

        with open(tsv_path, 'r', encoding='utf-8') as fh:
            fh.readline()  # 表头
            for line in fh:
                line = line.rstrip('\n')
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) < 7:
                    continue
                og_code = parts[0].strip()
                species_node = parts[1].strip()
                gene_node = parts[2].strip()
                support_raw = parts[3].strip()
                dtype = parts[4].strip()
                g1 = _split_genes(parts[5])
                g2 = _split_genes(parts[6])
                try:
                    support = float(support_raw) if support_raw else None
                except ValueError:
                    support = None
                rows.append(OrthofinderDuplication(
                    og_code=og_code,
                    species_node=species_node,
                    gene_tree_node=gene_node or None,
                    support=support,
                    dup_type=dtype,
                    genes1=','.join(_clean_dup_gene(g, species_node) for g in g1),
                    genes2=','.join(_clean_dup_gene(g, species_node) for g in g2),
                ))
                n_rows += 1
                if len(rows) >= batch_size:
                    self._flush(OrthofinderDuplication, rows)
                    rows = []

        if rows:
            self._flush(OrthofinderDuplication, rows)

        elapsed = time.time() - t0
        self.stdout.write(self.style.SUCCESS(
            f'完成：复制事件={n_rows:,}  用时 {elapsed:,.0f}s'))

    @staticmethod
    def _flush(model, rows):
        model.objects.bulk_create(rows, ignore_conflicts=True)

    def _progress(self, n, t0):
        elapsed = time.time() - t0
        rate = n / elapsed if elapsed else 0
        self.stdout.write(f'    进度 {n:,} 用时 {elapsed:,.0f}s 速率 {rate:,.0f} 行/s')
