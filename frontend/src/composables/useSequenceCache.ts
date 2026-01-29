import { ref, type Ref } from 'vue'
import httpInstance from '@/utils/http'
import { ElMessage } from 'element-plus'

interface FetchSequenceParams {
  geneId: string
  transcriptId: string
  type: string
  initialContent: string
  length?: number
  onSuccess: (fastaContent: string) => void
  onError: () => void
}

interface UseSequenceCacheReturn {
  sequenceCache: Ref<Record<string, string>>
  sequenceLoading: Ref<Record<string, boolean>>
  setSequenceCache: (key: string, value: string) => void
  getSequenceCache: (key: string) => string | undefined
  setSequenceLoading: (key: string, value: boolean) => void
  getSequenceLoading: (key: string) => boolean
  clearSequenceCache: (keys?: string[]) => void
  fetchSequence: (params: FetchSequenceParams) => Promise<void>
}

export function useSequenceCache(): UseSequenceCacheReturn {
  const sequenceCache = ref<Record<string, string>>({})
  const sequenceLoading = ref<Record<string, boolean>>({})

  const setSequenceCache = (key: string, value: string) => {
    sequenceCache.value[key] = value
  }

  const getSequenceCache = (key: string) => {
    return sequenceCache.value[key]
  }

  const setSequenceLoading = (key: string, value: boolean) => {
    sequenceLoading.value[key] = value
  }

  const getSequenceLoading = (key: string) => {
    return sequenceLoading.value[key] || false
  }

  const clearSequenceCache = (keys?: string[]) => {
    if (keys) {
      keys.forEach(key => {
        delete sequenceCache.value[key]
        delete sequenceLoading.value[key]
      })
    } else {
      sequenceCache.value = {}
      sequenceLoading.value = {}
    }
  }

  const fetchSequence = async (params: FetchSequenceParams) => {
    const { geneId, transcriptId, type, initialContent, length, onSuccess, onError } = params

    // 对于上下游序列，缓存key需要包含长度信息，确保不同长度的序列缓存分开
    const lengthPart = length ? `|${length}` : ''
    // 使用geneId作为基因ID，确保缓存key的准确性
    const cacheKey = `${geneId}|${type}|${transcriptId}${lengthPart}`

    // 已经加载过，直接使用缓存
    if (sequenceCache.value[cacheKey]) {
      onSuccess(sequenceCache.value[cacheKey])
      return
    }

    // 正在加载，避免重复点击
    if (sequenceLoading.value[cacheKey]) return
    sequenceLoading.value[cacheKey] = true

    try {
      let fastaContent = ''
      let seq = initialContent
      let isFromContent = true
      
      // 如果content为空，向后端请求序列
      if (!seq) {
        isFromContent = false
        const res = await httpInstance.post(
          '/CottonOGD_api/extract_seq/',
          {
            db_id: geneId,
            type: type
          }
        )
        const resData = res as any
        seq = resData.sequence || '未找到序列'
      }
      
      // 如果返回的是有效序列，添加FASTA格式头部
      if (seq && seq !== '未找到序列' && seq !== 'N/A') {
        // 构建FASTA头部，基因组序列使用geneId，其他使用transcriptId
        const headerId = type === 'genomic' ? geneId : transcriptId
        
        // 根据类型和长度截取序列
        let processedSeq = seq
        if (type === 'upstream' && length) {
          processedSeq = seq.slice(0, length)
        } else if (type === 'downstream' && length) {
          processedSeq = seq.slice(0, length)
        }
        
        const lengthInfo = length ? ` (${processedSeq.length}bp)` : ''
        fastaContent = `>${headerId} ${type}${lengthInfo}\n${processedSeq}\n`
      } else {
        // 无效序列直接使用
        fastaContent = seq
      }

      // 缓存FASTA格式的序列
      sequenceCache.value[cacheKey] = fastaContent
      sequenceLoading.value[cacheKey] = false

      // 调用成功回调
      onSuccess(fastaContent)
    } catch (err) {
      console.error('Failed to fetch sequence:', err)
      onError()
    } finally {
      sequenceLoading.value[cacheKey] = false
    }
  }

  return {
    sequenceCache,
    sequenceLoading,
    setSequenceCache,
    getSequenceCache,
    setSequenceLoading,
    getSequenceLoading,
    clearSequenceCache,
    fetchSequence
  }
}
