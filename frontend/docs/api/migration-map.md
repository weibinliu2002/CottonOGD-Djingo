# 旧路径 → v1 迁移表

本次重构**不保留旧路径双挂载**。前端必须一次性切到
`/CottonOGD_api/api/v1/`；未命中的旧 GET 会落到 SPA `index.html`（HTTP 200
但返回 HTML），旧 POST 返回 405——两者都不是接口。

## 1. 全局变化（所有域）

| 项 | 旧 | 新 |
|---|---|---|
| 前缀 | `/CottonOGD_api/<view>/`、`/api/*` | `/CottonOGD_api/api/v1/<domain>/...` |
| 成功响应 | 各视图自定义（`species_info` 为 JSON **字符串**、有的直接返回数组） | `{code:0,message:'ok',data:{...}}` |
| 错误响应 | 7 种：`{error}`、`{success:false,error:{code,...}}`、DRF detail… | `{code:<int>,message,data}`，HTTP = code//100 |
| 认证 | 必须先 `POST login/` 拿 uuid/token，几乎每个请求带 `uuid` header | 业务数据域**公开**；个人/账号端点用 JWT；AI 用会话 |
| 旧 token | 自定义 UUID + Redis token | JWT（登录）或匿名会话 token；旧 UUID 强制校验已取消 |
| 参数兼容 | 各视图自己解析 | GET query 与 POST body 同名参数等价；保留常用别名 |
| 路径命名 | 下划线拼接 | kebab-case 分层 |

> 旧的 `uuid` header **不再需要**；即使传了，也不会参与业务鉴权。
> 旧自定义 session 仍可用于 `auth_token` cookie / Bearer 的匿名会话。

## 2. 路径映射

### 账号 / 会话

| 旧路径 | 新路径 | 备注 |
|---|---|---|
| `POST /CottonOGD_api/login/` | `POST /CottonOGD_api/api/v1/auth/session/` | 旧 login 是**匿名会话**，不是账号登录 |
| `POST /CottonOGD_api/logout/` | `DELETE /CottonOGD_api/api/v1/auth/session/` | 清 Cookie 并吊销 token |
| `POST /api/auth/register/`（历史批次） | `POST v1/auth/register/` | |
| `POST /api/auth/login/` | `POST v1/auth/login/` | 返回 JWT |
| `POST /api/auth/refresh/` | `POST v1/auth/refresh/` | |
| `POST /api/auth/verify-email/` | `POST v1/auth/verify-email/` | |
| `POST /api/auth/resend-verification/` | `POST v1/auth/resend-verification/` | |
| `POST /api/auth/forgot-password/` | `POST v1/auth/forgot-password/` | 未注册邮箱改为 `40101`（防枚举） |
| `POST /api/auth/reset-password/` | `POST v1/auth/reset-password/` | |
| `GET/DELETE /api/auth/me/` | `GET/DELETE v1/auth/me/` | |
| `POST /api/auth/password/change/` | `POST v1/auth/password/change/` | |
| `POST /api/auth/set-password/` | `POST v1/auth/set-password/` | |
| `GET /api/auth/methods/` | `GET v1/auth/methods/` | |
| `POST /api/auth/bind-third-party/` | `POST v1/auth/bind-third-party/` | |
| `POST /api/auth/unbind-third-party/` | `POST v1/auth/unbind-third-party/` | |
| `/CottonOGD_api/api/auth/*`（nginx 兼容别名） | `/CottonOGD_api/api/v1/auth/*` | 别名已删除 |
| `/CottonOGD_api/accounts/...` | 不变 | allauth 邮箱链接 |

### meta / search / genes

| 旧路径 | 新路径 | 字段变化 |
|---|---|---|
| `GET /CottonOGD_api/get_species_info/` | `GET v1/meta/species/` | `data.species_info` 由 JSON **字符串**改为数组 |
| `POST /CottonOGD_api/get_family_info/` | `GET/POST v1/meta/families/` | `family_info`、`family_list` 由字符串改为数组 |
| `GET /CottonOGD_api/search_genes_meilisearch/` | `GET/POST v1/search/genes/` | 分页统一 `items`+`pagination` |
| `POST /CottonOGD_api/search/` | `POST v1/search/indexes/<index>/search/` | `index` 从 body 提升为路径参数 |
| `GET /CottonOGD_api/get_search_indexes/` | `GET v1/search/indexes/` | |
| `POST /CottonOGD_api/geneid_result/` | `POST v1/genes/lookup/`（`mode=detail`） | |
| `POST /CottonOGD_api/geneid_summary/` | `POST v1/genes/lookup/`（`mode=summary`，默认） | |
| `POST /CottonOGD_api/Id_map/` | `POST v1/genes/lookup/`（`mode=ids`） | 一次返回解析 + 摘要 |

### 注释 / 表达 / 序列

| 旧路径 | 新路径 |
|---|---|
| `GET/POST /CottonOGD_api/go_annotation/` | `v1/annotations/go/annotation/` |
| `GET/POST /CottonOGD_api/go_enrichment/` | `v1/annotations/go/enrichment/` |
| `GET/POST /CottonOGD_api/kegg_annotation/` | `v1/annotations/kegg/annotation/` |
| `GET/POST /CottonOGD_api/kegg_enrichment/` | `v1/annotations/kegg/enrichment/` |
| `POST /CottonOGD_api/extract_expression/` | `POST v1/expression/heatmap/` |
| `POST /CottonOGD_api/regenerate_heatmap/` | `POST v1/expression/heatmap/regenerate/` |
| `GET /CottonOGD_api/extract_expression/tissues/` | `GET v1/expression/tissues/` |
| `GET /CottonOGD_api/extract_expression/genomes/` | `GET v1/expression/genomes/` |
| `POST /CottonOGD_api/expression_EFP_image/` | `POST v1/expression/efp/` |
| `POST /CottonOGD_api/extract_seq/` | `POST v1/sequences/genes/` |
| `POST /CottonOGD_api/extract_seq_gff/` | `POST v1/sequences/region/` |

### 工具 / 基因组 / 共线性

| 旧路径 | 新路径 | 备注 |
|---|---|---|
| `POST /CottonOGD_api/blast_cmd/` | `POST v1/blast/search/` | |
| `POST /CottonOGD_api/search_similar_structure/` | `POST v1/structure/search/` | |
| `GET /CottonOGD_api/get_search_methods/` | `GET v1/structure/methods/` | 旧视图存在但**未挂路由** |
| `POST /CottonOGD_api/primer_design/` | `POST v1/primer/design/` | |
| `POST /CottonOGD_api/search_by_genome_location/` | `POST v1/genome/location/` | |
| `POST /CottonOGD_api/gene_genomic_distribution/` | `POST v1/genome/distribution/` | |
| `POST /CottonOGD_api/genome_synteny/` | `GET/POST v1/synteny/genome/` | |
| `POST /CottonOGD_api/microsynteny/` | `GET/POST v1/synteny/micro/` | |
| `POST /CottonOGD_api/synteny_block/` | `GET/POST v1/synteny/block/` | |
| `GET /CottonOGD_api/synteny_pairs/` | `GET v1/synteny/pairs/` | |
| `GET /CottonOGD_api/download_genome/<id>/<type>` | `GET v1/files/genome/<id>/<type>/` | 根路径 `/download_genome/...` 旧别名仍保留 |
| `/synteny/<pair>/work/<file>` | 不变 | 非信封字节流 |
| `/CottonOGD_api/tf_tree/...` | 不变 | 生产建议 nginx 直出 |

### 变异 / GWAS

| 旧路径 | 新路径 |
|---|---|
| `GET /CottonOGD_api/syri/pairs/` | `v1/variants/syri/pairs/` |
| `GET /CottonOGD_api/syri/structural/` | `v1/variants/syri/structural/` |
| `GET /CottonOGD_api/syri/sequence/` | `v1/variants/syri/sequence/` |
| `GET /CottonOGD_api/variant/sets/` | `v1/variants/sets/` |
| `GET /CottonOGD_api/variant/region/` | `v1/variants/region/` |
| `GET /CottonOGD_api/variant/id/` | `v1/variants/detail/` |
| `GET /CottonOGD_api/variant/density/` | `v1/variants/density/` |
| `GET /CottonOGD_api/variant/genotype/` | `v1/variants/genotype/` |
| `GET /CottonOGD_api/gwas/traits/` | `v1/gwas/traits/` |
| `GET /CottonOGD_api/gwas/accessions/` | `v1/gwas/accessions/` |
| `GET /CottonOGD_api/gwas/phenotype/` | `v1/gwas/phenotype/` |
| `GET /CottonOGD_api/gwas/markers/` | `v1/gwas/markers/` |
| `GET /CottonOGD_api/gwas/associations/` | `v1/gwas/associations/` |

### OrthoFinder

| 旧路径 | 新路径 |
|---|---|
| `POST /CottonOGD_api/orthofinder/ortholog_gene/` | `POST v1/orthofinder/genes/orthologs/` |
| `GET /CottonOGD_api/orthofinder/orthogroup_detail/` | `POST v1/orthofinder/orthogroups/detail/` |
| `GET /CottonOGD_api/orthofinder/orthogroups_by_species/` | `POST v1/orthofinder/orthogroups/search/` |
| `GET /CottonOGD_api/orthofinder/meta/` | `GET v1/orthofinder/meta/` |
| `GET /CottonOGD_api/orthofinder/sequence/<og>` | `GET v1/orthofinder/og/<og>/sequences/` |
| `GET /CottonOGD_api/orthofinder/tree/<og>` | `GET v1/orthofinder/og/<og>/tree/` |
| `GET /CottonOGD_api/orthofinder/msa/<og>` | `GET v1/orthofinder/og/<og>/msa/` |
| `GET /CottonOGD_api/orthofinder/tandem/<og>` | `GET v1/orthofinder/og/<og>/tandem/` |

`genes/orthologs/` 与 `genes/orthogroups/`、`genes/hogs/` 为新增按基因入口；
`orthogroups/members/`、`hogs/detail/`、`genome-pairs/`、`species/tree/`、
`statistics/`、`meta/orthofinder/statistics/` 为新增/拆分端点。

### PPI / AI / 文件

| 旧路径 | 新路径 |
|---|---|
| `POST /CottonOGD_api/ppi/string/` | `POST v1/ppi/string/` |
| `POST /CottonOGD_api/ai/chat/` | `POST v1/ai/chat/` |
| `GET /api/public/tree/`（历史批次） | `GET v1/files/public/tree/` |
| `GET /api/public/<uuid>/download/` | `GET v1/files/public/<uuid>/download/` |
| `GET /api/myfiles/tree/` | `GET v1/files/my/tree/` |
| `POST /api/myfiles/upload/` | `POST v1/files/my/upload/` |
| `DELETE /api/myfiles/<uuid>/` | `DELETE v1/files/my/<uuid>/` |
| `POST /api/myfiles/<uuid>/move/` | `POST v1/files/my/<uuid>/move/` |

## 3. 已删除 / 不再提供的端点

| 端点 | 原因 |
|---|---|
| `GET/POST /CottonOGD_api/search_genes/` | 旧路由误挂到 `search_genes`（未使用的分页实现）；实际搜索走 `search_genes_meilisearch/` |
| `/api/*` 全部旧路径 | 统一并入 v1，无双挂载 |
| `/CottonOGD_api/<view>/` 全部旧路径 | 同上 |
| `/CottonOGD_api/api/auth/*` 兼容别名 | 统一到 `/api/v1/auth/*` |
| 旧 `uuid` header 强校验 | 认证模型重做；需要会话时用 `auth_token` |
| `POST .../get_family_info/` 的 UUID 前置检查 | 公开端点，不再要求先建会话 |

`protein3D` 的两个旧视图（`search_similar_structure` / `get_search_methods`）：
旧配置中 `get_search_methods` 未挂路由，本次统一补为 `structure/methods/`。

## 4. 字段与行为变化清单（前端核对）

1. **所有响应**外包一层 `code/message/data`；旧代码里 `resp.species_info`
   → `resp.data.species_info`。
2. `meta/species/` 的 `species_info` 从字符串变为数组，前端不再 `JSON.parse`。
3. `meta/families/` 的 `family_info` / `family_list` 从字符串变为数组。
4. 错误字段从 `error` / `success+error.code` 改为 `code`(int) / `message`。
5. 分页统一 `data.items` + `data.pagination`；旧代码里的 `results`/`count`
   等以各端点文档为准。
6. 搜索代理的 `index` 从请求体移到 URL；请求体其余字段不变。
7. 登录账号体系：注册/登录使用 `v1/auth/*`；旧 `login/`（uuid 会话）仅对应
   `v1/auth/session/`。
8. 文件下载不再依赖 `uuid` header；`/v1/files/...` 返回 X-Accel 或字节流。
9. 公开业务数据域不再要求先建立会话——首页可直接请求。
10. `variants/syri/*`、`gwas/*` 等端点接受 GET query 与 POST body 两种传参。

## 5. 迁移检查命令

```bash
# 前端仓库中不应再出现旧前缀
grep -rn "CottonOGD_api/\(go_\|kegg_\|geneid_\|extract_\|search_genes\|Id_map\|variant/\|syri/\|gwas/\|orthofinder/ortholog_gene\|login/\|logout/\)" src
grep -rn "'/api/" src
grep -rn "uuid" src/utils src/stores | grep -i header
```

后端侧：

```bash
grep -rn "CottonOGD.views" CottonOGD/server CottonOGD/api   # 必须为空
grep -rn "JsonResponse" CottonOGD/api CottonOGD/server       # 必须为空
grep -rn "HTTP_INTERNAL_ERROR" CottonOGD                     # 必须为空
```