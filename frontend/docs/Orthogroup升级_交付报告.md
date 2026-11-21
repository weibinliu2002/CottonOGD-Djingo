# Orthogroup 页面升级 交付报告

- 交付日期：2026-11-21
- 分支：`development`
- 基线：`aa0d11fc`（标签 `before-v1-migration`）；本次交付提交：`a839bdef`、`16c3acc2`、`b0fa0e14`
- 范围：CottonOGD 前端 Orthogroup 页面就地升级 + 全站 API 迁移到 v1
- 不在范围：基因家族（iTAK 分类、家族成员、iTAK 树、domain、motif）

---

## 1. 交付物清单

### 1.1 修改文件

**API 层（v1 迁移，提交 `a839bdef`，30 个文件）**

| 文件 | 改动 |
|---|---|
| `src/utils/http.js` | 统一信封解包、`auth/session`、`auth/refresh`、匿名重登仅限 `ai/*` |
| `src/utils/api.ts` | `ApiEnvelope` / `V1ErrorBody` 类型，注释说明解包语义 |
| `src/api/index.ts` | 全站 60 个 v1 端点写法；orthofinder 域全部重写 |
| `src/stores/modules/{auth,blast,family,genome,geneSearch,enrichment}.ts` | 路径迁移 |
| `src/utils/{meiliSearchApi.ts,meilisearch.js}` | 路径迁移；`meilisearch.js` 保留旧返回形状 |
| `src/composables/{core/useAsyncTask.ts,features/useSequenceCache.ts}` | 路径迁移 |
| `src/components/{search/GlobalSearch.vue,home/ChatWidget.vue}` | 路径迁移 |
| `src/views/common/HomeView.vue` | 路径迁移 |
| `src/views/{genome/GenomeSyntenyView.vue,sequence/*.vue,tools/PrimerView.vue,test/ProteinViewerTest.vue,annotation/*.vue,enrichment/*.vue,expression/*.vue}` | 路径迁移 + 响应形状适配 |

**Orthogroup 收尾修复（提交 `16c3acc2`，8 个文件）**

| 文件 | 改动 |
|---|---|
| `src/api/index.ts` | 新增 `resolveOrthoGeneId`（基因级接口的 ID 归一） |
| `src/components/data-display/OrthogroupAnalysis.vue` | echarts 默认导入；基因级查询接入 ID 归一；成员行优先 `ortho_gene` |
| `src/components/data-display/OrthofinderStatistics.vue` | echarts 默认导入；复制事件 `value` 对象展示、`rows` 字典展开与截断提示 |
| `src/utils/echarts.ts` | 修正使用说明（禁止命名空间导入） |
| `src/views/ortholog/OrthogroupDetailView.vue` | 复制按钮改用 `CopyDocument`；文档引用更新 |
| `src/views/ortholog/OrthologView.vue` | 文档引用更新 |
| `src/locales/i18n/{zh-CN,en-US}.json` | 各 +4 个键（复制事件文案），双语保持对齐 |

**文档（提交 `b0fa0e14`）**

| 文件 | 说明 |
|---|---|
| `docs/COMPARATIVE_ANALYSIS_API_HANDOFF.md` | 重写为 v2.0（v1 契约 + 实测响应 + 差异清单） |
| `docs/api/*`（7 个文件） | 与服务器 `backend/docs/api/` 逐字节一致的契约快照 |
| `docs/Orthogroup升级_现状审查报告.md` | 纳入版本库（数据口径来源） |

### 1.2 新增组件

| 组件 | 行数 | 职责 |
|---|---|---|
| `src/components/data-display/OrthogroupAnalysis.vue` | 1012 | 单个 OG 的分析面板：概览 / 成员 / 直系同源 / HOG / 复制事件 / MSA / 基因树 / 序列，8 个页签按需加载 |
| `src/components/data-display/OrthofinderStatistics.vue` | 658 | 统计面板：总体 / 每物种 / Ortholog / 复制事件 / 物种重叠 + 基因组对共享 OG |

两个组件在基线 WIP 中已存在，本次完成 v1 对接、缺陷修复与语义校验。

### 1.3 页面组件结构

```
/tools/orthogroup                    OrthologView.vue (975 行)
├── 页签 1「按基因组浏览」
│   ├── 左侧：基因组树（按 Genome_type 分组、搜索、全选/清空、已选/总数）
│   ├── 筛选栏：OG 编号（精确/模糊）、基因数、物种数、覆盖数、单拷贝、all/any、排序、每页条数
│   ├── 主表：OG ID / 基因数 / 物种数 / 所选物种覆盖 / 单拷贝标签（服务端分页）
│   ├── 行点击 → 抽屉（OrthogroupAnalysis compact）
│   └── 底部折叠面板：OrthofinderStatistics（展开才加载）
└── 页签 2「按基因查」
    └── Meilisearch Orthologs 索引检索 + 成员分页

/tools/orthogroup/:og_code           OrthogroupDetailView.vue (96 行)
└── 壳页面：返回、OG 编号、复制按钮 + OrthogroupAnalysis（?species= 回显）
```

### 1.4 API 映射（前端函数 ↔ v1 端点）

| 前端函数 | v1 端点 | 消费方 |
|---|---|---|
| `getOrthofinderMeta` | `GET orthofinder/meta/` | 基因组树 |
| `getOrthologBySpecies` | `POST orthogroups/search/` | 主表 |
| `getOrthogroupDetailV2` | `POST orthogroups/detail/` | 概览 |
| `getOgMembers` | `POST orthogroups/members/` | 成员分页 |
| `getOrthologByGene` | `POST genes/orthogroups/` | 按基因查 OG |
| `getGeneOrthologs` | `POST genes/orthologs/` | 直系同源 |
| `getGeneHog` / `getHogDetail` | `POST genes/hogs/`、`POST hogs/detail/` | HOG |
| `getGenomePair` | `POST genome-pairs/` | 共享 OG |
| `getSpeciesTree` | `GET species/tree/` | 物种树 |
| `getOrthofinderStatistics` | `GET statistics/` | 统计面板 |
| `getOrthogroupSequence` / `getOrthogroupMsa` / `getOrthogroupTree` | `GET og/<og>/{sequences,msa,tree}/` | 序列 / MSA / 树 |
| `getOrthofinderTandem` | `GET og/<og>/tandem/` | 复制事件 |
| `resolveOrthoGeneId` | 内部两次 `genes/orthogroups/` | 基因级查询 ID 归一 |

---

## 2. 原有功能保留情况

| 原有功能 | 状态 | 说明 |
|---|---|---|
| 基因组选择（搜索/多选/清空/全选/提交/计数） | 保留 | 左侧树交互未改 |
| 按基因组筛选 OG（交集/并集） | 保留 | `mode=all/any` 原样传递，默认 `all` |
| OG ID 展示 | 保留 | 主表与详情页一致 |
| 所选基因组内的 OG 成员 | 保留 | 概览按所选物种计数，成员页签分页 |
| MSA 展示 | 保留 | 组件未换，端点改为 v1，缺失时“暂未就绪” |
| 基因树展示 | 保留 | 复用 `PhylocanvasViewer`，端点改为 v1 |
| `?og=` 深链、`/tools/orthogroup/:og_code` 路由 | 保留 | 未改路由表 |
| 导航入口（Tools 下拉、首页卡片） | 保留 | 未改 |
| 基因家族相关页面 | 未触碰 | 范围外 |

**验证方式**：升级后页面发出的查询参数与升级前逐项一致（物种数组、`mode`、筛选值、分页），
返回数据来自同一份 OrthoFinder 输出的 v1 接口；关键总量（258 物种、121,061 OG、
17,156,178 OG 内基因、严格单拷贝 0）与升级前文档记录一致。

---

## 3. 新增功能说明

1. **OG 详情抽屉/详情页**：8 个页签，模块独立加载、失败互不阻塞。
2. **成员分页**：66,532 成员的 OG 不再整包渲染，每页 50。
3. **真实直系同源**：仅使用 `genes/orthologs`（OrthoFinder `Orthologues/` 输出），
   与“同 OG 成员”“共享 OG”明确区分文案。
4. **HOG**：基因 → 最深 HOG → HOG 详情成员。
5. **复制事件**：汇总 + 明细分页；全部 OG 概览只展开前 200 条并提示总数。
6. **统计面板**：总体指标原样展示（不在前端重算）；每物种指标可切换柱图；
   Ortholog 物种两两矩阵按需加载；物种重叠未生成时明确提示不可用。
7. **筛选增强**：OG 编号精确/模糊、基因数/物种数/覆盖数范围、单拷贝、排序。
8. **按基因查 OG**：Meilisearch 检索 + 成员分页。

---

## 4. 测试结果

| 项目 | 结果 |
|---|---|
| `npm run build-only`（基线） | 通过，23.4 s |
| `npm run build-only`（v1 迁移后） | 通过，19.5 s |
| `npm run build-only`（本次收尾） | 通过，19.36 s |
| 真实接口联调（dev 代理 `localhost:5713` → 线上后端） | 通过：meta、search、detail、members、genes/*、hogs/detail、genome-pairs、species/tree、tandem、statistics 各 type、MSA 404 语义 |
| 大文件 | 基因树 Newick 流式返回正常；MSA（OG0013470 约 147 KB）正常；缺失时 JSON 404 |
| 浏览器渲染（canvas 图表） | **未验证**：本次仅有 dev server + curl，未做真实浏览器截图确认 |

已发现并修复的问题：

- `import * as echarts from '@/utils/echarts'` 拿到的是模块命名空间，没有 `init`（两个组件都中招）；
- 基因级接口只认带 `.1` 后缀的 OrthoFinder ID，原实现传 `genemaster_geneid` 必然查不到；
- 复制事件 `value` 为对象时原实现显示 `[object Object]`；`rows` 为字典时表格空白。

---

## 5. 仍需后端完善（实测确认）

1. `hogs/detail/` 服务器文档写 `hog_code`，实现读 `hog_id`。
2. `species_overlaps` 因未生成 `Orthogroups_SpeciesOverlaps.tsv` 不可用。
3. 统计错误码不一致：未知 `type` → 40002，未知 `kind` → 40401，未知 `scope` 静默回退。
4. 基因级接口的 ID 后缀规则未写入文档。
5. `duplications` 全量 `rows`（8 万余 OG）无分页。
6. 旧路径未双挂载（旧 GET → SPA HTML）。
7. `tf_tree` 非信封端点未列入 v1 文档。

---

## 6. 四类信息分离

**代码中可确认的事实**：文件清单、函数映射、组件结构、构建结果、`resolveOrthoGeneId` 行为、
统计面板的字段读取、MSA/树/序列的按需加载与 404 降级。

**外部/后端事实（以服务器文档与实测为准）**：v1 路径与信封、错误码、各端点的实际响应字段、
`hogs/detail` 参数名差异、`species_overlaps` 不可用、文件缺失返回 JSON 404。

**推断**：MSA/基因树“多数 OG 没有”是按报告口径（100,453 / 84,829）与总 OG 数（121,061）推得的比例；
浏览器端的视觉表现未经截图验证。

**待验证**：严格单拷贝定义的完整实现细节（来自审查报告，未读后端源码逐行核对）；
`tf_tree` 路由在线上长期可用性（仅做了一次探测）；第三方登录回调在新域名下的行为。