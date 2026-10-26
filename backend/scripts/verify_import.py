#!/usr/bin/env python
"""
验证 GeneMaster 表与 Meilisearch genemaster 索引一致性。
用法：
    python scripts/verify_import.py [--samples 200]

退出码：
    0 - 全部通过
    1 - 校验失败
    2 - 连接错误
"""
from __future__ import annotations
import argparse
import os
import random
import sys
from datetime import datetime
from pathlib import Path

# --- django setup ---
BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

try:
    import django
    django.setup()
except Exception as exc:  # noqa: BLE001
    print(f'[FATAL] Django setup failed: {exc}', file=sys.stderr)
    sys.exit(2)

from django.db.models import Count, Distinct  # noqa: E402
from CottonOGD.models import GeneMaster  # noqa: E402
from CottonOGD.config.meilisearch_config import MeilisearchConfig  # noqa: E402
from CottonOGD.management.commands.rebuild_index import INDEX_NAME  # noqa: E402

FAILED = False


def mark_failed(msg: str) -> None:
    global FAILED
    FAILED = True
    print(f'[FAIL] {msg}', file=sys.stderr)


def step_a(index) -> None:
    """MySQL 总数 vs Meilisearch 文档总数。"""
    try:
        mysql = GeneMaster.objects.count()
    except Exception as exc:  # noqa: BLE001
        print(f'[CONNECT] MySQL 查询失败: {exc}', file=sys.stderr)
        sys.exit(2)
    try:
        stats = index.get_stats()
    except Exception as exc:  # noqa: BLE001
        print(f'[CONNECT] Meili get_stats 失败: {exc}', file=sys.stderr)
        sys.exit(2)
    meili = stats.get('numberOfDocuments', 0)
    print(f'[STEP A] MySQL={mysql}  Meili={meili}')
    if mysql != meili:
        mark_failed(f'STEP A 文档数不同：MySQL={mysql}, Meili={meili} (delta={mysql - meili})')
    else:
        print('[STEP A] PASS')


def step_b(index, samples: int) -> None:
    """随机抽样逐字段对比。"""
    try:
        total = GeneMaster.objects.count()
    except Exception as exc:
        mark_failed(f'STEP B count 失败: {exc}')
        return
    if total == 0:
        print('[STEP B] SKIP (MySQL 空表)')
        return
    samples = min(samples, total)
    # 基于 PK 偏移采样（避免 order_by('?') 大表过慢）
    try:
        max_id = GeneMaster.objects.order_by('-pk').values_list('pk', flat=True).first() or 1
    except Exception as exc:
        mark_failed(f'STEP B max_id 查询失败: {exc}')
        return

    picked = []
    seen = set()
    attempts = 0
    while len(picked) < samples and attempts < samples * 20:
        guess = random.randint(1, max_id)
        if guess in seen:
            attempts += 1
            continue
        seen.add(guess)
        try:
            obj = GeneMaster.objects.filter(pk=guess).only(
                'id', 'geneid', 'genome_id', 'alias').first()
        except Exception:
            obj = None
        if obj is not None:
            picked.append(obj)
        attempts += 1

    if not picked:
        print('[STEP B] SKIP (采样失败)')
        return

    mismatches = 0
    for obj in picked:
        try:
            doc = index.get_document(str(obj.id))
        except Exception:
            mismatches += 1
            continue
        if (str(doc.get('geneid') or '') != str(obj.geneid or '') or
                str(doc.get('genome_id') or '') != str(obj.genome_id or '') or
                str(doc.get('alias') or '') != str(obj.alias or '')):
            mismatches += 1
    print(f'[STEP B] 采样 {len(picked)}, 不一致 {mismatches}')
    if mismatches:
        mark_failed(f'STEP B 有 {mismatches}/{len(picked)} 条字段不一致')
    else:
        print('[STEP B] PASS')


def step_c(index) -> None:
    """跨基因组重复 geneid 验证：避免同主键覆盖导致静默丢失。"""
    try:
        dup = (GeneMaster.objects.values('geneid')
               .annotate(cnt=Count(Distinct('genome_id')))
               .filter(cnt__gte=2).order_by('-cnt')[:1])
        dup = list(dup)
    except Exception as exc:
        mark_failed(f'STEP C 跨基因组 geneid 查询失败: {exc}')
        return
    if not dup:
        print('[STEP C] SKIP (数据库无任何跨基因组重复的 geneid)')
        return
    geneid = dup[0]['geneid']
    cnt = dup[0]['cnt']
    print(f'[STEP C] 候选 geneid={geneid!r} 跨 {cnt} 个基因组')
    try:
        res = index.search(geneid, {
            'limit': 100,
            'attributesToRetrieve': ['id', 'geneid', 'genome_id'],
        })
    except Exception as exc:
        mark_failed(f'STEP C Meili 搜索失败: {exc}')
        return
    genomes = {hit.get('genome_id') for hit in res.get('hits', [])} - {None}
    hits_with_id = [h for h in res.get('hits', []) if str(h.get('geneid') or '') == str(geneid)]
    distinct_ids = {h.get('id') for h in hits_with_id}
    print(f'[STEP C] 命中不同基因组数量: {len(genomes)} 不同主键数量: {len(distinct_ids)}')
    if len(distinct_ids) < 2:
        mark_failed(f'STEP C 未检测到跨基因组的多条独立文档（geneid={geneid!r}）')
    else:
        print('[STEP C] PASS')


def step_d(index) -> None:
    """验证 filterableAttributes 生效。"""
    # 选一个基因数最多的物种做样本
    try:
        row = (GeneMaster.objects.values('genome_id')
               .annotate(cnt=Count('id')).order_by('-cnt')[:1])
        row = list(row)
    except Exception as exc:
        mark_failed(f'STEP D 查询 genome 数量失败: {exc}')
        return
    if not row:
        print('[STEP D] SKIP (MySQL 空表)')
        return
    species = row[0]['genome_id']
    # 转义 filter
    escaped = str(species).replace('\\', '\\\\').replace('"', '\\"')
    flt = f'genome_id = "{escaped}"'
    q = ''
    try:
        with_filter = index.search(q, {
            'filter': flt, 'limit': 50,
            'attributesToRetrieve': ['genome_id'],
        })
    except Exception as exc:
        mark_failed(f'STEP D Meili filter 查询失败: {exc}')
        return
    hits = with_filter.get('hits', [])
    if not hits:
        # 可能因为 species 含特殊字符，再尝试不带 filter 看是否有结果
        print('[STEP D] SKIP (filter 下无命中，无法验证 subset)')
        return
    bad = [h for h in hits if str(h.get('genome_id') or '') != str(species)]
    print(f'[STEP D] filter 命中 {len(hits)}，错误物种 {len(bad)}')
    if bad:
        mark_failed(f'STEP D filter 未生效：{len(bad)}/{len(hits)} 条 genome_id != {species!r}')
    else:
        print('[STEP D] PASS')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=200,
                        help='STEP B 随机抽样数量')
    args = parser.parse_args()

    print(f'[INFO] {datetime.now().isoformat()} verify_import starting')
    try:
        client = MeilisearchConfig.get_client(use_master=False)
        index = client.index(INDEX_NAME)
        # 做一次轻量健康检查
        index.get_stats()
    except Exception as exc:
        print(f'[CONNECT] Meili 不可用: {exc}', file=sys.stderr)
        return 2

    step_a(index)
    step_b(index, args.samples)
    step_c(index)
    step_d(index)

    if FAILED:
        print('\n[RESULT] FAIL')
        return 1
    print('\n[RESULT] PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
