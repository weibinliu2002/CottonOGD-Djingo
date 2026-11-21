# v1 端点全集

前缀：`/CottonOGD_api/api/v1/`。未特别标注的端点返回统一信封（见
[README.md](README.md)），参数既可用 query string（GET）也可用 JSON/Form
body（POST）；下表的「参数」是业务参数，认证头不在其中。

认证列：

- **公开**：匿名可访问；仍会解析有效 Bearer。
- **登录**：必须 JWT（`Authorization: Bearer <access>`）或有效的 `auth_token`
  Cookie，否则 `40101`。
- **会话**：需要匿名会话或登录会话（`POST /v1/auth/session/` 或登录创建）。

## 系统

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `health/` | 公开 | 存活检查，返回 `{status:'ok'}` |
| GET | `schema/` | 公开 | OpenAPI 3（YAML 默认，`?format=json` 得 JSON） |
| GET | `docs/` | 公开 | Swagger UI |

## meta

| 方法 | 路径 | 认证 | 参数 | 返回 `data` |
|---|---|---|---|---|
| GET | `meta/species/` | 公开 | — | `{species_info}` |
| GET/POST | `meta/families/` | 公开 | `selectedGenome`/`selected_genome`、`Class`/`class`/`tf_class` | 家族信息 + TF 计数 |
| GET | `meta/orthofinder/statistics/` | 公开 | `sections`（逗号分隔）、`kind` | OrthoFinder 统计汇总 |

## search

| 方法 | 路径 | 认证 | 参数 | 返回 `data` |
|---|---|---|---|---|
| GET/POST | `search/genes/` | 公开 | 关键词：`q`、`genome_id`、`limit`(≤100)、`offset`；区间：`region=chr:start-end` 或 `chrom`/`chr`/`chromosome`+`start`+`end` | `items` + `pagination` + `query`/`region`/`match_type`/`processing_time` |
| GET | `search/indexes/` | 公开 | — | `{indexes}` |
| POST | `search/indexes/<index>/search/` | 公开 | Meilisearch 原始查询体（`q`、`filter`、`limit`…） | 索引原始响应透传 |

## genes

| 方法 | 路径 | 认证 | 参数 | 返回 `data` |
|---|---|---|---|---|
| POST | `genes/lookup/` | 公开 | `ids`（单值/分隔串/数组；兼容 `id`/`gene_id`/`db_id`）、`genome_id`、`mode=ids|summary|detail` | 解析结果 + 按 mode 附 `geneid_result`/`detail` 等 |

`genes/lookup/` 统一了旧 `geneid_result` / `geneid_summary` / `Id_map` 三个入口。

## annotations

四个端点同构，方法均为 GET/POST；`gene_id`/`gene_ids`（分隔串或数组）与
`genome_id`/`genome` 必填，富集端点可选 `p_value_threshold`。

| 路径 | 说明 |
|---|---|
| `annotations/go/annotation/` | GO 注释 |
| `annotations/go/enrichment/` | GO 富集 |
| `annotations/kegg/annotation/` | KEGG 注释 |
| `annotations/kegg/enrichment/` | KEGG 富集 |

## expression

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| GET | `expression/tissues/` | 公开 | `genome_id` |
| GET | `expression/genomes/` | 公开 | — |
| POST | `expression/heatmap/` | 公开 | `db_id` 或 `gene_id`+`genome_id`，`tissue` |
| POST | `expression/heatmap/regenerate/` | 公开 | `genes`、`tissues`、`config` |
| POST | `expression/efp/` | 公开 | `gene_id`+`genome_id`，`low_color`/`mid_color`/`high_color` |

## sequences

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| POST | `sequences/genes/` | 公开 | `db_id` 或 `gene_id`+`genome_id` |
| POST | `sequences/region/` | 公开 | `genome_id`、`seqid`、`start`、`end`、`strand`(默认 `+`) |

## blast

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| POST | `blast/search/` | 公开 | `sequence`、`blast_type`（兼容 `type`）、`selected_genomes`、`data_type=genome|cds|mrna|protein`、`evalue`、`max_hits`（兼容 `max_target_seqs`） |

## structure

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| POST | `structure/search/` | 公开 | `sequence`、`method=rcsb_api|hmmer|mmseqs2|blast`、`top_n`、`evalue`、`identity_cutoff`、`use_cache` |
| GET | `structure/methods/` | 公开 | — |

## primer

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| POST | `primer/design/` | 公开 | `sequence` 或 `db_id` 或 `gene_id`+`genome_id`；`sequence_id`；`parameters`（JSON 对象或 JSON 字符串） |

## genome

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| POST | `genome/location/` | 公开 | `region` 或 `seqid`/`chromosome`/`chr`+`start`+`end`；`genome` |
| POST | `genome/distribution/` | 公开 | `genome`、`gene_ids` |

## synteny

| 方法 | 路径 | 认证 | 参数 | 说明 |
|---|---|---|---|---|
| GET/POST | `synteny/genome/` | 公开 | `source`/`reference_genome`、`target`/`query_genome`、`chromosome`、`include_blocks` | 预计算 jcvi 结果；未预计算 `40401` 且 `data.pairs` 给候选 |
| GET/POST | `synteny/micro/` | 公开 | `gene_ids`、`source`/`reference_genome`、`target`/`query_genome` | 微共线性图 + 双侧轨道 |
| GET/POST | `synteny/block/` | 公开 | `source_genes`、`target_genes`、`source`、`target` | 定位共线性块 |
| GET | `synteny/pairs/` | 公开 | — | 已有预计算结果的基因组对 |

## variants

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| GET/POST | `variants/syri/pairs/` | 公开 | — |
| GET/POST | `variants/syri/structural/` | 公开 | `pair_id`（或 `ref_genome_id`+`query_genome_id`）、`chrom`、`start`、`end`、`son_type`、`limit` |
| GET/POST | `variants/syri/sequence/` | 公开 | 同上 |
| GET/POST | `variants/sets/` | 公开 | — |
| GET/POST | `variants/region/` | 公开 | `set_id`、`chrom`、`start`、`end`、`svtype`、`limit` |
| GET/POST | `variants/detail/` | 公开 | `id` |
| GET/POST | `variants/density/` | 公开 | `set_id`、`chrom`、`start`、`end`、`bins` |
| GET/POST | `variants/genotype/` | 公开 | `set_id`、`chrom`、`pos` 或 `start`+`end`、`samples`、`format` |

## gwas

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| GET/POST | `gwas/traits/` | 公开 | — |
| GET/POST | `gwas/accessions/` | 公开 | `species` |
| GET/POST | `gwas/phenotype/` | 公开 | `trait_code`、`accession` |
| GET/POST | `gwas/markers/` | 公开 | `set_id`、`chrom`、`start`、`end`、`limit` |
| GET/POST | `gwas/associations/` | 公开 | `trait_code`、`chrom`、`start`、`end`、`threshold`、`top_n` |

## conversion

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| GET | `conversion/pairs/` | 公开 | — |
| GET/POST | `conversion/coordinate/` | 公开 | `source_genome`/`source`、`target_genome`/`target`、`regions`、`tool`、`min_match`、`min_map_ratio` |
| GET/POST | `conversion/gene-ids/` | 公开 | 同上，改用 `gene_ids`/`gene_id` |
| GET/POST | `conversion/gene-ids/evidence/` | 公开 | 同上 + `methods`/`method` |

## orthofinder

| 方法 | 路径 | 认证 | 参数 | 返回 |
|---|---|---|---|---|
| GET | `orthofinder/meta/` | 公开 | — | 物种列表 |
| POST | `orthofinder/genes/orthogroups/` | 公开 | `geneid` | 基因所属 OG + 跨物种成员 |
| POST | `orthofinder/genes/orthologs/` | 公开 | `geneid`、`species`、`partner_species`、`og_code` | 真实直系同源 |
| POST | `orthofinder/genes/hogs/` | 公开 | `geneid`、`species` | 最深 HOG |
| POST | `orthofinder/orthogroups/search/` | 公开 | `species`（数组或重复参数）、`mode`、`og_code`、`og_code_like`、`min_genes`/`max_genes`、`min_species`/`max_species`、`min_selected_species`/`max_selected_species`、`sort`、`limit`、`offset` | OG 列表 |
| POST | `orthofinder/orthogroups/detail/` | 公开 | `og_code`、`include_genes` | OG 成员（按物种） |
| POST | `orthofinder/orthogroups/members/` | 公开 | `og_code`、`limit`、`offset` | 成员平铺分页 |
| POST | `orthofinder/hogs/detail/` | 公开 | `hog_code` | HOG 成员 |
| POST | `orthofinder/genome-pairs/` | 公开 | `genome_a`、`genome_b`、`og_code`、`limit`、`offset` | 两基因组共享 OG 成员 |
| GET | `orthofinder/species/tree/` | 公开 | `fmt=newick`（纯文本）或 `include_nodes` | 物种树 |
| GET | `orthofinder/statistics/` | 公开 | `type`、`kind`、`species_a`、`species_b`、`scope`、`og_code` | 统计 |
| GET | `orthofinder/og/<og>/sequences/` | 公开 | — | **FASTA 原始字节流**（非信封） |
| GET | `orthofinder/og/<og>/msa/` | 公开 | — | **MSA FASTA 原始字节流**（非信封） |
| GET | `orthofinder/og/<og>/tree/` | 公开 | — | **Newick 原始文本**（非信封） |
| GET | `orthofinder/og/<og>/tandem/` | 公开 | `limit`、`offset`、`include_events` | 串联重复/复制事件 |

## ppi

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| POST | `ppi/string/` | 公开 | `gene_ids`（数组，≤300）、`genome_id`、`score_threshold`(0-1000，默认 400) |

返回 `{elements:{nodes,edges}, note, stats}`；部分基因无法映射时仍在 `note`
说明，全部无法映射返回 `40401`。

## files

| 方法 | 路径 | 认证 | 参数 | 说明 |
|---|---|---|---|---|
| GET | `files/public/tree/` | 公开 | `path` | 仅 `is_public=True` 的文件树 |
| GET | `files/public/<uuid>/download/` | 公开 | — | 公开文件下载（X-Accel/流式） |
| GET | `files/my/tree/` | 登录 | `path` | 个人文件树（owner 隔离） |
| POST | `files/my/upload/` | 登录 | multipart：`file`、`path`、`replace` | 同名冲突 `40901`；`replace=true` 覆盖并复用存储名 |
| DELETE | `files/my/<uuid>/` | 登录 | — | 删除记录 + 物理文件；返回 `{deleted:true,id}` |
| POST | `files/my/<uuid>/move/` | 登录 | `new_path`、`new_name` | 移动/重命名；冲突 `40901` |
| GET | `files/genome/<genome_id>/<file_type>/` | 公开 | 路径参数 | 基因组数据下载 |

`file_type` ∈ `genome`、`gene`、`cds`、`protein`、`upstream2000`、`gff3`。

详情见 [files.md](files.md)。

## auth

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| POST/DELETE | `auth/session/` | 公开 | 无（创建匿名会话 / 注销当前会话） |
| POST | `auth/register/` | 公开 | `email`、`username`、`password`、`confirm_password` |
| POST | `auth/verify-email/` | 公开 | `key` |
| POST | `auth/login/` | 公开 | `email` 或 `username` + `password` |
| POST | `auth/refresh/` | 公开 | `refresh` |
| POST | `auth/token/` | 公开 | `username`/`email` + `password`（SimpleJWT 兼容） |
| POST | `auth/token/refresh/` | 公开 | `refresh` |
| POST | `auth/resend-verification/` | 公开 | `email`（60s 冷却，`42901`） |
| POST | `auth/forgot-password/` | 公开 | `email` |
| POST | `auth/reset-password/` | 公开 | `uidb36`、`key`、`new_password` |
| GET/DELETE | `auth/me/` | 登录 | GET 当前用户；DELETE 注销账号 |
| POST | `auth/password/change/` | 登录 | `new_password`（需已有密码） |
| POST | `auth/set-password/` | 登录 | `new_password`（第三方注册用户首次设密） |
| GET | `auth/methods/` | 登录 | — |
| POST | `auth/bind-third-party/` | 登录 | `provider`、`uid` |
| POST | `auth/unbind-third-party/` | 登录 | `provider`、`uid` |

详见 [auth.md](auth.md)。

## ai

| 方法 | 路径 | 认证 | 参数 |
|---|---|---|---|
| POST | `ai/chat/` | 会话 | `message`（必填）、`clear_history` |
| GET | `ai/tools/` | 公开 | — |

`ai/chat/` 返回 `{answer, tool_calls, history_turns}`；未配置模型返回 `50301`，
模型服务异常 `50201`。

## 非信封端点（字节流 / 重定向）

这些 URL 保持稳定，供浏览器、JBrowse、nginx 直接使用；不返回 JSON 信封。

| 路径 | 说明 |
|---|---|
| `GET /jbrowse/large/<genome>/<file>` | JBrowse 大文件；支持单段 Range/206 |
| `GET /static/jbrowse/data/<genome>/<file>` | 同上（JBrowse 配置绝对路径） |
| `GET /synteny/<source>_to_<target>/work/<file>` | SyntenyTrack 锚点/BED/GFF/`synteny.json` |
| `GET /download_genome/<genome_id>/<file_type>` | 旧下载别名，等价于 `files/genome/...` |
| `GET /CottonOGD_api/tf_tree/tree/genome/<genome>/{TF,TR}/<name>.treefile` | Newick 文本 |
| `GET /accounts/...` | allauth（邮箱验证链接等） |
| `GET /accounts/{google,orcid}/login/callback/` | 第三方登录回调，302 到前端并携带 token |
| `GET /admin/` | Django admin |