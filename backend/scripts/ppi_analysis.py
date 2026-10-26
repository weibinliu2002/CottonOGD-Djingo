#!/usr/bin/env python3
"""
PPI（蛋白质互作）分析脚本 —— STRING API 为主 + 预计算序列映射（trembl BLAST 表）为辅。

背景：本机基因 ID 在 STRING 无同名蛋白（STRING 棉花蛋白 ID 形如 "3635.Q43434" =
taxid.UniProt accession），所以用 data/genome/function/ 下已做好的
blastp_<基因组>_vs_trembl.xlsx（Query 基因ID / Match=UniProt accession /
Organism / PID）做序列级映射，再走 STRING REST API 取互作网络。

STRING 收录的棉属物种：3635 G.hirsutum、29730 G.raimondii、157791 G.herbaceum。
非这三个物种的基因组按"命中哪个棉属物种就用哪个 taxon"的就近原则映射。

输入：
  --genes  基因列表文件（每行一个；通常为 bulk_rna_seq_analysis.R 的
           deg_genes_<A>_vs_<B>.txt 输出）
  --genome 项目基因组名（用于在 data/genome/function/ 匹配该基因组的
           blastp/*_vs_trembl.xlsx 序列映射表）

用法：
  python scripts/ppi_analysis.py \
      --genes  results/bulk_20261025/deg_genes_Leaf_vs_Root.txt \
      --genome G.hirsutumAD1_Jin668_HAU_v1T2T \
      --outdir results/ppi_20261025 \
      [--taxid 3635]           # 只用单一 STRING 物种（默认自动按命中物种分组）
      [--score 400]            # STRING 互作置信度阈值（150/400/700/900）
      [--pid-min 70]           # 序列映射最低相似度 %%（默认 70）
      [--blast-table x.xlsx]   # 显式指定 BLAST 表（跳过按基因组名匹配）
      [--mapper-tsv map.tsv]   # 显式 gene<TAB>stringId 映射（最高优先级）
      [--max-genes 300]        # 超出时取 BLAST 分数最高/列表顺序前 N 个

输出（outdir 下）：
  id_mapping.tsv      gene -> STRING ID -> preferredName（含映射方式与 PID）
  ppi_edges.tsv       互作边（gene_a, gene_b, score, taxon）
  hub_genes.tsv       hub 排名（degree/betweenness/module）
  modules.tsv         网络模块划分
  network_cytoscape.json  Cytoscape 可导入的网络
  network.png         网络图
  unresolved_genes.txt 无法映射到 STRING 的基因
"""
import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNCTION_DIR = os.path.join(BASE_DIR, 'data', 'genome', 'function')
STRING_API = 'https://version-12-0.string-db.org/api'

# STRING 收录的棉属物种：Organism 名（trembl 表列）-> taxid
GOSSYPIUM_TAXA = {
    'gossypium hirsutum': '3635',
    'gossypium raimondii': '29730',
    'gossypium herbaceum': '157791',
}
GENERIC_TOKENS = {'g', 'fa', 'fasta', 'genome', 'v1', 'v2', 'v3', 'v11', 'v12',
                  'a1', 'a2', 'ad1', 'ad2', 'ad3', 'ad4', 'ad5', 'ad6', 'ad7',
                  'd1', 'd2', 'd4', 'd5', 'd6', 'd8', 'd10', 'b1', 'c1', 'e1',
                  'f1', 'g1'}


def log(msg):
    print(msg, flush=True)


def camel_split(s):
    """G.hirsutumAD1_Jin668 -> ['g','hirsutum','ad1','jin668']（小写、去版本号）"""
    s = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', s)
    s = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', s)
    return [t for t in re.split(r'[^A-Za-z0-9]+', s.lower()) if t]


def clean_accession(hit):
    """A0A2P5YC93_GOSBA -> A0A2P5YC93（UniProt FASTA 头带物种后缀）"""
    m = re.match(r'^([A-Z0-9]{6,10})_[A-Z0-9]{3,10}$', str(hit).strip())
    return m.group(1) if m else str(hit).strip()


def match_gene_rows(df, genes):
    """按点边界子串把输入基因匹配到 BLAST 表 Query。

    Query 格式因物种/流程差异很大：
      ddGosHirs.Jin668.HAU.v1.0.Ghjin_A01g000010.1
      Gher_04G001730.1_A1_HAU_ZC1_v1
      Gano_01G010010
    用 ".gene." 包裹后做子串匹配，兼容版本号与装配后缀，无需猜测 ID 规则。
    返回 {gene: 匹配到的行索引数组}
    """
    q = df['query'].astype(str).str.lower()
    wrapped = '.' + q + '.'
    out = {}
    for gene in genes:
        key = '.' + str(gene).strip().lower() + '.'
        out[gene] = wrapped.str.contains(key, regex=False).values
    return out


# ---------------------------------------------------------------------------
# STRING API（带重试的 POST TSV）
# ---------------------------------------------------------------------------

def string_post(endpoint, payload, retries=3, timeout=120):
    for attempt in range(retries):
        try:
            r = requests.post(f'{STRING_API}/tsv/{endpoint}', data=payload,
                              timeout=timeout)
            if r.status_code == 200:
                lines = [l for l in r.text.splitlines() if l.strip()]
                header = lines[0].split('\t') if lines else []
                rows = [dict(zip(header, l.split('\t'))) for l in lines[1:]]
                return rows
            log(f'  API {endpoint} HTTP {r.status_code}（第 {attempt + 1} 次）')
        except requests.RequestException as e:
            log(f'  API {endpoint} 网络错误（第 {attempt + 1} 次）: {e}')
        time.sleep(3 * (attempt + 1))
    return []


def resolve_accessions(accessions, taxid):
    """批量 UniProt accession -> STRING ID（get_string_ids）。
    返回 {accession: (stringId, preferredName)}"""
    out = {}
    accs = sorted(set(accessions))
    for i in range(0, len(accs), 100):
        chunk = accs[i:i + 100]
        rows = string_post('get_string_ids', {
            'identifiers': '\r'.join(chunk),
            'species': taxid,
            'limit': 1,
        })
        for row in rows:
            try:
                acc = chunk[int(row['queryIndex'])]
            except (KeyError, ValueError, IndexError):
                continue
            out[acc] = (row['stringId'], row.get('preferredName', ''))
    return out


def fetch_network(string_ids, taxid, min_score):
    """STRING network 端点：输入 STRING ID 集合，返回两两互作边。
    注意：API 返回的 score 是归一化到 0-1 的合成分数（required_score 才是 0-1000）。"""
    edges = []
    ids = sorted(set(string_ids))
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        rows = string_post('network', {
            'identifiers': '\r'.join(chunk),
            'species': taxid,
            'required_score': min_score,
        })
        edges.extend(rows)
    return edges


# ---------------------------------------------------------------------------
# 序列映射：预计算 trembl BLAST 表
# ---------------------------------------------------------------------------

def find_blast_table(genome):
    """按基因组名在 data/genome/function/ 匹配 *_vs_trembl.xlsx（blastp 优先）。
    token 匹配用 IDF 加权：稀有 token（如 jin668）权重高，机构名（如 hau）
    在很多表里出现、权重低，避免误匹配。"""
    if not os.path.isdir(FUNCTION_DIR):
        return None
    candidates = []
    for fname in sorted(os.listdir(FUNCTION_DIR)):
        m = re.match(r'^blast(p|x)_(.+)_vs_(trembl|swissprot)\.xlsx$', fname)
        if m:
            candidates.append((fname, m.group(1), m.group(2), m.group(3)))
    if not candidates:
        return None

    token_files = defaultdict(set)
    for fname, _, prefix, _ in candidates:
        for t in set(camel_split(prefix)) - GENERIC_TOKENS:
            token_files[t].add(fname)

    g_tokens = set(camel_split(genome)) - GENERIC_TOKENS
    if not g_tokens:
        g_tokens = set(camel_split(genome))

    best = None
    best_score = 0.0
    for fname, prog, prefix, db in candidates:
        prefix_tokens = set(camel_split(prefix)) - GENERIC_TOKENS
        shared = g_tokens & prefix_tokens
        if not shared:
            continue
        score = sum(1.0 / len(token_files[t]) for t in shared)
        score += 2 if prog == 'p' else 0        # 蛋白水平 blastp 更可信
        score += 1 if db == 'trembl' else 0     # trembl 覆盖棉属自身蛋白
        if score > best_score:
            best_score = score
            best = os.path.join(FUNCTION_DIR, fname)
    return best


def read_blast_table(path):
    """读 BLAST xlsx（真实表头不在第一行；可能多 sheet）-> DataFrame"""
    import pandas as pd
    frames = []
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        raw = xl.parse(sheet, header=None, nrows=6, dtype=str)
        header_row = None
        for i in range(len(raw)):
            if any(str(v).strip() == 'Query' for v in raw.iloc[i]):
                header_row = i
                break
        if header_row is None:
            continue
        df = xl.parse(sheet, skiprows=header_row)
        df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed')]
        frames.append(df)
    if not frames:
        raise RuntimeError(f'未在 {path} 中找到表头（Query/Match）')
    return pd.concat(frames, ignore_index=True)


def map_genes_via_blast(genes, table_path, pid_min, only_taxid=None):
    """trembl 表映射：gene -> (taxid, accession, pid)。
    每基因每个 taxon 保留最优命中（Exp 最小）；Organism 必须是 STRING 棉属物种。"""
    df = read_blast_table(table_path)
    import pandas as pd
    need = {'query', 'match', 'organism', 'exp', 'pid'}
    cols = {str(c).strip().lower(): c for c in df.columns}
    if not need <= set(cols):
        missing = need - set(cols)
        raise RuntimeError(f'BLAST 表缺少列 {missing}: {table_path}')

    df = df[[cols['query'], cols['match'], cols['organism'], cols['exp'],
             cols['pid']]].copy()
    df.columns = ['query', 'match', 'organism', 'exp', 'pid']
    df['exp'] = pd.to_numeric(df['exp'], errors='coerce')
    df['pid'] = pd.to_numeric(df['pid'], errors='coerce')
    df['match'] = df['match'].map(clean_accession)
    df = df[df['pid'] >= pid_min]

    org2taxid = {}
    for org in df['organism'].dropna().unique():
        low = str(org).strip().lower()
        for name, taxid in GOSSYPIUM_TAXA.items():
            if name in low:
                org2taxid[org] = taxid
                break
    df = df[df['organism'].map(org2taxid).notna()]
    if only_taxid:
        df = df[df['organism'].map(org2taxid) == only_taxid]

    row_sets = match_gene_rows(df, genes)
    taxids = df['organism'].map(org2taxid).values
    matches = df['match'].values
    pids = df['pid'].values
    exps = df['exp'].values

    hits = {}  # gene -> {taxid: (acc, pid, exp)}
    for gene, mask in row_sets.items():
        for i in mask.nonzero()[0]:
            taxid = taxids[i]
            exp = exps[i] if exps[i] == exps[i] else 1e5   # NaN 排最后
            cur = hits.setdefault(gene, {})
            if taxid not in cur or exp < cur[taxid][2]:
                cur[taxid] = (matches[i], float(pids[i]), float(exp))
    return hits


# ---------------------------------------------------------------------------
# 网络分析
# ---------------------------------------------------------------------------

def analyze_network(nodes, edges):
    """networkx 度/介数/模块。edges: [(ga, gb, score)]"""
    import networkx as nx
    g = nx.Graph()
    g.add_nodes_from(nodes)
    for ga, gb, score in edges:
        if g.has_edge(ga, gb):
            g[ga][gb]['score'] = max(g[ga][gb]['score'], score)
        else:
            g.add_edge(ga, gb, score=score)

    betweenness = nx.betweenness_centrality(g, weight='score') if len(g) > 1 else {}
    try:
        comms = list(nx.community.greedy_modularity_communities(g, weight='score'))
    except Exception:
        comms = []
    module_of = {}
    for i, comm in enumerate(comms, 1):
        for n in comm:
            module_of[n] = f'M{i}'

    hub_rows = sorted(
        (dict(gene=n, degree=g.degree(n),
              betweenness=round(betweenness.get(n, 0), 4),
              module=module_of.get(n, '-')) for n in g.nodes),
        key=lambda r: (-r['degree'], -r['betweenness']))
    modules = defaultdict(list)
    for n in g.nodes:
        modules[module_of.get(n, '-')].append(n)
    return g, hub_rows, dict(modules)


def plot_network(g, module_of, out_png):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if len(g) == 0:
        return
    import networkx as nx

    connected = [n for n in g.nodes if g.degree(n) > 0]
    isolated = sorted(n for n in g.nodes if g.degree(n) == 0)
    pos = {}
    if connected:
        sub = g.subgraph(connected)
        pos.update(nx.spring_layout(sub, seed=42, weight='score',
                                    k=max(0.4, 1.6 / (len(connected) ** 0.5))))
    if isolated:
        # 孤立节点（无互作）排在连通区域下方，按网格布点，避免相互挤压
        if connected:
            xs = [p[0] for p in pos.values()]
            ys = [p[1] for p in pos.values()]
            x_min, x_max = min(xs), max(xs)
            y0 = min(ys) - 0.3 * ((max(ys) - min(ys)) or 1.0)
        else:
            x_min, x_max, y0 = 0.0, 1.0, 0.0
        span = (x_max - x_min) or 1.0
        cols = max(2, int(len(isolated) ** 0.5) * 2)
        rows = (len(isolated) + cols - 1) // cols
        row_h = 0.35 * span / max(rows, 1)
        for i, n in enumerate(isolated):
            pos[n] = (x_min + span * ((i % cols) + 0.5) / cols,
                      y0 - (i // cols) * row_h)

    mod_colors = {}
    fig, ax = plt.subplots(figsize=(10, 8))
    for n in g.nodes:
        mod_colors.setdefault(module_of.get(n, '-'), None)
    cmap = matplotlib.colormaps.get_cmap('tab20')
    for i, mod in enumerate(sorted(mod_colors)):
        mod_colors[mod] = cmap(i % 20)
    degs = dict(g.degree())
    nx.draw_networkx_edges(
        g, pos, ax=ax, alpha=0.35,
        width=[0.5 + 3 * d['score'] for _, _, d in g.edges(data=True)])
    nx.draw_networkx_nodes(
        g, pos, ax=ax, node_size=[80 + 40 * degs[n] for n in g.nodes],
        node_color=[mod_colors.get(module_of.get(n, '-'), '#999999') for n in g.nodes],
        edgecolors='white', linewidths=0.5)
    if len(g) <= 80:
        # 标签放在节点上方，避免长基因名压住节点
        ys = [p[1] for p in pos.values()]
        dy = 0.03 * ((max(ys) - min(ys)) or 1.0)
        label_pos = {n: (x, y + dy) for n, (x, y) in pos.items()}
        nx.draw_networkx_labels(g, label_pos, ax=ax, font_size=6)
    ax.set_title(f'PPI network ({len(g)} nodes, {g.number_of_edges()} edges; '
                 f'{len(isolated)} isolated)')
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def cytoscape_json(g, attrs, out_path):
    """attrs: {gene: {string_id, preferred_name, degree, betweenness, module}}"""
    data = {'elements': {
        'nodes': [{'data': {'id': n, 'label': n, **attrs.get(n, {})}} for n in g.nodes],
        'edges': [{'data': {'source': a, 'target': b, 'interaction': 'string',
                            'score': d['score'], 'weight': d['score']}}
                  for a, b, d in g.edges(data=True)],
    }}
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='PPI 分析（STRING API + trembl 序列映射）')
    ap.add_argument('--genes', required=True, help='基因列表文件（每行一个）')
    ap.add_argument('--genome', help='项目基因组名（匹配 data/genome/function/ 的 BLAST 表）')
    ap.add_argument('--outdir', required=True, help='结果输出目录')
    ap.add_argument('--taxid', help='限定单一 STRING 物种（默认自动按命中棉属物种）')
    ap.add_argument('--score', type=int, default=400, help='互作置信度阈值（默认 400=medium）')
    ap.add_argument('--pid-min', type=float, default=70, help='序列映射最低相似度%%（默认 70）')
    ap.add_argument('--blast-table', help='显式指定 BLAST xlsx（跳过基因组名匹配）')
    ap.add_argument('--mapper-tsv', help='显式 gene<TAB>stringId 映射文件（最高优先）')
    ap.add_argument('--max-genes', type=int, default=300, help='参与分析的最大基因数')
    args = ap.parse_args()

    if not args.genome and not args.blast_table and not args.mapper_tsv:
        ap.error('需要 --genome / --blast-table / --mapper-tsv 之一提供基因映射')

    os.makedirs(args.outdir, exist_ok=True)

    with open(args.genes) as f:
        genes = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    if len(genes) > args.max_genes:
        log(f'基因数 {len(genes)} 超过上限，取前 {args.max_genes} 个')
        genes = genes[:args.max_genes]
    log(f'输入基因: {len(genes)} 个')

    # ---- 基因 -> STRING ID 映射 -----------------------------------------
    mapping = {}     # gene -> {taxid, string_id, name, method, pid}
    if args.mapper_tsv:
        with open(args.mapper_tsv) as f:
            for line in f:
                parts = line.rstrip('\n').split('\t')
                if len(parts) >= 2 and parts[0] and parts[1]:
                    mapping[parts[0]] = dict(taxid=parts[1].split('.')[0],
                                             string_id=parts[1], name='',
                                             method='mapper_tsv', pid='')
        log(f'mapper_tsv 提供 {len(mapping)} 条映射')
    else:
        table = args.blast_table or find_blast_table(args.genome)
        if not table:
            log(f'ERROR: 在 {FUNCTION_DIR} 找不到 {args.genome} 的 BLAST 表，'
                f'用 --blast-table 显式指定')
            sys.exit(1)
        log(f'序列映射表: {os.path.basename(table)}')

        hits = map_genes_via_blast(genes, table, args.pid_min,
                                   only_taxid=args.taxid)
        # 汇总：每基因取最优 taxon（优先命中物种特异：与基因组自身最近的
        # A/D/AD 命名对应关系交给 BLAST 本身——按 PID/Exp 最好的那个）
        cand = defaultdict(list)  # taxid -> [gene]
        acc_of = {}               # (taxid, gene) -> (acc, pid)
        for gene in genes:
            for taxid, (acc, pid, _exp) in hits.get(gene, {}).items():
                cand[taxid].append(gene)
                acc_of[(taxid, gene)] = (acc, pid)

        for taxid, tax_genes in sorted(cand.items()):
            accs = [acc_of[(taxid, g_)][0] for g_ in tax_genes]
            log(f'taxon {taxid}: {len(accs)} 个候选 accession，验证 STRING ID ...')
            resolved = resolve_accessions(accs, taxid)
            log(f'  STRING 解析成功 {len(resolved)}/{len(set(accs))}')
            for g_ in tax_genes:
                acc, pid = acc_of[(taxid, g_)]
                if acc in resolved and g_ not in mapping:
                    sid, name = resolved[acc]
                    mapping[g_] = dict(taxid=taxid, string_id=sid, name=name,
                                       method='trembl_blast', pid=round(pid, 1))

    if not mapping:
        log('没有任何基因映射成功（可降低 --pid-min 或检查基因 ID 命名）')
    else:
        log(f'映射成功 {len(mapping)}/{len(genes)} 个基因')

    with open(os.path.join(args.outdir, 'unresolved_genes.txt'), 'w') as f:
        f.write('\n'.join(g for g in genes if g not in mapping) + '\n')

    # ---- 拉取互作网络 ------------------------------------------------------
    all_edges = []   # (gene_a, gene_b, score)
    by_taxid = defaultdict(list)
    for gene, info in mapping.items():
        by_taxid[info['taxid']].append(gene)
    for taxid, tax_genes in sorted(by_taxid.items()):
        sids = [mapping[g_]['string_id'] for g_ in tax_genes]
        log(f'查询互作网络: taxon {taxid}, {len(sids)} 个蛋白 ...')
        rows = fetch_network(sids, taxid, args.score)
        if not rows and args.score > 150:
            # STRING 棉属网络较稀疏，零边时自动回退到低置信度阈值
            log(f'  {taxid}: 阈值 {args.score} 下无互作，回退到 150')
            rows = fetch_network(sids, taxid, 150)
        sid2gene = {mapping[g_]['string_id']: g_ for g_ in tax_genes}
        for row in rows:
            try:
                ga = sid2gene[row['stringId_A']]
                gb = sid2gene[row['stringId_B']]
                all_edges.append((ga, gb, float(row['score'])))
            except (KeyError, ValueError):
                continue
        log(f'  {taxid}: {len(rows)} 条互作')

    # ---- 分析与输出 --------------------------------------------------------
    nodes = list(mapping)
    g, hub_rows, modules = analyze_network(nodes, all_edges)
    log(f'网络: {len(g)} 节点, {g.number_of_edges()} 边')

    import pandas as pd
    pd.DataFrame([dict(gene=k, **v) for k, v in mapping.items()]) \
        .to_csv(os.path.join(args.outdir, 'id_mapping.tsv'), sep='\t', index=False)
    edge_df = pd.DataFrame([dict(gene_a=a, gene_b=b, score=s)
                            for a, b, s in all_edges],
                           columns=['gene_a', 'gene_b', 'score'])
    edge_df.sort_values('score', ascending=False) \
        .to_csv(os.path.join(args.outdir, 'ppi_edges.tsv'), sep='\t', index=False)
    pd.DataFrame(hub_rows) \
        .to_csv(os.path.join(args.outdir, 'hub_genes.tsv'), sep='\t', index=False)
    with open(os.path.join(args.outdir, 'modules.tsv'), 'w') as f:
        for mod, mgenes in sorted(modules.items()):
            f.write(f'{mod}\t{len(mgenes)}\t{",".join(sorted(mgenes))}\n')

    module_of = {r['gene']: r['module'] for r in hub_rows}
    attrs = {gene: dict(string_id=info['string_id'],
                        preferred_name=info['name'],
                        degree=g.degree(gene),
                        module=module_of.get(gene, '-'),
                        mapping_pid=info['pid'])
             for gene, info in mapping.items()}
    cytoscape_json(g, attrs, os.path.join(args.outdir, 'network_cytoscape.json'))
    plot_network(g, module_of, os.path.join(args.outdir, 'network.png'))

    top = ', '.join(f"{r['gene']}({r['degree']})" for r in hub_rows[:5]) or '-'
    log(f'完成。Top hub: {top}')


if __name__ == '__main__':
    main()
