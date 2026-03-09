# CottonOGD Frontend Logic Map

## 1) 目标

这份文档用于把你提到的前端文件按职责归位，减少“页面里又拿数据又做转换又做展示”的混杂写法。

## 2) 当前统一规则

- 基因组选择与默认值逻辑统一走 `src/composables/useGenomeBrowser.ts`
- 不再在页面内重复写 `genomeStore.fetchGenomes()` + 默认基因组硬编码
- 页面只保留“页面专属行为”，通用行为放 composable/store

## 3) 本次已统一的页面

- `src/views/IGVView.vue`
- `src/views/JbrowseView.vue`
- `src/views/TFView.vue`
- `src/views/TRView.vue`
- `src/views/PrimerView.vue`
- `src/views/BlastpView.vue`
- `src/views/GeneExpressionView.vue`
- `src/views/GeneExpressionEfpView.vue`
- `src/views/IdSearchView.vue`
- `src/views/DownloadView.vue`

这些页面的共同点：

- 全部改为依赖 `useGenomeSelector / ensureGenomesLoaded / pickDefaultGenome`
- 移除了分散在页面中的重复 genome 初始化逻辑

## 4) 模块职责分层

### A. Views（页面层）

页面层只做三件事：

- 组织布局与交互
- 调用 composable/store
- 处理页面级反馈（loading/error）

不建议在页面层做：

- 通用数据路径拼接
- 通用默认值策略
- 可复用的数据清洗算法

### B. Composables（复用逻辑）

- `useGenomeBrowser.ts`：基因组选择、默认值、路径与默认 locus
- `useAsyncTask.ts`：异步任务轮询
- `useSequenceCache.ts`：序列缓存
- `useLengthSelector.ts`：长度选择状态
- `useModal.ts`：序列弹窗行为

原则：页面间重复 >= 2 次，就应迁到 composable。

### C. Stores（业务状态）

- `genome_info.ts`：基因组数据源与缓存
- `familyInfo.ts`：TF/TR family 数据
- `blastStore.ts`：BLAST 表单与提交状态
- `geneExpressionStore.ts`：表达分析结果状态
- `geneSearch.ts`：ID 搜索流程状态
- 其他 store：维持单一职责，不放 UI 细节

原则：store 负责“状态与业务数据”，不负责 DOM 行为。

### D. Components（展示组件）

- `GeneInfoCard.vue`
- `SequenceDisplay.vue`
- `SequenceModal.vue`
- `TranscriptSelector.vue`
- `LanguageSelector.vue`

原则：组件尽量“可复用 + 输入输出清晰”，避免请求 API。

## 5) 你提到的文件如何理解

- `App.vue` + `router/index.js`：全局壳与路由编排
- `views/*.vue`：页面入口，每页只保留页面专属流程
- `stores/*`：状态中心
- `composables/*`：可复用逻辑中心
- `components/*`：纯展示/交互组件

## 6) 后续整理建议（下一轮）

- 把 `TFView.vue` 与 `TRView.vue` 的大量重复表格流程再抽一个 `useFamilyTable` composable
- 把 `PrimerView.vue` 的序列提取与染色体处理抽成 `usePrimerSequenceSource`
- 统一页面里的日志输出风格，保留必要错误日志，移除调试日志

## 7) 快速检查清单

- 新页面若涉及基因组：必须先用 `useGenomeSelector`
- 页面中出现第二处相同算法：立刻迁 composable
- store 中不写 DOM 操作
- component 中不直接请求后端（除非明确设计为容器组件）

