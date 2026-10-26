#!/usr/bin/env python3
"""
为 JBrowse 生成 GO / KEGG 注释 track（对应 SoybeanGDB 的 R 流程，Python 实现）。

流程（每个物种）：
  1. 从 eggnog_annoation/result/ 读取 emapper 注释（GO / KEGG_Knum / KEGG_Pathway）；
  2. 从 static/jbrowse/data/<genome>/<genome>.gff.gz 解析 gene 坐标；
  3. 生成 4 个 GFF：GO 三个 level + KEGG，属性格式与 SoybeanGDB 一致：
       GO:   ID=<gene>;Gene ontology:0004615=phosphomannomutase activity;...
       KEGG: ID=<gene>;Annotation=K11821:Tryptophan metabolism,...
  4. 按 .fai 染色体顺序 + 坐标排序 -> bgzip -> tabix；
  5. 产物写入 data/gokegg_track/<genome>/，软链到 static/jbrowse/data/<genome>/；
  6. 更新该物种 config.json，追加 4 个 track。

用法：
  python scripts/build_gokegg_tracks.py                 # 全部物种
  python scripts/build_gokegg_tracks.py --genome G.anomalumB1_HAU_v1
  python scripts/build_gokegg_tracks.py --dry-run       # 只列出物种匹配情况
  python scripts/build_gokegg_tracks.py --force         # 已存在的也重新生成
"""
import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict

# django 环境不需要；路径均按仓库相对解析
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JBROWSE_DATA = os.path.join(BASE_DIR, 'static', 'jbrowse', 'data')
EGGNOG_RESULT = '/data/wbliu/data/CottonOGD/eggnog_annoation/result'
KEGG_PATHWAY_DESC = '/data/wbliu/data/CottonOGD/eggnog_annoation/rest.kegg.jp.txt'
GO_OBO = os.path.join(BASE_DIR, 'data', 'go_ontology', 'go-basic.obo')
OUT_ROOT = os.path.join(BASE_DIR, 'data', 'gokegg_track')

BGZIP = shutil.which('bgzip') or '/usr/local/bin/bgzip'
TABIX = shutil.which('tabix') or '/usr/local/bin/tabix'

NAMESPACE_LEVEL = {
    'molecular_function': 'molecular_function',
    'biological_process': 'biological_process',
    'cellular_component': 'cellular_component',
}
LEVEL_DISPLAY = {
    'molecular_function': 'GO: Molecular Function',
    'biological_process': 'GO: Biological Process',
    'cellular_component': 'GO: Cellular Component',
}

VERSION_SUFFIX = re.compile(r'\.\d+$')  # 兼容保留；实际匹配见 resolve_gene


def log(msg):
    print(msg, flush=True)


def sanitize(text):
    """GFF 属性值安全化：逗号/分号是属性分隔符，替换为下划线。"""
    return re.sub(r'[;,]', '_', text)


# ---------------------------------------------------------------------------
# 参考表：GO obo（GO -> name/namespace）、KEGG pathway 描述
# ---------------------------------------------------------------------------

def load_go_obo(path):
    """解析 go-basic.obo -> {go_id: (name, namespace)}"""
    go_map = {}
    name = namespace = None
    go_id = None
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line == '[Term]':
                go_id, name, namespace = None, None, None
            elif line.startswith('id: GO:'):
                go_id = line[4:].strip()
            elif line.startswith('name: ') and go_id:
                name = line[6:].strip()
            elif line.startswith('namespace: ') and go_id:
                namespace = line[11:].strip()
            elif line == '' and go_id and name and namespace:
                go_map[go_id] = (name, namespace)
                go_id = None
    # 文件末尾的 Term
    if go_id and name and namespace:
        go_map[go_id] = (name, namespace)
    return go_map


def load_kegg_desc(path):
    """map 编号 -> 描述"""
    desc = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 2:
                desc[parts[0].strip()] = parts[1].strip()
    return desc


# ---------------------------------------------------------------------------
# 输入：emapper 注释文件
# ---------------------------------------------------------------------------

def find_emapper_files(genome):
    """找该物种的 emapper 注释文件。多个方法时取注释基因数最多的方法。

    返回 {'GO': path, 'KEGG_Knum': path, 'KEGG_Pathway': path} 或 None
    """
    candidates = defaultdict(dict)  # method -> {kind: path}
    for fname in os.listdir(EGGNOG_RESULT):
        m = re.match(rf'^{re.escape(genome)}\.(.+)\.emapper\.annotations\.(GO|KEGG_Knum|KEGG_Pathway)\.txt$', fname)
        if m:
            method, kind = m.group(1), m.group(2)
            candidates[method][kind] = os.path.join(EGGNOG_RESULT, fname)
    if not candidates:
        return None
    # GO 基因数最多的方法优先（注释更完整）
    best = None
    best_count = -1
    for method, kinds in candidates.items():
        if not {'GO', 'KEGG_Knum', 'KEGG_Pathway'} <= set(kinds):
            continue
        with open(kinds['GO'], encoding='utf-8') as f:
            n = sum(1 for _ in f)
        if n > best_count:
            best_count = n
            best = (method, kinds)
    if best is None:
        return None
    return best[1]


def read_pairs(path):
    """两列 TSV -> list[(a, b)]"""
    pairs = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 2 and parts[0] and parts[1]:
                pairs.append((parts[0], parts[1]))
    return pairs


# ---------------------------------------------------------------------------
# 输入：GFF gene 坐标
# ---------------------------------------------------------------------------

def parse_gff_genes(gff_gz_path):
    """解析 GFF -> (genes, tx2gene)

    genes:     {gene_id: (chr, start, end, strand)}   来自 gene 行的 ID=
    tx2gene:   {transcript_id: gene_id}                来自带 ID=/Parent= 且 Parent 是基因的行（mRNA 等）
    emapper 的基因 ID 是蛋白/转录本 ID，命名因物种而异：
    Gano_09G017840.1 / GB0307.A05G000396.mRNA1，通过 tx2gene 或后缀剥离映射回基因。
    """
    genes = {}
    tx2gene = {}
    with gzip.open(gff_gz_path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 9:
                continue
            attrs = parts[8]
            if parts[2] == 'gene':
                m = re.search(r'ID=([^;]+)', attrs)
                if m:
                    genes[m.group(1).strip()] = (parts[0], int(parts[3]), int(parts[4]), parts[6])
            else:
                mid = re.search(r'ID=([^;]+)', attrs)
                mparent = re.search(r'Parent=([^;]+)', attrs)
                if mid and mparent:
                    parent = mparent.group(1).strip()
                    if parent in genes:
                        tx2gene[mid.group(1).strip()] = parent
    return genes, tx2gene


SUFFIX_RE = re.compile(r'\.(mRNA|t|p)\d+$')
NUM_SUFFIX_RE = re.compile(r'\.\d+$')


def resolve_gene(eggnog_id, genes, tx2gene):
    """emapper 基因 ID -> GFF 基因 ID，失败返回 None"""
    if eggnog_id in genes:
        return eggnog_id
    if eggnog_id in tx2gene:
        return tx2gene[eggnog_id]
    bid = SUFFIX_RE.sub('', eggnog_id)
    if bid != eggnog_id and bid in genes:
        return bid
    bid = NUM_SUFFIX_RE.sub('', eggnog_id)
    if bid != eggnog_id:
        if bid in genes:
            return bid
        if bid in tx2gene:
            return tx2gene[bid]
    return None


def parse_fai_order(fai_path):
    """染色体顺序（.fai 首列顺序即参考顺序）"""
    order = []
    with open(fai_path, encoding='utf-8') as f:
        for line in f:
            name = line.split('\t', 1)[0].strip()
            if name:
                order.append(name)
    rank = {name: i for i, name in enumerate(order)}
    return rank


# ---------------------------------------------------------------------------
# GFF 生成
# ---------------------------------------------------------------------------

def write_gff(rows, rank, out_path):
    """rows: [(chr, start, end, strand, gene_id, attrs_str)] -> 排序后写文件"""
    def sort_key(r):
        return (rank.get(r[0], len(rank)), r[1], r[2], r[4])
    rows.sort(key=sort_key)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('##gff-version 3\n')
        for chr_, start, end, strand, gene_id, attrs in rows:
            f.write(f'{chr_}\teggnog\tgene\t{start}\t{end}\t.\t{strand}\t.\t{attrs}\n')


def build_gokegg_gff(genome, files, genes, tx2gene, go_map, kegg_desc):
    """生成 4 组 GFF 行。返回 {'biological_process': rows, ...'kegg': rows}"""
    # GO: gene -> set(GO)；按 namespace 分组
    go_rows = {ns: [] for ns in NAMESPACE_LEVEL}
    gene_gos = defaultdict(set)
    for gene, go_id in read_pairs(files['GO']):
        gene_gos[gene].add(go_id)

    # KEGG: gene -> KO（单个）；gene -> set(map pathway)
    gene_ko = {}
    for gene, ko in read_pairs(files['KEGG_Knum']):
        gene_ko[gene] = ko
    gene_pathways = defaultdict(set)
    for gene, pw in read_pairs(files['KEGG_Pathway']):
        if pw.startswith('map') and pw in kegg_desc:
            gene_pathways[gene].add(pw)

    # 统一解析到 GFF gene_id；一个基因多个转录本/版本时合并注释
    go_by_gene = defaultdict(lambda: defaultdict(set))  # gene_id -> namespace -> {go_id}
    for gene, gos in gene_gos.items():
        gid = resolve_gene(gene, genes, tx2gene)
        if gid is None:
            continue
        for go_id in gos:
            info = go_map.get(go_id)
            if not info:
                continue
            _, namespace = info
            if namespace in NAMESPACE_LEVEL:
                go_by_gene[gid][namespace].add(go_id)

    ko_by_gene = defaultdict(set)      # gene_id -> {ko}
    pw_by_gene = defaultdict(set)      # gene_id -> {map pathway}
    for gene, ko in gene_ko.items():
        gid = resolve_gene(gene, genes, tx2gene)
        if gid is not None:
            ko_by_gene[gid].add(ko)
    for gene, pws in gene_pathways.items():
        gid = resolve_gene(gene, genes, tx2gene)
        if gid is not None:
            pw_by_gene[gid].update(pws)

    matched = 0
    for bid, ns_map in go_by_gene.items():
        if bid not in genes:
            continue
        matched += 1
        chr_, start, end, strand = genes[bid]
        for namespace, go_ids in ns_map.items():
            parts = [f'ID={bid}']
            for go_id in sorted(go_ids):
                name, _ = go_map[go_id]
                parts.append(f'Gene ontology:{go_id[3:]}={sanitize(name)}')
            attrs = ';'.join(parts)
            go_rows[namespace].append((chr_, start, end, strand, bid, attrs))
    kegg_rows = []
    for bid in set(ko_by_gene) | set(pw_by_gene):
        if bid not in genes:
            continue
        chr_, start, end, strand = genes[bid]
        kos = sorted(ko_by_gene.get(bid, ()))
        pws = sorted(pw_by_gene.get(bid, ()))
        anns = []
        for pw in pws:
            kos_for_pw = kos if len(kos) == 1 else []
            if kos_for_pw:
                anns.append(f'{kos_for_pw[0]}:{sanitize(kegg_desc[pw])}')
            else:
                anns.append(sanitize(kegg_desc[pw]))
        if not anns:
            continue
        attrs = f'ID={bid};Annotation={",".join(anns)}'
        kegg_rows.append((chr_, start, end, strand, bid, attrs))

    go_rows['kegg'] = kegg_rows
    stats = {'go_matched_genes': matched, 'kegg_genes': len(kegg_rows)}
    return go_rows, stats


# ---------------------------------------------------------------------------
# bgzip + tabix + 软链 + config 更新
# ---------------------------------------------------------------------------

def bgzip_and_index(gff_path):
    gz = gff_path + '.gz'
    with open(gff_path, 'rb') as fin, subprocess.Popen([BGZIP, '-c'], stdin=fin, stdout=open(gz, 'wb')) as p:
        p.wait()
        if p.returncode != 0:
            raise RuntimeError(f'bgzip failed for {gff_path}')
    subprocess.run([TABIX, '-p', 'gff', gz], check=True)
    os.remove(gff_path)
    return gz


TRACK_TEMPLATES = [
    # (key, level, track 显示名)
    ('biological_process', 'biological_process', 'GO: Biological Process'),
    ('cellular_component', 'cellular_component', 'GO: Cellular Component'),
    ('molecular_function', 'molecular_function', 'GO: Molecular Function'),
    ('kegg', 'kegg', 'KEGG Annotation'),
]


def update_config(genome, added_files):
    config_path = os.path.join(JBROWSE_DATA, genome, 'config.json')
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)
    existing = {t.get('trackId') for t in config.get('tracks', [])}
    for key, _, display in TRACK_TEMPLATES:
        track_id = f'{key}_annotation'
        if track_id in existing:
            continue
        if key not in added_files:
            continue  # 该物种无此注释数据
        fname = added_files[key]
        config.setdefault('tracks', []).append({
            'type': 'FeatureTrack',
            'trackId': track_id,
            'name': display,
            'adapter': {
                'type': 'Gff3TabixAdapter',
                'gffGzLocation': {
                    'uri': f'/jbrowse/large/{genome}/{fname}',
                    'locationType': 'UriLocation',
                },
                'index': {
                    'location': {
                        'uri': f'/jbrowse/large/{genome}/{fname}.tbi',
                        'locationType': 'UriLocation',
                    },
                    'indexType': 'TBI',
                },
            },
            'assemblyNames': [genome],
        })
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def process_genome(genome, go_map, kegg_desc, force=False, dry=False):
    out_dir = os.path.join(OUT_ROOT, genome)
    jb_dir = os.path.join(JBROWSE_DATA, genome)
    gff_gz = os.path.join(jb_dir, f'{genome}.gff.gz')
    fai = os.path.join(jb_dir, f'{genome}.genome.fa.gz.fai')

    files = find_emapper_files(genome)
    if files is None:
        return ('skip_no_data', genome)
    if not os.path.exists(gff_gz) or not os.path.exists(fai):
        return ('skip_no_gff', genome)

    final_names = {
        'biological_process': f'{genome}_biological_process.sorted.gff.gz',
        'cellular_component': f'{genome}_cellular_component.sorted.gff.gz',
        'molecular_function': f'{genome}_molecular_function.sorted.gff.gz',
        'kegg': f'{genome}KO.sorted.gff.gz',
    }
    all_exist = all(os.path.exists(os.path.join(out_dir, n)) for n in final_names.values())
    if all_exist and not force:
        # 仍确保软链与 config 就绪（幂等）
        link_and_config(genome, jb_dir, out_dir, final_names)
        return ('cached', genome)
    if dry:
        return ('dry', genome)

    os.makedirs(out_dir, exist_ok=True)
    genes, tx2gene = parse_gff_genes(gff_gz)
    rank = parse_fai_order(fai)
    rows, stats = build_gokegg_gff(genome, files, genes, tx2gene, go_map, kegg_desc)

    produced = {}
    for key, _, _ in TRACK_TEMPLATES:
        if not rows[key]:
            produced[key] = None
            continue
        tmp = os.path.join(out_dir, f'.tmp_{genome}_{key}.gff')
        write_gff(rows[key], rank, tmp)
        gz = bgzip_and_index(tmp)
        final = os.path.join(out_dir, final_names[key])
        os.replace(gz, final)
        os.replace(gz + '.tbi', final + '.tbi')
        produced[key] = final_names[key]

    # 软链 + config（只注册有内容的 track）
    usable = {k: v for k, v in final_names.items() if produced.get(k)}
    link_and_config(genome, jb_dir, out_dir, usable)
    return ('ok', genome, stats)


def link_and_config(genome, jb_dir, out_dir, final_names):
    for fname in final_names.values():
        src = os.path.join(out_dir, fname)
        for suffix in ('', '.tbi'):
            dst = os.path.join(jb_dir, fname + suffix)
            s = src + suffix
            if not os.path.exists(s):
                continue
            if os.path.lexists(dst) and not os.path.islink(dst):
                # 已有同名实体文件则不动（避免覆盖既有数据）
                continue
            if os.path.lexists(dst):
                os.remove(dst)
            os.symlink(os.path.relpath(s, jb_dir), dst)
    update_config(genome, final_names)


def main():
    ap = argparse.ArgumentParser(description='生成 GO/KEGG JBrowse track')
    ap.add_argument('--genome', help='只处理指定物种')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()

    if not os.path.isdir(EGGNOG_RESULT):
        log(f'ERROR: emapper 结果目录不存在: {EGGNOG_RESULT}')
        sys.exit(1)
    if not os.path.exists(GO_OBO):
        log(f'ERROR: GO obo 不存在: {GO_OBO}')
        sys.exit(1)

    log('加载 GO obo ...')
    go_map = load_go_obo(GO_OBO)
    log(f'  GO terms: {len(go_map)}')
    kegg_desc = load_kegg_desc(KEGG_PATHWAY_DESC)
    log(f'  KEGG pathways: {len(kegg_desc)}')

    genomes = sorted(
        d for d in os.listdir(JBROWSE_DATA)
        if os.path.exists(os.path.join(JBROWSE_DATA, d, 'config.json'))
    )
    if args.genome:
        genomes = [g for g in genomes if g == args.genome]
        if not genomes:
            log(f'ERROR: 找不到物种 {args.genome}')
            sys.exit(1)

    counts = defaultdict(int)
    for genome in genomes:
        try:
            result = process_genome(genome, go_map, kegg_desc, force=args.force, dry=args.dry_run)
            status = result[0]
            counts[status] += 1
            if status in ('ok', 'cached', 'dry'):
                extra = f' {result[2]}' if len(result) > 2 else ''
                log(f'[{status}] {genome}{extra}')
            elif status.startswith('skip'):
                counts[result[0]] += 0  # 已计数
                log(f'[{status}] {genome}')
        except Exception as e:
            counts['error'] += 1
            log(f'[error] {genome}: {e}')

    log('---- 汇总 ----')
    for k, v in sorted(counts.items()):
        log(f'  {k}: {v}')
    log(f'  total: {len(genomes)}')


if __name__ == '__main__':
    main()
