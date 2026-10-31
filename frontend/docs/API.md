# CottonOGD 前端 API 接口文档

> 本文面向前端对接与后端实现，按「已有且已对接 / 已有但格式需微调 / 缺失需新开发」三类组织。
> 所有业务接口前缀均为 `/CottonOGD_api/`，开发环境经 Vite 代理到 `DJANGO_TARGET`，
> 生产环境由 Nginx 同源反代。
>
> 统一请求函数集中在 `src/api/index.ts`，页面不直接发请求。

---

## 0. 约定

### 0.1 统一响应格式（前端已封装，后端需对齐）

前端所有请求函数返回统一的 `ApiResult<T>`：

```ts
interface ApiResult<T = unknown> {
  /** 0 表示成功，非 0 表示失败 */
  code: number
  /** 提示信息；失败时为用户可读的错误原因 */
  message: string
  /** 业务数据 */
  data: T
}
```

- `code === 0` 视为成功，其余一律失败。
- 后端返回 Django/DRF 旧格式（如 `{status: 'success', data: {...}}` 或 `{error: '...'}`）时，
  由 `src/api/index.ts` 的适配层转换为上述格式，因此**现有旧接口无需一次性改造**即可继续工作。

### 0.2 mock 开关

后端尚未就绪的接口走 mock 分支，开关集中在 `src/api/index.ts`：

```ts
const MOCK_FLAGS = {
  news: true,               // 后端无 /CottonOGD_api/news/ 路由
  orthogroups: true,        // 后端无 orthogroup 相关路由，且 OrthoFinder 产物不存在
  geneExpression: true,     // 后端无 /CottonOGD_api/gene_expression/（GET）路由
  enrichmentResults: true,  // 后端无 go_enrichment_results / kegg_enrichment_results 路由
}
```

接口就绪后把对应开关置 `false` 即可；也可在 `.env.local` 设 `VITE_USE_MOCK=false` 一次性全部切到真实接口。
**切换时页面代码无需改动。**

### 0.3 认证

- `POST /CottonOGD_api/login/` 返回 `{uuid, token}`，并下发 7 天有效的 HttpOnly Cookie `auth_token`。
- `http.js` 请求拦截器自动带 `X-CSRFToken` 与 `Authorization: Bearer <token>`。
- 响应拦截器遇到 400/401 会自动重新登录并重放原请求（单次，防死循环）。

> 前端页面**不需要**自己处理登录/重试。

---

## 一、已有且已对接（a 类）

后端已存在路由，前端已对接，**本次未改动数据流**。

### 1.1 登录

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/login/` |
| 方法 | POST |
| 请求体 | 无 |
| 响应 data | `{ uuid: string, token: string }` |

```json
{ "code": 0, "message": "", "data": { "uuid": "u-xxx", "token": "t-xxx" } }
```

对应函数：`apiLogin()`

### 1.2 物种信息

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/get_species_info/` |
| 方法 | GET |
| 参数 | 无 |
| 响应 data | `SpeciesInfo[]`（含 name / alias / Genome_type / Cotton_Species / Ploidy / Busco / Genome_size / LAI_value / Article / Assembling_institution 等） |

对应函数：`getSpeciesInfo()`

### 1.3 基因家族信息

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/get_family_info/` |
| 方法 | POST |
| 请求体 | `{ genome_id: string, class: string }`（`class` 取值 `TF` / `TR`） |
| 响应 data | `FamilyInfoResult`（家族列表 + 每个家族的基因数） |

对应函数：`getFamilyInfo(params)`

### 1.4 基因检索汇总 / 结果

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/geneid_summary/` |
| 方法 | POST |
| 请求体 | `{ gene_id, genome_id, request_id }` |

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/geneid_result/` |
| 方法 | POST |
| 请求体 | `{ db_id, request_id }` |

响应中的 `geneid_result` / `gene_info_result` / `search_map` 可能是**字符串化 JSON**，
前端已统一 `JSON.parse` 处理。

对应函数：`getGeneidSummary(payload)` / `getGeneidResult(payload)`

### 1.5 表达量提取

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/extract_expression/tissues/` |
| 方法 | GET |
| 参数 | `genome_id?`（可选） |
| 响应 data | `string[]`（组织列表） |

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/extract_expression/genomes/` |
| 方法 | GET |
| 响应 data | `string[]`（含组织数据的基因组列表） |

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/extract_expression/` |
| 方法 | POST |
| 请求体 | `{ gene_id, genome_id, tissues[], ... }` |

对应函数：`getTissues(genomeId?)` / `getGenomesWithTissue()` / `extractExpression(payload)`

### 1.6 热图重绘

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/regenerate_heatmap/` |
| 方法 | POST |
| 请求体 | 与 `extract_expression/` 相同 |

对应函数：`regenerateHeatmap(payload)`

### 1.7 序列提取

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/extract_seq/` |
| 方法 | POST |
| 请求体 | `{ gene_id, genome_id, ... }` |
| 响应 data | `{ sequence: string }` |

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/extract_seq_gff/` |
| 方法 | POST |
| 请求体 | `{ gene_id, genome_id, ... }` |

对应函数：`extractSeq(payload)` / `extractSeqGff(payload)`

### 1.8 统一检索（经后端代理 Meilisearch）

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/search/` |
| 方法 | POST |
| 请求体 | `{ q, index, offset, limit, withFacets }` |
| 响应 data | `{ hits[], estimatedTotalHits, processingTimeMs }` |

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/get_search_indexes/` |
| 方法 | GET |
| 响应 data | `SearchIndexInfo[]`（uid / label / available） |

前端**不直连** Meilisearch，密钥只在后端。

对应函数：`searchGenes(params)` / `getSearchIndexes()`

### 1.9 AI 对话

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/ai/chat/` |
| 方法 | POST |
| 请求体 | `{ message: string, clear_history?: boolean }` |
| 响应 data | `{ success, answer, tool_calls, history_turns }` |
| 超时 | 120s（LLM 较慢，前端单独放宽） |

历史会话保存在服务端 Redis。

对应函数：`postAiChat(payload)`

---

## 二、已有但格式需微调（b 类）

后端**有路由、也在被前端调用**，但响应格式与统一约定不一致，需要适配。
目前这些不一致已由 `src/api/index.ts` 的适配层兜住，**功能正常**；后续建议后端逐步对齐。

### 2.1 GO / KEGG 注释

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/go_annotation/`、`/CottonOGD_api/kegg_annotation/` |
| 方法 | GET |
| 参数 | `gene_id`（多个用逗号/换行分隔）、`genome_id` |

**现状**：后端返回 `{status: 'success', data: {results, chart_data}}`，
非 `{code, message, data}`；且 `results[].description` 可能是**字符串化 JSON**
（也可能是纯文本，需 try/catch 兜底）。

**建议**：改为统一响应，并把 `description` 固定为对象 `{name, definition}`。

对应函数：`getGoAnnotation(params)` / `getKeggAnnotation(params)`

### 2.2 GO / KEGG 富集

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/go_enrichment/`、`/CottonOGD_api/kegg_enrichment/` |
| 方法 | POST（当前为 `multipart/form-data`） |
| 请求体 | `gene_id`、`genome_id`、`p_value_threshold`、`q_value_threshold` |

**现状**：后端为**同步**接口，直接返回 `{status: 'success', data: {results, plot_images}}`。
前端 `GoEnrichmentResultView.vue` / `KeggEnrichmentResultView.vue` 直接调用并渲染。

**注意**：`src/utils/` 下 `enrichment.ts` 中残留约 90 行**异步轮询死代码**，
引用了两个不存在的端点 `go_enrichment_results/:taskId/` 与 `kegg_enrichment_results/:taskId/`
（对应 `MOCK_FLAGS.enrichmentResults`）。这部分代码当前未被任何页面调用，
若后续富集改为异步，需后端新增这两个端点；否则建议清理死代码。

对应函数：`runGoEnrichment(payload)` / `runKeggEnrichment(payload)`

### 2.3 基因组文件下载

| 项 | 值 |
| --- | --- |
| URL | `/download_genome/<genome_id>/<file_type>`（根级路由，非 `/CottonOGD_api/` 下） |
| 方法 | GET |
| 响应 | 文件流（`Content-Disposition: attachment`） |

`file_type` 与后缀映射（见 `backend/CottonOGD/views/DownloadGenome.py`）：

| file_type | 后缀 |
| --- | --- |
| `genome` | `.genome.fa.gz` |
| `gene` | `.gene_genome.fa.gz` |
| `cds` | `.cds.fa.gz` |
| `protein` | `.pro.fa.gz` |
| `upstream2000` | `.upstream.fa.gz` |
| `gff3` | `.gff.gz` |

> 前端下载页已新增文件类型说明表，文案与上述映射保持一致。

### 2.4 BLAST

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/blast_cmd/` |
| 方法 | POST |
| 请求体 | `{ sequence, type, selected_genomes, data_type, evalue, max_hits, ... }` |
| 响应 | `{ results: { <基因组名>: "<字符串化 JSON 或 XML>" } }` |

**现状**：后端返回 `results` 的**值是字符串**（成功时为 JSON 串，解析失败时回落为 XML 文本）。
`src/api/index.ts` 的 `submitBlast()` 已统一解析：能解析成对象的放入 `results`，
解析失败的原文保留在 `rawResults`，页面不会崩。

**建议**：后端直接返回对象，去掉这层字符串包装。

> 现有 BLAST 页面（`BlastpView.vue` + `stores/modules/blast.ts`）已是完整可用的
> 表单 + 轮询 + 结果页链路，因此**未做 UI 占位**；api 层的 `submitBlast()` 作为
> 统一契约保留，供后续切换使用。

### 2.5 引物设计

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/primer_design/` |
| 方法 | POST |
| 请求体 | `{ sequence, ... }` |
| 响应 data | `PrimerPair[]` |

对应函数：`designPrimers(payload)`

### 2.6 蛋白结构相似性搜索

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/search_similar_structure/` |
| 方法 | POST |
| 请求体 | `{ ... }` |

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/get_search_methods/` |
| 方法 | GET |
| 响应 data | `Record<string, unknown>[]` |

对应函数：`searchSimilarStructure(payload)` / `getSearchMethods()`

### 2.7 EFP 表达图

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/expression_EFP_image/` |
| 方法 | POST |
| 请求体 | `{ genome_id, gene_id, ... }` |

对应函数：`getExpressionEfpImage(payload)`

---

## 三、缺失需新开发（c 类）

前端已写好请求函数并**暂时走 mock**，后端需新增对应路由。
接口就绪后把 `src/api/index.ts` 里对应的 `MOCK_FLAGS` 置 `false` 即可切换，页面无需改动。

### 3.1 新闻/动态列表

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/news/` |
| 方法 | GET |
| 参数 | 无 |
| 状态 | **缺失**。目前前端 `NewsBox` 静默回退到 mock |

**响应 data**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | number | 主键 |
| `title` | string | 标题 |
| `content` | string | 正文（可含简单 HTML） |
| `date` | string | 发布日期，建议 `YYYY-MM-DD` |
| `link` | string \| null | 外链，可为空 |

```json
{
  "code": 0,
  "message": "",
  "data": [
    {
      "id": 1,
      "title": "CottonOGD 数据库正式上线",
      "content": "集成了基因组、转录组与表型数据……",
      "date": "2026-01-15",
      "link": null
    }
  ]
}
```

对应函数：`getNews()`，mock 开关 `MOCK_FLAGS.news`

### 3.2 基因表达量（GET）

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/gene_expression/` |
| 方法 | GET |
| 状态 | **缺失**。前端仅定义了函数，暂无页面调用 |

**参数**：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `gene_id` | string | 是 | 基因 ID，多个用逗号分隔 |
| `genome_id` | string | 是 | 基因组 ID |
| `tissues` | string | 否 | 组织名，多个用逗号分隔 |

**响应 data**：

```json
{
  "code": 0,
  "message": "",
  "data": {
    "gene_id": "Ghir_A01G000010",
    "genome_id": "G.hirsutumAD1_TM-1_HAU_v1.1",
    "tissues": ["root", "stem", "leaf"],
    "values": [[1.2, 3.4, 5.6]]
  }
}
```

对应函数：`getGeneExpression(params)`，mock 开关 `MOCK_FLAGS.geneExpression`

### 3.3 同源分析 Orthogroup

后端目前**完全没有** orthogroup 相关路由；且 OrthoFinder 在
`WorkFile/config.yaml` 中 `enabled: false`，仓库内也无任何产物文件。

新增以下三个接口，`/homology` 页面即可从 mock 切到真实数据。

#### 3.3.1 orthogroup 列表

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/orthogroups/` |
| 方法 | GET |

**参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `keyword` | string | 否 | — | 匹配 `og_id` 或 `annotation` |
| `single_copy_only` | boolean | 否 | false | 仅返回单拷贝 orthogroup |
| `page` | number | 否 | 1 | 页码，从 1 开始 |
| `page_size` | number | 否 | 20 | 每页条数 |

**响应 data**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `list` | `OrthogroupItem[]` | 当前页数据 |
| `total` | number | 筛选后的总条数（非当前页条数） |

`OrthogroupItem`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `og_id` | string | OrthoFinder 风格 ID，如 `OG0000001` |
| `species_count` | number | 含该簇的物种数 |
| `gene_count` | number | 簇内基因总数 |
| `is_single_copy` | boolean | 是否单拷贝 |
| `annotation` | string \| undefined | 代表性功能注释 |

```json
{
  "code": 0,
  "message": "",
  "data": {
    "list": [
      {
        "og_id": "OG0000001",
        "species_count": 1,
        "gene_count": 2,
        "is_single_copy": false,
        "annotation": "示例功能注释 1"
      }
    ],
    "total": 24
  }
}
```

对应函数：`getOrthogroups(params)`，mock 开关 `MOCK_FLAGS.orthogroups`

#### 3.3.2 orthogroup 明细

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/orthogroups/<og_id>/` |
| 方法 | GET |

**响应 data**：`OrthogroupDetail | null`（未找到时为 `null`，且 `code` 仍为 0）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `og_id` | string | 同源簇编号 |
| `species_count` | number | 物种数 |
| `gene_count` | number | 基因数 |
| `is_single_copy` | boolean | 是否单拷贝 |
| `annotation` | string \| undefined | 功能注释 |
| `genes` | `OrthogroupGene[]` | 簇内基因 |

`OrthogroupGene`：`{ gene_id: string, genome_id: string, species?: string }`

```json
{
  "code": 0,
  "message": "",
  "data": {
    "og_id": "OG0000008",
    "species_count": 4,
    "gene_count": 4,
    "is_single_copy": true,
    "annotation": "示例功能注释 8",
    "genes": [
      { "gene_id": "Ghir_0000008_001", "genome_id": "G.hirsutumAD1_TM-1_HAU_v1.1", "species": "G.hirsutumAD1" }
    ]
  }
}
```

对应函数：`getOrthogroupDetail(ogId)`

#### 3.3.3 单拷贝 orthogroup

| 项 | 值 |
| --- | --- |
| URL | `/CottonOGD_api/orthogroups/single_copy/` |
| 方法 | GET |
| 参数 | `limit?`（默认 20） |

**响应 data**：`SingleCopyGene[]`，即 `{ og_id: string, genes: OrthogroupGene[] }`

对应函数：`getSingleCopyGenes(params)`

---

## 四、后端不可用但已有路由的接口（数据陷阱）

以下接口**有路由但不可用**，对接时请绕开，避免误以为能直接调用。

| 接口 | 问题 |
| --- | --- |
| `/CottonOGD_api/search_genes/` | 视图内部按 4 个参数调用，与 URL 签名不匹配，实际无法正常工作。统一检索请改用 `search/` |
| `/CottonOGD_api/Id_map/` | `@api_view` 装饰器被注释掉，DRF 无法处理请求 |
| `/CottonOGD_api/search_by_genome_location/` | 视图引用了已删除的模型字段 `geneid_id`（见 migration `0044` 与 `models.py`），调用必然报错 |

**其他注意**：

- `Id_map/` 的别名分隔符存在 `_` 与 `::` 两种写法，调用时**建议直接传 `db_id`**，不要用别名拼接。
- 前端有两套 Meilisearch 调用实现：`utils/meiliSearchApi.ts`（走 `search/`）与
  `utils/meilisearch.js`（走 `search_genes_meilisearch/`）。新代码统一用前者。
