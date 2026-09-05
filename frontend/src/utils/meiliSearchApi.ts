/**
 * Meilisearch 基因搜索 API 封装（直连模式）
 *
 * - 生产环境：Meilisearch 经 Nginx 反向代理同源暴露（如 https://<域名>/meili），无 CORS 问题
 * - 本地开发：直接连 http://localhost:7700
 * - 认证：Authorization: Bearer <SEARCH_API_KEY>，key 仅具 search 权限，通过环境变量注入
 *
 * 环境变量（见 .env.development / .env.production）：
 *   VITE_MEILI_HOST       Meilisearch 地址，如 https://example.com/meili 或 http://localhost:7700
 *   VITE_MEILI_SEARCH_KEY 仅限 search 权限的 API key（切勿硬编码在源码中）
 */

const MEILI_HOST = (import.meta.env.VITE_MEILI_HOST || 'http://localhost:7700').replace(/\/+$/, '')
const SEARCH_KEY: string = import.meta.env.VITE_MEILI_SEARCH_KEY || ''

/** 基因主索引名 */
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
  /** 按 genome_id 过滤（多选时 OR 连接） */
  genomeIds?: string[]
  /** 是否请求 genome_id 分面统计，默认 true */
  withFacets?: boolean
  /** 取消信号，用于丢弃过期请求 */
  signal?: AbortSignal
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
 * 搜索 genemaster 索引。
 * 关键词与过滤条件是独立参数：filter 不拼进 q。
 */
export async function searchGenes(params: GeneSearchParams): Promise<MeiliSearchResult> {
  const { q, offset = 0, limit = 20, genomeIds = [], withFacets = true, signal } = params

  const body: Record<string, unknown> = {
    q,
    offset,
    limit,
    attributesToRetrieve: ['id', 'geneid', 'alias', 'genome_id'],
    attributesToHighlight: ['geneid', 'alias'],
  }
  const filter = buildGenomeFilter(genomeIds)
  if (filter) body.filter = filter
  if (withFacets) body.facets = ['genome_id']

  let res: Response
  try {
    res = await fetch(`${MEILI_HOST}/indexes/${MEILI_INDEX}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(SEARCH_KEY ? { Authorization: `Bearer ${SEARCH_KEY}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    })
  } catch (e) {
    // 主动取消不算错误，向上抛出由调用方忽略
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    throw new MeiliSearchError('无法连接搜索服务，请检查网络后重试', 0, 'network_error')
  }

  if (!res.ok) {
    let message = `搜索服务错误（HTTP ${res.status}）`
    let code = ''
    try {
      const err = await res.json()
      message = err.message || message
      code = err.code || ''
    } catch {
      /* 非 JSON 响应体，使用默认消息 */
    }
    throw new MeiliSearchError(message, res.status, code)
  }

  const data = await res.json()
  return {
    hits: data.hits ?? [],
    estimatedTotalHits: data.estimatedTotalHits ?? 0,
    processingTimeMs: data.processingTimeMs ?? 0,
    offset: data.offset ?? offset,
    limit: data.limit ?? limit,
    genomeFacets: (data.facetDistribution?.genome_id ?? {}) as Record<string, number>,
  }
}
