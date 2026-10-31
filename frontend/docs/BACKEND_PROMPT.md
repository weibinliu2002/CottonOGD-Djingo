# CottonOGD 后端接口开发提示词

> 本文是一份**自包含**的后端开发提示词。可直接复制给后端开发（或 LLM）执行，
> 无需额外查阅前端代码。

---

## 提示词正文

```
你是一位资深 Django + DRF 后端工程师。请为 CottonOGD（iCotton）棉花组学数据库
实现一批缺失的后端接口，并把若干存量接口的响应格式对齐到统一约定。

# 一、项目背景

CottonOGD 是棉花多组学数据库，对标 SoyOmics（大豆组学数据库）的信息架构。
前端已完成"基础架构搭桥 + 结果表格增强 + 同源分析页面"的改造，
但后端缺少同源分析（Orthogroup）等若干接口，且部分存量接口
返回的是 Django 旧格式（{status, data} / {error}），与前端统一约定不一致。

前端页面已按统一契约写好请求函数，并对缺失接口配置了 mock 开关。
你的任务是补齐真实接口，使前端把开关从 mock 切到真实即可正常工作。

# 二、技术栈与工程约束

- 语言/框架：Python 3 + Django 5.2 + Django REST Framework，ASGI 由 Daphne 承载
- 存储：MySQL（业务数据）、Redis（缓存/会话）
- 检索：Meilisearch（由后端代理，前端不直连、不持有密钥）
- 代码位置：
  - 路由：backend/CottonOGD/urls.py（前缀 /CottonOGD_api/）
  - 视图：backend/CottonOGD/views/*.py
  - 模型：backend/CottonOGD/models.py
- 所有新增业务接口必须挂在 /CottonOGD_api/ 前缀下
- 不要改动前端任何文件（前端不在你的职责范围）

# 三、统一响应格式（硬性要求）

所有新增接口必须返回：

{
  "code": 0,            # 0 表示成功，非 0 表示失败
  "message": "",        # 失败时给人类可读的原因
  "data": <业务数据>     # 成功时为实际数据；失败时给同结构的空值（{} 或 [] 或 null）
}

要求：
- 成功时 code 必须为 0，data 放业务数据
- 失败时 code 非 0，message 说明原因，data 给出**同结构空值**，不要让前端做额外的 undefined 判断
- 不要用 {status: 'success', data: ...} 或 {error: ...} 这类旧格式
- 分页接口的 data 形如 { list: [...], total: <筛选后总条数> }
  （total 必须是筛选后的总数，不是当前页条数）

# 四、需要新增的接口（缺失，前端已走 mock）

## 4.1 新闻/动态列表

- URL: /CottonOGD_api/news/
- 方法: GET
- 参数: 无
- 响应 data: NewsItem[]

NewsItem 字段：
  id      number  主键
  title   string  标题
  content string  正文
  date    string  发布日期，格式 YYYY-MM-DD
  link    string|null  外链，可为空

示例：
{
  "code": 0,
  "message": "",
  "data": [
    { "id": 1, "title": "数据库上线", "content": "…", "date": "2026-01-15", "link": null }
  ]
}

## 4.2 同源分析 Orthogroup

背景：OrthoFinder 当前在 WorkFile/config.yaml 中 enabled: false，仓库内没有任何产物文件。
请设计 orthogroup 相关数据表，并提供下列三个接口。
如果暂时还没有真实数据，也要先把接口和表结构落地（可返回空列表），
不要返回 404/500，前端已按统一契约处理空数据。

### 4.2.1 orthogroup 列表

- URL: /CottonOGD_api/orthogroups/
- 方法: GET
- 参数:
    keyword          string   可选，模糊匹配 og_id 或 annotation
    single_copy_only boolean  可选，默认 false，仅返回单拷贝 orthogroup
    page             number   可选，默认 1
    page_size        number   可选，默认 20
- 响应 data: { list: OrthogroupItem[], total: number }

OrthogroupItem 字段：
  og_id           string   OrthoFinder 风格 ID，如 OG0000001
  species_count   number   含该簇的物种数
  gene_count      number   簇内基因总数
  is_single_copy  boolean  是否单拷贝（每个物种恰好一个基因）
  annotation      string   代表性功能注释，可为空

注意：ID 格式为 OG0000001（OrthoFinder 风格），
与项目内 gbdraw 使用的 og_<N> 风格不同，请统一使用 OG 前缀，避免两套 ID 体系混用。
另外，eggNOG 的同源分组与 OrthoFinder 的 orthogroup 不是同一套结果，不要混为一谈。

### 4.2.2 orthogroup 明细

- URL: /CottonOGD_api/orthogroups/<og_id>/
- 方法: GET
- 响应 data: OrthogroupDetail | null
  - 找不到时返回 { "code": 0, "message": "", "data": null }（不要用 404 打断前端渲染）

OrthogroupDetail = OrthogroupItem + genes: OrthogroupGene[]

OrthogroupGene 字段：
  gene_id    string
  genome_id  string
  species    string  可选

### 4.2.3 单拷贝 orthogroup

- URL: /CottonOGD_api/orthogroups/single_copy/
- 方法: GET
- 参数: limit  number 可选，默认 20
- 响应 data: SingleCopyGene[]

SingleCopyGene 字段：
  og_id string
  genes OrthogroupGene[]

## 4.3 基因表达量查询（GET）

- URL: /CottonOGD_api/gene_expression/
- 方法: GET
- 参数:
    gene_id    string  必填，多个用逗号分隔
    genome_id  string  必填
    tissues    string  可选，多个用逗号分隔
- 响应 data:
{
  "gene_id": "Ghir_A01G000010",
  "genome_id": "G.hirsutumAD1_TM-1_HAU_v1.1",
  "tissues": ["root", "stem", "leaf"],
  "values": [[1.2, 3.4, 5.6]]
}

# 五、需要调整格式的存量接口

以下接口有路由、也在被前端调用，目前返回旧格式，建议逐步对齐统一响应格式。
注意：前端已有适配层兼容旧格式，因此这不是紧急项，但新写的代码请一律用新格式。

1. /CottonOGD_api/go_annotation/（GET）
2. /CottonOGD_api/kegg_annotation/（GET）
   现状：{status: 'success', data: {results, chart_data}}
   问题：results[].description 可能是"字符串化 JSON"，也可能是纯文本，前端需 try/catch 兜底
   建议：description 固定为对象 {name, definition}

3. /CottonOGD_api/go_enrichment/（POST，multipart/form-data）
4. /CottonOGD_api/kegg_enrichment/（POST，multipart/form-data）
   现状：同步返回 {status: 'success', data: {results, plot_images}}
   注意：前端 utils/enrichment.ts 中残留约 90 行"异步轮询"死代码，引用了两个
   不存在的端点（go_enrichment_results/:taskId/、kegg_enrichment_results/:taskId/）。
   若富集保持同步，请忽略并协助清理死代码；若改异步，需新增这两个端点。

5. /CottonOGD_api/blast_cmd/（POST）
   现状：返回 { results: { <基因组名>: "<字符串化的 JSON 或 XML>" } }
   问题：results 的值是字符串而非对象，前端需二次解析（失败时按 XML 原文保留）
   建议：直接返回对象，去掉字符串包装

6. /download_genome/<genome_id>/<file_type>（GET，根级路由）
   现有映射需保持不变：
     genome        -> .genome.fa.gz
     gene          -> .gene_genome.fa.gz
     cds           -> .cds.fa.gz
     protein       -> .pro.fa.gz
     upstream2000  -> .upstream.fa.gz
     gff3          -> .gff.gz

# 六、切勿重复开发（已存在且可用）

以下接口已存在且被前端正确使用，**不要重新实现**：

  POST /CottonOGD_api/login/
  POST /CottonOGD_api/logout/
  GET  /CottonOGD_api/get_species_info/
  POST /CottonOGD_api/get_family_info/
  POST /CottonOGD_api/geneid_summary/
  POST /CottonOGD_api/geneid_result/
  POST /CottonOGD_api/extract_seq/
  POST /CottonOGD_api/extract_seq_gff/
  GET  /CottonOGD_api/extract_expression/tissues/
  GET  /CottonOGD_api/extract_expression/genomes/
  POST /CottonOGD_api/extract_expression/
  POST /CottonOGD_api/regenerate_heatmap/
  POST /CottonOGD_api/search/                 （统一检索代理）
  GET  /CottonOGD_api/get_search_indexes/
  POST /CottonOGD_api/ai/chat/
  POST /CottonOGD_api/primer_design/
  POST /CottonOGD_api/blast_cmd/
  POST /CottonOGD_api/expression_EFP_image/
  POST /CottonOGD_api/search_similar_structure/
  GET  /CottonOGD_api/get_search_methods/
  POST /CottonOGD_api/search_by_genome_location/
  POST /CottonOGD_api/gene_genomic_distribution/
  POST /CottonOGD_api/genome_synteny/

# 七、已知不可用接口（不要依赖，也不要"修复式"重写，除非明确要求）

  /CottonOGD_api/search_genes/              内部按 4 参数调用，与 URL 签名不匹配
  /CottonOGD_api/Id_map/                    @api_view 装饰器被注释，DRF 无法处理
  /CottonOGD_api/search_by_genome_location/ 引用已删除字段 geneid_id，必然报错

# 八、交付要求

1. 新增/修改 backend/ 下的路由、视图、（必要时）模型与迁移
2. 每个接口给出：URL、方法、请求参数、响应字段说明、示例 JSON
3. 为 orthogroup 相关接口给出建议的表结构（表名、字段、类型、索引、外键关系）
4. 严格遵循第三节的统一响应格式
5. 说明哪些接口已存在、无需改动（避免重复开发）
6. 不要修改任何前端文件
```

---

## 附：前端对接位置速查

| 关注点 | 位置 |
| --- | --- |
| 统一请求层与 mock 开关 | `src/api/index.ts` |
| 表格增强（排序/筛选/分页/导出） | `src/composables/core/useEnhancedTable.ts`、`src/components/data-display/TableToolbar.vue` |
| 分页原语 | `src/composables/core/useTablePagination.ts` |
| CSV 导出原语 | `src/utils/exportTable.ts` |
| 全球搜索框 | `src/components/search/GlobalSearch.vue` |
| 首页模块卡片 | `src/components/home/ModuleCard.vue` |
| 同源分析页 | `src/views/genome/HomologyView.vue`（路由 `/homology`） |
| BLAST 页面与状态 | `src/views/sequence/BlastpView.vue`、`src/stores/modules/blast.ts` |
