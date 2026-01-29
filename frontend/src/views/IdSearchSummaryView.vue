<template>
  <div class="container mt-4">
    <el-card class="mt-4">
      <template #header>
        <div class="card-header">
          <h1>ID搜索结果汇总</h1>
        </div>
      </template>
      
      <!-- 状态信息 -->
      <el-alert
        v-if="results.length > 0"
        :title="`找到 ${results.length} 个基因序列`"
        type="success"
        show-icon
        class="mb-4"
      />
      <el-alert
        v-else-if="!loading && !error"
        title="暂无数据，请检查输入的基因ID"
        type="info"
        show-icon
        class="mb-4"
      />
      
      <!-- 加载状态 -->
      <div v-if="loading" class="text-center py-5">
        <el-loading :fullscreen="false" text="正在加载数据，请稍候..." />
      </div>
      
      <!-- 错误信息 -->
      <el-alert
        v-else-if="error"
        :title="`错误: ${error}`"
        type="error"
        show-icon
        class="mt-4"
      >
        <template #default>
          <p>请检查URL参数格式或稍后重试</p>
        </template>
      </el-alert>
      
      <!-- 结果展示 - 只有在加载完成且没有错误时才显示 -->
      <template v-else-if="results">
        <!-- 结果表格 -->
        <el-table :data="results" style="width: 100%" class="mb-4">
          <el-table-column prop="original_id" label="Input ID" width="200" />
          <el-table-column label="Query ID" width="200">
            <template #default="scope">
              <router-link :to="{ path: '/tools/id-search/results/', query: { db_id: scope.row.db_id } }">
                {{ scope.row.IDs || '-' }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column prop="species" label="Species" width="200" />
        </el-table>

        <!-- 序列展示区域 - 为每个基因添加序列按钮 -->
        <div v-if="results.length > 0" class="mt-6">
          <h4>Gene Sequences</h4>
      
            <!-- 使用通用序列展示组件 -->
            <sequence-display
              :results="results"
              :loading="false"
              @show-sequence="handleShowSequence"
              @length-change="handleLengthChange"
            />
         
        
          <!-- 批量操作按钮 -->
          <div class="mt-4">
            <el-button type="primary" @click="downloadAllSequences">Download All Sequences</el-button>
          </div>
        </div>
        <el-empty v-else description="No gene sequences available." class="mt-4" />
      </template>
      
      <!-- 初始状态 - 未开始加载时显示 -->
      <div v-else class="text-center py-5">
        <el-empty description="准备加载数据..." />
      </div>
    </el-card>
    
    <!-- 序列弹窗组件 -->
    <el-dialog
      v-model="showModal"
      :title="modalTitle"
      width="80%"
      destroy-on-close
    >
      <el-scrollbar height="400px">
        <pre class="bg-light p-3 rounded" style="white-space: pre-wrap; font-family: monospace;">
          {{ modalContent }}
        </pre>
      </el-scrollbar>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeModal">Close</el-button>
          <el-button type="primary" @click="downloadFasta">Download FASTA</el-button>
          <el-button type="success" @click="copySequence(modalContent)">Copy Sequence</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>
<script>
import httpInstance from '../utils/http'
import SequenceDisplay from '@/components/SequenceDisplay.vue'

export default {
  name: 'IdSearchSummaryView',
  components: { SequenceDisplay },
  data() {
    return {
      results: [],
      has_sequences: false,
      loading: false,
      error: null,
      selectedUpstreamLength: 10000,
      selectedDownstreamLength: 10000,
      sequenceCache: {},   // key: geneId|type|transcriptId|upLen|downLen
      sequenceLoading: {}, // loading 状态
      showModal: false,
      modalTitle: '',
      modalContent: '',
      currentSeqType: '',
      currentGeneId: ''
    }
  },
  mounted() {
    this.fetchSearchResults()
  },
  methods: {

    handleLengthChange(lengths) {
      let upstreamLength, downstreamLength
      if (typeof lengths === 'object' && lengths !== null) {
        upstreamLength =
          lengths.upstreamLength ?? lengths.upstream ?? this.selectedUpstreamLength
        downstreamLength =
          lengths.downstreamLength ?? lengths.downstream ?? this.selectedDownstreamLength
      } else {
        upstreamLength = lengths ?? this.selectedUpstreamLength
        downstreamLength = lengths ?? this.selectedDownstreamLength
      }

      const changed =
        upstreamLength !== this.selectedUpstreamLength ||
        downstreamLength !== this.selectedDownstreamLength

      this.selectedUpstreamLength = upstreamLength
      this.selectedDownstreamLength = downstreamLength

      if (changed) {
        // 清理上下游 cache
        Object.keys(this.sequenceCache).forEach(key => {
          if (key.includes('|upstream|') || key.includes('|downstream|')) {
            delete this.sequenceCache[key]
          }
        })
        this.scheduleSequencePreload()
      }
    },

    async fetchSearchResults() {
      this.loading = true
      this.error = null
      this.results = []
      this.has_sequences = false

      try {
        const queryParams = new URLSearchParams(window.location.search)
        let geneIds = queryParams.get('db_id')
        if (!geneIds) {
          this.error = 'URL中未找到基因ID参数'
          this.loading = false
          return
        }
        
        // 获取并解析搜索映射参数
        const searchMapStr = queryParams.get('searchMap')
        let searchMap = {}
        if (searchMapStr) {
          try {
            searchMap = JSON.parse(searchMapStr)
            console.log('解析后的 searchMap:', searchMap)
          } catch (error) {
            console.error('解析 searchMap 失败:', error)
          }
        }
        
        // 获取并解析基因信息参数
        const geneInfoResultStr = queryParams.get('geneInfoResult')
        let geneInfoResult = []
        if (geneInfoResultStr) {
          try {
            geneInfoResult = JSON.parse(geneInfoResultStr)
            console.log('解析后的 geneInfoResult:', geneInfoResult)
          } catch (error) {
            console.error('解析 geneInfoResult 失败:', error)
          }
        }
        
        // 获取并解析基因ID参数
        const geneidResultStr = queryParams.get('geneidResult')
        let geneidResult = []
        if (geneidResultStr) {
          try {
            geneidResult = JSON.parse(geneidResultStr)
            console.log('解析后的 geneidResult:', geneidResult)
          } catch (error) {
            console.error('解析 geneidResult 失败:', error)
          }
        }

        // 使用 searchMap 构建结果，不再使用 geneIds
        this.results = []
        if (searchMap && typeof searchMap === 'object') {
          // 遍历 searchMap 中的每个条目
          for (const [originalId, info] of Object.entries(searchMap)) {
            if (info && typeof info === 'object') {
              this.results.push({
                original_id: originalId,  // 使用带 .1 的原始 ID
                IDs: info.geneid,         // 使用 geneid 作为 IDS
                db_id: info.db_id,        // 使用 db_id 作为数据库 ID
                species: info.genome_id || '未知物种',  // 使用 genome_id 作为物种
                mrna_transcripts: [{ id: info.geneid }]  // 添加默认的转录本信息
              })
            }
          }
        }
        
        // 如果 searchMap 解析失败，使用 geneIds 作为后备
        if (this.results.length === 0 && geneIds) {
          const geneIdList = geneIds.split(',')
          this.results = geneIdList.map(id => ({
            original_id: id,  // 使用输入的ID作为原始ID
            IDs: id,           // 使用输入的ID作为查询ID
            db_id: id,         // 使用输入的ID作为数据库ID
            species: '未知物种',  // 默认为未知物种，后续可以通过其他API获取
            mrna_transcripts: [{ id: id }]  // 添加默认的转录本信息
          }))
        }
        
        this.has_sequences = this.results.length > 0
        
        // 页面挂载后立即预热序列
        this.scheduleSequencePreload()
        
      } catch (error) {
        console.error('获取数据失败:', error)
        this.error = '获取数据失败: ' + (error.message || '未知错误')
      } finally {
        this.loading = false
      }
    },

    async scheduleSequencePreload() {
      if (!this.results?.length) return

      const typesToPreload = ['upstream', 'downstream', 'mrna', 'cdna', 'cds', 'protein']
      const upLen = this.selectedUpstreamLength || 500
      const downLen = this.selectedDownstreamLength || 500
      const batchPayload = []

      this.results.forEach(geneData => {
  const geneId = geneData.IDs

  // 统一 transcript 粒度
  const transcripts = geneData.mrna_transcripts?.length
    ? geneData.mrna_transcripts
    : [{ id: geneId }]

  transcripts.forEach(t => {
    const transcriptId = t.id || t.transcript_id || geneId

    typesToPreload.forEach(type => {
      const cacheKey = `${geneId}|${type}|${transcriptId}|${upLen}|${downLen}`

      // 已缓存 / 正在加载 → 跳过
      if (this.sequenceCache[cacheKey] || this.sequenceLoading[cacheKey]) return

      batchPayload.push({
        gene_id: geneId,
        transcript_id: transcriptId,
        type,
        upstream_length: upLen,
        downstream_length: downLen,
        cacheKey
      })

      this.sequenceLoading[cacheKey] = true
    })
  })
})

if (!batchPayload.length) return


      try {
  // 获取所有唯一的 db_id
  const dbIds = [...new Set(this.results.map(geneData => geneData.db_id).filter(Boolean))]
  
  if (dbIds.length === 0) {
    console.warn('No db_ids found for sequence extraction')
    batchPayload.forEach(r => {
      this.sequenceLoading[r.cacheKey] = false
    })
    return
  }

  const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''

  // 按照后端期望的格式传递参数
  const apiPayload = {
    db_id: dbIds
  }

  const res = await httpInstance.post(
    '/CottonOGD_api/extract_seq/',
    apiPayload,
    { headers: { 'X-CSRFToken': csrfToken } }
  )

  // 处理后端返回的数据
  console.log('Extract seq response:', res)
  
  // 暂时将所有缓存键标记为加载完成
  batchPayload.forEach(r => {
    this.sequenceCache[r.cacheKey] = 'Sequence data available'
    this.sequenceLoading[r.cacheKey] = false
  })
} catch (err) {
  console.error('批量热加载失败', err)
  batchPayload.forEach(r => {
    this.sequenceLoading[r.cacheKey] = false
  })
}

    },

    formatSequence(seq) {
      if (!seq) return ''
      return seq.replace(/(.{1,80})/g, '$1\n')
    },

    handleShowSequence({ type, title, content, id }) {
      this.modalTitle = title
      this.currentSeqType = type
      this.currentGeneId = id

      const upLen = this.selectedUpstreamLength || 500
      const downLen = this.selectedDownstreamLength || 500
      let allFastaContent = ''

      this.results.forEach(geneData => {
        const geneId = geneData.IDs
        if (type === 'genomic' && geneData.gene_seq && geneData.gene_seq !== 'N/A') {
          allFastaContent += `>${geneId} genomic\n${this.formatSequence(geneData.gene_seq)}\n\n`
          return
        }

        const transcripts = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts : [geneData]

        transcripts.forEach(transcript => {
          const transcriptId = transcript.id || transcript.transcript_id || geneId
          const cacheKey = `${geneId}|${type}|${transcriptId}|${upLen}|${downLen}`
          allFastaContent += this.sequenceCache[cacheKey]
            ? this.sequenceCache[cacheKey] + '\n\n'
            : `>${transcriptId} ${type}\n序列未加载\n\n`
        })
      })

      this.modalContent = allFastaContent.trim() || '未找到该类型的序列'
      this.showModal = true
    },

    closeModal() {
      this.showModal = false
    },

    downloadFasta() {
      const blob = new Blob([this.modalContent], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${this.currentGeneId}_${this.currentSeqType}_all_transcripts.fasta`
      a.click()
      URL.revokeObjectURL(url)
    },

    downloadAllSequences() {
      if (!this.results?.length) return
      const types = ['genomic', 'upstream', 'downstream', 'mrna', 'cdna', 'cds', 'protein']
      const upLen = this.selectedUpstreamLength || 500
      const downLen = this.selectedDownstreamLength || 500

      let allContent = ''
      this.results.forEach(geneData => {
        const geneId = geneData.IDs
        types.forEach(type => {
          if (type === 'genomic' && geneData.gene_seq && geneData.gene_seq !== 'N/A') {
            allContent += `>${geneId} genomic\n${this.formatSequence(geneData.gene_seq)}\n\n`
            return
          }

          const transcripts = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts : [geneData]
          transcripts.forEach(transcript => {
            const transcriptId = transcript.id || transcript.transcript_id || geneId
            const cacheKey = `${geneId}|${type}|${transcriptId}|${upLen}|${downLen}`
            allContent += this.sequenceCache[cacheKey]
              ? this.sequenceCache[cacheKey] + '\n\n'
              : `>${transcriptId} ${type}\n序列未加载\n\n`
          })
        })
      })

      const blob = new Blob([allContent.trim()], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `all_genes_all_sequences.fasta`
      a.click()
      URL.revokeObjectURL(url)
    }

  }
}
</script>






<style scoped>
/* 可以添加组件特定的样式 */
</style>