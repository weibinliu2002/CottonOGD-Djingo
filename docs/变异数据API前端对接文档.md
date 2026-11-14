# 变异数据（SyRI / 群体 SNP·InDel / GWAS）前端对接文档 v2

> 后端已就绪：路由、视图、模型、数据导入均已完成。本文档供前端按接口开发页面。
> 所有接口统一返回 JSON，挂载在 `/CottonOGD_api/`（前端既有前缀）下。
> 请求方式：`GET` / `POST` 均可，参数从 query string 或 body（JSON / form）读取。
> 文档版本：v2（2026-11-13）。相对 v1 的关键变更：**B 域定为 A+C 混合架构**、新增密度统计接口、新增逐样本基因型（tabix）接口。

---

## 1. 数据域概览与 B 域架构决策

| 域 | 后端表 | 含义 | 已导入数据 |
|---|---|---|---|
| **A. SyRI 成对结构变异** | `syri_sr`（结构重排）、`syri_seq`（序列级注释） | 参考×查询两套基因组比对出的 SV | 1 对（TM-1 × Jin668，170 SR + 856 SEQ） |
| **B. 群体 SNP/InDel** | `variant`（位点主表）+ `variant_population`（群体预聚合） | 1913 份材料的变异 | 位点主表按染色体幂等导入（目标约 5000 万位点，后台按 26 染色体推进） |
| **C. 文件层（逐样本基因型）** | `variation_file`（台账）+ tabix VCF | 逐样本 GT 不进 MySQL，经 tabix 取回 | 1913 VCF 已 bgzip+tabix（自带 .tbi）；GWAS SNP/CNV 待建索引 |
| **D. GWAS** | `gwas_trait`/`gwas_accession`/`gwas_phenotype`/`gwas_association` | 纤维性状 BLUP + 标记 | 5 性状 / 890 材料 / 4430 表型值 / 229 万 SNP 标记 / 2.7 万 CNV 标记；关联结果表为空（预留） |

### B 域 A+C 混合方案（已定案）

> 决策依据：1913 样本 × 26 染色体 ≈ **5000 万位点 × 1913 样本 ≈ 千亿级 GT 格子**，全量进 MySQL 不可行。
> 采用 **A（MySQL 位点主表 + 群体预聚合）+ C（tabix 文件层存逐样本基因型）** 混合：

- **A 侧（MySQL，`variant` 表）**：只存**位点主表**（约 5000 万行），支持区间/染色体/类型/ID 快速查询；`variant_population`（群体 AC 预聚合）待群体维表 `populations_info` 填充后启用。
- **C 侧（tabix 文件层）**：逐样本基因型**不进 MySQL**，原始 VCF 经 `bgzip + tabix` 索引，查询时后端调 `tabix` 按区间/位点取回基因型，零入库成本。台账 `variation_file` 登记文件路径，JBrowse / 前端链接从台账生成。
- **分工**：页面级浏览、位点密度、群体频率 → 走 A（MySQL，毫秒级）；"某位点所有样本基因型""某样本全部变异""单点 GT 明细" → 走 C（tabix，秒级）。

---

## 2. 接口总表

| 方法 | 路径 | 功能 | 关键参数 |
|---|---|---|---|
| GET/POST | `/syri/pairs/` | 列出成对比较批次 | 无 |
| GET/POST | `/syri/structural/` | 查结构重排（syri_sr） | `pair_id`（或 `ref`+`query`）；`chrom`/`start`/`end`/`son_type`/`limit` |
| GET/POST | `/syri/sequence/` | 查序列级注释（syri_seq） | 同上 |
| GET/POST | `/variant/sets/` | 列出群体数据集 | 无 |
| GET/POST | `/variant/region/` | 按区间/染色体/类型查位点 | `set_id`（必需）；`chrom`/`start`/`end`/`svtype`/`limit` |
| GET/POST | `/variant/id/` | 按位点 ID 查详情 | `id` |
| GET/POST | `/variant/density/` | **位点数密度（按 bin 直方图）** | `set_id`；`chrom`；`start`/`end`；`bins`（默认 100） |
| GET/POST | `/variant/genotype/` | **逐样本基因型（tabix 取回）** | `set_id`；`chrom`；`start`/`end` 或 `pos`；可选 `samples`/`format` |
| GET/POST | `/gwas/traits/` | 列出 GWAS 性状 | 无 |
| GET/POST | `/gwas/accessions/` | 列出 GWAS 材料 | 可选 `species` |
| GET/POST | `/gwas/phenotype/` | 查表型 BLUP 值 | `trait_code` 和/或 `accession` |
| GET/POST | `/gwas/markers/` | 查 GWAS 标记位点 | `set_id`；`chrom`/`start`/`end`/`limit` |
| GET/POST | `/gwas/associations/` | 查 GWAS 关联结果（预留，当前空） | `trait_code`/`chrom`/`start`/`end`/`threshold`/`top_n` |

---

## 3. 接口详细定义

### 3.1 SyRI 成对结构变异（A 域）

#### `GET /syri/pairs/`
```json
[{"id": 1, "ref_genome_id": 67, "query_genome_id": 84, "status": "verified", "syri_version": "syri", "created_at": "2026-11-13T13:48:36Z"}]
```
`ref_genome_id`/`query_genome_id` 对应 `species.id`（67=TM-1 HAU_v1.1，84=Jin668）。

#### `GET /syri/structural/?pair_id=1&chrom=Ghir_A01&son_type=SYN&start=1&end=1000000&limit=500`
```json
{
  "pair_id": 1, "count": 2,
  "type_stat": [
    {"son_type": "SYN", "count": 56}, {"son_type": "DUP", "count": 43},
    {"son_type": "INV", "count": 15}, {"son_type": "TRANS", "count": 10},
    {"son_type": "INVTR", "count": 18}, {"son_type": "INVDP", "count": 28}
  ],
  "rows": [
    {"id": 2, "genome_pair_id": 1, "ref_genome_id": 67, "query_genome_id": 84,
     "ref_genome_chr": "Ghir_A01", "ref_start": 29, "ref_end": 5068,
     "ref_seq": null, "alt_seq": null,
     "query_genome_chr": "Ghjin_A01", "query_start": 3674, "query_end": 10113,
     "event_id": "SYN1", "parent_event": null, "son_type": "SYN", "copygain": null, "sv_length": 5040}
  ]
}
```
**查询方式**：① `pair_id`（或 `ref_genome_id`+`query_genome_id` 反查）定位一对；② `chrom` 过滤参考染色体；③ `start`/`end` 参考坐标区间；④ `son_type` 类型；⑤ `limit`（默认 500，最大 2000）。
`/syri/sequence/` 结构完全一致，数据来自 `syri_seq`（HDR/TDM/CPG/CPL）。

### 3.2 群体变异位点（B 域 · A 侧 MySQL）

#### `GET /variant/sets/`
```json
[{"id": 1, "name": "cotton_pan_sv_v1", "reference_genome": 67, "caller": "pan-genome calling", "sample_count": 1913},
 {"id": 2, "name": "gwas_snp_890", "reference_genome": 67, "caller": "GWAS marker", "sample_count": 890},
 {"id": 3, "name": "gwas_cnv_419", "reference_genome": 67, "caller": "GWAS marker", "sample_count": 419}]
```

#### `GET /variant/region/?set_id=1&chrom=A01&start=1&end=100000&svtype=SNP&limit=1000`
```json
{
  "set_id": 1, "count": 1000,
  "type_stat": [{"svtype": "SNP", "count": 1250000}, {"svtype": "INDEL", "count": 650000}],
  "rows": [{"id": 2800001, "chrom": "A01", "pos": 6178, "end_pos": 6178, "svtype": "SNP", "ref": "T", "alt": "C", "filter": "PASS"}]
}
```
`type_stat` 为**全数据集**类型计数（画分布饼图用），不受当前区间/分页影响。`limit` 默认 1000，最大 5000。

#### `GET /variant/id/?id=2800001`
```json
{"id": 2800001, "set_id": 1, "chrom": "A01", "pos": 6178, "end_pos": 6178, "svtype": "SNP", "ref": "T", "alt": "C", "qual": null, "filter": "PASS", "info_json": null}
```

#### `GET /variant/density/?set_id=1&chrom=A01&start=1&end=5000000&bins=100`  **【新增·密度统计】**
返回该区间按 `bins` 个等宽窗口的位点数分布，用于 JBrowse histogram / 前端密度图。
```json
{
  "set_id": 1, "chrom": "A01", "start": 1, "end": 5000000, "bins": 100, "bin_size": 50000,
  "total": 48012,
  "histogram": [
    {"bin": 0, "start": 1, "end": 50000, "count": 612},
    {"bin": 1, "start": 50001, "end": 100000, "count": 588},
    {"bin": 99, "start": 4950001, "end": 5000000, "count": 503}
  ]
}
```
> 后端用 `(set_id, chrom, pos)` 索引做范围计数（毫秒级），无需全表聚合。前端可直接画柱状密度图或喂 JBrowse。

### 3.3 逐样本基因型（B 域 · C 侧 tabix）**【新增】**

#### `GET /variant/genotype/?set_id=1&chrom=A01&start=100000&end=200000`  **【新增·tabix 取回】**
从已 tabix 索引的群体 VCF 取回区间内的逐样本基因型。后端调 `tabix` 命令，返回解析后的记录。
```json
{
  "set_id": 1, "chrom": "A01", "start": 100000, "end": 200000,
  "samples": ["H84021", "BYU11001", "..."],
  "records": [
    {"chrom": "A01", "pos": 123456, "id": ".", "ref": "A", "alt": "G",
     "genotypes": {"H84021": "0/1", "BYU11001": "1/1", "...": "0/0"}}
  ]
}
```
**查询方式**：① `set_id` 必需；② `chrom`+`start`/`end` 区间，或 `chrom`+`pos` 单点；③ 可选 `samples`（子集，逗号分隔）只取指定样本；④ 可选 `format`（默认 `GT`）。
> 说明：逐样本 GT 不进 MySQL（A+C 决策），经 tabix 实时取回，区间建议 ≤ 1 Mb 以保证响应。前端"某位点所有样本基因型""某区间样本分布"走此接口。返回的 `samples` 为该数据集 **全部样本列序**（用于矩阵化渲染），`records[].genotypes` 为逐位点 `{样本: GT}`（缺失为 `./.`）。染色体只用 display 名（`A01`/`D13`），后端按 set_id 自动映射到各 VCF 内部 contig。

### 3.4 GWAS（D 域）

#### `GET /gwas/traits/`
```json
[{"id": 1, "code": "FE", "name": "Fiber elongation", "unit": "%", "description": null},
 {"id": 2, "code": "FL", "name": "Fiber length", "unit": "mm", "description": null},
 {"id": 3, "code": "FM", "name": "Fiber micronaire", "unit": "μg/inch", "description": null},
 {"id": 4, "code": "FS", "name": "Fiber strength", "unit": "cN/tex", "description": null},
 {"id": 5, "code": "FU", "name": "Fiber uniformity", "unit": "%", "description": null}]
```
FE 伸长率 / FL 长度 / FM 马克隆值 / FS 强度 / FU 整齐度。

#### `GET /gwas/accessions/?species=G. hirsutum`
```json
[{"id": 1, "name": "HBAU1", "species": "G. hirsutum", "population": null}]
```

#### `GET /gwas/phenotype/?trait_code=FE` （或 `?accession=HBAU1` 或两者同时）
```json
{"count": 886, "rows": [
  {"accession": "HBAU1", "trait": "FE", "value": 6.83847094954162},
  {"accession": "HBAU2", "trait": "FE", "value": 6.81434350399835}
]}
```
- 只给 `trait_code` → 该性状全群体分布（直方图/箱线图）；只给 `accession` → 该材料 5 性状（雷达图）；两者都给 → 单值。

#### `GET /gwas/markers/?set_id=2&chrom=A01&limit=1000`
GWAS 标记位点（SNP=set_id 2，CNV=set_id 3），参数同 `/variant/region/`（不含 `svtype`）。
```json
{"set_id": 2, "count": 1000, "rows": [{"id": 1350001, "chrom": "A01", "pos": 8547, "svtype": "SNP", "ref": "A", "alt": "G"}]}
```

#### `GET /gwas/associations/?trait_code=FE&threshold=1e-5&top_n=100`
GWAS 关联结果。**当前表为空**，返回 `{"count": 0, "rows": []}`。返回行结构：
```json
{"id": 1, "set_id": null, "trait_id": 1, "chrom": "A01", "pos": 12345, "variant_id": null,
 "ref": "A", "alt": "G", "pvalue": 1.2e-7, "effect": 0.03, "r2": 0.15, "maf": 0.21, "information_json": null}
```

---

## 4. 常见查询组合（前端可直接套用）

| 用户想要 | 接口 | 参数 |
|---|---|---|
| 某对基因组 SV 类型分布 | `/syri/structural/` + `/syri/sequence/` | `pair_id` |
| 参考基因组某区间 SV | 同上 | `pair_id`+`chrom`+`start`+`end` |
| 只看重排中的倒位 | `/syri/structural/` | `pair_id`+`son_type=INV` |
| 某数据集某染色体位点密度 | `/variant/density/` | `set_id`+`chrom`+`start`+`end`+`bins` |
| 某基因附近 SNP | `/variant/region/` | `set_id`+`chrom`+`start`+`end` |
| 某位点全部样本基因型 | `/variant/genotype/` | `set_id`+`chrom`+`pos`（或 `start`/`end`） |
| 某性状全群体分布 | `/gwas/phenotype/` | `trait_code=FE` |
| 某材料多性状画像 | `/gwas/phenotype/` | `accession=HBAU1` |
| GWAS 显著位点曼哈顿图 | `/gwas/associations/` | `trait_code`+`threshold` |

---

## 5. 已知限制 / 待办（前端注意）

1. **泛基因组位点主表导入进行中**：set_id=1 目标约 5000 万（26 条染色体），按染色体幂等导入；接口契约不变，缺染色体时 `/variant/region/` 与 `/variant/density/` 仅返回已导入染色体的数据。
2. **群体预聚合（`variant_population`）未启用**：待群体维表 `populations_info` 填充后，新增群体频率接口。
3. **GWAS 关联结果为空**：`gwas_association` 表已建但无数据，曼哈顿图/Top 位点待 GWAS 计算后启用。
4. **染色体命名（前端统一用 `A01..A13`/`D01..D13`）**：三个数据集 VCF 内部 contig 命名不同，后端已按 set_id 自动映射，**前端只需传 display 名**，无需关心：
   - 泛基因组（set_id=1）：分染色体文件，内部 contig 为 `1..26`（A01→1 … D13→26）；
   - GWAS SNP（set_id=2）：单文件，内部 contig 为 `GHIR_A01..GHIR_D13`；
   - GWAS CNV（set_id=3）：单文件，内部 contig 为 `1..26`。
5. **`/variant/genotype/` 区间限制**：建议 ≤ 1 Mb，超出按染色体分块请求；返回 `samples` 为该文件**全部样本列序**，`records[].genotypes` 为逐位点字典（含 `./.` 缺失）。
6. **GWAS VCF 已落地到可写目录并建索引**：`890.hmp`（set 2，890 样本）与 `419.CNV`（set 3，419 样本）已复制到 `backend/data/variant_vcf/` 并完成 tabix 索引（源目录只读，故用副本）；1913 泛基因组 26 个文件在源目录自带 `.tbi`，台账直接登记。

---

## 6. 返回码约定

| 场景 | HTTP | body |
|---|---|---|
| 成功 | 200 | 数据 JSON |
| 缺必需参数 | 400 | `{"error": "..."}` |
| 记录不存在 | 404 | `{"error": "variant not found"}` |
| tabix 文件未索引 | 400 | `{"error": "vcf not tabix-indexed: <path>"}` |
