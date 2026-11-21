import httpInstance from './http.js'

const meilisearchClient = httpInstance

export const searchGenes = async (query, options = {}) => {
  try {
    const params = {
      q: query,
      limit: options.limit || 20,
      offset: options.offset || 0,
      genome_id: options.genome_id || null
    }
    
    // v1：统一检索端点（索引名进 URL），http.js 拦截器已解包信封
    const data = await meilisearchClient.post(
      '/CottonOGD_api/api/v1/search/indexes/genemaster/search/',
      {
        q: params.q,
        limit: params.limit,
        offset: params.offset,
        filter: params.genome_id ? `genome_id = "${params.genome_id}"` : undefined
      }
    )
    // 确保返回一致的结构
    return {
      success: true,
      results: data.hits || [],
      total: data.estimatedTotalHits || 0,
      processing_time: data.processingTimeMs || 0
    }
    
  } catch (error) {
    console.error('Meilisearch search error:', error)
    return {
      success: false,
      results: [],
      total: 0,
      error: error.message || 'Search failed'
    }
  }
}

export default meilisearchClient
