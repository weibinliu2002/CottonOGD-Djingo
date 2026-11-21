/**
 * 统一 API 层（阶段 2）
 *
 * 设计目标
 * 1. 每个后端接口对应一个具名函数，页面/组件只依赖本模块，不再散落裸 axios / httpInstance 调用。
 * 2. 内部统一响应适配：无论后端当前返回什么包裹格式，对外一律暴露 { code, message, data }。
 *    后端将来按此格式实现后，只需删掉各 adapter 里的兼容分支，调用方零改动。
 * 3. 后端尚未实现的接口走 mock：由 USE_MOCK 开关控制，接口就绪后改一行即可切换。
 *
 * 约定
 * - code === 0 表示成功；非 0 为失败，message 为可直接展示的中文文案。
 * - 认证、401 自动重登重放、CSRF 头均由 utils/http.js 的拦截器统一处理，本层不重复实现。
 * - 本层不做全局响应拦截抽象：后端各接口包裹格式差异较大（见 docs/API.md），逐接口适配更稳。
 */
import httpInstance from '@/utils/http.js'
import { parsePpiNetwork, type PpiNetwork } from '@/utils/ppiNetwork'

// ==================== 通用类型 ====================

/** 统一响应包裹：前端按此格式封装，后端将来按此实现 */
export interface ApiResult<T = unknown> {
  /** 0 为成功，非 0 为失败 */
  code: number
  /** 可直接展示的提示文案 */
  message: string
  /** 业务数据 */
  data: T
}

/** 失败时的默认文案 */
const DEFAULT_ERROR_MESSAGE = '请求失败，请稍后重试'

// ==================== mock 开关 ====================
// 后端接口就绪后，把对应开关置为 false（或整体关闭 USE_MOCK）即可切换到真实接口。
// 也可在 .env.local 用 VITE_USE_MOCK=false 整体关闭。
const FORCE_REAL = import.meta.env?.VITE_USE_MOCK === 'false'

const MOCK_FLAGS = {
  /** 后端无 /CottonOGD_api/news/ 路由 */
  news: true,
  /** 后端无 orthogroup 相关路由，且 OrthoFinder 产物不存在 */
  orthogroups: true,
  /** 后端无 /CottonOGD_api/gene_expression/（GET）路由 */
  geneExpression: true,
  /** 后端无 go_enrichment_results / kegg_enrichment_results 路由 */
  enrichmentResults: true,
}

/** 单个 mock 开关的最终取值：全局强制真实时一律走真实接口 */
function shouldMock(key: keyof typeof MOCK_FLAGS): boolean {
  if (FORCE_REAL) return false
  return MOCK_FLAGS[key] === true
}

// ==================== 适配工具 ====================

/** 成功包裹 */
function ok<T>(data: T, message = ''): ApiResult<T> {
  return { code: 0, message, data }
}

/** 失败包裹 */
function fail<T>(message: string, data?: T): ApiResult<T> {
  return { code: -1, message: message || DEFAULT_ERROR_MESSAGE, data: (data ?? null) as unknown as unknown as T }
}

/**
 * 安全解析"字符串化的 JSON"。
 * 后端若干接口（get_species_info / get_family_info / blast_cmd）返回字符串而非对象，
 * 另外 geneid_* 系列返回的是真实对象——误解析会抛异常，故统一走这个兜底函数。
 */
function parseMaybeJson<T>(value: unknown, fallback: T): T {
  if (typeof value !== 'string') return (value as unknown as T) ?? fallback
  try {
    return JSON.parse(value) as unknown as unknown as T
  } catch {
    return fallback
  }
}

/** 把未知错误规整为文案 */
function toMessage(err: unknown): string {
  if (!err) return DEFAULT_ERROR_MESSAGE
  const anyErr = err as { response?: { data?: { message?: string; error?: unknown } }; message?: string }
  const data = anyErr.response?.data
  if (data?.message) return String(data.message)
  if (data?.error) {
    // DRF 字段级错误是对象，如 {"sequence": ["Ensure this field has at least 5 characters."]}
    return typeof data.error === 'string' ? data.error : JSON.stringify(data.error)
  }
  if (anyErr.message) return anyErr.message
  return DEFAULT_ERROR_MESSAGE
}

// ==================== 一、认证与会话 ====================

/** 登录：由 http.js 拦截器自动调用，页面一般无需直接调用 */
export async function apiLogin(): Promise<ApiResult<{ token: string; uuid: string }>> {
  try {
    const data = await httpInstance.post('/CottonOGD_api/login/')
    return ok(data as unknown as { token: string; uuid: string })
  } catch (e) {
    return fail(toMessage(e))
  }
}

// ==================== 二、物种与家族信息 ====================

/** 物种条目（对应后端 species 表） */
export interface SpeciesInfo {
  id?: number
  name?: string
  alias?: string
  Cotton_Species?: string
  Genome_type?: string
  Category?: string
  Accession?: string | null
  Ploidy?: string
  Assembling_institution?: string
  Website?: string | null
  Article?: string
  LAI_value?: string
  Busco?: string
  Genome_size?: number | null
  description?: string | null
  common_name?: string
  assembly_version?: string
  annotation_version?: string
  submitter?: string
}

/**
 * 获取全部物种/基因组信息。
 * 后端返回 { species_info: "<JSON 字符串>" }，需手动解析（已由 parseMaybeJson 兜底）。
 */
export async function getSpeciesInfo(): Promise<ApiResult<SpeciesInfo[]>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/get_species_info/')
    const raw = (res as { species_info?: unknown })?.species_info
    const list = parseMaybeJson<SpeciesInfo[]>(raw, [])
    return ok(Array.isArray(list) ? list : [])
  } catch (e) {
    return fail<SpeciesInfo[]>(toMessage(e), [])
  }
}

/** 家族聚合信息 */
export interface FamilyInfo {
  name: string
  count: number
}

/** 家族明细条目 */
export interface FamilyItem {
  id?: number
  geneid?: string
  genome_id?: number | string
  TF_class?: string
  class_name?: string
  TF_name?: string
}

/** 家族信息响应 */
export interface FamilyInfoResult {
  familyInfo: FamilyInfo[]
  familyList: FamilyItem[]
}

/**
 * 获取基因家族信息（TF / TR / kinase）。
 * 入参对应后端 { selectedGenome, Class }（注意 Class 首字母大写）。
 * 后端两个字段都是字符串化 JSON。
 */
export async function getFamilyInfo(params?: {
  selectedGenome?: string
  Class?: 'TF' | 'TR' | 'kinase' | string
}): Promise<ApiResult<FamilyInfoResult>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/get_family_info/', {
      selectedGenome: params?.selectedGenome ?? '',
      Class: params?.Class ?? '',
    })
    const data = res as { family_info?: unknown; family_list?: unknown }
    const familyInfo = parseMaybeJson<FamilyInfo[]>(data?.family_info, [])
    const familyList = parseMaybeJson<FamilyItem[]>(data?.family_list, [])
    return ok({
      familyInfo: Array.isArray(familyInfo) ? familyInfo : [],
      familyList: Array.isArray(familyList) ? familyList : [],
    })
  } catch (e) {
    return fail<FamilyInfoResult>(toMessage(e), { familyInfo: [], familyList: [] })
  }
}

// ==================== 三、基因 ID 解析与详情 ====================

/** 基因摘要结果 */
export interface GeneidSummary {
  geneid_result?: unknown[]
  gene_info_result?: unknown[]
  gene_go_result?: unknown[]
  gene_kegg_result?: unknown[]
  [key: string]: unknown
}

/**
 * 基因 ID 摘要查询。
 * 传 db_id 优先（GeneMaster 主键）；也可传 gene_id + genome_id 走检索解析。
 * 注意：不要只传 gene_id 去调 extract_seq / extract_expression（后端 Id_map 有分隔符 bug）。
 */
export async function getGeneidSummary(payload: {
  db_id?: number | string | (number | string)[]
  gene_id?: string
  genome_id?: string
  request_id?: string
}): Promise<ApiResult<GeneidSummary>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/geneid_summary/', payload)
    return ok(res as unknown as GeneidSummary)
  } catch (e) {
    return fail<GeneidSummary>(toMessage(e))
  }
}

/**
 * 基因详情查询（含序列、GFF、JBrowse 链接、转录本）。
 * 入参与 geneid_summary 一致。
 */
export async function getGeneidResult(payload: {
  db_id?: number | string | (number | string)[]
  gene_id?: string
  genome_id?: string
  request_id?: string
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/geneid_result/', payload)
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

// ==================== 四、表达量 ====================

/** 获取组织列表；不传 genome_id 返回全部去重组织 */
export async function getTissues(genomeId?: string): Promise<ApiResult<string[]>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/extract_expression/tissues/', {
      params: genomeId ? { genome_id: genomeId } : undefined,
    })
    const list = Array.isArray(res) ? (res as unknown as string[]) : ((res as { tissues?: string[] })?.tissues ?? [])
    return ok(list)
  } catch (e) {
    return fail<string[]>(toMessage(e), [])
  }
}

/** 获取含有表达数据的物种列表 */
export async function getGenomesWithTissue(): Promise<ApiResult<string[]>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/extract_expression/genomes/')
    const list = Array.isArray(res) ? (res as unknown as string[]) : ((res as { genomes?: string[] })?.genomes ?? [])
    return ok(list)
  } catch (e) {
    return fail<string[]>(toMessage(e), [])
  }
}

/** 表达量查询：db_id 优先，否则 gene_id + genome_id */
export async function extractExpression(payload: {
  db_id?: number | string | (number | string)[]
  gene_id?: string
  genome_id?: string
  tissue?: string
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/extract_expression/', payload)
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

/** 重新生成热图（后端返回裸 base64，无 data: 前缀） */
export async function regenerateHeatmap(payload: {
  genes: unknown[]
  tissues: string[]
  config?: Record<string, unknown>
}): Promise<ApiResult<{ success: boolean; image: string }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/regenerate_heatmap/', payload)
    return ok(res as unknown as { success: boolean; image: string })
  } catch (e) {
    return fail<{ success: boolean; image: string }>(toMessage(e), { success: false, image: '' })
  }
}

/**
 * 单基因表达量查询（GET）。
 * ⚠️ 后端当前无此路由（见 docs/API.md 第三节 C），故走 mock。
 */
export async function getGeneExpression(params: {
  gene_id: string
  tissue?: string
  db_id?: string
}): Promise<ApiResult<Record<string, unknown>>> {
  if (shouldMock('geneExpression')) {
    return ok(mockGeneExpression(params))
  }
  try {
    const res = await httpInstance.get('/CottonOGD_api/gene_expression/', { params })
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

// ==================== 五、序列提取 ====================

/** 序列提取：db_id 优先（推荐）；gene_id + genome_id 分支后端存在缺陷 */
export async function extractSeq(payload: {
  db_id?: number | string | (number | string)[]
  gene_id?: string
  genome_id?: string
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/extract_seq/', payload)
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

/** 按基因组坐标提取序列（需要 uuid 头，由拦截器统一注入） */
export async function extractSeqGff(payload: {
  genome_id: string
  seqid: string
  start: number | string
  end: number | string
  strand?: string
}): Promise<ApiResult<{ sequence: string }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/extract_seq_gff/', payload)
    return ok(res as unknown as { sequence: string })
  } catch (e) {
    return fail<{ sequence: string }>(toMessage(e), { sequence: '' })
  }
}

// ==================== 六、检索（经后端代理 Meilisearch） ====================

/** 检索结果 */
export interface SearchResult {
  hits: Record<string, unknown>[]
  estimatedTotalHits: number
  processingTimeMs: number
  offset: number
  limit: number
  genomeFacets: Record<string, number>
}

/** 同源分析（Orthologs）Meilisearch 索引 uid（注意大写 O，与后端登记一致） */
export const ORTHOLOG_INDEX = 'Orthologs'

/** 检索入参 */
export interface SearchParams {
  q: string
  index?: string
  offset?: number
  limit?: number
  genomeIds?: string[]
  /** 透传 Meilisearch 过滤表达式（如 'og_code = "OG0000001"'），与 genomeIds 二选一或叠加 */
  filter?: string
  withFacets?: boolean
  facets?: string[]
  attributesToRetrieve?: string[]
  attributesToHighlight?: string[]
  signal?: AbortSignal
}

/** 过滤值转义：双引号会破坏过滤表达式 */
function escapeFilterValue(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
}

/** 统一检索（POST /CottonOGD_api/search/）。关键词与过滤条件独立传参。 */
export async function searchGenes(params: SearchParams): Promise<ApiResult<SearchResult>> {
  const {
    q,
    index = 'genemaster',
    offset = 0,
    limit = 20,
    genomeIds = [],
    filter,
    withFacets = true,
    facets = ['genome_id'],
    attributesToRetrieve,
    attributesToHighlight,
    signal,
  } = params

  const body: Record<string, unknown> = {
    index,
    q,
    offset,
    limit,
    attributesToRetrieve: attributesToRetrieve ?? (index === 'genemaster' ? ['id', 'geneid', 'alias', 'genome_id'] : ['*']),
    attributesToHighlight: attributesToHighlight ?? ['geneid', 'alias'],
  }
  if (genomeIds.length) {
    const conds = genomeIds.map((g) => `genome_id = "${escapeFilterValue(g)}"`)
    body.filter = genomeIds.length === 1 ? conds[0] : `(${conds.join(' OR ')})`
  } else if (filter) {
    // 显式过滤表达式优先（如 og_code = "OG0000001"），与 genomeIds 互斥
    body.filter = filter
  }
  if (withFacets) body.facets = facets

  try {
    const data = await httpInstance.post('/CottonOGD_api/search/', body, { signal }) as unknown as unknown as Record<string, any>
    return ok({
      hits: data.hits ?? [],
      estimatedTotalHits: data.estimatedTotalHits ?? 0,
      processingTimeMs: data.processingTimeMs ?? 0,
      offset: data.offset ?? offset,
      limit: data.limit ?? limit,
      genomeFacets: (data.facetDistribution?.genome_id ?? {}) as unknown as unknown as Record<string, number>,
    })
  } catch (e: any) {
    // 主动取消不算错误
    if (e?.name === 'AbortError' || e?.name === 'CanceledError' || e?.code === 'ERR_CANCELED') throw e
    return fail<SearchResult>(toMessage(e), {
      hits: [], estimatedTotalHits: 0, processingTimeMs: 0, offset, limit, genomeFacets: {},
    })
  }
}

/** 可用检索索引条目 */
export interface SearchIndexInfo {
  uid: string
  label: string
  description?: string
  available: boolean
  documents?: number | null
}

/** 拉取可用检索索引列表 */
export async function getSearchIndexes(): Promise<ApiResult<SearchIndexInfo[]>> {
  try {
    const data = await httpInstance.get('/CottonOGD_api/get_search_indexes/') as unknown as unknown as Record<string, any>
    const list = Array.isArray(data?.indexes) ? (data.indexes as unknown as SearchIndexInfo[]) : []
    return ok(list)
  } catch (e) {
    return fail<SearchIndexInfo[]>(toMessage(e), [])
  }
}

// ==================== 七、GO / KEGG 注释与富集 ====================

/**
 * GO 注释查询。
 * 注意与 kegg_annotation 的 chart_data.data 结构不同（本接口为 {BP:[],MF:[],CC:[]}），不可共用解析。
 */
export async function getGoAnnotation(params: {
  gene_id: string
  genome_id?: string
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/go_annotation/', { params })
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

/** KEGG 注释查询 */
export async function getKeggAnnotation(params: {
  gene_id: string
  genome_id?: string
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/kegg_annotation/', { params })
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

/**
 * GO 富集分析（后端为同步接口，直接返回结果，无 task_id）。
 * 入参固定为 gene_id / genome_id / p_value_threshold，与页面现有调用一致，请勿改成 gene_list。
 */
export async function runGoEnrichment(payload: {
  gene_id: string
  genome_id?: string
  p_value_threshold?: number
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const formData = new FormData()
    formData.append('gene_id', payload.gene_id)
    formData.append('genome_id', payload.genome_id ?? '')
    formData.append('p_value_threshold', String(payload.p_value_threshold ?? 0.05))

    const res = await httpInstance.post('/CottonOGD_api/go_enrichment/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

/** KEGG 富集分析（同步） */
export async function runKeggEnrichment(payload: {
  gene_id: string
  genome_id?: string
  p_value_threshold?: number
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const formData = new FormData()
    formData.append('gene_id', payload.gene_id)
    formData.append('genome_id', payload.genome_id ?? '')
    formData.append('p_value_threshold', String(payload.p_value_threshold ?? 0.05))

    const res = await httpInstance.post('/CottonOGD_api/kegg_enrichment/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

// ==================== 八、基因组 API ====================

/**
 * 区间内基因查询。
 * ⚠️ 后端当前实现引用已删除字段 geneid_id，调用必然 500（见 docs/API.md）。
 * 已保留真实调用路径，待后端修复后可直接启用；当前由调用方决定降级策略。
 */
export async function searchByGenomeLocation(payload: {
  genome: string
  region: string
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const formData = new FormData()
    formData.append('genome', payload.genome)
    formData.append('region', payload.region)

    const res = await httpInstance.post('/CottonOGD_api/search_by_genome_location/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

/** 基因位置行（后端 gene_genomic_distribution 返回）。
 * 注意：后端当前 gene_id 字段为空字符串，只有 chr/start/end/strand 可用（见 docs/API.md）。 */
export interface GeneLocationRow {
  gene_id: string
  chr: string
  start: number
  end: number
  strand: string
}

/** 基因染色体分布查询结果。注意后端读的参数名是 genome（不是 genome_id） */
export interface GeneGenomicDistributionResult {
  genome: string
  chr_distribution: Record<string, number>
  gene_locations: GeneLocationRow[]
  total_genes: number
}

/** 基因染色体分布查询。注意后端读的参数名是 genome（不是 genome_id） */
export async function getGeneGenomicDistribution(payload: {
  genome: string
  gene_ids?: string
}): Promise<ApiResult<GeneGenomicDistributionResult>> {
  try {
    const formData = new FormData()
    formData.append('genome', payload.genome)
    formData.append('gene_ids', payload.gene_ids ?? '')

    const res = await httpInstance.post('/CottonOGD_api/gene_genomic_distribution/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return ok((res ?? {}) as unknown as GeneGenomicDistributionResult)
  } catch (e) {
    return fail<GeneGenomicDistributionResult>(toMessage(e), {
      genome: payload.genome,
      chr_distribution: {},
      gene_locations: [],
      total_genes: 0,
    })
  }
}

/** 共线性桑葚图节点：name 为展示名，genome 标记来源（source/target），chr 为原始染色体 id（如 A01，非 1/2/3） */
export interface SyntenySankeyNode {
  name: string
  genome: string
  chr: string
}

/** 共线性区块（include_blocks=true 时返回） */
export interface SyntenyBlock {
  block_id: string
  score: number | null
  source_genes: string[]
  target_genes: string[]
}

/** 共线性响应（后端 jcvi 预计算管线）：
 * - 默认（不指定 region/gene_id）：sankey 仅含染色体级节点（genome=target），不绘制 scaffold/contig，blocks 为空
 * - 指定 region 或 gene_id：sankey.links 与 blocks 填充检索到的共线性区块 */
export interface GenomeSyntenyResult {
  source_id: string
  target_id: string
  chromosome: string
  block_count: number
  gene_count: number
  sankey: {
    nodes: SyntenySankeyNode[]
    links: { source: string; target: string; value: number }[]
  }
  figures: {
    dotplot: string
    depth: string
    karyotype: string
  }
  blocks: SyntenyBlock[]
}

/** 共线性查询参数（后端 genome_synteny 接口）
 * - source/target：基因组名称（来自 synteny_pairs 返回的可用组合）
 * - chromosome（可选）：源基因组染色体名，如 Ghir_A01；**省略该参数时后端返回全基因组染色体级桑葚图**
 *   （实测：只传 source/target → 53 节点 / 472 连线；传 chromosome=Ghir_A01 → 该染色体 18 节点 / 17 连线）
 * - region（可选）：区间检索，格式如 Ghir_A01:1-1000000（后端当前仅按染色体过滤，亚区间暂不下钻）
 * - gene_id（可选）：基因检索（注意：genome_synteny 会忽略该参数，基因级检索请走 getMicrosynteny） */
export async function getGenomeSynteny(payload: {
  source: string
  target: string
  chromosome?: string
  region?: string
  gene_id?: string
  /** true 时返回完整 blocks（约 4.3 MiB），仅在需要区块级基因/区间时开启 */
  includeBlocks?: boolean
}): Promise<ApiResult<GenomeSyntenyResult>> {
  try {
    const formData = new FormData()
    formData.append('source', payload.source)
    formData.append('target', payload.target)
    const chr = payload.chromosome?.trim()
    if (chr) formData.append('chromosome', chr)
    if (payload.region?.trim()) formData.append('region', payload.region.trim())
    if (payload.gene_id?.trim()) formData.append('gene_id', payload.gene_id.trim())
    if (payload.includeBlocks) formData.append('include_blocks', 'true')

    const res = await httpInstance.post('/CottonOGD_api/genome_synteny/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return ok((res ?? {}) as unknown as GenomeSyntenyResult)
  } catch (e) {
    return fail<GenomeSyntenyResult>(toMessage(e), {} as GenomeSyntenyResult)
  }
}

/** 微共线性轨道上的单个基因（source/target 两条轨道各一组） */
export interface SyntenyTrackGene {
  id: string
  chr: string
  start: number
  end: number
  strand: string
  block_id: string
  order: number
  query: boolean
}

/** 微共线性响应（后端 microsynteny 接口，基因级）：
 * - query_genes：命中的查询基因
 * - graph.nodes/links：查询基因所在的共线性图（节点可能只含查询基因，部分连线端点需从 tracks 补齐）
 * - tracks.source/target：源/目标基因组上该共线性区块的完整基因列表，按 (block_id, order) 一一对应 */
export interface MicrosyntenyResult {
  source_id: string
  target_id: string
  query_genes: string[]
  graph: {
    nodes: {
      id: string
      genome: string
      chr: string
      start?: number
      end?: number
      strand?: string
      block_id?: string
      order?: number
    }[]
    links: { source: string; target: string; block_id?: string }[]
  }
  tracks: {
    source: SyntenyTrackGene[]
    target: SyntenyTrackGene[]
  }
}

/** 基因级微共线性检索（后端 microsynteny 接口）
 * - source/target：基因组名称
 * - gene_ids：基因 ID，多个用逗号分隔（如 Ghir_A01G000100） */
export async function getMicrosynteny(payload: {
  source: string
  target: string
  gene_ids: string
}): Promise<ApiResult<MicrosyntenyResult>> {
  try {
    const formData = new FormData()
    formData.append('source', payload.source)
    formData.append('target', payload.target)
    formData.append('gene_ids', payload.gene_ids)
    const res = await httpInstance.post('/CottonOGD_api/microsynteny/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return ok((res ?? {}) as unknown as MicrosyntenyResult)
  } catch (e) {
    return fail<MicrosyntenyResult>(toMessage(e), {} as MicrosyntenyResult)
  }
}

/** 染色体实际长度（bp）：key 为 FASTA 序列 id（如 Ghir_A01 / A01），来自 JBrowse ReferenceSequenceTrack 的 .fai 索引 */
export type ChromosomeLengths = Record<string, number>

/** 读取基因组的 JBrowse FASTA 索引（.fai），得到每条染色体/序列的实际长度（bp）。
 * .fai 每行格式：name\tlength\toffset\tlineBases\tlineWidth；路径由 JBrowse config 的 faiLocation 给出。
 * 供共线性桑葚图按染色体真实长度设置节点高度（而非仅按共线 block 数）。
 * 失败时返回空对象，调用方降级为后端 block 数（不阻断图表）。 */
export async function getChromosomeLengths(genome: string): Promise<ChromosomeLengths> {
  if (!genome) return {}
  try {
    // 先读 JBrowse config 里的 faiLocation（以服务器实际配置为准），失败再按约定路径回退
    let uri = `/jbrowse/large/${encodeURIComponent(genome)}/${encodeURIComponent(genome)}.genome.fa.gz.fai`
    try {
      const cfg = await httpInstance.get(`/assets/jbrowse/data/${encodeURIComponent(genome)}/config.json`)
      const adapter = cfg?.assemblies?.[0]?.sequence?.adapter
      const fai = adapter?.faiLocation
      const faiUri = fai?.uri ?? fai
      if (typeof faiUri === 'string' && faiUri) uri = faiUri
    } catch {
      /* 配置读取失败：沿用约定路径 */
    }
    const res = await httpInstance.get(uri, { responseType: 'text' })
    const text = typeof res === 'string' ? res : String((res as { data?: unknown })?.data ?? '')
    const lengths: ChromosomeLengths = {}
    text.split(/\r?\n/).forEach((line) => {
      const [name, len] = line.split('\t')
      const bp = Number(len)
      if (name && Number.isFinite(bp) && bp > 0) lengths[name] = bp
    })
    return lengths
  } catch {
    return {}
  }
}

/** 可用共线性基因组对（后端 synteny_pairs 接口，无需鉴权） */
export async function getSyntenyPairs(): Promise<ApiResult<{ pairs: { source: string; target: string }[] }>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/synteny_pairs/')
    return ok((res ?? { pairs: [] }) as unknown as { pairs: { source: string; target: string }[] })
  } catch (e) {
    return fail<{ pairs: { source: string; target: string }[] }>(toMessage(e), { pairs: [] })
  }
}

// ==================== 九、BLAST ====================

/** BLAST 结果条目 */
export interface BlastHit {
  protein_id?: string
  description?: string
  length?: number
  identity?: number
  alignment_length?: number
  mismatches?: number
  gaps?: number
  gap_openings?: number
  query_start?: number
  query_end?: number
  subject_start?: number
  subject_end?: number
  evalue?: number
  bit_score?: number
  score?: number
  query_sequence?: string
  subject_sequence?: string
  match_sequence?: string
  [key: string]: unknown
}

/** BLAST 单库结果：query 元信息 + 命中列表 */
export interface BlastQueryResult {
  query_id?: string
  query_def?: string
  query_length?: number
  program?: string
  version?: string
  reference?: string
  db?: string
  parameters?: Record<string, unknown>
  hits?: BlastHit[]
  [key: string]: unknown
}

/** BLAST 响应：{ 基因组名: 结果 }，值为字符串化 JSON（解析失败时为 XML 串） */
export interface BlastResult {
  /** 基因组名 → 已解析的查询结果 */
  results: Record<string, BlastQueryResult>
  /** 解析失败的原始文本（按基因组名） */
  rawResults: Record<string, string>
}

/**
 * 提交 BLAST 比对。
 * 后端返回 { results: { 基因组: "<JSON 或 XML 字符串>" } }，这里做统一解析；
 * 无法解析为 JSON 时保留原文到 rawResults（后端解析失败会回落为 XML）。
 */
export async function submitBlast(payload: {
  sequence: string
  type: string
  selected_genomes: string | string[]
  data_type?: string
  evalue?: number | string
  max_hits?: number | string
}): Promise<ApiResult<BlastResult>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/blast_cmd/', payload) as unknown as unknown as Record<string, any>
    const rawMap = (res?.results ?? {}) as unknown as unknown as Record<string, unknown>
    const results: Record<string, BlastQueryResult> = {}
    const rawResults: Record<string, string> = {}

    for (const [genome, value] of Object.entries(rawMap)) {
      if (typeof value === 'string') {
        rawResults[genome] = value
        const parsed = parseMaybeJson<BlastQueryResult | null>(value, null)
        if (parsed && typeof parsed === 'object') results[genome] = parsed
      } else if (value && typeof value === 'object') {
        results[genome] = value as unknown as BlastQueryResult
      }
    }
    return ok({ results, rawResults })
  } catch (e) {
    return fail<BlastResult>(toMessage(e), { results: {}, rawResults: {} })
  }
}

// ==================== 十、引物设计 ====================

/** 引物设计结果条目 */
export interface PrimerPair {
  forward?: Record<string, unknown>
  reverse?: Record<string, unknown>
  penalty?: number
  productSize?: number
  productTm?: number
  complAny?: number
  complEnd?: number
  [key: string]: unknown
}

/**
 * 引物设计。
 * 入参三选一：sequence（裸序列）/ db_id / gene_id + genome_id。
 * ⚠️ 走 gene_id 分支时后端不回退 gene_seq 表，取不到序列会直接报错，优先用 db_id 或 sequence。
 */
export async function designPrimers(payload: {
  sequence?: string
  db_id?: number | string
  gene_id?: string
  genome_id?: string
  sequence_id?: string
  parameters?: Record<string, unknown>
}): Promise<ApiResult<{ status: string; results: PrimerPair[] }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/primer_design/', payload)
    return ok(res as unknown as { status: string; results: PrimerPair[] })
  } catch (e) {
    return fail<{ status: string; results: PrimerPair[] }>(toMessage(e), { status: 'error', results: [] })
  }
}

// ==================== 十一、蛋白 3D 结构 ====================

/** 结构相似搜索结果 */
export interface StructureSearchResult {
  query_id?: string
  method?: string
  top_hits?: Record<string, unknown>[]
  total_hits?: number
  time_elapsed?: number
  from_cache?: boolean
  [key: string]: unknown
}

/** 搜索相似蛋白结构；method 支持 rcsb_api / hmmer / mmseqs2 / blast */
export async function searchSimilarStructure(payload: {
  sequence: string
  method?: 'rcsb_api' | 'hmmer' | 'mmseqs2' | 'blast'
  top_n?: number
  evalue?: number
  identity_cutoff?: number
  use_cache?: boolean
}): Promise<ApiResult<StructureSearchResult>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/search_similar_structure/', payload)
    return ok((res ?? {}) as unknown as unknown as StructureSearchResult)
  } catch (e) {
    return fail<StructureSearchResult>(toMessage(e), {})
  }
}

/** 获取可用的结构搜索方法列表（后端为硬编码返回） */
export async function getSearchMethods(): Promise<ApiResult<Record<string, unknown>[]>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/get_search_methods/') as unknown as unknown as Record<string, any>
    return ok(Array.isArray(res?.methods) ? (res.methods as unknown as Record<string, unknown>[]) : [])
  } catch (e) {
    return fail<Record<string, unknown>[]>(toMessage(e), [])
  }
}

// ==================== 十二、eFP 表达图 ====================

/** eFP 表达区域信息。value 类型不稳定：数值 / "NA" / "No Polygon" / "Invalid Polygon" */
export interface EfpRegionInfo {
  name: string
  value: number | string
  polygon?: number[][]
  has_data?: boolean
  color?: number[]
  normalized?: number
}

/** eFP 图片响应（image 带 data:image/png;base64, 前缀） */
export interface EfpImageResult {
  success: boolean
  image: string
  regions_info?: EfpRegionInfo[]
  image_width?: number
  image_height?: number
  gene_id?: string
  genome_id?: string
  min_value?: number
  max_value?: number
  valid_regions?: number
  total_regions?: number
  drawing_method?: string
  error?: string
  [key: string]: unknown
}

/** 生成 eFP 表达图 */
export async function getExpressionEfpImage(payload: {
  gene_id: string
  genome_id?: string
  low_color?: string
  mid_color?: string
  high_color?: string
}): Promise<ApiResult<EfpImageResult>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/expression_EFP_image/', payload)
    return ok((res ?? {}) as unknown as unknown as EfpImageResult)
  } catch (e) {
    return fail<EfpImageResult>(toMessage(e), { success: false, image: '' })
  }
}

// ==================== 十三、AI 对话 ====================

/** AI 对话响应 */
export interface AiChatResult {
  success: boolean
  answer?: string
  tool_calls?: Array<{ name: string; arguments?: string; elapsed_ms?: number }>
  history_turns?: number
  error?: string
  [key: string]: unknown
}

/** AI 对话；LLM 较慢，超时给 120s */
export async function postAiChat(payload: {
  message: string
  clear_history?: boolean
}): Promise<ApiResult<AiChatResult>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/ai/chat/', payload, { timeout: 120_000 })
    return ok((res ?? {}) as unknown as unknown as AiChatResult)
  } catch (e) {
    return fail<AiChatResult>(toMessage(e), { success: false })
  }
}

// ==================== 十四、新闻（后端缺失，走 mock） ====================

/** 新闻条目 */
export interface NewsItem {
  date: string
  type: 'update' | 'release' | 'publication' | 'event'
  title: string
  summary: string
  link?: string
}

/** mock 新闻数据：后端 /CottonOGD_api/news/ 尚未实现，接口就绪后置 news:false 即可 */
const MOCK_NEWS: NewsItem[] = [
  {
    date: '2026-10-29',
    type: 'release',
    title: 'CottonOGD 棉花组学数据库正式发布',
    summary: '集成基因组、转录组、变异与同源分析模块，支持 258 个棉花基因组的统一检索。',
  },
  {
    date: '2026-10-20',
    type: 'update',
    title: '新增 AI 对话助手',
    summary: '支持自然语言查询基因、转录因子家族与基因详情，自动调用数据库工具。',
  },
  {
    date: '2026-10-10',
    type: 'update',
    title: '基因组浏览器支持 JBrowse 与 IGV 双引擎',
    summary: '可按基因组切换查看基因结构、表达与注释轨道。',
  },
]

/** 拉取首页新闻（后端缺失时返回 mock） */
export async function getNews(): Promise<ApiResult<NewsItem[]>> {
  if (shouldMock('news')) {
    return ok(MOCK_NEWS)
  }
  try {
    const res = await httpInstance.get('/CottonOGD_api/news/')
    const list = Array.isArray(res) ? (res as unknown as NewsItem[]) : ((res as { data?: NewsItem[] })?.data ?? [])
    return ok(list)
  } catch (e) {
    return fail<NewsItem[]>(toMessage(e), [])
  }
}

/** mock 单基因表达查询：后端无 GET /gene_expression/ 路由 */
function mockGeneExpression(params: { gene_id: string; tissue?: string }): Record<string, unknown> {
  return {
    gene_id: params.gene_id,
    tissue: params.tissue || 'all',
    expression: [],
    note: 'mock：后端 GET /CottonOGD_api/gene_expression/ 尚未实现',
  }
}

// ==================== 十五、同源分析 Orthogroup（后端缺失，走 mock） ====================

/** orthogroup 列表条目 */
export interface OrthogroupItem {
  /** OrthoFinder 风格 ID，如 OG0000001 */
  og_id: string
  /** 含该 orthogroup 的物种数 */
  species_count: number
  /** orthogroup 内基因总数 */
  gene_count: number
  /** 是否为单拷贝 orthogroup */
  is_single_copy: boolean
  /** 代表性功能注释 */
  annotation?: string
}

/** orthogroup 明细中的基因条目 */
export interface OrthogroupGene {
  gene_id: string
  genome_id: string
  species?: string
}

/** orthogroup 明细 */
export interface OrthogroupDetail extends OrthogroupItem {
  genes: OrthogroupGene[]
}

/** 单拷贝基因条目 */
export interface SingleCopyGene {
  og_id: string
  genes: OrthogroupGene[]
}

// —— mock 数据：OrthoFinder 产物在仓库中不存在（WorkFile/config.yaml 中 enabled: false），
//    故此处为预置数据；后端接口就绪后把 orthogroups 置为 false 并接入真实 URL。
const MOCK_SPECIES = [
  'G.hirsutumAD1_TM-1_HAU_v1.1',
  'G.barbadenseAD2_HAU_v1.1',
  'G.arboreumA2_HAU_v1.1',
  'G.raimondiiD5_HAU_v1.1',
]

const MOCK_ORTHOGROUPS: OrthogroupItem[] = Array.from({ length: 24 }, (_, i) => {
  const n = i + 1
  const speciesCount = n % 4 === 0 ? 4 : n % 4
  return {
    og_id: `OG${String(n).padStart(7, '0')}`,
    species_count: speciesCount,
    gene_count: speciesCount * (1 + (n % 3)),
    is_single_copy: speciesCount === 4 && n % 8 === 0,
    annotation: `示例功能注释 ${n}`,
  }
})

/** orthogroup 列表查询（当前 mock） */
export async function getOrthogroups(params?: {
  keyword?: string
  singleCopyOnly?: boolean
  page?: number
  pageSize?: number
}): Promise<ApiResult<{ list: OrthogroupItem[]; total: number }>> {
  let list = MOCK_ORTHOGROUPS
  if (params?.singleCopyOnly) list = list.filter((o) => o.is_single_copy)
  if (params?.keyword?.trim()) {
    const kw = params.keyword.trim().toLowerCase()
    list = list.filter((o) => o.og_id.toLowerCase().includes(kw) || (o.annotation ?? '').toLowerCase().includes(kw))
  }
  const total = list.length
  const page = params?.page ?? 1
  const pageSize = params?.pageSize ?? 20
  const start = (page - 1) * pageSize
  return ok({ list: list.slice(start, start + pageSize), total })
}

/** orthogroup 明细查询（当前 mock） */
export async function getOrthogroupDetail(ogId: string): Promise<ApiResult<OrthogroupDetail | null>> {
  const base = MOCK_ORTHOGROUPS.find((o) => o.og_id === ogId)
  if (!base) return ok(null, `未找到 ${ogId}`)
  const genes: OrthogroupGene[] = MOCK_SPECIES.slice(0, base.species_count).map((g, idx) => ({
    gene_id: `${ogId.replace('OG', 'Ghir_')}_${String(idx + 1).padStart(3, '0')}`,
    genome_id: g,
    species: g.split('_')[0],
  }))
  return ok({ ...base, genes })
}

/** 单拷贝 orthogroup 查询（当前 mock） */
export async function getSingleCopyGenes(params?: {
  limit?: number
}): Promise<ApiResult<SingleCopyGene[]>> {
  const limit = params?.limit ?? 20
  const sc = MOCK_ORTHOGROUPS.filter((o) => o.is_single_copy).slice(0, limit)
  const list = sc.map((o) => ({
    og_id: o.og_id,
    genes: MOCK_SPECIES.slice(0, o.species_count).map((g, idx) => ({
      gene_id: `${o.og_id.replace('OG', 'Ghir_')}_${String(idx + 1).padStart(3, '0')}`,
      genome_id: g,
      species: g.split('_')[0],
    })),
  }))
  return ok(list)
}

// ==================== 十六、Ortholog / Orthogroup 查询（后端已就绪） ====================

/** 一个物种内的成员基因条目 */
export interface OrthologMemberGene {
  /** 该物种内的同源基因名（始终有值） */
  ortho_gene: string
  /** genemaster 中的 geneid；约 16% 基因无对应，可能为 null，原样展示 */
  genemaster_geneid: string | null
}

/** 一个物种在某 orthogroup 下的成员 */
export interface OrthologSpeciesMember {
  /** 物种内部名（如 G.stocksiiE1_HAU_v1） */
  species: string
  /** 展示用名（优先使用，回退 species） */
  display_name?: string
  /** 该物种成员基因数 */
  n: number
  genes: OrthologMemberGene[]
}

/** 一个 orthogroup 的查询结果（列表与明细共用） */
export interface OrthologOrthogroup {
  og_code: string
  species_count: number
  gene_count: number
  is_single_copy: boolean
  /** one_to_one | one_to_many | many_to_one | many_to_many | single | none */
  relation_type: string
  species_members: OrthologSpeciesMember[]
  /** 所选物种中出现的物种数；未按物种筛选时为 null（交接文档 C.3/C.2） */
  selected_species_count?: number | null
  /** 功能注释；后端当前未返回，预留字段，补齐后列表/明细自动生效 */
  annotation?: string
}

/** 按基因查询直系同源的响应 */
export interface OrthologGeneResponse {
  query_gene: string
  found: boolean
  orthogroups: OrthologOrthogroup[]
}

/** 物种元数据条目（orthofinder/meta/） */
export interface OrthologSpeciesMeta {
  name: string
  alias?: string
  Cotton_Species?: string
  Genome_type?: string
  Category?: string
}

/** 按物种筛选 orthogroup 的单个命中（带分页信息） */
export interface OrthogroupsBySpeciesResponse {
  found: boolean
  mode: string
  species: string[]
  total: number
  limit: number
  offset: number
  orthogroups: OrthologOrthogroup[]
  /** 后端回显的筛选条件（v1.1 新增） */
  filters?: Record<string, unknown>
  /** 是否还有下一页（v1.1 新增） */
  has_more?: boolean
}

/**
 * 按基因查询直系同源。
 * POST /CottonOGD_api/orthofinder/ortholog_gene/，body { geneid }。
 * 未命中时后端返回 found:false、orthogroups:[]。
 */
export async function getOrthologByGene(geneid: string): Promise<OrthologGeneResponse> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/orthofinder/ortholog_gene/', {
      geneid,
    }) as unknown as OrthologGeneResponse
    return res ?? { query_gene: geneid, found: false, orthogroups: [] }
  } catch {
    return { query_gene: geneid, found: false, orthogroups: [] }
  }
}

/**
 * 查询单个 orthogroup 的全部成员。
 * POST /CottonOGD_api/orthofinder/orthogroup_detail/，body { og_code }。
 * 后端返回**扁平结构**：{ found, og_code, species_count, ..., species_members }。
 */
export async function getOrthogroupDetailV2(
  ogCode: string,
  options?: {
    /** 只返回这些物种的成员（交接文档 C.2） */
    species?: string[]
    /** 传 0 时只返回物种与计数，不返回 genes（大 OG 推荐） */
    includeGenes?: boolean
  },
): Promise<OrthologOrthogroup | null> {
  try {
    const body: Record<string, unknown> = { og_code: ogCode }
    if (options?.species?.length) body.species = options.species
    if (options?.includeGenes === false) body.include_genes = 0
    const res = await httpInstance.post(
      '/CottonOGD_api/orthofinder/orthogroup_detail/',
      body,
    ) as unknown as OrthologOrthogroup & { found: boolean; selected_species_count?: number | null }
    // 后端 found:true 但 orthogroup 为空对象时也视为未命中
    if (res && res.found && (res.og_code || (res.species_members && res.species_members.length))) {
      return res
    }
    return null
  } catch {
    return null
  }
}

/**
 * 按物种筛选 orthogroup（跨物种共有）。
 * POST /CottonOGD_api/orthofinder/orthogroups_by_species/。
 * mode: all=全部选中物种共有（默认）；any=任一物种含有。
 */
export async function getOrthogroupsBySpecies(params: {
  /** 物种名列表；为空时后端按 OG 元数据浏览（交接文档 C.3） */
  species?: string[]
  mode?: 'all' | 'any'
  /** OG 精确匹配 */
  og_code?: string
  /** OG 子串模糊匹配（不区分大小写） */
  og_code_like?: string
  min_genes?: number
  max_genes?: number
  min_species?: number
  max_species?: number
  min_selected_species?: number
  max_selected_species?: number
  sort?: 'selected_species' | 'gene_count' | 'species_count' | 'og_code'
  limit?: number
  offset?: number
}): Promise<OrthogroupsBySpeciesResponse> {
  const body: Record<string, unknown> = {
    species: params.species ?? [],
    mode: params.mode ?? 'all',
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
  }
  // 仅传递有值的可选筛选参数，保持旧调用（只传 species/mode）行为不变
  const optionalKeys = [
    'og_code', 'og_code_like', 'min_genes', 'max_genes',
    'min_species', 'max_species', 'min_selected_species', 'max_selected_species',
    'sort',
  ] as const
  for (const key of optionalKeys) {
    const value = params[key]
    if (value !== undefined && value !== null && value !== '') body[key] = value
  }
  try {
    const res = await httpInstance.post(
      '/CottonOGD_api/orthofinder/orthogroups_by_species/',
      body,
    ) as unknown as OrthogroupsBySpeciesResponse
    return res ?? {
      found: false, mode: params.mode ?? 'all', species: params.species ?? [],
      total: 0, limit: params.limit ?? 50, offset: params.offset ?? 0, orthogroups: [],
    }
  } catch {
    return {
      found: false, mode: params.mode ?? 'all', species: params.species ?? [],
      total: 0, limit: params.limit ?? 50, offset: params.offset ?? 0, orthogroups: [],
    }
  }
}

/**
 * 拉取物种元数据（供物种下拉/筛选）。
 * GET /CottonOGD_api/orthofinder/meta/，无参。
 */
export async function getOrthologMeta(): Promise<OrthologSpeciesMeta[]> {
  try {
    // 后端返回 { species: [...] }（而非裸数组），两种形态都兼容
    const res = await httpInstance.get('/CottonOGD_api/orthofinder/meta/') as unknown as
      | OrthologSpeciesMeta[]
      | { species?: OrthologSpeciesMeta[] }
    if (Array.isArray(res)) return res
    if (res && Array.isArray((res as { species?: OrthologSpeciesMeta[] }).species)) {
      return (res as { species: OrthologSpeciesMeta[] }).species
    }
    return []
  } catch {
    return []
  }
}

/**
 * 拉取单个 orthogroup 的 FASTA 序列文本（按需，零全量加载）。
 * GET /CottonOGD_api/orthofinder/sequence/<og_code>
 */
export async function getOrthogroupSequence(ogCode: string): Promise<string> {
  try {
    const res = await httpInstance.get(`/CottonOGD_api/orthofinder/sequence/${ogCode}`, {
      responseType: 'text',
    }) as unknown as string
    return typeof res === 'string' ? res : ''
  } catch {
    return ''
  }
}

/**
 * 拉取单个 orthogroup 的基因树（newick 纯文本）。
 * GET /CottonOGD_api/orthofinder/tree/<og_code>
 * 内容为标准 newick 字符串，可直接喂给 phylotree.js / D3 渲染。
 * 资源不存在时后端返回 HTTP 404，前端 catch 后静默隐藏该区块。
 */
export async function getOrthogroupTree(ogCode: string): Promise<string> {
  try {
    const res = await httpInstance.get(`/CottonOGD_api/orthofinder/tree/${ogCode}`, {
      responseType: 'text',
    }) as unknown as string
    return typeof res === 'string' ? res : ''
  } catch {
    return ''
  }
}

/**
 * 拉取单个 orthogroup 的多序列比对（MSA）纯文本 FASTA。
 * GET /CottonOGD_api/orthofinder/msa/<og_code>
 * 资源不存在时后端返回 HTTP 404，前端 catch 后静默隐藏该面板（约 7.1 万/8.4 万有 MSA）。
 */
export async function getOrthogroupMsa(ogCode: string): Promise<string> {
  try {
    const res = await httpInstance.get(`/CottonOGD_api/orthofinder/msa/${ogCode}`, {
      responseType: 'text',
    }) as unknown as string
    // 仅接受以 '>' 开头的 FASTA 文本；若后端未实现 msa/ 路由，
    // 请求会落到静态服务器 SPA 兜底页（text/html），不能当 MSA 渲染。
    if (typeof res !== 'string' || !res.trimStart().startsWith('>')) return ''
    return res
  } catch {
    return ''
  }
}

// ==================== 十七、比较基因组学扩展接口（v1.1 交接文档 C.9–C.15） ====================
// 全部按 docs/COMPARATIVE_ANALYSIS_API_HANDOFF.md 实现；响应为裸 JSON。

/** 从 axios 错误中提取后端 error 文案 */
function readBackendError(err: unknown): string {
  const e = err as {
    response?: { data?: { error?: string; note?: string } }
    message?: string
  }
  return e?.response?.data?.error || e?.message || DEFAULT_ERROR_MESSAGE
}

/** OG 成员平铺行（C.9） */
export interface OgMemberRow {
  species: string
  display_name?: string
  ortho_gene: string
  genemaster_geneid: string | null
}

/** OG 成员分页响应（C.9） */
export interface OgMembersResponse {
  found: boolean
  og_code: string
  members: OgMemberRow[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

/** 大 OG 成员平铺分页（C.9） */
export async function getOgMembers(params: {
  og_code: string
  species?: string[]
  limit?: number
  offset?: number
}): Promise<OgMembersResponse> {
  const body: Record<string, unknown> = {
    og_code: params.og_code,
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
  }
  if (params.species?.length) body.species = params.species
  try {
    const res = await httpInstance.post(
      '/CottonOGD_api/orthofinder/og_members/',
      body,
    ) as unknown as OgMembersResponse
    return res ?? {
      found: false, og_code: params.og_code, members: [], total: 0,
      limit: params.limit ?? 50, offset: params.offset ?? 0, has_more: false,
    }
  } catch (err) {
    throw new Error(readBackendError(err))
  }
}

/** 真实直系同源关系中的配对物种（C.10） */
export interface OrthologPartner {
  species: string
  genes: string[]
  query_gene_count: number
  partner_gene_count: number
  /** one_to_one | one_to_many | many_to_one | many_to_many */
  relation_type: string
}

/** 单个 OG 下的真实直系同源配对（C.10） */
export interface GeneOrthologGroup {
  og_code: string
  partners: OrthologPartner[]
}

/** 按来源物种分组的直系同源结果（C.10） */
export interface GeneOrthologSpeciesResult {
  species: string
  orthogroups: GeneOrthologGroup[]
  /** 该物种索引缺失时的说明（交接文档 I.3） */
  error?: string
}

/** 基因 → 真实直系同源响应（C.10） */
export interface GeneOrthologsResponse {
  query_gene: string
  found: boolean
  partner_species: string | null
  results: GeneOrthologSpeciesResult[]
  note?: string
  error?: string
}

/**
 * 基因 → 真实直系同源（C.10）。
 * 这是唯一可信的 Ortholog 查询接口，数据来自 OrthoFinder Orthologues 输出。
 */
export async function getGeneOrthologs(params: {
  geneid: string
  species?: string
  partner_species?: string
  og_code?: string
}): Promise<GeneOrthologsResponse> {
  try {
    const res = await httpInstance.post(
      '/CottonOGD_api/orthofinder/gene_orthologs/',
      params,
    ) as unknown as GeneOrthologsResponse
    return res ?? {
      query_gene: params.geneid, found: false, partner_species: null, results: [],
    }
  } catch (err) {
    return {
      query_gene: params.geneid, found: false, partner_species: null, results: [],
      error: readBackendError(err),
    }
  }
}

/** 两个 Genome 共享的 OG（C.11） */
export interface GenomePairOg {
  og_code: string
  gene_count: number
  species_count: number
  genes_a: string[]
  genes_b: string[]
}

/** 两个 Genome 的共享 OG 响应（C.11） */
export interface GenomePairResponse {
  found: boolean
  genome_a: string
  genome_b: string
  relationship: string
  note?: string
  orthogroups: GenomePairOg[]
  total: number
  limit: number
  offset: number
  has_more: boolean
  error?: string
}

/**
 * 两个 Genome 的共享 OG（C.11）。
 * 返回的是“同一 OG 的成员”，不是 Ortholog 对；UI 必须按共享 OG 文案展示。
 */
export async function getGenomePair(params: {
  genome_a: string
  genome_b: string
  og_code?: string
  limit?: number
  offset?: number
}): Promise<GenomePairResponse> {
  try {
    const res = await httpInstance.post(
      '/CottonOGD_api/orthofinder/genome_pair/',
      { ...params, limit: params.limit ?? 50, offset: params.offset ?? 0 },
    ) as unknown as GenomePairResponse
    return res ?? {
      found: false, genome_a: params.genome_a, genome_b: params.genome_b,
      relationship: 'shared_orthogroup_members', orthogroups: [],
      total: 0, limit: params.limit ?? 50, offset: params.offset ?? 0, has_more: false,
    }
  } catch (err) {
    return {
      found: false, genome_a: params.genome_a, genome_b: params.genome_b,
      relationship: 'shared_orthogroup_members', orthogroups: [],
      total: 0, limit: params.limit ?? 50, offset: params.offset ?? 0, has_more: false,
      error: readBackendError(err),
    }
  }
}

/** 基因 → 最具体 HOG 命中（C.12） */
export interface GeneHogHit {
  species: string
  hog_id: string
  node: string
  og_code: string
  parent_clade: string
  species_count: number
  gene_count: number
}

/** 基因 → 最具体 HOG 响应（C.12） */
export interface GeneHogResponse {
  query_gene: string
  found: boolean
  hogs: GeneHogHit[]
  error?: string
}

/** 基因 → 最具体 HOG（C.12） */
export async function getGeneHog(params: {
  geneid: string
  species?: string
}): Promise<GeneHogResponse> {
  try {
    const res = await httpInstance.post(
      '/CottonOGD_api/orthofinder/gene_hog/',
      params,
    ) as unknown as GeneHogResponse
    return res ?? { query_gene: params.geneid, found: false, hogs: [] }
  } catch (err) {
    return {
      query_gene: params.geneid, found: false, hogs: [],
      error: readBackendError(err),
    }
  }
}

/** HOG 成员分组（C.13） */
export interface HogMemberGroup {
  species: string
  genes: string[]
  n: number
}

/** HOG 详情响应（C.13） */
export interface HogDetailResponse {
  found: boolean
  hog_id: string
  node?: string
  og_code?: string
  parent_clade?: string
  species_count?: number
  gene_count?: number
  members?: HogMemberGroup[]
  error?: string
}

/** HOG 详情（C.13） */
export async function getHogDetail(hogId: string): Promise<HogDetailResponse> {
  try {
    const res = await httpInstance.post(
      '/CottonOGD_api/orthofinder/hog_detail/',
      { hog_id: hogId },
    ) as unknown as HogDetailResponse
    return res ?? { found: false, hog_id: hogId }
  } catch (err) {
    return { found: false, hog_id: hogId, error: readBackendError(err) }
  }
}

/** 物种树内部节点（C.14） */
export interface SpeciesTreeNodeInfo {
  id: string
  parent: string | null
  is_leaf: boolean
  branch_length: string | number
  ancestors: string[]
}

/** 物种树响应（C.14） */
export interface SpeciesTreeResponse {
  newick: string
  root: string
  leaf_count: number
  leaves: string[]
  leaf_parent: Record<string, string>
  nodes?: SpeciesTreeNodeInfo[]
  error?: string
}

/** 物种树（C.14）；fmt=newick 时由后端直接返回 Newick 文本 */
export async function getSpeciesTree(params?: {
  fmt?: 'newick'
  includeNodes?: boolean
}): Promise<SpeciesTreeResponse> {
  const query: Record<string, unknown> = {}
  // 注意：DRF 保留 format 参数，交接文档要求使用 fmt
  if (params?.fmt) query.fmt = params.fmt
  if (params?.includeNodes === false) query.include_nodes = 0
  try {
    const res = await httpInstance.get(
      '/CottonOGD_api/orthofinder/species_tree/',
      { params: query },
    )
    if (typeof res === 'string') {
      return { newick: res, root: '', leaf_count: 0, leaves: [], leaf_parent: {} }
    }
    return res as unknown as SpeciesTreeResponse
  } catch (err) {
    return {
      newick: '', root: '', leaf_count: 0, leaves: [], leaf_parent: {},
      error: readBackendError(err),
    }
  }
}

/** 统计接口 type/kind/scope 枚举（C.15） */
export type StatisticsType =
  | 'overall' | 'per_species' | 'orthologs' | 'duplications' | 'species_overlaps'
export type StatisticsOrthologKind =
  | 'one-to-one' | 'one-to-many' | 'many-to-one' | 'many-to-many' | 'totals'
export type StatisticsDuplicationScope = 'orthogroup' | 'species_node'

/** 统计响应：不同 type 返回结构不同，调用方按 type 收窄 */
export type OrthofinderStatisticsResponse = Record<string, unknown> & {
  error?: string
  available?: boolean
}

/** 直接读取 Comparative_Genomics_Statistics（C.15，不在前端重算） */
export async function getOrthofinderStatistics(params: {
  type?: StatisticsType
  kind?: StatisticsOrthologKind
  species_a?: string
  species_b?: string
  scope?: StatisticsDuplicationScope
  og_code?: string
}): Promise<OrthofinderStatisticsResponse> {
  const query: Record<string, unknown> = { type: params.type ?? 'overall' }
  if (params.kind) query.kind = params.kind
  if (params.species_a) query.species_a = params.species_a
  if (params.species_b) query.species_b = params.species_b
  if (params.scope) query.scope = params.scope
  if (params.og_code) query.og_code = params.og_code
  try {
    const res = await httpInstance.get('/CottonOGD_api/orthofinder/statistics/', {
      params: query,
    })
    return (res ?? {}) as OrthofinderStatisticsResponse
  } catch (err) {
    return { error: readBackendError(err) }
  }
}

/** 复制事件分页响应（C.8） */
export interface OrthofinderTandemEvent {
  species: string
  type: string
  support: number | null
  gene_tree_node: string
  genes1: string[]
  genes2: string[]
}

export interface OrthofinderTandemSummary {
  og_code: string
  by_type: Record<string, number>
  species: Record<string, Array<{ geneid: string; n: number }>>
  total_events: number
  limit: number
  offset: number
  has_more: boolean
  events: OrthofinderTandemEvent[]
  error?: string
}

/**
 * 基因复制事件（C.8）：汇总始终全量，events 明细按 limit/offset 分页。
 * include_events=false 时只取汇总。
 */
export async function getOrthofinderTandem(
  ogCode: string,
  params?: { limit?: number; offset?: number; includeEvents?: boolean },
): Promise<OrthofinderTandemSummary | null> {
  const query: Record<string, unknown> = {
    limit: params?.limit ?? 2000,
    offset: params?.offset ?? 0,
  }
  if (params?.includeEvents === false) query.include_events = 0
  try {
    const res = await httpInstance.get(
      `/CottonOGD_api/orthofinder/tandem/${ogCode}`,
      { params: query },
    ) as unknown as OrthofinderTandemSummary | Record<string, never>
    // 无复制事件时后端返回 {}
    if (!res || !Object.keys(res).length) return null
    return res as OrthofinderTandemSummary
  } catch (err) {
    throw new Error(readBackendError(err))
  }
}

/**
 * Submit gene identifiers and genome for STRING annotation and return a Cytoscape network.
 * The matching backend endpoint is part of the PPI frontend/backend handoff.
 */
export async function getStringPpiNetwork(payload: {
  gene_ids: string[]
  genome_id: string
}): Promise<{ network: PpiNetwork; message: string }> {
  const response: unknown = await httpInstance.post('/CottonOGD_api/ppi/string/', payload, {
    timeout: 120_000,
  })
  const message =
    typeof response === 'object' &&
    response !== null &&
    'message' in response &&
    typeof response.message === 'string'
      ? response.message
      : ''
  return { network: parsePpiNetwork(response), message }
}

// ==================== 十七、变异与 GWAS（Variome） ====================
//
// 已验证真实后端（iCotton.henau.edu.cn），以下接口/类型以后端实际响应为准。
// 统一返回 ApiResult<T>，与既有 API 一致；不走 mock（用户要求直接对接真实接口）。

// ---------- A 域：SyRI 结构变异 ----------

/** SyRI pairwise 批次 — 后端返回 {id, ref_genome_id, query_genome_id, status, syri_version, created_at} */
export interface SyriPair {
  id: number
  ref_genome_id: number
  query_genome_id: number
  status: string
  syri_version: string
  created_at: string
}

/** SyRI 结构变异条目 — 后端返回 {id, genome_pair_id, ref_genome_id, query_genome_id,
 *  ref_genome_chr, ref_start, ref_end, query_genome_chr, query_start, query_end,
 *  event_id, parent_event, son_type, copygain, sv_length} */
export interface SyriStructural {
  id: number
  genome_pair_id: number
  ref_genome_id: number
  query_genome_id: number
  ref_genome_chr: string
  ref_start: number
  ref_end: number
  query_genome_chr: string
  query_start: number
  query_end: number
  event_id: string
  parent_event: string | null
  son_type: string
  copygain: number | null
  sv_length: number
}

/** SyRI 序列级注释条目（复用后端 structural 的行格式） */
export interface SyriSequence {
  id: number
  ref_genome_chr: string
  ref_start: number
  ref_end: number
  query_genome_chr: string
  query_start: number
  query_end: number
  son_type: string
  sv_length: number
}

/** SyRI / variant 类型统计 — 后端返回 {son_type/svtype, count} */
export interface TypeStat {
  son_type?: string
  svtype?: string
  count: number
}

/** 获取所有 SyRI pairwise 比对批次 */
export async function getSyriPairs(): Promise<ApiResult<SyriPair[]>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/syri/pairs/')
    return ok(res as unknown as SyriPair[])
  } catch (e) {
    return fail<SyriPair[]>(toMessage(e), [])
  }
}

/** 按区间 + 类型查询结构变异 — 后端需 pair_id(int) */
export async function getSyriStructural(payload: {
  pair_id: number
  ref_chr?: string
  start?: number
  end?: number
  types?: string[]
  limit?: number
}): Promise<ApiResult<{ pair_id: number; count: number; type_stat: TypeStat[]; rows: SyriStructural[] }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/syri/structural/', payload)
    return ok(res as unknown as { pair_id: number; count: number; type_stat: TypeStat[]; rows: SyriStructural[] })
  } catch (e) {
    return fail<{ pair_id: number; count: number; type_stat: TypeStat[]; rows: SyriStructural[] }>(
      toMessage(e),
      { pair_id: 0, count: 0, type_stat: [], rows: [] },
    )
  }
}

/** 查询序列级结构变异注释 */
export async function getSyriSequence(payload: {
  pair_id: number
  ref_chr?: string
  start?: number
  end?: number
  types?: string[]
  limit?: number
}): Promise<ApiResult<{ pair_id: number; count: number; rows: SyriSequence[] }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/syri/sequence/', payload)
    return ok(res as unknown as { pair_id: number; count: number; rows: SyriSequence[] })
  } catch (e) {
    return fail<{ pair_id: number; count: number; rows: SyriSequence[] }>(toMessage(e), { pair_id: 0, count: 0, rows: [] })
  }
}

// ---------- B 域：群体变异位点 ----------

/** 群体变异数据集 — 后端返回 {id, name, reference_genome, caller, sample_count} */
export interface VariantSet {
  id: number
  name: string
  reference_genome: number
  caller: string
  sample_count: number
}

/** 群体变异位点条目 — 后端返回 {id, chrom, pos, end_pos, svtype, ref, alt, filter} */
export interface VariantRecord {
  id: number
  chrom: string
  pos: number
  end_pos: number
  svtype: string
  ref: string
  alt: string
  filter: string
}

/** 变异密度直方图 bin — 后端返回 {bin, start, end, count} */
export interface VariantDensityBin {
  bin: number
  start: number
  end: number
  count: number
}

/** 获取所有群体变异数据集 */
export async function getVariantSets(): Promise<ApiResult<VariantSet[]>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/variant/sets/')
    return ok(res as unknown as VariantSet[])
  } catch (e) {
    return fail<VariantSet[]>(toMessage(e), [])
  }
}

/** 按区间查询变异位点 — 后端需 set_id(int) */
export async function getVariantRegion(payload: {
  set_id: number
  chrom: string
  start: number
  end: number
  svtype?: string
  limit?: number
}): Promise<ApiResult<{ set_id: number; count: number; type_stat: TypeStat[]; rows: VariantRecord[] }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/variant/region/', payload)
    return ok(res as unknown as { set_id: number; count: number; type_stat: TypeStat[]; rows: VariantRecord[] })
  } catch (e) {
    return fail<{ set_id: number; count: number; type_stat: TypeStat[]; rows: VariantRecord[] }>(
      toMessage(e),
      { set_id: 0, count: 0, type_stat: [], rows: [] },
    )
  }
}

/** 查询单个变异位点详情 */
export async function getVariantById(id: number | string): Promise<ApiResult<VariantRecord>> {
  try {
    const res = await httpInstance.get(`/CottonOGD_api/variant/id/${id}/`)
    return ok(res as unknown as VariantRecord)
  } catch (e) {
    return fail<VariantRecord>(toMessage(e), {} as VariantRecord)
  }
}

/** 查询变异密度 — 后端需 set_id + chrom，返回 {set_id, chrom, start, end, bins, bin_size, total, histogram} */
export async function getVariantDensity(payload: {
  set_id: number
  chrom: string
  start?: number
  end?: number
  bins?: number
}): Promise<ApiResult<{ set_id: number; chrom: string; start: number; end: number; bins: number; bin_size: number; total: number; histogram: VariantDensityBin[] }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/variant/density/', payload)
    return ok(res as unknown as { set_id: number; chrom: string; start: number; end: number; bins: number; bin_size: number; total: number; histogram: VariantDensityBin[] })
  } catch (e) {
    return fail<{ set_id: number; chrom: string; start: number; end: number; bins: number; bin_size: number; total: number; histogram: VariantDensityBin[] }>(
      toMessage(e),
      { set_id: 0, chrom: '', start: 0, end: 0, bins: 0, bin_size: 0, total: 0, histogram: [] },
    )
  }
}

// ---------- C 域：逐样本基因型 ----------

/** 逐样本基因型条目 — 后端返回 {chrom, pos, ref, alt, id?, genotypes:{sample:gt}} */
export interface VariantGenotypeRow {
  chrom: string
  pos: number
  ref: string
  alt: string
  id?: number
  genotypes: Record<string, string>
}

/** 基因型查询响应 — 后端返回 {set_id, chrom, start, end, samples:[], records:[]} */
export interface VariantGenotypeResult {
  set_id: number
  chrom: string
  start: number
  end: number
  samples: string[]
  records: VariantGenotypeRow[]
}

/** 查询逐样本基因型矩阵 — 后端需 set_id(int) + chrom */
export async function getVariantGenotype(payload: {
  set_id: number
  chrom: string
  start: number
  end: number
  samples?: string[]
  format?: string
}): Promise<ApiResult<VariantGenotypeResult>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/variant/genotype/', payload)
    return ok(res as unknown as VariantGenotypeResult)
  } catch (e) {
    return fail<VariantGenotypeResult>(toMessage(e), { set_id: 0, chrom: '', start: 0, end: 0, samples: [], records: [] })
  }
}

// ---------- D 域：GWAS ----------

/** GWAS 性状 — 后端返回 {id, code, name, unit, description} */
export interface GwasTrait {
  id: number
  code: string
  name: string
  unit: string
  description: string | null
}

/** GWAS 材料 — 后端返回 {id, name, species, population} */
export interface GwasAccession {
  id: number
  name: string
  species: string
  population: string | null
}

/** GWAS 标记/关联条目 — 后端返回 {id, chrom, pos, svtype, ref, alt} */
export interface GwasMarker {
  id: number
  chrom: string
  pos: number
  svtype: string
  ref: string
  alt: string
}

/** GWAS 表型行 — 后端返回 {accession, trait, value} */
export interface GwasPhenotypeRow {
  accession: string
  trait: string
  value: number
}

/** 获取 GWAS 全部性状 */
export async function getGwasTraits(): Promise<ApiResult<GwasTrait[]>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/gwas/traits/')
    return ok(res as unknown as GwasTrait[])
  } catch (e) {
    return fail<GwasTrait[]>(toMessage(e), [])
  }
}

/** 获取 GWAS 材料列表 */
export async function getGwasAccessions(): Promise<ApiResult<GwasAccession[]>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/gwas/accessions/')
    return ok(res as unknown as GwasAccession[])
  } catch (e) {
    return fail<GwasAccession[]>(toMessage(e), [])
  }
}

/** 获取表型数据 — 后端需 code，返回 {count, rows:[{accession, trait, value}]} */
export async function getGwasPhenotype(payload: {
  code: string
}): Promise<ApiResult<{ count: number; rows: GwasPhenotypeRow[] }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/gwas/phenotype/', payload)
    return ok(res as unknown as { count: number; rows: GwasPhenotypeRow[] })
  } catch (e) {
    return fail<{ count: number; rows: GwasPhenotypeRow[] }>(toMessage(e), { count: 0, rows: [] })
  }
}

/** 查询 GWAS 标记位点 — 后端需 set_id + code */
export async function getGwasMarkers(payload: {
  set_id: number
  code: string
  chrom?: string
  start?: number
  end?: number
  limit?: number
}): Promise<ApiResult<{ set_id: number; count: number; rows: GwasMarker[] }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/gwas/markers/', payload)
    return ok(res as unknown as { set_id: number; count: number; rows: GwasMarker[] })
  } catch (e) {
    return fail<{ set_id: number; count: number; rows: GwasMarker[] }>(toMessage(e), {
      set_id: 0,
      count: 0,
      rows: [],
    })
  }
}

/** 查询 GWAS 关联结果（曼哈顿图数据） — 后端需 code，返回 {count, rows} */
export async function getGwasAssociations(payload: {
  code: string
  chrom?: string
  start?: number
  end?: number
}): Promise<ApiResult<{ count: number; rows: GwasMarker[] }>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/gwas/associations/', payload)
    return ok(res as unknown as { count: number; rows: GwasMarker[] })
  } catch (e) {
    return fail<{ count: number; rows: GwasMarker[] }>(toMessage(e), { count: 0, rows: [] })
  }
}

// ==================== 十八、基因组坐标 / 基因ID转换 ====================
// 后端契约见 docs/坐标与基因ID转换_前端对接文档.md（v1，2026-11-18）
// 已用 curl 实测：/conversion/pairs/、/conversion/coordinate/、/conversion/geneid/ 均可返回真实数据。

/** 一个可用的转换方向（chain 是单向的，只支持 source -> target） */
export interface ConversionPair {
  source: string
  target: string
  /** 后端内部 chain 路径，仅供调试，不展示给用户 */
  chain: string
}

/** 转换工具可用性：值为 null 表示该工具当前不可用 */
export interface ConversionTools {
  liftover: string | null
  crossmap: string | null
}

export interface ConversionPairsResult {
  pairs: ConversionPair[]
  count: number
  tools: ConversionTools
  default_tool: 'crossmap' | 'liftover'
}

/** 批量区间输入（1-based inclusive） */
export interface ConversionRegion {
  chr: string
  start: number
  end: number
  strand?: '+' | '-'
}

export interface ConversionInterval {
  chr: string
  start: number
  end: number
}

/** 坐标转换状态：mapped 完整映射 / partial 部分映射 / split 多区间 / unmapped 未映射 */
export type CoordinateStatus = 'mapped' | 'partial' | 'split' | 'unmapped'

/** 单条区间转换结果（批量结果里的元素同构，另可能带 error/input） */
export interface CoordinateConversionResult {
  query?: { genome?: string; chr: string; start: number; end: number; strand?: string }
  target_genome?: string
  tool?: string
  status: CoordinateStatus
  found: boolean
  /** 仅 crossmap 提供；liftover 恒为 null */
  map_ratio: number | null
  target_interval: ConversionInterval | null
  target_intervals: ConversionInterval[]
  segments?: Array<{ target_chr: string; target_start: number; target_end: number }>
  chain?: string
  /** 单条参数非法时返回，其余行不受影响 */
  error?: string
  input?: Record<string, unknown>
}

/** 批量区间转换响应 */
export interface BatchCoordinateConversionResult {
  chain?: string
  tool: string
  count: number
  results: CoordinateConversionResult[]
}

/** 基因 ID 转换状态 */
export type GeneIdStatus = 'mapped' | 'no_target_gene' | 'unmapped' | 'not_found'

export interface TargetGene {
  gene_id: string
  chr: string
  start: number
  end: number
  strand: string
}

export interface GeneIdConversionRow {
  gene_id: string
  status: GeneIdStatus
  source: { chr: string; start: number; end: number; strand: string } | null
  target_genes: TargetGene[]
  target_intervals: ConversionInterval[]
}

export interface GeneIdConversionResult {
  source_genome: string
  target_genome: string
  chain?: string
  tool: string
  count: number
  /** 成功条数，可直接用于「成功 N / 共 M」的汇总展示 */
  mapped: number
  results: GeneIdConversionRow[]
}

/** 转换接口公共参数 */
interface ConversionCommonPayload {
  source_genome: string
  target_genome: string
  tool?: 'crossmap' | 'liftover'
  /** liftOver -minMatch，默认 0.95 */
  min_match?: number
  /** CrossMap -r，默认 0 */
  min_map_ratio?: number
}

/** 坐标转换请求：单个区间（chrom/start/end）或批量（regions，最多 5000 条） */
export type CoordinateConversionPayload = ConversionCommonPayload &
  (
    | { chrom: string; start: number; end: number; strand?: '+' | '-' }
    | { regions: ConversionRegion[] }
  )

/** 基因 ID 转换请求 */
export interface GeneIdConversionPayload extends ConversionCommonPayload {
  /** 数组或逗号/空格/换行分隔的字符串，最多 5000 个 */
  gene_ids: string[] | string
}

/** 转换接口可能耗时较长（crossmap 冷启动约 20s），放宽超时到 120s */
const CONVERSION_TIMEOUT = 120000

/** 获取可用的转换方向与工具 */
export async function getConversionPairs(): Promise<ApiResult<ConversionPairsResult>> {
  try {
    const res = await httpInstance.get('/CottonOGD_api/conversion/pairs/')
    return ok(res as unknown as ConversionPairsResult)
  } catch (e) {
    return fail<ConversionPairsResult>(toMessage(e), {
      pairs: [],
      count: 0,
      tools: { liftover: null, crossmap: null },
      default_tool: 'liftover',
    })
  }
}

/** 区间转换：传 chrom/start/end 时返回单条结果，传 regions 时返回批量结果 */
export async function convertCoordinate(
  payload: CoordinateConversionPayload,
): Promise<ApiResult<CoordinateConversionResult | BatchCoordinateConversionResult>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/conversion/coordinate/', payload, {
      timeout: CONVERSION_TIMEOUT,
    })
    return ok(res as unknown as CoordinateConversionResult | BatchCoordinateConversionResult)
  } catch (e) {
    return fail<CoordinateConversionResult | BatchCoordinateConversionResult>(toMessage(e))
  }
}

/** 基因 ID 转换（单个或批量） */
export async function convertGeneIds(
  payload: GeneIdConversionPayload,
): Promise<ApiResult<GeneIdConversionResult>> {
  try {
    const res = await httpInstance.post('/CottonOGD_api/conversion/geneid/', payload, {
      timeout: CONVERSION_TIMEOUT,
    })
    return ok(res as unknown as GeneIdConversionResult)
  } catch (e) {
    return fail<GeneIdConversionResult>(toMessage(e), {
      source_genome: payload.source_genome,
      target_genome: payload.target_genome,
      tool: payload.tool || 'liftover',
      count: 0,
      mapped: 0,
      results: [],
    })
  }
}