# 阶段 1：功能对照分析（对标 SoyOmics）

> 基线 tag：`before-refactor` @ `d1652023`
> 生成日期：2026-10-31
> 数据依据：《已有接口清单》（后端 33 个接口）+《现有功能清单》（前端 40 页面 / 11 组件 / 12 store / 5 composable / 6 util）

## 0. 判定标准

| 标记 | 含义 | 处理原则 |
|:---:|------|---------|
| 🟢 | 已有且完善 | 不动数据流，仅样式微调对齐 SoyOmics 风格 |
| 🟡 | 已有但可增强 | 原地增强（表格排序/筛选/分页/下载），**不改数据流** |
| 🔴 | 缺失 | 新增模块（新路由 + 新组件 + mock 数据），接口预留开关 |

---

## 1. 总览对照表

### 1.1 SoyOmics 六大模块

| SoyOmics 模块 | CottonOGD 现状 | 标记 | 说明 |
|---|---|:---:|---|
| **Genome** | `/genome/browse`、`/genome/detail/:key`、`/species/{diploid,tetraploid}` | 🟡 | 列表已有筛选+排序+分页；缺导出；详情页无表格 |
| **Variome** | 无独立模块 | 🔴 | 仅 `genome_synteny` 的 `Variation_type` 字段有弱关联 |
| **Transcriptome** | `/expression/gene`、`/expression/efp` | 🟡 | 功能完整；热图是后端 PNG；缺表格排序与统一导出 |
| **Phenome** | 无 | 🔴 | 后端无表、无接口 |
| **Homology** | `/tools/orthogroup`（**仅 PlaceholderView**） | 🔴 | **OrthoFinder 数据不存在**，`enabled: false`；走 mock |
| **Synteny** | `/genome/synteny`、`/genome/gene-location` | 🟡 | 有接口有页面；表格无排序/分页/导出 |

### 1.2 SoyOmics 工具

| 工具 | CottonOGD 现状 | 标记 | 说明 |
|---|---|:---:|---|
| **BLAST** | `/sequence/blast`、`/sequence/blast/results`、`/sequence/server` | 🟡 | 已对接 `blast_cmd/`；结果表缺排序；阶段 3 补 UI 增强 |
| **单倍型分析** | 无 | 🔴 | 后端无支撑 |
| **GWAS 浏览** | 无 | 🔴 | 后端无支撑 |
| **基因组浏览器** | `/genome/jbrowse`、`/genome/igv` | 🟢 | iframe 嵌入，功能完整 |
| **引物设计** | `/tools/primer-design` | 🟢 | 已对接 `primer_design/`，有导出 |
| **GO/KEGG 注释** | `/annotation/{go,kegg}` | 🟡 | 已对接；缺表格排序 |
| **GO/KEGG 富集** | `/enrichment/{go,kegg}` | 🟡 | **页面直连后端，契约匹配，功能可用**；见 §3.1 |
| **系统发育树** | `/visualization/phylotree`、`PhyloTreeViewer` | 🟢 | 功能完整（1459 行组件） |
| **蛋白 3D** | `ProteinStructureViewer` | 🟢 | 3Dmol.js，本地优先 + CDN 降级 |
| **AI 对话** | `ChatWidget`（全局） | 🟢 | 已对接 `ai/chat/` |

---

## 2. 逐项明细

### 2.1 🟢 已有且完善（仅样式微调）

| 功能 | 路由/组件 | 接口 | 备注 |
|---|---|---|---|
| 基因组浏览器 | `/genome/jbrowse`、`/genome/igv` | 静态文件代理 | iframe 嵌入 |
| 引物设计 | `/tools/primer-design` | `POST primer_design/` | 已有导出 |
| 系统发育树 | `/visualization/phylotree` | `tf_tree/...` 静态 | 支持 Newick 导入 |
| 蛋白 3D 结构 | `ProteinStructureViewer` | `search_similar_structure/` | 4 种方法 |
| AI 对话 | `ChatWidget` | `POST ai/chat/` | 全局挂载 |
| 数据下载 | `/download` | `download_genome/<id>/<type>` | 6 种文件类型 |
| 关于/联系 | `/about`、`/contact` | — | 纯静态 |
| 可视化（Circos/PPI/热图/CanvasXpress） | `/visualization/*` | — | 部分含硬编码 demo 数据，保留不动 |

### 2.2 🟡 已有但可增强（原地增强，不改数据流）

| # | 功能 | 现状 | 增强动作 |
|:--:|---|---|---|
| 1 | **基因组列表导出** | `BrowseGenomeView` 10 列大表，有排序/分页，**无导出** | 加 CSV 导出按钮（新增 `utils/exportTable.ts`） |
| 2 | **TF 表格** | `TFView` 5 列，有 selection 多选 + 分页×2，**无排序、无导出** | `TF_name`/`TF_class`/`TF_gene`/`TF_genome` 加 `sortable`；加"导出选中行" |
| 3 | **TR 表格** | 同 TFView（近乎复制） | 同上 |
| 4 | **BLAST 结果表** | 有分页+导出，**无排序** | `bit_score`/`e_value`/`identity` 加数值排序 |
| 5 | **表达结果表** | 手写切片分页+CSV/PNG 导出，**无排序** | 改统一分页 + 加排序 |
| 6 | **GO 注释结果表** | 有分页，**无排序、无导出** | 加排序 + 导出 |
| 7 | **KEGG 注释结果表** | **无分页、无排序、无导出** | 三项全补 |
| 8 | **GO 富集结果表** | 有分页，**无排序、无导出** | 加排序 + 导出 |
| 9 | **KEGG 富集结果表** | 有分页，**无排序、无导出**；缺 i18n 键 | 加排序 + 导出；补 `pvalue` 键 |
| 10 | **Synteny 结果表** | **无分页、无排序、无导出** | 三项全补 |
| 11 | **Gene Location 表** | 有导出，**无排序、无分页** | 加排序 + 分页 |
| 12 | **Region Search 表** | **无排序、无分页、无导出** | 三项全补 |
| 13 | **HTTP 调用统一** | 3 处裸 `axios` 绕过 `httpInstance` | 改用 `apiPost`（`KeggAnnotationResultView:125`、`GoEnrichmentResultView:224`、`KeggEnrichmentResultView:183`）|
| 14 | **检索链路统一** | `meiliSearchApi.ts`（`search/`）与 `meilisearch.js`（`search_genes_meilisearch/`）并存 | 阶段 2 统一，暂不删旧文件 |
| 15 | **i18n 缺口** | zh 缺 `gene`；41 个键两文件皆缺 | 随模块逐个补齐 |

### 2.3 🔴 缺失（新增模块 + mock）

| # | 模块 | 路由 | 数据来源 | 说明 |
|:--:|---|---|---|---|
| 1 | **Homology / Orthogroup** | `/homology`（新） | **mock**（OrthoFinder 无产物） | 阶段 3 重点，见 §4 |
| 2 | **Variome** | `/variome`（新） | mock | 变异浏览/检索 |
| 3 | **Phenome** | — | 后端无支撑 | 仅列入 BACKEND_PROMPT，**本阶段不建前端** |
| 4 | **全局搜索框组件** | 组件 | 复用现有 `search/` | 阶段 2 先做 UI + 路由跳转 |
| 5 | **统一 API 层** | `src/api/index.js` | — | 阶段 2，每接口一函数 + mock 开关 |
| 6 | **序列下载页** | `/download`（增强） | 已有文件路径 | 阶段 3.4 |

---

## 3. 关键发现（含对我此前判断的更正）

### 3.1 ⚠️ 更正：富集分析**并非"必然失败"**

我在阶段 0 报告中称"富集分析前后端参数名不匹配、功能必然失败"。**经逐行核实，该结论部分错误**，更正如下：

| 项 | 我此前的说法 | 核实后的事实 |
|---|---|---|
| 调用路径 | 前端走 `enrichment.ts` 的 `runEnrichment`，发 `gene_list`/`p_value`/`q_value` | **页面不调 `runEnrichment`**。`GoEnrichmentResultView.vue:216-226` **直接用 axios 调接口**，发 `gene_id`/`genome_id`/`p_value_threshold` |
| 后端契约 | 读 `gene_id` | 确实读 `gene_id`（`gene_Go.py:206`），**与页面发送一致** |
| 同步/异步 | 未区分 | **后端是同步的**（返回 `{status:'success', data:{results:[...]}}`，**无 `task_id`**） |

**真实问题**：`enrichment.ts` 里有约 90 行**无人调用的死代码**——`runEnrichment` / `pollEnrichmentResults` 基于 `useAsyncTask` 的异步轮询机制，还引用了两个**后端根本不存在**的端点：
- `/CottonOGD_api/go_enrichment_results/:taskId/`
- `/CottonOGD_api/kegg_enrichment_results/:taskId/`

**结论**：GO/KEGG 富集**功能可用**，无需改动数据流。按你的指示归为 🟡。我在阶段 3 会做的事是：清理这段死代码 + 给结果表加排序/导出，**不碰页面的直连调用逻辑**。

### 3.2 表格能力现状（阶段 3 的主要工作量）

已精确统计，非估算：

| 页面 | sortable | el-pagination | 导出 |
|---|:---:|:---:|:---:|
| `BrowseGenomeView` | ✅ 4 列 | ✅ | ❌ |
| `TFView` / `TRView` | ❌ | ✅ ×2 | ❌ |
| `GoEnrichmentResultView` | ❌ | ✅ | ❌ |
| `KeggEnrichmentResultView` | ❌ | ✅ | ❌ |
| `GoAnnotationResultView` | ❌ | ✅ | ❌ |
| `KeggAnnotationResultView` | ❌ | ❌ | ❌ |
| `GenomeSyntenyView` | ❌ | ❌ | ❌ |
| `RegionSearchView` | ❌ | ❌ | ❌ |
| `GeneLocationView` | ❌ | ❌ | ✅ |
| `GeneExpressionResultView` | ❌ | 手写切片 | ✅ |

**全项目 0 处列筛选（`filters`/`filter-method`）、0 处行点击。**

### 3.3 前后端契约缺口（写进 BACKEND_PROMPT）

**A. 后端有路由但视图不可调用（2 个）**

| 接口 | 原因 |
|---|---|
| `search_genes/` | 绑定到 4 参数内部函数 `search_genes(query, limit, offset, genome_id)`，无视图装饰器 → `TypeError` |
| `Id_map/` | `@api_view(['POST'])` 被注释（`location_ID.py:28`），函数需 2 个位置参数 → `TypeError` |

**B. 后端存在但必然 500（1 个）**

| 接口 | 原因 |
|---|---|
| `search_by_genome_location/` | `.values('geneid_id', ...)` 引用被 migration `0044` 删除的字段（已核实 `0044` 第 27 行 `name="geneid_id"`，`models.py:240` 已注释掉） |

**C. 前端调用但后端无路由（4 个）**

| 位置 | 路径 |
|---|---|
| `components/home/NewsBox.vue:21` | `/CottonOGD_api/news/`（已静默降级，实测返回 SPA HTML 而非 JSON） |
| `stores/modules/enrichment.ts:137,165` | `go_enrichment_results/:taskId/`、`kegg_enrichment_results/:taskId/`（死代码，见 §3.1）|
| `views/sequence/IdSearchResultsView.vue:1326` | `GET /CottonOGD_api/gene_expression/` |

**D. 已知数据契约坑（对接时规避，不改后端）**

| 坑 | 影响 | 前端规避方式 |
|---|---|---|
| `Id_map` 用 `_` 拼 `search_id`，`GeneMaster.alias` 用 `::` 拼 | `db_id` 恒为 `None` | **一律传 `db_id`**，不用 `gene_id` 调 `extract_seq`/`extract_expression` |
| `extract_expression.heatmap_image` 是裸 base64；`expression_EFP_image.image` 带 `data:image/png;base64,` 前缀 | 两处前缀不一致 | 封装时统一补/剥前缀 |
| `regions_info[*].value` 类型不稳定（`float` / `"NA"` / `"No Polygon"` / `"Invalid Polygon"`） | 直接取值会显示脏字符串 | 渲染前做类型判断 |
| `go_annotation` 结果含废弃字段 `dddd`（与 `Gene_Ontology` 同值） | 误用会脏 | 不用该字段 |
| 响应包裹格式至少 5 种：`{success}`/`{message,code}`/`{status,data}`/`{status,results}`/`{error}` | 统一拦截器会误判 | **逐接口适配**，不做全局抽象 |
| 字符串化 JSON 与真对象混杂 | 误 `JSON.parse` 会抛 | `get_species_info.species_info`、`get_family_info.*`、`blast_cmd.results[*]` 需 parse；`geneid_*` 系列**不要** parse |

---

## 4. Homology / Orthogroup 模块方案（已确认走 mock）

### 4.1 数据现状（已核实）

- `WorkFile/config.yaml:100-103` → `orthofinder.enabled: false`（注释 "placeholder only"）
- **不存在**任何 OrthoFinder 产物：`Orthogroups.tsv` / `Orthogroups_SingleCopyOrthologues.txt` / `Statistics_Overall.tsv` 等均无
- `WorkFile/results` 目录整体缺失；二进制路径 `/data/wbliu/soft/Orthofinder3.2/...` 在本机不存在
- 历史：`.pyc` 显示 `Orthogroups` 表曾建（`0002`，`col_0`…`col_37` 共 38 列宽表）后删（`0016_delete_orthogroups`）
- 首页 `HomeView.vue:67` 的 "15,000+ Orthogroups" **无数据来源**

### 4.2 实施计划（阶段 3.3）

1. **新建 `src/mock/orthogroups.ts`**：预置 orthogroup 列表、单拷贝基因、物种矩阵统计
2. **新建 `src/views/homology/HomologyView.vue`** + 路由 `/homology`
3. **新建 `src/views/homology/OrthogroupDetailView.vue`** + 路由 `/homology/:ogId`
4. **在 `src/api/index.js` 预留接口函数**（默认走 mock，开关一行切换）：
   - `getOrthogroups(params)` → 后端缺失，建议 `GET /CottonOGD_api/orthogroups/`
   - `getOrthogroupDetail(ogId)` → 后端缺失，建议 `GET /CottonOGD_api/orthogroups/<og_id>/`
   - `getSingleCopyGenes(params)` → 后端缺失，建议 `GET /CottonOGD_api/orthogroups/single_copy/`
5. **表格能力**：orthogroup 列表支持排序（基因数/物种数）、分页、CSV 导出；详情页支持点击展开基因列表
6. **替换首页占位数字**：改为从 mock 派生，标注数据来源

### 4.3 ⚠️ ID 格式冲突（需提前规划）

- OrthoFinder 输出 ID 格式：`OG0000000`
- vendored 的 gbdraw 解析格式：`og_<N>`（见 `protein_colinearity.py:1161`：`orthogroup_id = f"og_{component_index}"`）
- **不写转换器则无法对接**，将在 BACKEND_PROMPT 中明确规格

### 4.4 eggNOG 不可顶替

`models.py:301` 的 `eggnog_og` 是 **eggNOG orthologous group**，与 OrthoFinder orthogroup 是**不同来源、不同构建方法**，不可混用或冒充。mock 数据中会明确标注，避免误导。

---

## 5. 阶段 2 衔接

| 交付物 | 路径 | 说明 |
|---|---|---|
| 统一请求层 | `src/api/index.js` | 每接口一函数，内部 `USE_MOCK` 开关 |
| 响应适配 | 内嵌于 `src/api/index.js` | 统一包装为 `{ code, message, data }`，后端将来按此实现 |
| 全局搜索框 | `src/components/search/GlobalSearch.vue` | 先 UI + 路由跳转；目录 `components/search/` 当前为空 |
| 表格导出工具 | `src/utils/exportTable.ts` | 供 §2.2 的 8 个页面复用 |
| 分页统一 | `src/composables/core/useTablePagination.ts` | 收敛手写切片/手写页码 |

**注意**：`src/api/index.js` 定为 `.js` 是按你的任务书原文要求；项目新代码规范推荐 `.ts`（见 skill 中 `utils/api.ts`）。若你希望统一用 TS，我改成 `src/api/index.ts`，**请告知**，否则我按 `.js` 交付。
