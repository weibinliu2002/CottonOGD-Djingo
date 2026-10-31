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

/** 检索入参 */
export interface SearchParams {
  q: string
  index?: string
  offset?: number
  limit?: number
  genomeIds?: string[]
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

/** 基因染色体分布查询。注意后端读的参数名是 genome（不是 genome_id） */
export async function getGeneGenomicDistribution(payload: {
  genome: string
  gene_ids?: string
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const formData = new FormData()
    formData.append('genome', payload.genome)
    formData.append('gene_ids', payload.gene_ids ?? '')

    const res = await httpInstance.post('/CottonOGD_api/gene_genomic_distribution/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
  }
}

/** 共线性/变异查询。注意 Variation_type 首字母大写 */
export async function getGenomeSynteny(payload: {
  reference_genome: string
  query_genome: string
  chromosome: string
  Variation_type: string
}): Promise<ApiResult<Record<string, unknown>>> {
  try {
    const formData = new FormData()
    formData.append('reference_genome', payload.reference_genome)
    formData.append('query_genome', payload.query_genome)
    formData.append('chromosome', payload.chromosome)
    formData.append('Variation_type', payload.Variation_type)

    const res = await httpInstance.post('/CottonOGD_api/genome_synteny/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return ok((res ?? {}) as unknown as unknown as Record<string, unknown>)
  } catch (e) {
    return fail<Record<string, unknown>>(toMessage(e), {})
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