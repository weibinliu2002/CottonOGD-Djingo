import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import httpInstance from '@/utils/http.js'
import { useUUIDStore } from './uuidStore.ts'

// 定义接口
interface SearchParams {
  gene_id: string
  genome_id: string
  request_id: string
}

interface GeneIdResult {
  // 根据你的实际数据结构定义
  [key: string]: any
}

interface GeneInfoResult {
  // 根据你的实际数据结构定义
  [key: string]: any
}

interface SearchResult {
  geneid_result: GeneIdResult[]
  gene_info_result: GeneInfoResult[]
  search_map: Record<string, { db_id: number; [key: string]: any }>
}

export const useGeneSearchStore = defineStore('geneSearch', () => {
  const router = useRouter()
  const uuidStore = useUUIDStore()

  // State
  const searchInput = ref('')
  const selectedGenome = ref<string[]>([])
  const searchResults = ref<SearchResult | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const sequenceCache = ref<Record<string, string>>({}) // 缓存序列数据，key: geneId|type|transcriptId|upLen|downLen
  const sequenceLoading = ref<Record<string, boolean>>({}) // 缓存加载状态

  // Actions
  async function performSearch(geneIds: string, genomeId: string[]) {
    console.log('performSearch called');
    isLoading.value = true;
    error.value = null;
    const request_id = uuidStore.uuid;
    console.log('Request ID:', request_id);
    console.log('Search Input:', geneIds);
    console.log('Selected Genome:', genomeId);

    try {
      const params = {
        gene_id: geneIds,
        genome_id: genomeId.join(','),
        request_id: request_id
      };
      console.log('API Request Params:', params);

      const response = await httpInstance.post('/CottonOGD_api/geneid_summary/', params);
      console.log('API Response:', response);

      const data = response as any;
      // 只要返回了 geneid_result，就认为成功
      if (data && data.geneid_result) {
        console.log('Search success');
        searchResults.value = {
          geneid_result: typeof data.geneid_result === 'string' ? JSON.parse(data.geneid_result) : data.geneid_result,
          gene_info_result: typeof data.gene_info_result === 'string' ? JSON.parse(data.gene_info_result) : data.gene_info_result,
          search_map: typeof data.search_map === 'string' ? JSON.parse(data.search_map) : data.search_map
        };
        console.log('Parsed Search Results:', searchResults.value);

        // 导航到总结页面
        // search_map 的结构是: { gene_id: { db_id: number, ... }, ... }
        // 需要提取所有的 db_id
        const dbIds = searchResults.value?.search_map 
          ? Object.values(searchResults.value.search_map).map((item: any) => item.db_id).filter(Boolean)
          : [];
        console.log('Navigating to summary with DB IDs:', dbIds);
        router.push({
          name: 'idSearchSummary',
          query: {
            db_id: dbIds.join(','),
            request_id: request_id
          }
        });
      } else {
        console.error('Search failed: missing geneid_result');
        throw new Error(data.message || 'Search failed: No data returned');
      }
    } catch (e: any) {
      console.error('Search failed with exception:', e);
      error.value = e.message || 'An unknown error occurred';
      searchResults.value = null;
    } finally {
      isLoading.value = false;
      console.log('performSearch finished');
    }
  }

  function clearState() {
    searchInput.value = ''
    selectedGenome.value = []
    searchResults.value = null
    isLoading.value = false
    error.value = null
  }

  function clearError() {
    error.value = null
  }

  function setError(message: string) {
    error.value = message
  }

  // 序列相关方法
  async function fetchSequence(geneId: string, transcriptId: string, type: string, upstreamLength: number = 500, downstreamLength: number = 500) {
    const lengthPart = (type === 'upstream' || type === 'downstream') ? `|${type === 'upstream' ? upstreamLength : downstreamLength}` : ''
    const cacheKey = `${geneId}|${type}|${transcriptId}${lengthPart}`

    // 检查缓存
    if (sequenceCache.value[cacheKey]) {
      return sequenceCache.value[cacheKey]
    }

    // 检查是否正在加载
    if (sequenceLoading.value[cacheKey]) {
      // 等待加载完成
      return new Promise<string>((resolve) => {
        const checkLoading = setInterval(() => {
          if (!sequenceLoading.value[cacheKey]) {
            clearInterval(checkLoading)
            resolve(sequenceCache.value[cacheKey] || '')
          }
        }, 100)
      })
    }

    // 开始加载
    sequenceLoading.value[cacheKey] = true

    try {
      const params: any = {
        gene_id: geneId,
        transcript_id: transcriptId,
        type: type
      }

      if (type === 'upstream') {
        params.upstream_length = upstreamLength
      } else if (type === 'downstream') {
        params.downstream_length = downstreamLength
      }

      const response = await httpInstance.post('/CottonOGD_api/extract_seq/', params)
      const data = response as any
      const sequence = data.sequence || '未找到序列'

      // 缓存序列
      sequenceCache.value[cacheKey] = sequence
      return sequence
    } catch (error: any) {
      console.error('Error fetching sequence:', error)
      return '序列获取失败'
    } finally {
      sequenceLoading.value[cacheKey] = false
    }
  }

  function clearSequenceCache() {
    sequenceCache.value = {}
    sequenceLoading.value = {}
  }

  return {
    // state
    searchInput,
    selectedGenome,
    searchResults,
    isLoading,
    error,
    sequenceCache,
    sequenceLoading,
    // actions
    performSearch,
    clearState,
    clearError,
    setError,
    fetchSequence,
    clearSequenceCache
  }
})
