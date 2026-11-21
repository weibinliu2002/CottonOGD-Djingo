# CottonOGD 比较基因组学（Orthogroup / Ortholog / HOG）v1 接口交接与前端对接文档

- 版本：v2.0（2026-11-21）
  - v2.0：全站前端 API 已迁移到 `/CottonOGD_api/api/v1/`，本文按 **v1 实际部署实现** 重写；
    旧版 v1.1（2026-11-20）中的 `/CottonOGD_api/orthofinder/*` 路径已全部失效。
  - 权威契约：服务器 `backend/docs/api/`（`endpoints.md` / `migration-map.md` / `errors.md` / `files.md`），
    已逐字镜像到本仓库 `frontend/docs/api/`，与服务器文件逐字节一致。
  - 本文在服务器文档之外，补充了**前端实测得到的字段细节、语义约束与差异清单**。
- 后端：Django 5.2 + DRF，daphne `mysite.asgi:application`（部署机 0.0.0.0:8000，nginx 反代）。
- 适用数据：OrthoFinder 3.2 输出，258 个物种、121,061 个 OG。
- 读者：前端开发者（本文）、后端开发者（差异清单见第 8 节）。

> **最重要的一条语义**
> **“同一个 OG”不等于“互为 Ortholog”。** 同一 OG 只是同源基因簇；真实的直系同源/旁系同源关系
> 只来自 OrthoFinder 的 `Orthologues/` 输出，在 v1 中对应 `orthofinder/genes/orthologs/`。
> 因此：
> - 展示“共同出现的 OG / 同组基因”时使用 `genes/orthogroups`、`orthogroups/detail`、
>   `orthogroups/members`、`genome-pairs`；
> - 展示“直系同源”时**只能**使用 `genes/orthologs`。

---

## 0. 事实来源与验证方式

本文的事实分三类，阅读时请注意区分：

1. **服务器接口文档（权威契约）**：`frontend/docs/api/*`，与服务器
   `/data/web/CottonOGD/OGD/backend/docs/api/*` 逐字节一致（`cmp` 校验通过）。
2. **2026-11-21 实测**：经本地 dev server（`localhost:5713`，vite 代理到 `DJANGO_TARGET`）
   对真实后端发起请求，记录真实响应字段。文中“实测”字样均指此类。
3. **前端代码事实**：`frontend/src/api/index.ts` 的封装与组件调用，均可在代码中核对。

实测命令统一加 `--noproxy '*'`（本机系统代理访问不了内网/线上后端）：

```bash
curl -s --noproxy '*' "http://localhost:5713/CottonOGD_api/api/v1/orthofinder/meta/"
```

---

## 1. 全局约定（v1）

- 前缀：`/CottonOGD_api/api/v1/`，下文省略前缀，只写 `orthofinder/...`。
- **统一信封**：所有 v1 JSON 接口返回 `{ "code": 0, "message": "ok", "data": ... }`。
  - 成功 `code = 0`（HTTP 200/201）；失败 `code` 为非零业务码，`data` 为 `null` 或补充信息。
  - `HTTP 状态码 = code // 100`（`40401 → 404`，`40002 → 400`）。
  - 前端 `src/utils/http.js` 的响应拦截器已统一解包为 `data`；`src/utils/api.ts` 的泛型即业务数据类型。
    组件里**不要**再判断 `code` 字段。
- 参数：GET 用 query string；POST 既可用 JSON body，也可用 query string / form body。
- 分页：`limit` + `offset`；响应通常带 `total`/`limit`/`offset`/`has_more`（列表类端点）。
- 错误码：`40001` 参数缺失、`40002` 参数非法、`40401` 资源不存在、`40901` 冲突、
  `42901` 限流、`5xx01` 服务端错误等，完整清单见 `docs/api/errors.md`。
- 认证：业务数据域全部**公开**（匿名可访问）；`ai/chat/` 需要会话。
  匿名会话：`POST auth/session/` → `data.{uuid,token}`，同时种 HttpOnly cookie；账号 JWT 走 `Authorization: Bearer`。
- **文件类端点**（`og/<og>/sequences|msa|tree/`）返回**原始字节/文本**，不是信封；
  后端在文件缺失时返回 JSON 404（仍是信封结构，见第 6 节）。
- 旧路径（无 `/api/v1/`）**没有双挂载**：旧 GET 会落到前端 SPA 兜底页（HTTP 200 + HTML），
  旧 POST 返回 405。排查时不要被 200 误导。

---

## 2. 端点总表（orthofinder 域）

| 方法 | v1 路径 | 参数 | `data` 结构（实测） |
|---|---|---|---|
| GET | `orthofinder/meta/` | — | `{ species: [{name, alias, Cotton_Species, Genome_type, Category}] }` |
| POST | `orthofinder/genes/orthogroups/` | `geneid` | `{query_gene, found, orthogroups:[...]}` |
| POST | `orthofinder/genes/orthologs/` | `geneid`、`species`?、`partner_species`?、`og_code`? | `{query_gene, found, partner_species, results:[...]}` |
| POST | `orthofinder/genes/hogs/` | `geneid`、`species`? | `{query_gene, found, hogs:[...]}` |
| POST | `orthofinder/orthogroups/search/` | `species`、`mode`、`og_code`、`og_code_like`、`min_genes`/`max_genes`、`min_species`/`max_species`、`min_selected_species`/`max_selected_species`、`sort`、`limit`、`offset` | `{found, mode, species, filters, total, limit, offset, has_more, orthogroups:[...]}` |
| POST | `orthofinder/orthogroups/detail/` | `og_code`、`species`?、`include_genes` | `{found, og_code, species_count, selected_species_count, gene_count, is_single_copy, relation_type, species_members:[...]}` |
| POST | `orthofinder/orthogroups/members/` | `og_code`、`limit`、`offset` | `{found, og_code, members:[...], total, limit, offset, has_more}` |
| POST | `orthofinder/hogs/detail/` | `hog_id`（**注意**：服务器文档写的是 `hog_code`，见第 8 节） | `{found, hog_id, node, og_code, parent_clade, species_count, gene_count, members:[{species, genes, n}]}` |
| POST | `orthofinder/genome-pairs/` | `genome_a`、`genome_b`、`og_code`?、`limit`、`offset` | `{found, genome_a, genome_b, relationship, note, orthogroups:[...], total, limit, offset, has_more}` |
| GET | `orthofinder/species/tree/` | `fmt=newick` 或 `include_nodes` | 默认 JSON：`{newick, root, leaf_count, leaves, leaf_parent, nodes:[...]}` |
| GET | `orthofinder/statistics/` | `type`、`kind`、`species_a`、`species_b`、`scope`、`og_code` | 随 `type` 变化，见 3.11 |
| GET | `orthofinder/og/<og>/sequences/` | — | **FASTA 原始字节**（非信封） |
| GET | `orthofinder/og/<og>/msa/` | — | **MSA FASTA 原始字节**（非信封） |
| GET | `orthofinder/og/<og>/tree/` | — | **Newick 原始文本**（非信封） |
| GET | `orthofinder/og/<og>/tandem/` | `limit`、`offset`、`include_events` | `{og_code, by_type, species, total_events, limit, offset, has_more, events:[...]}` |

聚合统计端点（前端目前未使用，可作为首屏优化）：
`GET meta/orthofinder/statistics/?sections=overall,per_species,duplications&kind=...`
→ `{type, sections:[...], overall:{raw, kv}, per_species:{species, metrics}, duplications:{tree_nodes}}`（实测）。

---

## 3. 逐端点细节

### 3.1 物种列表 `orthofinder/meta/`

实测每个物种：`{name, alias, Cotton_Species, Genome_type, Category}`。
`name` 是接口里所有 `species` 参数应使用的值（如 `G.turneriD10_NCF_v1.2`），
`alias` 仅供展示（如 `G.turneri(D10)_NCF_v1.2`）。

前端：`getOrthofinderMeta()` → `OrthologView` 左侧基因组树按 `Genome_type` 分组。

### 3.2 按物种筛选 OG `orthogroups/search/`

参数（与旧版一致的部分不再重复）：

| 参数 | 说明 |
|---|---|
| `species` | 物种名数组（JSON 数组或重复参数） |
| `mode` | `all` = 交集（默认），`any` = 并集 |
| `og_code` / `og_code_like` | OG 编号精确 / 模糊 |
| `min_genes`/`max_genes`、`min_species`/`max_species` | 基因数 / 物种数范围 |
| `min_selected_species`/`max_selected_species` | 所选物种覆盖数范围 |
| `sort` | 默认 `selected_species`；实测 `-gene_count` 等带负号排序可用 |
| `limit` / `offset` | 分页 |

实测响应：

```json
{
  "found": true, "mode": "all", "species": ["G.turneriD10_NCF_v1.2"],
  "filters": {"og_code": null, "sort": "selected_species", "...": "..."},
  "total": 36590, "limit": 3, "offset": 0, "has_more": true,
  "orthogroups": [
    {"og_code":"OG0013470","n_sp":1,"gene_count":66532,"species_count":228,"is_single_copy":false}
  ]
}
```

- **字段名差异**：v1 用 `n_sp` 表示“所选物种覆盖数”，`orthogroups/detail` 用
  `selected_species_count`。前端 `getOrthologBySpecies` 已统一映射为 `selected_species_count`
  （`row.selected_species_count ?? row.n_sp`），组件只读前者。
- `is_single_copy` 为严格定义（见第 5 节），当前数据恒为 `false`。

### 3.3 OG 详情 `orthogroups/detail/`

实测：

```json
{
  "found": true, "og_code": "OG0013470", "species_count": 228,
  "selected_species_count": null, "gene_count": 66532, "is_single_copy": false,
  "relation_type": "many_to_many",
  "species_members": [{"species": "...", "display_name": "...", "n": 2868}]
}
```

- 传 `species` 时 `species_members` 只含这些物种，`selected_species_count` 为覆盖数。
- `include_genes: 0` / `false` 时成员行**不带 `genes`**，只给 `n`；适合大 OG 首屏。
- `relation_type` 取值实测有 `many_to_many` 等；含义为 OG 内所选物种间的拷贝数关系，
  **不是**单基因的 ortholog 关系。

### 3.4 成员平铺分页 `orthogroups/members/`

实测：

```json
{
  "found": true, "og_code": "OG0013470",
  "members": [
    {"species":"...","display_name":"...","ortho_gene":"Gano_01G016940.1","genemaster_geneid":"Gano_01G016940"}
  ],
  "total": 66532, "limit": 3, "offset": 0, "has_more": true
}
```

- `ortho_gene`：OrthoFinder 蛋白 ID（**带转录本后缀**），基因级接口只认它。
- `genemaster_geneid`：映射到 GeneMaster 的基因 ID（无后缀；可能为 `null`）。
- 大 OG（如 66,532 个成员）必须分页，前端每页 50。

### 3.5 基因 → 所属 OG `genes/orthogroups/`

实测：`{query_gene, found, orthogroups:[{og_code, species_count, gene_count, is_single_copy,
relation_type, species_members:[{species, display_name, n, genes:[{ortho_gene, genemaster_geneid}]}]}]}`。

**ID 规则（实测，重要）**：只接受带转录本后缀的 OrthoFinder ID
（`Gano_01G016940.1` → `found:true`；`Gano_01G016940` → `found:false`）。
前端 `resolveOrthoGeneId()` 在未命中且无后缀时自动补 `.1` 重试一次。

### 3.6 基因 → 真实直系同源 `genes/orthologs/`

实测：

```json
{
  "query_gene": "Gano_01G016940.1", "found": true, "partner_species": null,
  "results": [{
    "species": "G.anomalumB1_HAU_v1",
    "orthogroups": [{
      "og_code": "OG0013470",
      "partners": [{"species":"G.arboreumA2_DC089_HAU_v1","genes":["Chr03012610.1"],
                    "query_gene_count":1,"partner_gene_count":1,"relation_type":"one_to_one"}]
    }]
  }]
}
```

- 来源是 OrthoFinder `Orthologues/` 输出，是唯一可信的 Ortholog 关系。
- `relation_type` 取值形如 `one_to_one` / `many_to_one`（下划线），与统计接口的
  `one-to-one`（连字符）**不是同一套词汇**，不要混用。
- 可选 `species`（限定结果物种）、`partner_species`（只看某个对照物种）、`og_code`（限定 OG）。

### 3.7 基因 → 最深 HOG `genes/hogs/` 与 HOG 详情 `hogs/detail/`

`genes/hogs/` 实测：`{query_gene, found, hogs:[{species, hog_id, node, og_code, parent_clade,
species_count, gene_count}]}`，`hog_id` 形如 `N42.HOG0000008`。

`hogs/detail/` 实测：`{found, hog_id, node, og_code, parent_clade, species_count, gene_count,
members:[{species, genes:[...], n}]}`。

- 传 `hog_id` 可用；传服务器文档写的 `hog_code` → `40001 hog_id is required`（第 8 节差异 1）。
- HOG 是 OrthoFinder 层次化直系同源分组，展示时必须与“基因级 Ortholog”区分文案。

### 3.8 两个基因组共享 OG `genome-pairs/`

实测：

```json
{
  "found": true, "genome_a": "...", "genome_b": "...",
  "relationship": "shared_orthogroup_members",
  "note": "同一 OG 的成员不自动互为 Ortholog，真实 Ortholog 请查询 /v1/orthofinder/genes/orthologs/",
  "orthogroups": [{"og_code":"OG0013470","gene_count":66532,"species_count":228,
                   "genes_a":["..."],"genes_b":["..."]}],
  "total": 1, "limit": 2, "offset": 0, "has_more": false
}
```

- 语义是“同一 OG 的成员”，UI 必须按“共享 OG”表述并展示后端 `note`。

### 3.9 物种树 `species/tree/`

- 默认返回 JSON：`{newick, root, leaf_count, leaves:[...], leaf_parent:{leaf: parent}, nodes:[{id, parent, is_leaf, branch_length, ancestors}]}`（实测）。
- `fmt=newick` 返回纯文本 Newick。
- 前端 `getSpeciesTree()` 使用默认 JSON。

### 3.10 基因复制事件 `og/<og>/tandem/`

实测：汇总始终全量，`events` 明细分页。

```json
{
  "og_code": "OG0013470",
  "by_type": {"Terminal": 2, "Non-Terminal": 3},
  "species": {"G.barbadenseAD2_3-79_HAU_v1": [{"geneid": "...", "n": 1}]},
  "total_events": 5, "limit": 2, "offset": 0, "has_more": true,
  "events": [{"species": "...", "type": "Terminal", "support": 1.0, "gene_tree_node": "...",
              "genes1": ["..."], "genes2": ["..."]}]
}
```

- `include_events=0` → 只取汇总。
- 无复制事件时后端返回 `{}`；前端 `getOrthofinderTandem()` 返回 `null`，组件显示空态。
- 复制事件最多的 OG 有 9,846 条（旧版一次性 186 MB），必须分页取明细。

### 3.11 统计 `statistics/`

`type` 合法值（实测）：`overall`、`per_species`、`orthologs`、`duplications`、`species_overlaps`。
未知 `type` → `40002 未知统计类型：<type>`。

| type | 额外参数 | data 结构（实测） |
|---|---|---|
| `overall` | — | `{type, raw, kv:{<英文指标名>: <字符串>}}` |
| `per_species` | — | `{type, species:[...], metrics:[{metric, values:[...]}]}`（实测 94 个指标） |
| `orthologs` | `kind`、`species_a`、`species_b` | 见下 |
| `duplications` | `scope`、`og_code` | 见下 |
| `species_overlaps` | — | `{type, available:false, error:"<说明>"}`（本次运行未生成该文件） |

`orthologs`：
- `kind ∈ {one-to-one, one-to-many, many-to-one, many-to-many, totals}`，默认 `totals`；
  未知 `kind` → `40401`（注意与未知 type 的 40002 不一致，第 8 节差异 3）。
- 不带 `species_a`/`species_b`：`{type, kind, species:[...], matrix:{sp:{sp:"<数值字符串>"}}}`
  —— 258×258 全矩阵，前端必须**按需**加载（`OrthofinderStatistics` 提供“加载完整矩阵”按钮）。
- 带 `species_a`+`species_b`：`{type, kind, species_a, species_b, value:"24294.0"}`
  —— `value` 是**字符串**，前端原样展示。

`duplications`：
- `scope=species_node`：`{type, scope, rows:[{node, all, support_50}]}`。
- `scope=orthogroup` + `og_code`：`{type, scope, og_code, value:{all, support_50}}`
  —— `value` 是**对象**，不是字符串。
- `scope=orthogroup` 不带 `og_code`：`{type, scope, rows:{<og_code>:{all, support_50}, ...}}`
  —— **8 万余个 OG 的字典**，无分页参数；前端只展开前 200 行并提示总数。
- 未知 `scope` 被后端静默忽略并回退为上面的全量字典（应报 40002，第 8 节差异 3）。

`overall.kv` 为 `Comparative_Genomics_Statistics/Comparative_Genomics_Statistics.tsv`
的键值对原文（英文指标名，含基因数/物种数分布直方图键如 `<1`、`1001+`、`1`..`258`），
前端**原样展示**，不在前端重算。

---

## 4. 字段字典（易混点）

| 字段 | 出现位置 | 含义 |
|---|---|---|
| `n_sp` | `orthogroups/search` 行 | 所选物种覆盖数（v1 命名） |
| `selected_species_count` | `orthogroups/detail` | 同上（详情端点命名）；未传 species 时为 `null` |
| `species_count` | search / detail / HOG / genome-pairs | OG 或 HOG 覆盖的全部物种数 |
| `ortho_gene` | members / genes/orthogroups | OrthoFinder 蛋白 ID，**带转录本后缀**，基因级接口只认它 |
| `genemaster_geneid` | members | GeneMaster 基因 ID（无后缀，可能为 null） |
| `gene_count` | search / detail | OG 内基因总数（非物种数） |
| `is_single_copy` | search / detail | 严格单拷贝（258 物种全覆盖且每物种 1 基因），当前恒为 false |
| `relation_type` | detail / orthologs | 详情为 OG 内拷贝关系；orthologs 为 `one_to_one` 等下划线词汇 |
| `hog_id` | genes/hogs / hogs/detail | 形如 `N42.HOG0000008` |
| `by_type` | tandem | `{Terminal, Non-Terminal}` 事件计数 |

---

## 5. 数据规模与口径

以下为数据方法学事实（来源：`docs/Orthogroup升级_现状审查报告.md`，后端构建索引时统计；
本文未在 2026-11-21 重新全量核对，故标注为“报告口径”）：

| 指标 | 数值 | 来源 |
|---|---|---|
| 物种数 | 258 | 报告口径；`statistics?type=overall` 实测同值 |
| OG 数 | 121,061 | 同上 |
| OG 内基因数 | 17,156,178 | 同上 |
| 严格单拷贝 OG | **0** | 实测 `overall.kv["Number of single-copy orthogroups"] = "0"` |
| 全部 258 物种共有的 OG | 10 | 实测 `overall.kv["Number of orthogroups with all species present"] = "10"` |
| 有 MSA 的 OG | 100,453 | 报告口径 |
| 有解析基因树的 OG | 84,829 | 报告口径 |

口径约束：

- 严格单拷贝 = 覆盖全部 258 物种且每物种恰好 1 个基因；当前为 0，
  前端**按实际值显示 0**，不做任何“修正”或隐藏。
- MSA / 基因树缺失是常态（多数 OG 没有），前端按“模块暂未就绪”处理，不视为错误。

---

## 6. MSA、基因树与序列

| 端点 | 正常响应 | 缺失响应（实测） |
|---|---|---|
| `og/<og>/sequences/` | FASTA 原始字节 | HTTP 404 + 信封 `{code:40401, message:"OG 没有 sequences 文件", data:{og_code}}` |
| `og/<og>/msa/` | FASTA 原始字节（实测 OG0013470 约 147 KB） | HTTP 404 + 信封 `{code:40401, message:"OG 没有 msa 文件", ...}` |
| `og/<og>/tree/` | Newick 原始文本 | HTTP 404 + 信封 `{code:40401, message:"OG 没有解析树（Resolved_Gene_Trees 未生成）", ...}` |

前端实现（`OrthogroupAnalysis.vue`）：

- 三个模块**按需加载**（点击按钮才请求），大 OG（`gene_count > 300`）额外确认后才加载 MSA。
- 请求失败/404 → 显示“暂未就绪”提示，不缓存失败结果，不阻塞其他页签。
- MSA 下载与序列下载直接指向文件端点（浏览器直链，避免把大文件读进内存）；
  基因树下载用已加载的 Newick 文本生成 Blob。
- 基因树渲染复用 `PhylocanvasViewer.vue`（Phylocanvas.gl）；MSA 渲染复用 `MsaViewer.vue`。

---

## 7. 前端对接映射（`src/api/index.ts`）

| 前端函数 | v1 端点 | 使用位置 |
|---|---|---|
| `getOrthofinderMeta` | `GET orthofinder/meta/` | `OrthologView` 基因组树 |
| `getOrthologByGene` | `POST genes/orthogroups/` | 详情页“按基因查 OG” |
| `resolveOrthoGeneId` | 内部两次 `genes/orthogroups/` | 基因级查询的 ID 归一 |
| `getGeneOrthologs` | `POST genes/orthologs/` | `OrthogroupAnalysis` 直系同源页签 |
| `getGeneHog` / `getHogDetail` | `POST genes/hogs/`、`hogs/detail/` | HOG 页签 |
| `getOrthologBySpecies` | `POST orthogroups/search/` | `OrthologView` 主表 |
| `getOrthogroupDetailV2` | `POST orthogroups/detail/` | 概览页签 |
| `getOgMembers` | `POST orthogroups/members/` | 成员页签（分页） |
| `getGenomePair` | `POST genome-pairs/` | 统计面板“共享 OG” |
| `getSpeciesTree` | `GET species/tree/` | 物种树展示 |
| `getOrthofinderStatistics` | `GET statistics/` | `OrthofinderStatistics` |
| `getOrthogroupSequence` / `getOrthogroupMsa` / `getOrthogroupTree` | `GET og/<og>/{sequences,msa,tree}/` | 序列 / MSA / 基因树页签 |
| `getOrthofinderTandem` | `GET og/<og>/tandem/` | 复制事件页签（汇总 + 分页） |

---

## 8. 与服务器文档/实现的差异，及待后端修正项

以下均为 2026-11-21 实测发现，供后端修正文档或实现（前端已按实测行为对接）：

1. **`hogs/detail/` 参数名**：`docs/api/endpoints.md` 写 `hog_code`，部署实现读 `hog_id`；
   传 `hog_code` 返回 `40001 hog_id is required`。前端使用 `hog_id`。
2. **`species_overlaps` 不可用**：本次 OrthoFinder 运行未生成 `Orthogroups_SpeciesOverlaps.tsv`，
   接口返回 `{available:false, error:"..."}`；前端显示“不可用”。需后端补跑/补生成该文件。
3. **统计接口错误码不一致**：未知 `type` → `40002`，未知 `kind` → `40401`；
   未知 `scope` 被**静默忽略**并回退为全部 OG 字典。建议统一为 `40002`。
4. **基因级接口的 ID 规则未写进文档**：`genes/orthogroups|orthologs|hogs` 只接受带转录本后缀的
   OrthoFinder ID。建议在 `endpoints.md` 明确，避免前端反复踩坑。
5. **`duplications` 全量 `rows` 无分页**：`scope=orthogroup` 不带 `og_code` 时返回 8 万余个 OG 的字典，
   单次响应很大；建议增加 `limit`/`offset` 或提供分页端点。
6. **旧路径未双挂载**：无 `/api/v1/` 的旧 URL 返回 SPA HTML 或 405，排查时容易误判为接口正常。
7. **`tf_tree` 仍在旧路径**：`/CottonOGD_api/tf_tree/tree/genome/<genome>/{TF,TR}/<name>.treefile`
   不在 v1 文档的非信封端点清单里，但实际仍在服务（基因树可视化依赖它）。建议补进 `files.md`。

---

## 9. 测试数据与调用示例

```bash
# 物种列表
curl -s --noproxy '*' "http://localhost:5713/CottonOGD_api/api/v1/orthofinder/meta/"

# 按物种筛选（交集）
curl -s --noproxy '*' -X POST \
  -H 'Content-Type: application/json' \
  -d '{"species":["G.turneriD10_NCF_v1.2"],"mode":"all","limit":5}' \
  "http://localhost:5713/CottonOGD_api/api/v1/orthofinder/orthogroups/search/"

# OG 详情（只要计数，不返回成员基因）
curl -s --noproxy '*' -X POST -H 'Content-Type: application/json' \
  -d '{"og_code":"OG0013470","include_genes":0}' \
  "http://localhost:5713/CottonOGD_api/api/v1/orthofinder/orthogroups/detail/"

# 基因级直系同源（必须带 .1 后缀）
curl -s --noproxy '*' -X POST -H 'Content-Type: application/json' \
  -d '{"geneid":"Gano_01G016940.1"}' \
  "http://localhost:5713/CottonOGD_api/api/v1/orthofinder/genes/orthologs/"

# 统计：两个物种的直系同源对数
curl -s --noproxy '*' "http://localhost:5713/CottonOGD_api/api/v1/orthofinder/statistics/?type=orthologs&species_a=G.anomalumB1_HAU_v1&species_b=G.arboreumA2_DC089_HAU_v1"

# 物种树（Newick）
curl -s --noproxy '*' "http://localhost:5713/CottonOGD_api/api/v1/orthofinder/species/tree/?fmt=newick"
```

---

## 10. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-11-19 | 初版：旧 `/orthofinder/*` 8 个接口 + C.9–C.15 扩展 |
| v1.1 | 2026-11-20 | tandem 明细分页、tree JSON 404、genome_pair 性能优化 |
| v2.0 | 2026-11-21 | 全站迁移 v1；按部署实现重写全部路径/参数/响应；补实测差异与待修正项 |