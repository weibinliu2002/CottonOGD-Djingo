"""
STRING PPI 服务层 —— 从 scripts/ppi_analysis.py 移植并重构。

调用链：gene_ids → trembl BLAST 表 → UniProt accession → STRING get_string_ids
       → STRING network → Cytoscape elements。
"""
from __future__ import annotations

import logging
import os
import re
import time
from collections import defaultdict

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 配置（从 settings 读取，带默认值）
# ---------------------------------------------------------------------------

def _cfg(name, default):
    return getattr(settings, name, default)

STRING_API_URL = _cfg('STRING_API_URL', 'https://version-12-0.string-db.org/api')
STRING_CALLER_ID = _cfg('STRING_CALLER_ID', 'cottonogd')
STRING_REQUEST_TIMEOUT = _cfg('STRING_REQUEST_TIMEOUT', 30)
STRING_MAX_RETRIES = _cfg('STRING_MAX_RETRIES', 3)
STRING_SCORE_THRESHOLD = _cfg('STRING_SCORE_THRESHOLD', 400)

# Species_info.name → NCBI taxon ID（仅 STRING 收录的 3 个棉属物种）
GENOME_TO_TAXON: dict[str, str] = _cfg('STRING_GENOME_TAXON_MAP', {})

# trembl BLAST Organism 列值 → taxon
GOSSYPIUM_TAXA = {
    'gossypium hirsutum': '3635',
    'gossypium raimondii': '29730',
    'gossypium herbaceum': '157791',
}

FUNCTION_DIR = os.path.join(str(settings.BASE_DIR), 'data', 'genome', 'function')

# BLAST 表文件名中常见的无区分力 token（与原脚本一致）
GENERIC_TOKENS = {
    'g', 'fa', 'fasta', 'genome', 'v1', 'v2', 'v3', 'v11', 'v12',
    'a1', 'a2', 'ad1', 'ad2', 'ad3', 'ad4', 'ad5', 'ad6', 'ad7',
    'd1', 'd2', 'd4', 'd5', 'd6', 'd8', 'd10', 'b1', 'c1', 'e1',
    'f1', 'g1',
}

# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------


def resolve_taxon(genome_id: str) -> str | None:
    """genome_id (Species_info.name) → STRING NCBI taxon ID。

    查找顺序：
    1. settings.STRING_GENOME_TAXON_MAP 精确匹配
    2. Species_info.Cotton_Species 模糊匹配 GOSSYPIUM_TAXA
    3. trembl BLAST 表名 token 匹配 → GOSSYPIUM_TAXA
    """
    if not genome_id:
        return None

    # 1) 精确匹配
    taxon = GENOME_TO_TAXON.get(genome_id)
    if taxon:
        return taxon

    # 2) 通过 Species_info.Cotton_Species 模糊匹配
    try:
        from CottonOGD.models import Species_info
        sp = Species_info.objects.filter(name=genome_id).values_list('Cotton_Species', flat=True).first()
        if sp:
            low = sp.strip().lower()
            for name, tid in GOSSYPIUM_TAXA.items():
                if name in low:
                    return tid
    except Exception:
        pass

    # 3) BLAST 表名 token 匹配
    table = find_blast_table(genome_id)
    if table:
        # 从文件名推断 taxon：尝试匹配表内 Organism 列
        # 简化：用文件名 token 匹配 GOSSYPIUM_TAXA key
        fname = os.path.basename(table)
        m = re.match(r'^blast(?:p|x)_(.+)_vs_(?:trembl|swissprot)\.xlsx$', fname)
        if m:
            tokens = [t for t in camel_split(m.group(1)) if t not in GENERIC_TOKENS]
            for name, tid in GOSSYPIUM_TAXA.items():
                name_tokens = set(camel_split(name))
                if name_tokens & set(tokens):
                    return tid
    return None


def map_genes_to_string(
    gene_ids: list[str],
    genome_id: str,
    pid_min: float = 70.0,
) -> tuple[dict[str, dict], list[str]]:
    """基因 ID → STRING ID 映射。

    返回 (mapping, unmapped)：
      mapping: {gene_id: {taxid, string_id, preferred_name, pid}}
      unmapped: 未能映射的 gene_id 列表
    BLAST 表找不到时抛出 RuntimeError。
    """
    table = find_blast_table(genome_id)
    if not table:
        raise RuntimeError(
            f'基因组 {genome_id} 在 {FUNCTION_DIR} 找不到 trembl BLAST 映射表')

    logger.info('PPI: 序列映射表 %s', os.path.basename(table))
    hits = map_genes_via_blast(gene_ids, table, pid_min)

    # 每基因取最优 taxon，按 taxid 分批 resolve
    mapping: dict[str, dict] = {}
    by_taxid: dict[str, list[str]] = defaultdict(list)
    acc_of: dict[tuple[str, str], tuple[str, float]] = {}

    for gene in gene_ids:
        for taxid, (acc, pid, _exp) in hits.get(gene, {}).items():
            by_taxid[taxid].append(gene)
            acc_of[(taxid, gene)] = (acc, pid)

    for taxid, tax_genes in sorted(by_taxid.items()):
        accs = [acc_of[(taxid, g)][0] for g in tax_genes]
        logger.info('PPI: taxon %s, %d 个候选 accession，验证 STRING ID ...',
                    taxid, len(accs))
        resolved = resolve_accessions(accs, taxid)
        logger.info('PPI: STRING 解析成功 %d/%d', len(resolved), len(set(accs)))
        for g in tax_genes:
            acc, pid = acc_of[(taxid, g)]
            if acc in resolved and g not in mapping:
                sid, name = resolved[acc]
                mapping[g] = dict(taxid=taxid, string_id=sid,
                                  preferred_name=name, pid=round(pid, 1))

    unmapped = [g for g in gene_ids if g not in mapping]
    logger.info('PPI: 映射成功 %d/%d', len(mapping), len(gene_ids))
    return mapping, unmapped


def fetch_interactions(
    string_ids: list[str],
    taxid: str,
    min_score: int = 400,
) -> list[dict]:
    """STRING network 端点 → 互作边列表。

    自动低阈值回退：当 min_score > 150 且零边时回退到 150
    （棉花 STRING 网络稀疏）。
    STRING API 失败时抛出 requests.RequestException。
    """
    edges = _fetch_network(string_ids, taxid, min_score)
    if not edges and min_score > 150:
        logger.info('PPI: 阈值 %d 下无互作，回退到 150', min_score)
        edges = _fetch_network(string_ids, taxid, 150)
    return edges


def build_cytoscape_network(
    gene_ids: list[str],
    mapping: dict[str, dict],
    edges: list[dict],
) -> dict:
    """构建 Cytoscape JSON elements。

    - nodes: 映射成功的基因
    - edges: 去重，score 为 0-1000 整数
    - edge source/target 必须引用返回节点
    """
    # 仅有映射的基因作为节点
    node_ids = set(mapping.keys())
    nodes = []
    for gid in gene_ids:
        if gid not in mapping:
            continue
        info = mapping[gid]
        label = info.get('preferred_name') or gid
        if not label:
            label = gid
        nodes.append({'data': {'id': gid, 'label': label}})

    # 构建边，仅保留 source/target 都在节点中的边
    sid_to_gene = {info['string_id']: g for g, info in mapping.items()}
    seen_edges = set()
    cyto_edges = []
    for row in edges:
        ga = sid_to_gene.get(row.get('stringId_A'))
        gb = sid_to_gene.get(row.get('stringId_B'))
        if not ga or not gb:
            continue
        # 保证 edge id 唯一且确定
        lo, hi = (ga, gb) if ga < gb else (gb, ga)
        edge_key = f'{lo}_{hi}'
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        try:
            score = int(float(row.get('score', 0)) * 1000)
        except (ValueError, TypeError):
            score = 0
        score = max(0, min(score, 1000))
        cyto_edges.append({
            'data': {
                'id': edge_key,
                'source': lo,
                'target': hi,
                'score': score,
            }
        })

    return {'nodes': nodes, 'edges': cyto_edges}


# ---------------------------------------------------------------------------
# STRING API（带重试的 POST TSV）
# ---------------------------------------------------------------------------


def string_post(endpoint: str, payload: dict,
                retries: int | None = None,
                timeout: int | None = None) -> list[dict]:
    """STRING REST API POST TSV 格式请求。"""
    retries = retries if retries is not None else STRING_MAX_RETRIES
    timeout = timeout if timeout is not None else STRING_REQUEST_TIMEOUT
    payload = dict(payload)
    payload.setdefault('caller_identity', STRING_CALLER_ID)
    url = f'{STRING_API_URL}/tsv/{endpoint}'

    for attempt in range(retries):
        try:
            r = requests.post(url, data=payload, timeout=timeout)
            if r.status_code == 200:
                lines = [l for l in r.text.splitlines() if l.strip()]
                header = lines[0].split('\t') if lines else []
                return [dict(zip(header, l.split('\t'))) for l in lines[1:]]
            logger.warning('PPI: API %s HTTP %d（第 %d 次）',
                           endpoint, r.status_code, attempt + 1)
        except requests.Timeout as e:
            # 最后一次重试仍超时时向上抛出，让视图层返回 504
            if attempt == retries - 1:
                raise
            logger.warning('PPI: API %s 超时（第 %d 次）: %s', endpoint, attempt + 1, e)
        except requests.ConnectionError as e:
            if attempt == retries - 1:
                raise
            logger.warning('PPI: API %s 连接失败（第 %d 次）: %s', endpoint, attempt + 1, e)
        except requests.RequestException as e:
            if attempt == retries - 1:
                raise
            logger.warning('PPI: API %s 网络错误（第 %d 次）: %s', endpoint, attempt + 1, e)
        time.sleep(2 * (attempt + 1))
    return []


def resolve_accessions(accessions: list[str], taxid: str) -> dict[str, tuple[str, str]]:
    """批量 UniProt accession → STRING ID（get_string_ids）。
    返回 {accession: (stringId, preferredName)}"""
    out: dict[str, tuple[str, str]] = {}
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


def _fetch_network(string_ids: list[str], taxid: str, min_score: int) -> list[dict]:
    """STRING network 端点。"""
    edges: list[dict] = []
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


def camel_split(s: str) -> list[str]:
    """G.hirsutumAD1_Jin668 → ['g','hirsutum','ad1','jin668']"""
    s = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', s)
    s = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', s)
    return [t for t in re.split(r'[^A-Za-z0-9]+', s.lower()) if t]


def clean_accession(hit: str) -> str:
    """A0A2P5YC93_GOSBA → A0A2P5YC93"""
    m = re.match(r'^([A-Z0-9]{6,10})_[A-Z0-9]{3,10}$', str(hit).strip())
    return m.group(1) if m else str(hit).strip()


def find_blast_table(genome: str) -> str | None:
    """按基因组名匹配 blastp_*_vs_trembl.xlsx（IDF 加权 token 匹配）。"""
    if not os.path.isdir(FUNCTION_DIR):
        return None
    candidates = []
    for fname in sorted(os.listdir(FUNCTION_DIR)):
        m = re.match(r'^blast(p|x)_(.+)_vs_(trembl|swissprot)\.xlsx$', fname)
        if m:
            candidates.append((fname, m.group(1), m.group(2), m.group(3)))
    if not candidates:
        return None

    token_files: dict[str, set[str]] = defaultdict(set)
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
        score += 2 if prog == 'p' else 0
        score += 1 if db == 'trembl' else 0
        if score > best_score:
            best_score = score
            best = os.path.join(FUNCTION_DIR, fname)
    return best


def read_blast_table(path: str):
    """读 BLAST xlsx → DataFrame"""
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


def match_gene_rows(df, genes: list[str]) -> dict[str, list]:
    """按点边界子串把输入基因匹配到 BLAST 表 Query。"""
    import numpy as np
    q = df['query'].astype(str).str.lower()
    wrapped = '.' + q + '.'
    out: dict[str, list] = {}
    for gene in genes:
        key = '.' + str(gene).strip().lower() + '.'
        out[gene] = wrapped.str.contains(key, regex=False).values
    return out


def map_genes_via_blast(
    genes: list[str],
    table_path: str,
    pid_min: float,
    only_taxid: str | None = None,
) -> dict[str, dict[str, tuple[str, float, float]]]:
    """trembl 表映射：gene → {taxid: (accession, pid, exp)}。"""
    import pandas as pd
    df = read_blast_table(table_path)
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

    org2taxid: dict[str, str] = {}
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

    hits: dict[str, dict[str, tuple[str, float, float]]] = {}
    for gene, mask in row_sets.items():
        for i in mask.nonzero()[0]:
            taxid = taxids[i]
            exp = exps[i] if exps[i] == exps[i] else 1e5
            cur = hits.setdefault(gene, {})
            if taxid not in cur or exp < cur[taxid][2]:
                cur[taxid] = (matches[i], float(pids[i]), float(exp))
    return hits
