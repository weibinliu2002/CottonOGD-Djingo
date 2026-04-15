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
    
    // http.js 的响应拦截器直接返回 response.data
    const data = await meilisearchClient.post('/CottonOGD_api/search_genes_meilisearch/', params)
    // 确保返回一致的结构
    return {
      success: data.success || false,
      results: data.results || [],
      total: data.total || 0,
      processing_time: data.processing_time || 0
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
