# Orthogroup 功能升级：现状审查报告与数据库调整方案

> 审查对象：`/data/web/CottonOGD/OGD/backend` 现有 OrthoFinder 相关实现 + `/data/web/CottonOGD/OGD/backend/data/Orthofinder` 实际 OrthoFinder 3.2 结果。
> 审查日期：2026-11-20。本文只记录事实与方案，**未修改任何代码、数据库或原始结果文件**。

---

## 一、现有 Orthogroup 功能架构

### 1.1 代码位置

Orthogroup/Ortholog 功能不是一个独立 Django app，而是主 app `CottonOGD` 内的一个功能模块：

| 层 | 文件 | 说明 |
|---|---|---|
| 模型 | `CottonOGD/models.py` L641–696 | `OrthofinderOrthogroup`、`OrthofinderOgGene`、`OrthofinderDuplication` |
| 视图 | `CottonOGD/views/orthofinder.py` | 8 个接口，全部手写 `JsonResponse/Response` |
| 路由 | `CottonOGD/urls.py` L132–140 | 前缀 `/CottonOGD_api/orthofinder/` |
| 索引构建 | `management/commands/build_orthofinder_index.py` | 从 `Orthogroups/Orthogroups.tsv` 构建 OG 成员表 |
| 索引构建 | `management/commands/build_orthofinder_duplications.py` | 从 `Gene_Duplication_Events/Duplications.tsv` 构建复制事件表 |
| 搜索索引 | `management/commands/rebuild_orthologs_index.py` | 把基因→OG 写入 Meilisearch `Orthologs` 索引 |
| 配置 | `mysite/settings.py` L29 | `ORTHOFINDER_RESULTS_DIR = BASE_DIR/data/Orthofinder` |
| 迁移 | `0056_orthofinder.py`、`0057_orthofinder_duplication.py` | 三张表 |

### 1.2 现有数据库表

#### `orthofinder_orthogroup`（OG 元数据）

| 字段 | 类型 | 含义 |
|---|---|---|
| `og_code` | varchar(20) PK | OG 编号，如 `OG0000000` |
| `gene_count` | int | 该 OG 总基因数（构建时按 TSV 单元格统计） |
| `species_count` | int | 该 OG 涉及的物种数（非空物种列数） |
| `is_single_copy` | bool | **当前实现 = (species_count == 物种列总数)**，语义是“所有物种都出现”，不是“严格单拷贝” |

索引：`is_single_copy`。

#### `orthofinder_og_gene`（OG ↔ 基因成员，核心表）

| 字段 | 类型 | 含义 |
|---|---|---|
| `og_code` | varchar(20)，索引 | OG 编号 |
| `species` | FK → `species.name` | 物种名（与 `Species_info.name` 完全对齐） |
| `geneid` | varchar(200)，索引 | OrthoFinder transcript id（如 `Gano_03G008390.1`） |

唯一约束 `(og_code, species, geneid)`；无 `(species, og_code)` 复合索引。

#### `orthofinder_duplication`（基因复制事件）

字段 `og_code`、`species_node`、`gene_tree_node`、`support`、`dup_type`、`genes1`、`genes2`；索引 `(og_code, species_node)`。

#### 关联到既有基因模型的方式

- `orthofinder_og_gene.geneid` = OrthoFinder 输入蛋白 id = `TranscriptMaster.transcriptid`（带版本号）。
- 查询时 `_resolve_genemaster()` 按“原 id / 去版本 id”批量查 `TranscriptMaster` → `GeneMaster.geneid`，未命中返回 `null`。
- **没有**复制 Gene/Genome 的基本信息，符合“复用既有 Gene 模型”的要求。

### 1.3 现有 API 清单（共 8 个）

| Method | URL | 入参 | 行为 |
|---|---|---|---|
| POST | `/CottonOGD_api/orthofinder/ortholog_gene/` | `geneid` | 基因 → 所属 OG（可多个）→ 各 OG 的跨物种成员 |
| POST | `/CottonOGD_api/orthofinder/orthogroup_detail/` | `og_code` | OG → 全部跨物种成员 |
| POST | `/CottonOGD_api/orthofinder/orthogroups_by_species/` | `species[]`, `mode=all\|any`, `limit`, `offset` | 按物种筛选 OG；默认 `all`（**交集**） |
| GET | `/CottonOGD_api/orthofinder/meta/` | — | 物种下拉列表 |
| GET | `/CottonOGD_api/orthofinder/sequence/<og_code>` | — | `Orthogroup_Sequences/<og>.fa` |
| GET | `/CottonOGD_api/orthofinder/tree/<og_code>` | — | 解析基因树 Newick |
| GET | `/CottonOGD_api/orthofinder/msa/<og_code>` | — | `MultipleSequenceAlignments/<og>.fa` |
| GET | `/CottonOGD_api/orthofinder/tandem/<og_code>` | — | 基于 `orthofinder_duplication` 的复制事件 |

响应均为裸 JSON（非 DRF 统一分页结构）；文件接口不存在时返回裸 404，前端静默降级。

### 1.4 现有筛选语义（必须保持）

`orthogroups_by_species`：

```python
qs = OrthofinderOgGene.objects.filter(species__in=known)
          .values('og_code').annotate(n_sp=Count('species', distinct=True))
if mode == 'all':
    qs = qs.filter(n_sp=len(known))          # 交集：所选物种全部出现
# mode='any' 不加过滤：并集
```

- **默认 `all` = 交集**；`any` = 并集（只要出现任一所选物种）。
- 只统计“所选物种”内的覆盖数，不校验 OG 是否也被其他物种共享。
- 排序 `-n_sp, og_code`；`limit` 硬上限 500。
- 物种名先与 `Species_info` 求交，未知物种被静默丢弃。

### 1.5 MSA / Tree / Sequence 文件读取方式（现状）

- **MSA**：`MultipleSequenceAlignments/<og_code>.fa`，`FileResponse` 流式返回，`text/plain`。
- **Sequence**：`Orthogroup_Sequences/<og_code>.fa`，同上。
- **Tree**：OrthoFinder 3.2 **没有** `Gene_Trees/` 目录，也没有每 OG 单独的 `.treefile`；只有合并文件 `Resolved_Gene_Trees/Resolved_Gene_Trees.txt`（每行 `OGxxxx: (newick)`）。现有实现：
  1. 先找 `Resolved_Gene_Trees/<og>.treefile`（旧版兼容）；
  2. 否则首次请求时为 896MB 合并文件构建内存索引 `{og_code: 行首字节偏移}`，之后 `seek` 读取该行并去掉 `OGxxxx:` 前缀。
- 三个文件接口都**不落 MySQL**，符合项目既有约定。

---

## 二、当前数据库实际状态（重要）

通过 Django ORM 直接查询：

| 表 | 行数 | 最后更新时间 |
|---|---|---|
| `orthofinder_orthogroup` | **84,279** | 2026-11-10 17:28 |
| `orthofinder_og_gene` | **2,862,766** | 2026-11-10 17:28 |
| `orthofinder_duplication` | **242,888** | 2026-11-10 21:05 |

`orthofinder_og_gene` 中只有 **61 个 distinct species**；OG 编号范围 `OG0000000`–`OG0084278`。

而实际 OrthoFinder 3.2 结果是：

- **258 个物种**
- **121,061 个 OG**
- **17,412,359 个基因**，其中 17,156,178（98.5%）进入 OG
- OG 编号范围 `OG0000000`–`OG0121060`

**结论：现有 MySQL 索引是 2026-11-10 一次旧的 61 物种分析结果，与当前 258 物种结果不一致，必须重建。** 现有页面实际只能看到旧分析的 61 个物种/8.4 万个 OG，这是当前功能最大的问题。

`is_single_copy` 现有 1,212 条为 `true`，其语义是“61 个物种全部出现”；按真实定义（每个物种恰好 1 个基因）重新计算后应为 **0**（与 `Statistics_Overall.tsv` 一致）。

---

## 三、OrthoFinder 3.2 实际结果目录审查

根目录：`/data/web/CottonOGD/OGD/backend/data/Orthofinder`（只读，勿修改）。

| 目录/文件 | 规模 | 格式与用途 |
|---|---|---|
| `Orthogroups/Orthogroups.tsv` | 367MB，121,062 行（含表头），259 列 | 第 1 列 `Orthogroup`，其余 **258 个物种列**；单元格为逗号分隔的 transcript id |
| `Orthogroups/Orthogroups.GeneCount.tsv` | 64MB，121,062 行，260 列 | 同上 + 末尾 `Total` 列，值为每 OG 每物种基因数 |
| `Orthogroups/Orthogroups.tsv` 同目录 `MCL_*` | 2.4GB | MCL 算法原始输出，现有代码未使用；不是主结果 |
| `Orthogroups/Orthogroups_UnassignedGenes.tsv` | 73MB | 未分配到 OG 的基因，现有代码未导入 |
| `Orthogroups/Orthogroups_SingleCopyOrthologs.txt` | **0 字节** | 严格单拷贝 OG 列表为空；与统计“Number of single-copy orthogroups = 0”一致 |
| `Orthologs/<species>.tsv.gz` | 258 个文件，合计约 28GB；单文件约 6.48M 行 | 表头 `Orthogroup / Species / <查询物种> / Orthologs`；每行是一个 (OG, 配对物种) 的基因对集合，两列均为逗号分隔 |
| `Phylogenetic_Hierarchical_Orthogroups/N*.tsv` | 256 个文件（N1–N256），18GB，合计 54.4M 行 | 表头 `HOG / OG / Gene Tree Parent Clade / 258 个物种列`；HOG id 形如 `N12.HOG0000123` |
| `Resolved_Gene_Trees/Resolved_Gene_Trees.txt` | 856MB，84,829 行 | 每行 `OGxxxx: (newick)`；只有 84,829 个 OG 有基因树（编号越小 OG 越大，故只覆盖 `OG0000000`–`OG0084828`） |
| `Species_Tree/SpeciesTree_rooted_node_labels.txt` | 12KB | Newick，258 个叶 + 256 个内部节点 `N1`–`N256`；节点编号与 PHOG 文件一一对应 |
| `Species_Tree/SpeciesTree_rooted.txt` | 12KB | 无节点标签版本 |
| `Comparative_Genomics_Statistics/Statistics_Overall.tsv` | 3.4KB | 总体统计（键值对） |
| `Comparative_Genomics_Statistics/Statistics_PerSpecies.tsv` | 122KB | 每物种统计（矩阵） |
| `Comparative_Genomics_Statistics/OrthologsStats_*.tsv` | 5 个，各 0.37–0.54MB | 物种两两矩阵：one-to-one / one-to-many / many-to-one / many-to-many / Totals |
| `Comparative_Genomics_Statistics/Duplications_per_Orthogroup.tsv` | 1.2MB，84,830 行 | 每 OG 复制数 |
| `Comparative_Genomics_Statistics/Duplications_per_Species_Tree_Node.tsv` | 10.7KB | 每物种树节点复制数 |
| `Comparative_Genomics_Statistics/Orthogroups_SpeciesOverlaps.tsv` | **不存在** | `Statistics_Overall.tsv` 中引用了该文件，但实际未生成，接口需明确返回“不可用” |
| `Gene_Duplication_Events/Duplications.tsv` | 3.8GB，457,328 行 | 表头 `Orthogroup / Species Tree Node / Gene Tree Node / Support / Type / Genes 1 / Genes 2` |
| `MultipleSequenceAlignments/<og>.fa` | 100,453 个，12GB | 预生成的 MSA（FASTA），**不是**每个 OG 都有（缺 20,608 个） |
| `Orthogroup_Sequences/<og>.fa` | 377,242 个，9GB | 每 OG 的未比对序列；当前 121,061 个 OG 均有文件，另有 **256,181 个旧分析遗留文件**（最大 `OG0377241`） |
| `WorkingDirectory/` | 528MB | OrthoFinder 中间文件，不使用 |
| `Log.txt` | — | 记录本次运行完成于 2026-11-14 03:25 |

### 3.1 统计事实（来自 `Statistics_Overall.tsv`）

- 物种 258，基因 17,412,359，进入 OG 17,156,178（98.5%）
- OG 121,061；物种特异 OG 10,410（基因 49,806）
- 平均 OG 大小 141.7，中位数 12.0
- **所有物种都出现的 OG：10 个**
- **严格单拷贝 OG：0 个**（必须如实展示）

### 3.2 物种与基因 ID 映射

- `Orthogroups.tsv` 的 258 个物种列与 `Species_info.name` **258/258 完全一致**（已用 ORM 校验，无缺失、无多余）。
- `TranscriptMaster`/`GeneMaster` 的映射沿用现有 `_resolve_genemaster`（先精确、再去末尾 `.\d+` 版本号匹配）。
- 基因 id 形态不统一，例如 `Gano_03G008390.1`、`TURN.01g321260.m01-v1.0.a2`；不能假设统一正则。
- 存在 1 个非标准 OG 编号（数据源自带，`Orthogroups.tsv` 与 `Orthogroup_Sequences` 均存在），索引构建时按字符串原样处理。

---

## 四、现有功能存在的问题清单

| # | 问题 | 影响 | 处理建议 |
|---|---|---|---|
| 1 | MySQL 索引停留在旧 61 物种分析 | 页面数据严重不完整 | **重建**三张表（必须） |
| 2 | `is_single_copy` 语义错误（“全物种出现”） | 单拷贝标记错误 | 重建时改为 `gene_count == species_count == 258`；本次全部为 false |
| 3 | 无 `(species, og_code)` 复合索引 | 多 Genome 交集查询在 17.4M 行上慢 | 新增复合索引 |
| 4 | `orthogroups_by_species` 无 OG ID 精确/模糊查询、无成员数/覆盖数筛选 | 功能不满足升级目标 | **扩展**同一接口，保持 `all/any` 语义 |
| 5 | OG 成员一次性全量返回，无分页 | 大 OG（最大 5,364 基因）响应过大 | 新增成员分页参数，默认保持旧行为 |
| 6 | 没有基于 `Orthologs/` 的真实直系同源查询 | 现有 `ortholog_gene` 只是“同 OG 成员”，不能区分直系/旁系 | **新增**真实 ortholog 查询（读取 Orthologs 输出） |
| 7 | 没有 HOG 支持 | 功能缺失 | **新增** HOG 查询 |
| 8 | 没有统计文件 / 物种树接口 | 功能缺失 | **新增**只读接口 |
| 9 | `orthofinder_meta` 每次 `SELECT DISTINCT species FROM orthofinder_og_gene` | 重建后扫描 17.4M 行 | 改为从 `species`/索引读取并缓存 |
| 10 | `orthofinder_tree` 首次请求在进程内构建 856MB 文件索引 | 首次请求阻塞、重启重复构建 | 持久化索引或落 Redis，保留现有读取语义 |
| 11 | `Orthogroup_Sequences` 混有 25.6 万个旧分析文件 | 目录膨胀 9GB、可能误导 | **不删除**；接口只按当前 OG 访问，报告中记录 |
| 12 | 无任何 OrthoFinder 单元测试 | 升级无回归保障 | 新增测试 |
| 13 | `Orthogroups_SpeciesOverlaps.tsv` 缺失 | 统计接口需处理缺失 | 明确返回“该统计文件未生成” |

---

## 五、保留、扩展、删除建议

### 保留（不改行为）

- `/orthofinder/ortholog_gene/`、`/orthogroup_detail/`、`/orthogroups_by_species/`、`/meta/`、`/sequence/`、`/tree/`、`/msa/`、`/tandem/` 的 URL、方法、主要字段。
- `all=交集 / any=并集` 的筛选语义。
- 文件不存在返回 404 的静默降级约定。
- `orthofinder_og_gene` 作为 OG 成员的唯一关系表，不重复存储基因/物种信息。

### 扩展（在原接口上增加可选参数/字段，默认值保持旧行为）

- `orthogroups_by_species`：增加 `og_code`（精确）、`og_code_like`（模糊）、`min_genes`、`max_genes`、`min_species`、`max_species`、`min_selected_species`、`sort`。
- `orthogroup_detail`：增加 `include_genes`、`limit/offset` 成员分页、`species` 过滤。
- `ortholog_gene`：保留同 OG 结果，新增 `orthologs` 字段（真实 Orthologs 输出），并明确标注两者区别。

### 新增接口（统一前缀 `/CottonOGD_api/orthofinder/`）

- OG 列表分页（在 `orthogroups_by_species` 基础上，可直接复用）。
- `gene_orthologs`：基因 → 真实 Ortholog（可过滤 partner genome、OG）。
- `ortholog_pair` / `genome_pair_orthologs`：两个 Genome 的共享 OG/基因（明确标注为“同 OG 成员”，不冒充 ortholog 对）。
- `gene_hog`、`hog_detail`、`hog_members`。
- `statistics/overall`、`statistics/per_species`、`statistics/orthologs`、`statistics/duplications`。
- `species_tree`、`species_tree_nodes`。

### 不删除

- 现有三张表全部保留；`orthofinder_duplication` 继续服务 `tandem`。
- 不修改、不移动、不删除任何原始 OrthoFinder 结果文件。
- 不新建 `Species Tree 文件索引`、`OG Gene Tree 文件索引`、`MSA 文件索引` 等表。

---

## 六、数据库调整方案

### 6.1 必须重建的三张表（复用现有模型，不新增字段）

1. `build_orthofinder_index`：以当前 `Orthogroups/Orthogroups.tsv` 为准，清空重建。
   - 预计 `orthofinder_og_gene` **17,412,359 行**（含未分配基因的 OG 不计；实际成员 = 17,156,178 + 可能的重复计数以 TSV 为准）。
   - `orthofinder_orthogroup` **121,061 行**。
   - `is_single_copy = (species_count == 258 and gene_count == 258)`。
   - 分块 `bulk_create`，2–5 万/批；预计 10–30 分钟，表约 5–6GB。
2. `build_orthofinder_duplications`：以当前 `Duplications.tsv` 为准重建，预计 **457,326 行**（3.8GB 源文件，表约 2–4GB）。
3. 新增索引（迁移）：
   - `orthofinder_og_gene (species, og_code)`：服务“所选 Genome 交集/并集 + 覆盖数”查询。
   - `orthofinder_orthogroup (species_count)`、`(gene_count)`：服务成员数/覆盖数筛选。
   - 保留现有 `(og_code)`、`(geneid)` 与唯一约束。

### 6.2 不新建 MySQL 表的部分及理由

| 数据 | 规模 | 为什么不能用 MySQL | 采用方案 |
|---|---|---|---|
| Ortholog 基因对 | 单物种文件约 648 万行 × 258 ≈ **16 亿行**；展开成基因对约 30 亿 | 远超合理 MySQL 容量，导入/索引成本不可接受 | **按物种建立 gzip 随机访问索引**：每个 `<species>.tsv.gz` 建 `OG → 解压后字节偏移` 索引（约 12 万项/物种，合计约 3100 万项，存为每物种小索引文件），用 `indexed_gzip` 随机 seek 读取该 OG 的连续行块；不复制原始数据 |
| HOG 记录 | **54,372,724 行**（256 个节点文件合计）+ 估约 1.4 亿“基因-节点”归属 | 表体量 20GB+，且原始文件已是权威数据 | **每节点文件建立 HOG→字节偏移数组**（54.4M 个 int64，合计约 435MB）；另建**每物种 gene→(node, hog) 倒排文件**（约 1.4 亿条，约 1–2GB），用于 Gene→HOG |
| 统计文件 | 总计 < 10MB | 无需入库 | 直接读取 TSV，Redis 缓存 10 分钟 |
| 物种树 / 基因树 / MSA / 序列 | 12KB / 856MB / 12GB / 9GB | 大文本不入库 | 沿用现有按需读取；基因树索引持久化到磁盘 |

> 上述派生索引全部写入**独立目录**（建议 `backend/data/Orthofinder_index/`），不修改 `data/Orthofinder/` 原始结果。派生索引可随时删除重建。

### 6.3 新增/复用的配置

- 复用 `settings.ORTHOFINDER_RESULTS_DIR`。
- 新增 `settings.ORTHOFINDER_INDEX_DIR`（派生索引目录），默认 `BASE_DIR/data/Orthofinder_index`。
- 现有 Redis 缓存可直接使用，但 `CACHES['default']['TIMEOUT'] = None`，**所有缓存必须显式设置 timeout**，且只缓存小对象（统计、物种列表、基因树索引片段），不缓存大型 MSA/树全文。

### 6.4 构建命令（新增，不改旧命令语义）

- `build_orthofinder_ortholog_index`：为 258 个 Orthologs gz 文件建立 OG 偏移索引。
- `build_orthofinder_hog_index`：建立 HOG 偏移数组与每物种 gene→HOG 倒排。
- `build_orthofinder_tree_index`：把 856MB 合并基因树的行偏移索引持久化（替代进程内首次构建）。
- 三个命令均幂等、可 `--force` 重建，构建前校验源文件存在与物种对齐。

---

## 七、实施顺序与风险

1. 重建 `orthofinder_orthogroup` / `orthofinder_og_gene`（阻塞项，约 10–30 分钟）。
2. 重建 `orthofinder_duplication`（约 5–15 分钟）。
3. 新增索引迁移 + 构建派生文件索引（正交同源约 20–40 分钟；HOG 约 30–60 分钟）。
4. 扩展/新增视图与 URL、统一响应结构、分页、参数校验、缓存。
5. 编写测试（使用小型 fixture 或对真实数据只读抽样，不依赖全量构建）。
6. 回归验证现有 8 个接口。
7. 输出 `COMPARATIVE_ANALYSIS_API_HANDOFF.md`。

风险与约束：

- 重建期间 OG 接口数据会短暂不一致；建议在低峰执行，先建新表或使用 `--append` 校验后再切换（本次选择“清空重建”并提前备份旧表）。
- 派生索引占用：Ortholog 索引约 1GB，HOG 索引约 2–3GB；磁盘当前剩余 5.2TB，充足。
- `indexed_gzip` 需新增依赖（已确认有可用的 abi3 wheel），仅用于只读随机访问，不改变原始文件。
- 不删除 `Orthogroup_Sequences` 中 25.6 万个旧文件，避免误删用户数据。

---

## 八、需要确认的设计选择

1. **Ortholog 查询**：采用“每物种 gzip OG 偏移索引 + `indexed_gzip` 随机读取”（不建 MySQL 基因对表）。这是唯一能在 16 亿行规模下满足性能要求的方案。
2. **HOG 查询**：采用“每节点偏移数组 + 每物种 gene→HOG 倒排文件”（不建 5400 万/1.4 亿行 MySQL 表）。
3. **重建策略**：清空重建现有三张表（旧数据为 61 物种分析，已无保留价值）；重建前导出旧表备份。

确认后按第七节顺序实施。
