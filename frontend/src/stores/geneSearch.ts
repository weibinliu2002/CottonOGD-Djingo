import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import httpInstance from '@/utils/http.js'
import { useUUIDStore } from './uuidStore.ts'
import { useNavigationStore } from './navigationStore.ts'

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
  const navigationStore = useNavigationStore()

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
      if (data && data.geneid_result) {
        console.log('Search success');
        searchResults.value = {
          geneid_result: typeof data.geneid_result === 'string' ? JSON.parse(data.geneid_result) : data.geneid_result,
          gene_info_result: typeof data.gene_info_result === 'string' ? JSON.parse(data.gene_info_result) : data.gene_info_result,
          search_map: typeof data.search_map === 'string' ? JSON.parse(data.search_map) : data.search_map
        };
        console.log('Parsed Search Results:', searchResults.value);

        const dbIds = searchResults.value?.search_map 
          ? Object.values(searchResults.value.search_map).map((item: any) => item.db_id).filter(Boolean)
          : [];
        console.log('DB IDs:', dbIds);

        navigationStore.setNavigationData('geneSearch', {
          results: searchResults.value,
          dbIds: dbIds,
          requestId: request_id
        });

        router.push({
          name: 'idSearchSummary'
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
    // 对于上游和下游序列，缓存键不包含长度参数，以便在不同长度下都能获取完整序列
    const cacheKey = (type === 'upstream' || type === 'downstream')
      ? `${geneId}|${type}|${transcriptId}`
      : `${geneId}|${type}|${transcriptId}|${upstreamLength}|${downstreamLength}`

    // 检查缓存
    if (sequenceCache.value[cacheKey]) {
      console.log('从缓存获取序列:', cacheKey)
      let sequence = sequenceCache.value[cacheKey]
      
      // 对于上游和下游序列，根据用户选择的长度进行截断
      if (type === 'upstream' && sequence.length > upstreamLength) {
        sequence = sequence.slice(0, upstreamLength)
        console.log('上游序列截断到长度:', upstreamLength)
      } else if (type === 'downstream' && sequence.length > downstreamLength) {
        sequence = sequence.slice(0, downstreamLength)
        console.log('下游序列截断到长度:', downstreamLength)
      }
      
      return sequence
    }

    // 检查是否正在加载
    if (sequenceLoading.value[cacheKey]) {
      // 等待加载完成
      return new Promise<string>((resolve) => {
        const checkLoading = setInterval(() => {
          if (!sequenceLoading.value[cacheKey]) {
            clearInterval(checkLoading)
            let sequence = sequenceCache.value[cacheKey] || ''
            
            // 对于上游和下游序列，根据用户选择的长度进行截断
            if (type === 'upstream' && sequence.length > upstreamLength) {
              sequence = sequence.slice(0, upstreamLength)
            } else if (type === 'downstream' && sequence.length > downstreamLength) {
              sequence = sequence.slice(0, downstreamLength)
            }
            
            resolve(sequence)
          }
        }, 100)
      })
    }

    // 如果缓存中没有数据，返回默认值，不再发送 API 请求
    // 因为 IdSearchSummaryView.vue 已经预加载了所有序列数据
    console.log('缓存中没有找到序列:', cacheKey, '返回默认值')
    return '未找到序列'
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
