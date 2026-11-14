# CottonOGD Backend 架构梳理与分层优化报告

日期：2026-09-14
范围：`backend/` 目录（Django，前后端分离）
性质：阶段 1 / 1.5 / 2 已实施（2026-09-14），gene_seq 表保留作备用数据源、未删除；实施后验证记录见文末「六、实施与验证记录」。

---

## 一、现状总结

### 1.1 总体结构

```
backend/
├── CottonOGD/            # 主 app（几乎全部业务都在这一个 app 里）
│   ├── models.py         # 22 个模型，547 行
│   ├── urls.py           # 全部路由集中于此（约 30 个端点）
│   ├── views/            # 17 个视图模块，约 3300 行（HTTP 层 + 业务逻辑混写）
│   ├── server/           # 搜索服务封装（blast/hmmer/mmseqs/annotation/go_kegg/3D）
│   ├── config/           # meilisearch_config.py（key 管理已较规范）
│   ├── management/       # build_genesets / rebuild_index / setup_meili_keys / sync_genes
│   └── data/             # blast_db、Genome（含 genome/*.fa.gz + .fai + .gzi）、GO obo 等
├── mysite/               # settings / urls
└── migrations/           # 0040~0049+ 近期大改（TranscriptMaster、注释表拆分、gene_seq 去重）
```

### 1.2 目标数据链路（用户计划的分层，2026-09-14 二次澄清后）

```
前端搜索
   → Meilisearch 索引 `genemaster`（字段: id, geneid, alias, genome_id）   views/Meilisearch.py
   → 命中结果直接携带 id_id（即 GeneMaster.id）
     —— Id_map / location_ID 整条映射链路废弃，不再修复、直接下线
   → 用 id_id 并行查业务表：gene_info / gene_annotation / gene_go / gene_kegg
   → 序列：gene_seq 表彻底退役，全部改由 pysam（samtools faidx 体系）从文件提取：
     基因组坐标型（gene）      → data/Genome/genome/*.genome.fa.gz（.fai/.gzi 已就绪）
     拼接产物型（cdna/cds/mrna/pro/up/down）→ data/Genome/{cdna,cds,pep,...} 产物文件做 bgzip+faidx
```

> 决策记录：第一版报告中「修复 Id_map 的 P0 问题」一条随此决策**作废**——Id_map 不修而是下线；`geneid_result/geneid_summary` 中「只有 gene_id+genome_id 时回退 Id_map」的分支同步删除，前端必须携带 Meilisearch 返回的 id（或后端内部直接调 `search_genes()` 补齐）。

### 1.3 已核实的关键事实

| 事实 | 依据 |
|---|---|
| Meilisearch 搜索层已可用且返回 `id`（即 db_id） | views/Meilisearch.py:20,63-74（RETREIVE_FIELDS 含 `id`） |
| `Id_map` 是「gene_id+genome → db_id」的桥接函数，但查询条件可疑 | views/location_ID.py:55 `filter(Q(geneid__in=norm_map) \| Q(genome_id__in=genome_ids))` |
| `geneid_result` 单次请求会对每个 mRNA 做 6 次 `gene_seq.filter(...).first()`（N×6 次查询） | views/gene_id_result.py:160-181 |
| `gene_seq` 表把 cdna/cds/mrna/pro/up/downstream/genome 全部序列以 TextField 存库 | models.py:255-269 |
| 基因组 bgzip+faidx 文件已存在：`data/Genome/genome/*.genome.fa.gz(.fai/.gzi)` | 实测目录列表；pysam==0.24.0（htslib，与 samtools 同源）与 pyfaidx==0.9.0.3 均已在 requirements.txt，方案选用 pysam |
| 注释已拆成 AnnotationSource / AnnotationDetail / gene_annotation 三表（迁移 0048+） | models.py:178-253 |
| 视图层大量 `csrf_exempt` + 裸 `JsonResponse`，与 DRF `api_view` 混用 | views/Meilisearch.py:125-126 vs views/gene_id_result.py:21 |
| `gene_info.id_id` 是裸 IntegerField，不是外键 | models.py:154 |

### 1.4 现有分层雏形

其实已有三层雏形，只是边界不严：

- **检索层**：Meilisearch（views/Meilisearch.py + server/ 下的各 search）
- **映射层**：Id_map（gene_id → GeneMaster.id）——**已决定废弃**，检索结果自带 id
- **数据层**：models.py 直查，无 service 层、无 serializer 体系（server/serializers.py 仅 21 行）

---

## 二、问题清单（按严重程度）

### P0 — 正确性风险

1. **`Id_map` 的查询条件逻辑错误**（location_ID.py:55）——【已决策：整体下线，不修复】
   `Q(geneid__in=norm_map) | Q(genome_id__in=genome_ids)` 是「或」关系：只给 genome_id 也会命中该物种**全部**基因的 alias 映射，然后 `attach_db_id` 用 `search_id`（`genome_geneid`）去字典里取，多数取到 None。Meilisearch 命中结果已自带 id，此函数及其 URL 端点（`Id_map/`）与 views 中的回退分支一并移除即可，问题随之消失。

2. **`gene_seq` 的 `__str__` 引用不存在的属性**（models.py:267 `return str(self.geneid)`）——模型无 `geneid` 字段，任何 admin/日志触发 `str()` 即抛 AttributeError。

3. **`mran_id` 解析脆弱**（gene_id_result.py:162）：从 `attributes` 文本里 `split(';')[0].split('=')[1]` 取 mRNA ID，属性顺序一变就崩或取错；且未捕获 IndexError。

### P1 — 性能

4. **gene_seq 按序列取数是 N+1 × 6**：每个转录本 6 次独立 `filter().first()`。应一次 `filter(mrna_id__in=..., gene_type__in=...)` 后在内存分组。序列迁移到 pysam 文件提取后此问题整体消失。

5. **序列存 DB 本身**：基因/CDS/蛋白序列全部以 TextField 入库，是库膨胀的主因（迁移 0045-0047 显示已在重塑该表）。FAI 索引随机读取是 O(1)，且 .gz 版本省一个数量级磁盘。

6. **`geneid_summary` 对 `gene_go/gene_kegg` 用 `.values()` 无字段裁剪**，注释拆表后应只取需要的列。

### P2 — 结构/可维护性

7. **视图层职责混杂**：HTTP 解析、权限、业务编排、SQL 全在一个函数里（如 geneid_result 200 行）。缺 service/repository 层。
8. **响应风格不统一**：DRF `Response` 与 Django `JsonResponse`+`csrf_exempt` 混用；错误格式有 `{success, error}` 与 `{error}` 两种。
9. **单 app 巨石**：22 个模型、30 个路由都在一个 app。`apps.py` 存在但 Browse 等子 app 被注释。
10. **重复实现**：Meilisearch 有两个端点（`search_genes/` 与 `search_genes_meilisearch/`），`views/search_genes` 与 `server/` 的搜索封装存在职责重叠。
11. **硬编码索引名** `'genemaster'` 在视图里写死，应进 config。

---

## 三、优化建议（未应用，供决策）

### 阶段 1：低风险修正（不影响接口形状）

1. **下线 Id_map**：删除 `views/location_ID.py` 及 urls 中的 `Id_map/` 端点；`geneid_result`/`geneid_summary` 的参数收敛为 `db_id`（即 Meilisearch 返回的 `id`），删除 gene_id+genome_id 回退分支。前端搜索页点击结果时直接把命中项的 `id` 传给详情接口——这是本阶段最大的提速来源（省掉一次 DB 全表 alias 映射 + 省掉一轮往返）。
2. 修复 `gene_seq.__str__`、`mran_id` 解析加防御。
3. 把 `INDEX_NAME`、`MAX_LIMIT` 等移入 `config/meilisearch_config.py`。

### 阶段 1.5：页面搜索/详情提速（基于「Meilisearch 自带 id_id」）

- **请求次数**：搜索一次 Meilisearch（毫秒级）→ 前端持 id → 详情接口一次拿全。不再出现「gene_id+genome_id → Id_map 查库 → 再查详情」的两段式。
- **详情接口内部并行**：`gene_annotation / gene_info / gene_go / gene_kegg` 四组查询互相独立，可用 Django `concurrent.futures`（或保持顺序但都走 `id_id__in` 索引单次 IN 查询）消除串行等待；注释三表查询用 `select_related('source', 'annotation_detail')` 避免 N+1。
- **去掉双重序列化**：`geneid_result` 返回 `json.dumps(results)` 后 DRF 又渲染一遍 JSON，前端还要 `JSON.parse` 两次——直接返回 dict，Content-Type 正确且省 CPU。
- **Meilisearch 索引瘦身**：`genemaster` 索引只放 `id/geneid/alias/genome_id` 四字段已经正确；把 `attributesToHighlight` 收敛到 `geneid/alias`，避免 `_formatted` 携带冗余对象。前端可考虑直连 Meilisearch（search-only key 已在 config 中规划）进一步省掉 Django 一跳，详情再回 Django。
- **缓存**：详情页对同 id 的注释/GO/KEGG 结果基本不变，可用现有 `SearchCache` 模型或进程内 LRU 做短 TTL 缓存（序列不用缓存，pysam 提取本身是 O(1) 随机读）。

### 阶段 2：序列层迁移到 samtools/htslib 体系（核心变更，按用户澄清修正）

思路与 `samtools faidx ref.gz chr:beg-end` 完全一致，但用 Python 库 **pysam**（`pysam.FastaFile`，底层就是 htslib）在 Django 进程内完成，不 shell out；通过 **`functools.lru_cache(maxsize=20)` 缓存已打开的基因组文件句柄**，避免每次请求重新 open（物种很多，打开开销大；只保留最近 20 个基因组）。

`pysam==0.24.0` 已在 requirements.txt；现有 `data/Genome/genome/*.genome.fa.gz` 已带 `.fai` + `.gzi`，与 pysam.FastaFile 的要求完全匹配（bgzip 压缩的 FASTA 必须同时有 faidx 和 gzi 索引，pysam 与 samtools 读取方式相同）。

新建 `server/seq_fetch.py`（唯一序列出口）：

```python
from functools import lru_cache
from django.conf import settings
import pysam

GENOME_DIR = settings.BASE_DIR / 'data' / 'Genome' / 'genome'  # 注意：目录名是小写 genome/
GENOME_FILE = '{genome}.genome.fa.gz'                          # 已有 .fai/.gzi

@lru_cache(maxsize=20)   # 按用户要求：缓存 20 个已打开的基因组文件句柄
def _open_fasta(genome_name: str) -> pysam.FastaFile:
    return pysam.FastaFile(str(GENOME_DIR / GENOME_FILE.format(genome=genome_name)))

def fetch_seq(genome_name: str, seqid: str, start: int, end: int, strand: str = '+') -> str:
    """坐标换算：GFF 1-based inclusive -> pysam/htslib 0-based half-open"""
    fa = _open_fasta(genome_name)
    if seqid not in fa.references:
        return ''
    seq = fa.fetch(seqid, start - 1, end)   # 与 samtools faidx chr:beg-end 同语义
    if strand == '-':
        seq = _revcomp(seq)
    return seq

_COMPLEMENT = str.maketrans('ACGTNacgtn', 'TGCANtgcan')
def _revcomp(seq: str) -> str:
    return seq.translate(_COMPLEMENT)[::-1]
```

要点：
- **等价性**：`pysam.FastaFile.fetch(ref, start, end)` 与 `samtools faidx` 使用同一 htslib 索引与解码路径，结果一致；不需要额外维护 pyfaidx。
- **句柄缓存**：`lru_cache(20)` 以 genome_name 为 key；Django 多 worker（gunicorn/uwsgi）下每个进程各自持有缓存，20 个句柄内存可控。如后续物种超过 20 且访问热点集中，可调大 maxsize 或改为按「最近访问」淘汰的 OrderedDict。
- **按 ID 提取**：`samtools faidx` 支持整条序列提取（只给 seqid 不给区间），pysam 里即 `fa.fetch(seqid)`，用于 cds/cdna/pep 产物文件（这些文件若也做 bgzip+faidx 索引，同样走此函数，传 start=1, end=fa.get_reference_length(seqid) 即可）。
- **基因序列（gene/genome 类型）**：用 gene_info 的 seqid/start/end 直接从基因组 fa.gz 提取——这一类完全可以删库存储。
- **mRNA/cds/cdna/pro/upstream/downstream**：这些是**拼接产物**，无法只靠基因组 fa.gz 还原。方案 B（推荐）：为 `data/Genome/{cdna,cds,pep,mrna,longest}` 下已有产物文件统一做 bgzip+faidx（`bgzip` 后 `samtools faidx`），然后全部经由 `_open_fasta`/`fetch_seq` 提取，句柄缓存同样生效；DB 只存坐标或完全不存。
- **gene_seq 表退役（已决策）**：新接口不再读写 `gene_seq`；模型、`extract_seq` 等引用点随阶段 2 切换后一并清理，后续迁移删表释放空间。如需保险，可保留只读灰度一周（文件读取失败时回退 DB），到期删除。
- **批量优化**：`geneid_result` 里同一转录本要取 6 种序列，cds/mrna 等若走产物文件则各取一次；若走基因组提取则可把 gene_info 的 exon/CDS 行一次查出后在内存拼接，避免重复 fetch。

### 阶段 3：分层落地

```
views/     仅 HTTP：参数校验（DRF Serializer）、调 service、统一响应包 {success,data,error}
services/  业务编排：GeneDetailService(geneid_result/summary)、SequenceService、AnnotationService
server/    外部引擎适配：blast/hmmer/mmseqs/meilisearch 客户端（保持现状，收敛命名）
models/    拆成 models/ 包：master.py / annotation.py / sequence.py / expression.py / ontology.py
urls.py    按资源分路由 include
```

统一：全部走 DRF `api_view` + Serializer，去掉 `csrf_exempt`（前后端分离用 session/token 认证时更安全），响应包统一。

### 阶段 4：其他

- `gene_info.id_id` 的裸 IntegerField 建议改为真外键（迁移 0044-0049 已在向这个方向走）；`gene_seq` 退役后其索引问题随之消失。
- Meilisearch 双端点收敛为一个；`pagination.maxTotalHits` 按需调大以支撑 MAX_OFFSET=9900。
- 加最小化测试（尤其 seq_fetch 的坐标换算：FAI 0-based vs GFF 1-based，是此类迁移最高发的 off-by-one 来源）。

---

## 四、风险提示

1. **坐标换算**：GFF 1-based inclusive → pysam/htslib 0-based half-open；负链要 revcomp；upstream/downstream 在负链基因上方向相反。这是本次改造最容易出隐性 bug 的点，务必用几个已知基因做 golden-case 校验。
2. **bgzip 行长**：确认 .fai 与实际文件一致（重新生成过 .gz 就必须重建 .fai）。
3. **并发**：pysam.FastaFile 不要跨线程共享句柄（Django 多 worker 下 lru_cache(20) 是按进程独立的，天然满足；多线程共享同一 FastaFile 需注意）。

## 五、验证动作记录（实事求是）

- 实际读取了 Meilisearch.py / gene_id_result.py / location_ID.py / models.py / urls.py / meilisearch_config.py。
- 实际列出了 `data/Genome/genome/`：确认存在 `*.genome.fa.gz + .fai + .gzi` 三件套；`requirements.txt` 已含 `pyfaidx==0.9.0.3`。
- 未运行服务、未改任何文件。

---

## 六、实施与验证记录（2026-09-14）

### 已实施

| 项 | 内容 |
|---|---|
| 新建 `CottonOGD/server/seq_fetch.py` | pysam.FastaFile（htslib，与 samtools faidx 同源）+ `lru_cache(maxsize=20)` 句柄缓存；支持按 ID 整条提取（`fetch_by_id`）与按基因组坐标提取（`fetch_region`，含负链 revcomp、1-based→0-based 换算）；文件/索引缺失返回 None 由调用方回退 |
| 重写 `views/gene_id_result.py` | `Id_map` 调用移除；`db_id` 优先，gene_id+genome_id 回退改为经 Meilisearch `search_genes()` 解析 id；`geneid_result/geneid_summary` 均生效；响应改为原始 dict（去掉 `json.dumps` 双重序列化）；mRNA ID 解析改为 `parse_mrna_ids`（按 `ID=` 键取值，防御性） |
| 序列读取策略 | 文件优先（genome 走坐标、cdna/cds/pro/mrna 走产物文件 faidx），失败自动回退 `gene_seq` 表；**gene_seq 表保留未删、数据未动** |
| 配置收敛 | `INDEX_NAME / MAX_LIMIT / MAX_OFFSET / RETRIEVE_FIELDS` 移入 `config/meilisearch_config.py` |
| 修复 | `gene_seq.__str__` 引用不存在属性的问题（models.py:265） |

### 未实施（保持现状）

- `location_ID.py` 模块与 `Id_map/` 端点保留：`primer_design / gene_expression / extract_seq / genome_api` 仍在 import，贸然删除会连带破坏这些功能；仅页面搜索主链路已解耦。后续随这些模块逐步迁移后统一下线。
- gene_seq 表删除、阶段 3 分层重构、阶段 4 项均未动。

### 验证结果（实测）

1. `manage.py check`：0 issues。
2. 基因序列坐标提取：`fetch_region('G.hirsutumAD1_ZY10_HAU_v1','ZY10_A01',57980,62775)` → 4796bp，与 gene_seq 表该基因序列**逐字节一致**。
3. samtools CLI 对拍：`samtools faidx ... ZY10_A01:57980-62775` 输出与 `fetch_region` 结果**一致**（忽略大小写完全相同）。
4. 转录本序列：ZY10_A01000010.1 的 cdna/cds/pro/mrna 四类，文件提取与 gene_seq 表（经 id_id 索引查询）**全部一致**（1314/1314/437/4796bp）。
5. 旁证：按 `mrna_id` 查 gene_seq 表触发 MySQL 全表扫描超时（该字段无索引）——印证序列改走文件提取的必要性。

### 补充（2026-09-14）：转录本 ID 解析

问题：用户输入常为转录本 ID（带版本号，如 `Gano_01G000010.1`），而 `genemaster` 索引只含去版本号的基因 ID，导致部分输入搜不到/命中噪音。

已在 `views/Meilisearch.py::search_genes()` 内实现三级解析（搜索接口与详情解析共用，`resolve_db_ids` 自动受益）：
1. 原始 query 查索引；
2. 0 命中且带版本号 → `normalize_gene_query()` 去掉 `.1/.t1` 后重试；
3. 仍 0 命中 → TranscriptMaster 兜底（`transcriptid` 有索引，1797 万行），返回合成 hit：`id` = 所属基因的 GeneMaster 主键，`match_type='transcript'`，支持 genome_id 过滤。

验证：`_transcript_fallback('Gano_01G000010.1')` → id=1447 → GeneMaster.geneid=`Gano_01G000010`，正确；物种过滤生效（正确物种 1 条、错误物种 0 条）。

长期方案（未实施）：重建 `genemaster` 索引时在基因文档中内嵌 `transcripts` 数组（或在 rebuild_index 中增加 transcriptmaster 索引 + multi-search），把兜底从 DB 查询彻底移入 Meilisearch。

### 补充（2026-09-14）：get_family_info 400 修复

根因：`UuidManager.uuid_storage` 是进程内存 dict——daphne 重启（当日 00:15）后全部会话丢失，前端持旧 uuid 请求即 400；多 worker 部署下同样必现。

修复：`views/base.py` 中 `UuidManager` 改为 Redis 缓存（settings.CACHES，已配置）承载：`uuid_storage` 换成 `_CacheSessionMap` 代理对象（实现 `__contains__/get/pop` 等），9 处 `uuid not in UuidManager.uuid_storage` 校验零改动；会话 TTL 24 小时；`logout` 顺带补上原本缺失的会话条目删除（此前只删临时目录）。

验证：add → 校验通过 → delete → 校验失败，全程落 Redis；`manage.py check` 0 issues。

### 补充（2026-09-14）：token / cookie / 会话校验

- 新建 `CottonOGD/auth.py`：`issue_token / revoke_token / resolve_token`（Redis，`auth_token:` 前缀，TTL 7 天）+ `ClientTokenMiddleware`。
- `/login/` 改为服务端生成 uuid、签发 token、返回体携带 `token` 并种 HttpOnly+SameSite=Lax 的 `auth_token` cookie；`/logout/` 同时吊销 token、清会话、删 cookie。
- 中间件把有效 token（header Bearer 优先、cookie 兜底）桥接为 `HTTP_UUID`，既有 9 处 `uuid not in UuidManager.uuid_storage` 校验零改动继续生效；过渡期裸 uuid header 仍可用。
- 端到端验证（Django test client）：login 200 → Bearer 访问 200 → 仅 cookie 访问 200 → 无凭证 400 → logout 后 400。

### 补充（2026-09-15）：annotation / enrichment / primer 迁移到新体系

- 抽出公共解析 `resolve_input_ids(raw_gene_id, genome_id)`（gene_id_result.py），脱离 request，供各视图复用：多 ID 分割 → Meilisearch 精确命中 → MySQL 兜底。
- `gene_Go.py`：`go_annotation` / `go_enrichment` 去掉裸 SQL 与 `geneid IN` 匹配，改 ORM（`gene_go` 通过 `go_id` 外键取 term 名称/namespace；背景按 `id_id__genome__name` 圈定）；GET/POST/JSON body 统一取参；响应结构不变。
- `gene_Kegg.py`：`kegg_annotation` / `kegg_enrichment` 同样迁移；KO→通路沿用 `PathwayEnzyme` 联结语义，基因坐标从 `gene_info` 取回；响应结构不变（含 chart / plot_image）。
- `primer_design.py`：新增按需取序列——请求未带 `sequence` 时，用 `db_id` 或 `gene_id`(+`genome_id`) 经 `resolve_input_ids` 定位基因，再用 `seq_fetch.fetch_region` 从基因组 fa.gz 提取；直接传 `sequence` 的旧行为保留。

验证（Django test client + 真实数据，G.anomalumB1_HAU_v1）：
- go_annotation：多 ID（逗号分隔，含带版本号转录本）→ 200，136 行 + 图表；无注释基因 → 200 空结果不报错。
- kegg_annotation：200，40 行含通路/分类，坐标正确（Chr13:70423237-70425414）。
- go_enrichment / kegg_enrichment：200，input=1，结果 66 / 1 条。
- primer_design：gene_id → 4 对引物；db_id → 4 对；直接传 sequence 兼容；非法 ID → 400 且错误信息明确。
- `manage.py check`：0 issues。
