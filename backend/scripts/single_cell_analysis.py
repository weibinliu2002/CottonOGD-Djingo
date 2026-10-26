#!/usr/bin/env python3
"""
单细胞转录组（scRNA-seq）分析脚本（scanpy 标准流程）。

输入两个文件：
  1. 基因 count 矩阵：TSV/CSV，首列 gene_id，表头为细胞 barcode（基因 x 细胞）
     也支持 10x h5（--counts matrix.h5）或 10x mtx 目录（--counts <dir>）
  2. 分组文件：TSV/CSV，两列 cell,group（细胞 barcode -> 预先分组/处理条件），
     可选（不提供则只做聚类，不做组间比较）

流程：
  QC 过滤（基因/细胞阈值） -> normalize_total + log1p -> HVG ->
  Scale -> PCA -> 邻居图 -> Leiden 聚类 -> UMAP ->
  marker 基因（rank_genes_groups，Wilcoxon）->
  若提供分组文件：按分组的差异表达 + marker 基因按分组富集统计

用法：
  python scripts/single_cell_analysis.py \
      --counts  counts.csv \
      --outdir  results/sc_20261025 \
      [--group  cell_groups.tsv] \
      [--min-genes 200] [--min-cells 3] \
      [--max-mito-pct 20] [--n-top-genes 2000] \
      [--resolution 1.0] [--leiden-key leiden] \
      [--species G.hirsutumAD1_TM1_HAU_v1]      # 提供时用项目数据库做 marker GO 富集

输出（outdir 下）：
  qc_metrics.tsv               每细胞 QC 指标（过滤前）
  filtered_summary.txt         过滤统计
  pca.png / umap_leiden.png / umap_group.png（有分组时）
  cluster_markers_leiden.tsv   Leiden 各簇 marker 基因
  markers_<group>.tsv          各组 marker 基因（有分组时）
  deg_<A>_vs_<B>.tsv / deg_genes_<A>_vs_<B>.txt（分组恰为 2 组时，供 PPI 用）
  sc_anndata.h5ad              全部结果（坐标、聚类、marker）的 AnnData
"""
import argparse
import os
import sys
import warnings


def log(msg):
    print(msg, flush=True)


def fail(msg):
    log(f'ERROR: {msg}')
    sys.exit(1)


def check_deps():
    missing = []
    for mod, hint in (('scanpy', 'scanpy'), ('anndata', 'anndata'),
                      ('scipy', 'scipy'), ('sklearn', 'scikit-learn'),
                      ('numpy', 'numpy'), ('pandas', 'pandas'),
                      ('matplotlib', 'matplotlib'), ('seaborn', 'seaborn')):
        try:
            __import__(mod)
        except ImportError:
            missing.append(hint)
    if missing:
        fail('缺少依赖: ' + ', '.join(missing) +
             '\n  安装: pip install ' + ' '.join(missing) +
             '\n  leiden 聚类还需要: pip install leidenalg igraph')


check_deps()

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import scanpy as sc  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams['axes.unicode_minus'] = False


def read_table(path):
    """按扩展名读 TSV/CSV，首列作为索引"""
    sep = ',' if path.lower().endswith('.csv') else '\t'
    return pd.read_csv(path, sep=sep, index_col=0)


def load_counts(counts_path):
    """支持 10x h5 / 10x mtx 目录 / TSV/CSV 矩阵 -> AnnData（细胞 x 基因）"""
    if counts_path.endswith('.h5'):
        adata = sc.read_10x_h5(counts_path)
        adata.var_names_make_unique()
        return adata
    if os.path.isdir(counts_path):
        adata = sc.read_10x_mtx(counts_path, var_names='gene_symbols', cache=True)
        adata.var_names_make_unique()
        return adata
    df = read_table(counts_path)
    log(f'count 矩阵: {df.shape[0]} 基因 x {df.shape[1]} 细胞')
    # 存成 细胞 x 基因（scanpy 约定），稀疏化省内存
    import scipy.sparse as sp
    X = sp.csr_matrix(df.values.T)
    adata = sc.AnnData(X=X, obs=pd.DataFrame(index=df.columns.astype(str)),
                       var=pd.DataFrame(index=df.index.astype(str)))
    adata.var_names_make_unique()
    adata.obs_names_make_unique()
    return adata


def qc_and_filter(adata, min_genes, min_cells, max_mito_pct):
    """QC 指标 + 过滤。线粒体基因按 mt- / MT- 前缀识别（植物用 mt）。"""
    adata.var['mt'] = adata.var_names.str.match(r'^(?i)mt[-_]')
    adata.var['mt'] = adata.var['mt'].astype(bool)
    sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], percent_top=None,
                               log1p=False, inplace=True)
    adata.obs[['total_counts', 'n_genes_by_counts', 'pct_counts_mt']] \
        .to_csv('qc_metrics.tsv', sep='\t')

    n0 = adata.n_obs
    has_mito = bool(adata.var['mt'].any())
    keep_cells = (adata.obs['n_genes_by_counts'] >= min_genes).values
    if has_mito and max_mito_pct > 0:
        keep_cells &= (adata.obs['pct_counts_mt'] <= max_mito_pct).values
    adata._inplace_subset_obs(keep_cells)
    sc.pp.filter_genes(adata, min_cells=min_cells)
    lines = [
        f'细胞: {n0} -> {adata.n_obs}（基因数阈值 {min_genes}，'
        f'线粒体阈值 {max_mito_pct if has_mito else "不适用"}%）',
        f'基因: 保留 {adata.n_vars}（至少 {min_cells} 个细胞表达）',
    ]
    with open('filtered_summary.txt', 'w') as f:
        f.write('\n'.join(lines) + '\n')
    log('QC: ' + '; '.join(lines))


def cluster_and_embed(adata, n_top_genes, resolution, leiden_key):
    """归一化 -> HVG -> scale -> PCA -> neighbors -> leiden -> umap"""
    adata.layers['counts'] = adata.X.copy()
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    n_hvg = min(n_top_genes, adata.n_vars)
    sc.pp.highly_variable_genes(adata, n_top_genes=n_hvg, flavor='seurat')
    log(f'HVG: {int(adata.var["highly_variable"].sum())} 个')
    sc.pp.scale(adata, max_value=10)
    sc.tl.pca(adata, n_comps=min(50, min(adata.n_obs, adata.n_vars) - 1),
              svd_solver='arpack')
    sc.pp.neighbors(adata, n_neighbors=15, n_pcs=15)
    try:
        sc.tl.leiden(adata, resolution=resolution, key_added=leiden_key)
    except Exception as e:
        fail(f'Leiden 聚类失败（需要 leidenalg/igraph: pip install leidenalg igraph）: {e}')
    n_clusters = adata.obs[leiden_key].nunique()
    log(f'Leiden: {n_clusters} 个簇 (resolution={resolution})')
    sc.tl.umap(adata)
    return n_clusters


def plot_embeddings(adata, leiden_key, group_col=None):
    sc.settings.figdir = '.'
    sc.pl.umap(adata, color=[leiden_key], show=False, save='_leiden.png')
    log('UMAP -> figures/umap_leiden.png（scanpy 以 figures/ 前缀保存）')
    if group_col and group_col in adata.obs:
        sc.pl.umap(adata, color=[group_col], show=False, save='_group.png')
    plt.close('all')


def marker_analysis(adata, groupby_key, out_tsv):
    """rank_genes_groups（Wilcoxon）-> 长表 tsv"""
    sc.tl.rank_genes_groups(adata, groupby=groupby_key, method='wilcoxon')
    res = adata.uns['rank_genes_groups']
    rows = []
    for grp in res['names'].dtype.names:
        for i in range(len(res['names'][grp])):
            rows.append({
                'group': grp,
                'gene_id': res['names'][grp][i],
                'score': res['scores'][grp][i],
                'p_value': res['pvals'][grp][i],
                'p_adj': res['pvals_adj'][grp][i],
                'logFC': res['logfoldchanges'][grp][i],
            })
    df = pd.DataFrame(rows)
    df.to_csv(out_tsv, sep='\t', index=False)
    log(f'marker -> {out_tsv} ({len(df)} 行)')
    return df


def save_h5ad(adata):
    slim = adata.copy()
    # 删除大对象减小体积
    for key in ('counts',):
        if key in slim.layers:
            del slim.layers[key]
    slim.obsm.pop('X_pca', None)
    try:
        slim.write('sc_anndata.h5ad', compression='gzip')
        log('结果保存 -> sc_anndata.h5ad')
    except Exception as e:
        log(f'h5ad 保存失败（跳过）: {e}')


def main():
    ap = argparse.ArgumentParser(description='单细胞转录组分析（输入 count 矩阵 + 可选分组）')
    ap.add_argument('--counts', required=True,
                    help='count 矩阵（TSV/CSV 首列 gene_id，或 10x h5 / mtx 目录）')
    ap.add_argument('--group', help='分组文件（cell,group 两列，可选）')
    ap.add_argument('--outdir', required=True, help='结果输出目录')
    ap.add_argument('--min-genes', type=int, default=200, help='细胞最少表达基因数（默认 200）')
    ap.add_argument('--min-cells', type=int, default=3, help='基因最少在几个细胞中表达（默认 3）')
    ap.add_argument('--max-mito-pct', type=float, default=20, help='线粒体比例上限%%（默认 20，0 表示不过滤）')
    ap.add_argument('--n-top-genes', type=int, default=2000, help='HVG 数（默认 2000）')
    ap.add_argument('--resolution', type=float, default=1.0, help='Leiden 分辨率（默认 1.0）')
    ap.add_argument('--leiden-key', default='leiden', help='Leiden 结果在 obs 中的列名（默认 leiden）')
    ap.add_argument('--species', help='基因组名（Species_info.name，提供时对 marker 做项目数据库 GO 富集）')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    os.chdir(args.outdir)

    adata = load_counts(args.counts)

    group_col = None
    if args.group:
        groups = read_table(args.group)
        if groups.shape[1] < 1:
            fail(f'分组文件需包含 cell,group 两列: {args.group}')
        s2g = dict(zip(groups.iloc[:, 0].astype(str), groups.iloc[:, 1].astype(str)))
        matched = [c for c in adata.obs_names if c in s2g]
        if len(matched) < len(adata.obs_names):
            log(f'警告: {adata.n_obs - len(matched)} 个细胞在分组文件中缺失，将被过滤')
        adata = adata[matched].copy()
        group_col = 'user_group'
        adata.obs[group_col] = [s2g[c] for c in adata.obs_names]
        log(f'分组: {adata.obs[group_col].nunique()} 组, {adata.n_obs} 细胞')

    qc_and_filter(adata, args.min_genes, args.min_cells, args.max_mito_pct)
    if adata.n_obs < 10:
        fail(f'过滤后细胞过少（{adata.n_obs}），检查 QC 阈值')
    if group_col:
        # QC 过滤后再丢掉空组
        keep_groups = adata.obs[group_col].value_counts()
        adata = adata[adata.obs[group_col].isin(keep_groups[keep_groups >= 3].index)].copy()

    cluster_and_embed(adata, args.n_top_genes, args.resolution, args.leiden_key)

    plot_embeddings(adata, args.leiden_key, group_col)

    # Leiden 簇 marker
    marker_analysis(adata, args.leiden_key, 'cluster_markers_leiden.tsv')

    # 分组 marker / 组间差异
    if group_col:
        n_groups = adata.obs[group_col].nunique()
        marker_analysis(adata, group_col, 'markers_user_group.tsv')
        if n_groups == 2:
            ga, gb = sorted(adata.obs[group_col].unique())
            sub = adata[adata.obs[group_col].isin([ga, gb])].copy()
            sub.obs[group_col] = pd.Categorical(sub.obs[group_col], categories=[gb, ga])
            sc.tl.rank_genes_groups(sub, groupby=group_col, method='wilcoxon')
            res = sub.uns['rank_genes_groups']
            df = pd.DataFrame({
                'gene_id': res['names'][ga],
                'score': res['scores'][ga],
                'p_value': res['pvals'][ga],
                'p_adj': res['pvals_adj'][ga],
                'logFC': res['logfoldchanges'][ga],
            })
            df.to_csv(f'deg_{ga}_vs_{gb}.tsv', sep='\t', index=False)
            sig = df[(df['p_adj'] < 0.05) & (df['logFC'].abs() >= 1)]
            with open(f'deg_genes_{ga}_vs_{gb}.txt', 'w') as f:
                f.write('\n'.join(sig['gene_id']))
            log(f'组间差异: {ga} vs {gb} 显著 {len(sig)} 个 -> deg_genes_{ga}_vs_{gb}.txt')

    if args.species:
        run_marker_enrichment(adata, args.leiden_key, args.species)

    save_h5ad(adata)
    log('完成。')


def run_marker_enrichment(adata, leiden_key, genome_id):
    """对每个 Leiden 簇的 top marker 用项目数据库 GO 背景做富集（可选）。"""
    try:
        import gseapy as gp
    except ImportError:
        log('gseapy 未安装，跳过 marker 富集')
        return
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
        import django
        django.setup()
        from collections import defaultdict
        from CottonOGD.models import gene_go
    except Exception as e:
        log(f'无法连接项目数据库（{e}），跳过 marker 富集')
        return

    go_sets = defaultdict(set)
    background = set()
    for gene, go_id in gene_go.objects.filter(
            id_id__genome__name=genome_id, go_id__isnull=False
    ).values_list('id_id__geneid', 'go_id_id'):
        if go_id:
            go_sets[str(go_id).strip()].add(gene)
            background.add(gene)
    if not go_sets:
        log(f'{genome_id} 无 GO 背景注释，跳过 marker 富集')
        return
    gene_sets = {k: sorted(v) for k, v in go_sets.items() if v}

    rank = adata.uns['rank_genes_groups']
    for grp in rank['names'].dtype.names:
        top = [g for g in rank['names'][grp][:200] if g in background]
        if len(top) < 10:
            continue
        try:
            enr = gp.enrich(gene_list=sorted(top), gene_sets=gene_sets,
                            background=sorted(background), no_plot=True,
                            outdir=None, verbose=False)
            out = f'enrichment_cluster_{grp}.tsv'
            enr.res2d.to_csv(out, sep='\t', index=False)
            log(f'簇 {grp} marker GO 富集 -> {out}')
        except Exception as e:
            log(f'簇 {grp} 富集失败（跳过）: {e}')


if __name__ == '__main__':
    warnings.filterwarnings('ignore', category=FutureWarning)
    main()
