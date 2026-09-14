/**
 * 基因搜索 API 封装（统一后端检索模式）
 *
 * 前端不直接访问 Meilisearch：所有检索请求经 Django 统一检索端点
 * `/CottonOGD_api/search/` 代理（Meilisearch 地址与 API key 仅存在于后端），
 * 认证与全站一致（Bearer token / auth_token cookie，见 utils/http.js）。
 */

import httpInstance from './http.js'

/** 基因主索引名（作为 index 参数传给后端统一检索端点） */
export const MEILI_INDEX = 'genemaster'

/**
 * Meilisearch 默认分页窗口上限：offset + limit 不得超过该值，否则报错。
 * 深分页场景应引导用户细化关键词或使用过滤条件。
 */
export const MEILI_MAX_WINDOW = 1000

/** genemaster 索引文档结构 */
export interface MeiliGeneDoc {
  /** 主键，对应 MySQL genemaster 表自增 id */
  id: string
  /** 基因 ID（不同基因组下可能重复，展示时必须同时给出 genome_id） */
  geneid: string
  /** 所属基因组（物种名） */
  genome_id: string
  /** 检索别名，格式 "{基因组}::{基因ID}"，全局唯一 */
  alias: string
}

/** 带高亮信息的搜索命中 */
export interface MeiliGeneHit extends MeiliGeneDoc {
  /** 高亮结果（含 <em> 标签），仅 attributesToHighlight 指定的字段存在 */
  _formatted?: Partial<Record<keyof MeiliGeneDoc, string>>
}

/** 统一的搜索响应结构 */
export interface MeiliSearchResult {
  hits: MeiliGeneHit[]
  estimatedTotalHits: number
  processingTimeMs: number
  offset: number
  limit: number
  /** 按 genome_id 聚合的命中数（请求 facets 时返回），用于物种过滤下拉 */
  genomeFacets: Record<string, number>
}

/** Meilisearch 业务错误（携带 HTTP 状态码与错误码） */
export class MeiliSearchError extends Error {
  status: number
  code: string

  constructor(message: string, status: number, code = '') {
    super(message)
    this.name = 'MeiliSearchError'
    this.status = status
    this.code = code
  }
}

export interface GeneSearchParams {
  q: string
  offset?: number
  limit?: number
  /** 检索索引 uid（genemaster / family ...），默认 genemaster */
  index?: string
  /** 按 genome_id 过滤（多选时 OR 连接） */
  genomeIds?: string[]
  /** 是否请求分面统计，默认 true（使用 facets 默认值） */
  withFacets?: boolean
  /** 分面字段，默认 ['genome_id']；非基因索引应传该索引已配置的分面字段 */
  facets?: string[]
  /** 指定返回字段，默认基因索引字段集 */
  attributesToRetrieve?: string[]
  /** 取消信号，用于丢弃过期请求 */
  signal?: AbortSignal
}

/** 后端返回的可选检索索引信息 */
export interface SearchIndexInfo {
  /** 索引 uid，作为搜索请求的 index 参数 */
  uid: string
  /** 展示名称 */
  label: string
  /** 索引是否已建好可检索 */
  available: boolean
}

/** 拉取当前可用的检索索引列表（经后端统一端点） */
export async function getSearchIndexes(): Promise<SearchIndexInfo[]> {
  try {
    const data = await httpInstance.get('/CottonOGD_api/get_search_indexes/') as Record<string, any>
    return Array.isArray(data?.indexes) ? (data.indexes as SearchIndexInfo[]) : []
  } catch (e) {
    console.error('Failed to load search indexes:', e)
    return []
  }
}

/** 过滤值转义：双引号会破坏过滤表达式，必须转义 */
function escapeFilterValue(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
}

/**
 * 构造 genome_id 过滤表达式。
 * 注意：genome_id 是字符串，值必须用双引号包裹，否则报 invalid_request_filter；
 * 多个基因组用 OR 连接：'genome_id = "Cotton" OR genome_id = "Soybean"'。
 */
function buildGenomeFilter(genomeIds: string[]): string | undefined {
  if (genomeIds.length === 0) return undefined
  const conds = genomeIds.map((g) => `genome_id = "${escapeFilterValue(g)}"`)
  return genomeIds.length === 1 ? conds[0] : `(${conds.join(' OR ')})`
}

/** 清洗高亮 HTML：只保留 Meilisearch 的 <em> 标签，其余标签一律移除，防注入 */
export function sanitizeHighlight(html: string): string {
  return html.replace(/<(?!\/?em\b)[^>]*>/gi, '')
}

/** 纯文本转 HTML（用于无高亮内容时的兜底展示） */
export function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/**
 * 搜索 genemaster 索引（经后端统一检索端点代理）。
 * 关键词与过滤条件是独立参数：filter 不拼进 q。
 */
export async function searchGenes(params: GeneSearchParams): Promise<MeiliSearchResult> {
  const {
    q,
    offset = 0,
    limit = 20,
    index = MEILI_INDEX,
    genomeIds = [],
    withFacets = true,
    facets = ['genome_id'],
    attributesToRetrieve,
    signal,
  } = params

  const body: Record<string, unknown> = {
    index,
    q,
    offset,
    limit,
    // 默认：基因索引只取展示字段；其他索引（family 等）返回全部字段
    attributesToRetrieve: attributesToRetrieve ?? (
      index === MEILI_INDEX
        ? ['id', 'geneid', 'alias', 'genome_id']
        : ['*']
    ),
    attributesToHighlight: ['geneid', 'alias'],
  }
  const filter = buildGenomeFilter(genomeIds)
  if (filter) body.filter = filter
  if (withFacets) body.facets = facets

  try {
    // http.js 的响应拦截器直接返回 response.data；401 时自动重登并重放
    const data = await httpInstance.post('/CottonOGD_api/search/', body, { signal }) as Record<string, any>
    return {
      hits: data.hits ?? [],
      estimatedTotalHits: data.estimatedTotalHits ?? 0,
      processingTimeMs: data.processingTimeMs ?? 0,
      offset: data.offset ?? offset,
      limit: data.limit ?? limit,
      genomeFacets: (data.facetDistribution?.genome_id ?? {}) as Record<string, number>,
    }
  } catch (e: any) {
    // 主动取消不算错误，向上抛出由调用方忽略（axios: CanceledError / ERR_CANCELED）
    if (e?.name === 'AbortError' || e?.name === 'CanceledError' || e?.code === 'ERR_CANCELED') throw e
    const status: number = e?.response?.status ?? 0
    const message: string = e?.response?.data?.message || e?.message || '无法连接搜索服务，请检查网络后重试'
    const code: string = e?.response?.data?.code || 'network_error'
    throw new MeiliSearchError(message, status, code)
  }
}
