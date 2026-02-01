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
              <router-link :to="{ path: '/tools/id-search/results/', query: { db_id: scope.row.db_id, 
                geneData: JSON.stringify(scope.row) } }">
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
    <sequence-modal
      v-model:show-modal="showModal"
      :modal-title="modalTitle"
      :modal-content="modalContent"
      :current-seq-type="currentSeqType"
      :current-gene-id="currentGeneId"
      @download="handleDownload"
      @copy="handleCopy"
    />
  </div>
</template>
<script>
import httpInstance from '../utils/http'
import SequenceDisplay from '@/components/SequenceDisplay.vue'
import SequenceModal from '@/components/SequenceModal.vue'
import { useGeneSearchStore } from '@/stores/geneSearch.ts'
import { useNavigationStore } from '@/stores/navigationStore.ts'

export default {
  name: 'IdSearchSummaryView',
  components: { SequenceDisplay, SequenceModal },
  data() {
    return {
      results: [],
      has_sequences: false,
      loading: false,
      error: null,
      selectedUpstreamLength: 10000,
      selectedDownstreamLength: 10000,
      showModal: false,
      modalTitle: '',
      modalContent: '',
      currentSeqType: '',
      currentGeneId: '',
      geneSearchStore: null,
      navigationStore: null
    }
  },
  created() {
    this.geneSearchStore = useGeneSearchStore()
    this.navigationStore = useNavigationStore()
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
    Object.keys(this.geneSearchStore.sequenceCache).forEach(key => {
      if (key.includes('|upstream|') || key.includes('|downstream|')) {
        delete this.geneSearchStore.sequenceCache[key]
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
        const navigationData = this.navigationStore.getNavigationData('geneSearch')
        
        if (!navigationData || !navigationData.results) {
          this.error = '未找到搜索结果数据，请重新进行搜索'
          this.loading = false
          return
        }

        const searchResults = navigationData.results
        const searchMap = searchResults.search_map || {}
        const geneInfoResult = searchResults.gene_info_result || []
        const geneidResult = searchResults.geneid_result || []

        console.log('从 navigationStore 获取的数据:', searchResults)
        console.log('searchMap:', searchMap)
        console.log('geneInfoResult 长度:', geneInfoResult?.length)
        
        if (geneInfoResult && Array.isArray(geneInfoResult) && geneInfoResult.length > 0) {
          console.log('geneInfoResult[0] 示例:', geneInfoResult[0])
        }
        
        const geneInfoMap = {}
        const mrnaInfoMap = {}
        
        if (geneInfoResult && Array.isArray(geneInfoResult)) {
          geneInfoResult.forEach((item, index) => {
            console.log(`处理 geneInfoResult[${index}]:`, item)
            if (item.db_id) {
              if (item.type === 'gene') {
                geneInfoMap[item.db_id] = {
                  start: item.start,
                  end: item.end,
                  strand: item.strand,
                  species: item.species
                }
                console.log(`添加基因信息到 geneInfoMap: ${item.db_id}`, geneInfoMap[item.db_id])
              } else if (item.type === 'mrna') {
                let transcriptId = ''
                if (item.attributes) {
                  console.log(`  处理 mRNA attributes: ${item.attributes}`)
                  const idMatch = item.attributes.match(/ID=([^;]+)/)
                  if (idMatch) {
                    transcriptId = idMatch[1]
                    console.log(`  提取到转录本 ID: ${transcriptId}`)
                  } else {
                    console.log(`  无法从 attributes 中提取转录本 ID: ${item.attributes}`)
                  }
                } else {
                  console.log(`  mRNA 条目没有 attributes 字段:`, item)
                }
                console.log(`处理 mRNA 条目: db_id=${item.db_id}, transcriptId=${transcriptId}, attributes=${item.attributes}`)
                if (transcriptId) {
                  mrnaInfoMap[transcriptId] = {
                    start: item.start,
                    end: item.end,
                    strand: item.strand,
                    species: item.species,
                    db_id: item.db_id
                  }
                } else {
                  // 如果没有提取到转录本 ID，使用 db_id 作为键
                  console.log(`  使用 db_id 作为转录本键: ${item.db_id}`)
                  mrnaInfoMap[item.db_id] = {
                    start: item.start,
                    end: item.end,
                    strand: item.strand,
                    species: item.species,
                    db_id: item.db_id
                  }
                }
              }
            }
          })
        }
        
        console.log('处理后的 geneInfoMap:', geneInfoMap)
        console.log('处理后的 mrnaInfoMap:', mrnaInfoMap)
        console.log('searchMap keys:', Object.keys(searchMap))

        this.results = []
        if (searchMap && typeof searchMap === 'object') {
          for (const [originalId, info] of Object.entries(searchMap)) {
            console.log(`处理 searchMap 条目: originalId=${originalId}, info=`, info)
            if (info && typeof info === 'object') {
              console.log(`  info.db_id: ${info.db_id}, info.geneid: ${info.geneid}`)
              console.log(`  geneInfoMap 中是否存在 info.db_id (${info.db_id}):`, !!geneInfoMap[info.db_id])
              if (geneInfoMap[info.db_id]) {
                console.log(`  geneInfoMap[${info.db_id}]:`, geneInfoMap[info.db_id])
              }
              
              let speciesInfo = '未知物种'
              
              if (info.genome_id) {
                speciesInfo = info.genome_id
              }
              
              if (geneInfoMap[info.db_id] && geneInfoMap[info.db_id].species) {
                speciesInfo = geneInfoMap[info.db_id].species
              }
              
              if (geneidResult && Array.isArray(geneidResult)) {
                const geneidInfo = geneidResult.find(item => 
                  item.db_id === info.db_id || item.geneid === info.geneid
                )
                if (geneidInfo && geneidInfo.species) {
                  speciesInfo = geneidInfo.species
                }
              }
              
              const geneInfo = geneInfoMap[info.db_id] || {}
              const mrnaTranscripts = []
              
              console.log(`  开始匹配转录本，info.db_id=${info.db_id}`)
              console.log(`  mrnaInfoMap keys:`, Object.keys(mrnaInfoMap))
              
              for (const [transcriptId, mrnaInfo] of Object.entries(mrnaInfoMap)) {
                console.log(`    检查转录本: transcriptId=${transcriptId}, mrnaInfo.db_id=${mrnaInfo.db_id}, 是否匹配=${mrnaInfo.db_id === info.db_id}`)
                if (mrnaInfo.db_id === info.db_id) {
                  mrnaTranscripts.push({
                    id: transcriptId,
                    start: mrnaInfo.start,
                    end: mrnaInfo.end,
                    strand: mrnaInfo.strand
                  })
                  console.log(`      添加转录本:`, transcriptId)
                }
              }
              
              console.log(`  最终 mrnaTranscripts 数量: ${mrnaTranscripts.length}`)
              
              if (mrnaTranscripts.length === 0) {
                mrnaTranscripts.push({ id: info.geneid })
                console.log(`  使用默认转录本: ${info.geneid}`)
              }
              
              this.results.push({
                original_id: originalId,
                IDs: info.geneid,
                db_id: info.db_id,
                species: speciesInfo,
                start: geneInfo.start,
                end: geneInfo.end,
                strand: geneInfo.strand,
                mrna_transcripts: mrnaTranscripts
              })
            }
          }
        }
        
        this.has_sequences = this.results.length > 0
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
      if (this.geneSearchStore.sequenceCache[cacheKey] || this.geneSearchStore.sequenceLoading[cacheKey]) return

      batchPayload.push({
        gene_id: geneId,
        transcript_id: transcriptId,
        type,
        upstream_length: upLen,
        downstream_length: downLen,
        cacheKey
      })

      this.geneSearchStore.sequenceLoading[cacheKey] = true
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
      this.geneSearchStore.sequenceLoading[r.cacheKey] = false
    })
    return
  }

  const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''

  // 按照后端期望的格式传递参数
  const apiPayload = {
    db_id: dbIds
  }

  console.log('Sending batch sequence request with db_ids:', dbIds)

  const res = await httpInstance.post(
    '/CottonOGD_api/extract_seq/',
    apiPayload,
    { headers: { 'X-CSRFToken': csrfToken } }
  )

  // 处理后端返回的数据
  console.log('Extract seq response:', res)
  
  // 解析返回的序列数据并存储到缓存
  const seqData = res.data?.seq || {}
  
  // 为每个缓存键设置对应的序列数据
  for (const r of batchPayload) {
    // 根据类型获取对应的序列
    let sequence = '未找到序列'
    switch (r.type) {
      case 'genomic':
        if (seqData.genome_seq && seqData.genome_seq.length > 0) {
          sequence = seqData.genome_seq[0].seq
        }
        break
      case 'mrna':
        if (seqData.mrna_seq && seqData.mrna_seq.length > 0) {
          // 尝试找到匹配的转录本
          const mrnaSeq = seqData.mrna_seq.find(item => 
            item.mrna_id === r.transcript_id
          )
          sequence = mrnaSeq ? mrnaSeq.seq : seqData.mrna_seq[0].seq
        }
        break
      case 'upstream':
      case 'downstream':
        // 对于上下游序列，需要根据长度参数动态计算位置并提取
        const geneData = this.results.find(g => g.IDs === r.gene_id)
        if (geneData && geneData.db_id) {
          const geneInfo = this.geneInfoMap[geneData.db_id]
          if (geneInfo) {
            console.log(`计算 ${r.type} 序列位置:`, geneInfo)
            // 计算上下游序列的位置
            let start, end
            if (r.type === 'upstream') {
              if (geneInfo.strand === '+') {
                start = geneInfo.start - r.upstream_length
                end = geneInfo.start - 1
              } else {
                start = geneInfo.end + 1
                end = geneInfo.end + r.upstream_length
              }
            } else { // downstream
              if (geneInfo.strand === '+') {
                start = geneInfo.end + 1
                end = geneInfo.end + r.downstream_length
              } else {
                start = geneInfo.start - r.downstream_length
                end = geneInfo.start - 1
              }
            }
            
            // 确保位置为正数
            start = Math.max(1, start)
            
            console.log(`提取 ${r.type} 序列: genome_id=${geneInfo.species}, seqid=${geneData.chromosome || 'unknown'}, start=${start}, end=${end}, strand=${geneInfo.strand}`)
            
            // 调用 extract_seq_gff API 提取序列
            try {
              const gffRes = await httpInstance.post(
                '/CottonOGD_api/extract_seq_gff/',
                {
                  genome_id: geneInfo.species,
                  seqid: geneData.chromosome || 'unknown',
                  start: start,
                  end: end,
                  strand: geneInfo.strand
                },
                { headers: { 'X-CSRFToken': csrfToken } }
              )
              console.log(`${r.type} 序列提取响应:`, gffRes)
              if (gffRes.data && gffRes.data.sequence) {
                sequence = gffRes.data.sequence
              }
            } catch (gffError) {
              console.error(`提取 ${r.type} 序列失败:`, gffError)
            }
          }
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
    this.geneSearchStore.sequenceCache[r.cacheKey] = sequence
    this.geneSearchStore.sequenceLoading[r.cacheKey] = false
  }
} catch (err) {
  console.error('批量热加载失败', err)
  batchPayload.forEach(r => {
    this.geneSearchStore.sequenceLoading[r.cacheKey] = false
  })
}

    },

    formatSequence(seq) {
      if (!seq) return ''
      return seq.replace(/(.{1,80})/g, '$1\n')
    },

    async handleShowSequence({ type, title, content, id }) {
      this.modalTitle = title
      this.currentSeqType = type
      this.currentGeneId = id

      const upLen = this.selectedUpstreamLength || 500
      const downLen = this.selectedDownstreamLength || 500
      let allFastaContent = ''

      for (const geneData of this.results) {
        const geneId = geneData.IDs
        if (type === 'genomic' && geneData.gene_seq && geneData.gene_seq !== 'N/A') {
          allFastaContent += `>${geneId} genomic\n${this.formatSequence(geneData.gene_seq)}\n\n`
          continue
        }

        const transcripts = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts : [geneData]

        for (const transcript of transcripts) {
          const transcriptId = transcript.id || transcript.transcript_id || geneId
          try {
            const sequence = await this.geneSearchStore.fetchSequence(geneId, transcriptId, type, upLen, downLen)
            if (sequence && sequence !== '未找到序列' && sequence !== 'N/A') {
              allFastaContent += `>${transcriptId} ${type}\n${this.formatSequence(sequence)}\n\n`
            } else {
              allFastaContent += `>${transcriptId} ${type}\n${sequence}\n\n`
            }
          } catch (error) {
            console.error('Error fetching sequence:', error)
            allFastaContent += `>${transcriptId} ${type}\n序列获取失败\n\n`
          }
        }
      }

      this.modalContent = allFastaContent.trim() || '未找到该类型的序列'
      this.showModal = true
    },

    handleDownload({ content, type, geneId }) {
      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${geneId}_${type}_all_transcripts.fasta`
      a.click()
      URL.revokeObjectURL(url)
    },

    handleCopy({ content }) {
      navigator.clipboard.writeText(content).then(() => {
        this.$message.success('序列已复制到剪贴板')
      }).catch(err => {
        console.error('复制失败:', err)
        this.$message.error('复制失败，请手动复制')
      })
    },

    async downloadAllSequences() {
      if (!this.results?.length) return
      const types = ['genomic', 'upstream', 'downstream', 'mrna', 'cdna', 'cds', 'protein']
      const upLen = this.selectedUpstreamLength || 500
      const downLen = this.selectedDownstreamLength || 500

      let allContent = ''
      
      for (const geneData of this.results) {
        const geneId = geneData.IDs
        for (const type of types) {
          if (type === 'genomic' && geneData.gene_seq && geneData.gene_seq !== 'N/A') {
            allContent += `>${geneId} genomic\n${this.formatSequence(geneData.gene_seq)}\n\n`
            continue
          }

          const transcripts = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts : [geneData]
          for (const transcript of transcripts) {
            const transcriptId = transcript.id || transcript.transcript_id || geneId
            try {
              const sequence = await this.geneSearchStore.fetchSequence(geneId, transcriptId, type, upLen, downLen)
              if (sequence && sequence !== '未找到序列' && sequence !== 'N/A') {
                allContent += `>${transcriptId} ${type}\n${this.formatSequence(sequence)}\n\n`
              } else {
                allContent += `>${transcriptId} ${type}\n${sequence}\n\n`
              }
            } catch (error) {
              console.error('Error fetching sequence:', error)
              allContent += `>${transcriptId} ${type}\n序列获取失败\n\n`
            }
          }
        }
      }

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