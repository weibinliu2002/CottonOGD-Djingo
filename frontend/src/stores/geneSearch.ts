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
      // 从 searchResults 中查找 db_id
      let dbId = null
      if (searchResults.value && searchResults.value.search_map) {
        for (const [originalId, info] of Object.entries(searchResults.value.search_map)) {
          if (info.geneid === geneId) {
            dbId = info.db_id
            break
          }
        }
      }

      if (!dbId) {
        console.error('Cannot find db_id for gene:', geneId)
        return '未找到基因对应的数据库ID'
      }

      // 对于上下游序列，使用 extract_seq_gff API 动态提取
      if (type === 'upstream' || type === 'downstream') {
        // 从 searchResults 中查找基因位置信息
        let geneInfo = null
        if (searchResults.value && searchResults.value.geneid_result) {
          const geneItem = searchResults.value.geneid_result.find((item: any) => item.db_id === dbId && item.type === 'gene')
          if (geneItem) {
            geneInfo = {
              start: geneItem.start,
              end: geneItem.end,
              strand: geneItem.strand,
              species: geneItem.species,
              chromosome: geneItem.seqid
            }
          }
        }
        
        if (geneInfo) {
          // 计算上下游序列的位置
          let start, end
          if (type === 'upstream') {
            if (geneInfo.strand === '+') {
              start = geneInfo.start - upstreamLength
              end = geneInfo.start - 1
            } else {
              start = geneInfo.end + 1
              end = geneInfo.end + upstreamLength
            }
          } else { // downstream
            if (geneInfo.strand === '+') {
              start = geneInfo.end + 1
              end = geneInfo.end + downstreamLength
            } else {
              start = geneInfo.start - downstreamLength
              end = geneInfo.start - 1
            }
          }
          
          // 确保位置为正数
          start = Math.max(1, start)
          
          // 调用 extract_seq_gff API 提取序列
          try {
            const gffRes = await httpInstance.post('/CottonOGD_api/extract_seq_gff/', {
              genome_id: geneInfo.species,
              seqid: geneInfo.chromosome || 'unknown',
              start: start,
              end: end,
              strand: geneInfo.strand
            })
            
            if (gffRes.data && gffRes.data.sequence) {
              const sequence = gffRes.data.sequence
              sequenceCache.value[cacheKey] = sequence
              return sequence
            }
          } catch (gffError) {
            console.error('Error fetching sequence from gff:', gffError)
          }
        }
      }

      // 使用 db_id 参数调用后端 API
      const params = {
        db_id: dbId
      }

      console.log('Fetching sequence with db_id:', dbId)

      const response = await httpInstance.post('/CottonOGD_api/extract_seq/', params)
      const data = response as any
      const seqData = data.seq || {}

      // 根据类型获取对应的序列
      let sequence = '未找到序列'
      switch (type) {
        case 'genomic':
          if (seqData.genome_seq && seqData.genome_seq.length > 0) {
            sequence = seqData.genome_seq[0].seq
          }
          break
        case 'mrna':
          if (seqData.mrna_seq && seqData.mrna_seq.length > 0) {
            // 尝试找到匹配的转录本
            const mrnaSeq = seqData.mrna_seq.find((item: any) => 
              item.mrna_id === transcriptId
            )
            sequence = mrnaSeq ? mrnaSeq.seq : seqData.mrna_seq[0].seq
          }
          break
        case 'upstream':
          if (seqData.upstream_seq && seqData.upstream_seq.length > 0) {
            sequence = seqData.upstream_seq[0].seq
          }
          break
        case 'downstream':
          if (seqData.downstream_seq && seqData.downstream_seq.length > 0) {
            sequence = seqData.downstream_seq[0].seq
          }
          break
        case 'cdna':
          if (seqData.cdna_seq && seqData.cdna_seq.length > 0) {
            sequence = seqData.cdna_seq[0].seq
          }
          break
        case 'cds':
          if (seqData.cds_seq && seqData.cds_seq.length > 0) {
            sequence = seqData.cds_seq[0].seq
          }
          break
        case 'protein':
          if (seqData.protein_seq && seqData.protein_seq.length > 0) {
            sequence = seqData.protein_seq[0].seq
          }
          break
      }

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
