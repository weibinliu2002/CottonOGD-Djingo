<template>
  <div class="container mt-4">
    <el-card class="mt-4">
      <template #header>
        <div class="card-header">
          <h1>{{ t('id') }}</h1>
        </div>
      </template>
      
      <!-- 状态信息 -->
      <el-alert
        v-if="results.length > 0"
        :title="`${t('found')} ${results.length} ${t('gene_sequences')}`"
        type="success"
        show-icon
        class="mb-4"
      />
      <el-alert
        v-else-if="!loading && !error"
        :title="t('no_data_check_gene_ids')"
        type="info"
        show-icon
        class="mb-4"
      />
      
      <!-- 加载状态 -->
      <div v-if="loading" class="text-center py-5">
        <el-loading :fullscreen="false" :text="t('loading_data_please_wait')" />
      </div>
      
      <!-- 错误信息 -->
      <el-alert
        v-else-if="error"
        :title="`${t('error')}: ${error}`"
        type="error"
        show-icon
        class="mt-4"
      >
        <template #default>
          <p>{{ t('check_url_parameters_or_try_again_later') }}</p>
        </template>
      </el-alert>
      
      <!-- 结果展示 - 只有在加载完成且没有错误时才显示 -->
      <template v-else-if="results">
        <!-- 结果表格 -->
        <el-table :data="results" style="width: 100%" class="mb-4">
          <el-table-column prop="original_id" :label="t('input_id')" width="200" />
          <el-table-column :label="t('query_id')" width="200">
            <template #default="scope">
              <a href="javascript:void(0)" @click="navigateToResults(scope.row)">
                {{ scope.row.IDs || '-' }}
              </a>
            </template>
          </el-table-column>
          <el-table-column prop="species" :label="t('species')" width="200" />
        </el-table>

        <!-- 序列展示区域 - 为每个基因添加序列按钮 -->
        <div v-if="results.length > 0" class="mt-6">
          <h4>{{ t('gene_sequences') }}</h4>
      
            <!-- 使用通用序列展示组件 -->
            <sequence-display
              :results="results"
              :loading="false"
              @show-sequence="handleShowSequence"
              @length-change="handleLengthChange"
            />
         
        
          <!-- 批量操作按钮 -->
          <div class="mt-4">
            <el-button type="primary" @click="downloadAllSequences">{{ t('download_all_sequences') }}</el-button>
          </div>
        </div>
        <el-empty v-else :description="t('no_gene_sequences_available')" class="mt-4" />
      </template>
      
      <!-- 初始状态 - 未开始加载时显示 -->
      <div v-else class="text-center py-5">
        <el-empty :description="t('preparing_to_load_data')" />
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
import { useI18n } from 'vue-i18n'
import httpInstance from '../utils/http'
import SequenceDisplay from '@/components/SequenceDisplay.vue'
import SequenceModal from '@/components/SequenceModal.vue'
import { useGeneSearchStore } from '@/stores/geneSearch.ts'
import { useNavigationStore } from '@/stores/navigationStore.ts'

export default {
  name: 'IdSearchSummaryView',
  components: { SequenceDisplay, SequenceModal },
  setup() {
    const { t } = useI18n()
    return { t }
  },
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

      this.selectedUpstreamLength = upstreamLength
      this.selectedDownstreamLength = downstreamLength

      // 不再清理缓存和重新请求序列，而是在展示时根据长度进行截断
    },

    // 导航到结果详情页
    async navigateToResults(geneData) {
      // 从 navigationStore 获取完整的搜索结果数据
      const navigationData = this.navigationStore.getNavigationData('geneSearch')
      
      if (!navigationData || !navigationData.results) {
        console.error('没有找到搜索结果数据')
        return
      }

      const searchResults = navigationData.results
      const geneInfoResult = searchResults.gene_info_result || []
      const geneidResult = searchResults.geneid_result || []
      
      // 根据当前基因的 db_id 过滤出对应的 geneInfoResult 和 geneidResult
      const currentGeneInfoResult = geneInfoResult.filter(item => item.id_id === geneData.db_id)
      const currentGeneidResult = geneidResult.filter(item => item.id_id === geneData.db_id)
      
      // 获取序列缓存中的数据
      const geneId = geneData.IDs
      const transcriptID = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts[0].id : geneId
      console.log('te',transcriptID)
      const upLen = this.selectedUpstreamLength || 500
      const downLen = this.selectedDownstreamLength || 500
      
      // 获取所有序列数据
      const sequenceCache = this.geneSearchStore.sequenceCache
      
      // 获取基因组序列
      const genomicCacheKey = `${geneId}|genomic|${geneId}|${upLen}|${downLen}`
      const genomicSequence = sequenceCache[genomicCacheKey] || ''
      
      
      
      console.log('缓存键列表:', Object.keys(sequenceCache))
      console.log('genomicCacheKey:', genomicCacheKey, '序列长度:', genomicSequence.length)
     
      
      // 获取所有转录本序列
      const transcriptTypes = ['upstream','downstream','mrna', 'cdna', 'cds', 'protein']
      const mrnaTranscripts = []
      
      // 使用 geneData.mrna_transcripts 中的转录本 ID
      const transcripts = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts : [{ id: geneId }]
      
      console.log('geneData.mrna_transcripts:', geneData.mrna_transcripts)
      console.log('transcripts:', transcripts)
      
      // 为每个转录本构建序列数据
      transcripts.forEach(t => {
        const transcriptId = t.id || t.transcript_id || geneId
        console.log('处理转录本:', transcriptId)
        
        // 缓存键必须与 scheduleSequencePreload 方法中的缓存键一致
        const mrnaCacheKey = `${geneId}|mrna|${transcriptId}|${upLen}|${downLen}`
        const cdnaCacheKey = `${geneId}|cdna|${transcriptId}|${upLen}|${downLen}`
        const cdsCacheKey = `${geneId}|cds|${transcriptId}|${upLen}|${downLen}`
        const proteinCacheKey = `${geneId}|protein|${transcriptId}|${upLen}|${downLen}`
        const upstreamCacheKey = `${geneId}|upstream|${transcriptId}`
        const downstreamCacheKey = `${geneId}|downstream|${transcriptId}`
        
        console.log('upstreamCacheKey:', upstreamCacheKey, '序列长度:', (sequenceCache[upstreamCacheKey] || '').length)
        console.log('downstreamCacheKey:', downstreamCacheKey, '序列长度:', (sequenceCache[downstreamCacheKey] || '').length)
        console.log('mrnaCacheKey:', mrnaCacheKey, '序列长度:', (sequenceCache[mrnaCacheKey] || '').length)
        console.log('cdnaCacheKey:', cdnaCacheKey, '序列长度:', (sequenceCache[cdnaCacheKey] || '').length)
        console.log('cdsCacheKey:', cdsCacheKey, '序列长度:', (sequenceCache[cdsCacheKey] || '').length)
        console.log('proteinCacheKey:', proteinCacheKey, '序列长度:', (sequenceCache[proteinCacheKey] || '').length)
        
        const transcriptData = {
          id: transcriptId,
          mrna_seq: sequenceCache[mrnaCacheKey] || '',
          cdna_seq: sequenceCache[cdnaCacheKey] || '',
          cds_seq: sequenceCache[cdsCacheKey] || '',
          protein_seq: sequenceCache[proteinCacheKey] || '',
          upstream_seq: sequenceCache[upstreamCacheKey] || '',
          downstream_seq: sequenceCache[downstreamCacheKey] || ''
        }
        mrnaTranscripts.push(transcriptData)
      })
      
      // 获取主转录本序列（第一个转录本）
      const mainTranscript = mrnaTranscripts.length > 0 ? mrnaTranscripts[0] : {}
      const mrnaSequence = mainTranscript.mrna_seq || ''
      const cdnaSequence = mainTranscript.cdna_seq || ''
      const cdsSequence = mainTranscript.cds_seq || ''
      const proteinSequence = mainTranscript.protein_seq || ''
      const upstreamSequence = mainTranscript.upstream_seq || ''
      const downstreamSequence = mainTranscript.downstream_seq || ''
      
      console.log('获取到的序列数据:', {
        genomicSequence: genomicSequence.length,
        upstreamSequence: upstreamSequence.length,
        downstreamSequence: downstreamSequence.length,
        mrnaSequence: mrnaSequence.length,
        cdnaSequence: cdnaSequence.length,
        cdsSequence: cdsSequence.length,
        proteinSequence: proteinSequence.length,
        transcriptCount: mrnaTranscripts.length
      })
      
      // 根据已有的 gene_info_result 数据生成 jbrowse_url 和 gff_data
      let jbrowseUrl = ''
      let gffData = []
      
      // 从 currentGeneInfoResult 中获取基因信息
      if (currentGeneInfoResult && currentGeneInfoResult.length > 0) {
        const geneInfo = currentGeneInfoResult.find(item => item.type === 'gene')
        console.log('geneInfo:', geneInfo)
        const seqid = geneInfo?.seqid || 'Ghir_A01'
        const start = geneInfo?.start || 0
        const end = geneInfo?.end || 0
        const genomeId = geneInfo?.genome_id || geneInfo?.genome || ''
        
        // 构建 JBrowse URL
        if (seqid && start && end && genomeId) {
          const gffName = 'GFF'
          const loc = `${seqid}:${Math.max(0, start - 1000)}-${end + 1000}`
          jbrowseUrl = `/assets/jbrowse/index.html?config=data/${genomeId}/config.json&assembly=${genomeId}&loc=${loc}&tracks=${gffName}`
          console.log('生成 jbrowse_url:', jbrowseUrl)
        }
        
        // 提取 GFF 数据
        gffData = currentGeneInfoResult.filter(item => item.type !== 'gene')
        console.log('提取 gff_data:', gffData)
      }
      
      // 构建完整的数据对象
      const fullGeneData = {
        ...geneData,
        seqid: gffData[0]?.seqid || '',
        gene_seq: genomicSequence,
        mrna_seq: mrnaSequence,
        cdna_seq: cdnaSequence,
        cds_seq: cdsSequence,
        protein_seq: proteinSequence,
        upstream_seq: upstreamSequence,
        downstream_seq: downstreamSequence,
        mrna_transcripts: mrnaTranscripts,
        gene_info_result: currentGeneInfoResult,
        geneid_result: currentGeneidResult,
        jbrowse_url: jbrowseUrl,
        gff_data: gffData
      }
      
      // 将完整的基因数据存储到 navigationStore 的 geneDetail 键中
      this.navigationStore.setNavigationData('geneDetail', {
        results: fullGeneData
      })
      
      console.log('传递到详情页的数据:', fullGeneData)
      
      // 导航到结果详情页
      this.$router.push({
        path: '/tools/id-search/results/',
        query: { db_id: geneData.db_id }
      })
    },

    async fetchSearchResults() {
      this.loading = true
      this.error = null
      this.results = []
      this.has_sequences = false

      try {
        const navigationData = this.navigationStore.getNavigationData('geneSearch')
        
        if (!navigationData || !navigationData.results) {
          this.error = this.t('no_search_results_data_please_search_again')
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
          //console.log('开始处理 geneInfoResult，长度:', geneInfoResult.length)
          geneInfoResult.forEach((item, index) => {
            try {
              //console.log(`处理 geneInfoResult[${index}]:`, item)
              if (!item) {
                //console.warn(`跳过无效条目 (undefined/null):`, index)
                return
              }
              if (!item.id_id) {
                //console.warn(`跳过没有 db_id 的条目:`, item)
                return
              }
              if (item.type === 'gene') {
                geneInfoMap[item.id_id] = {
                  start: item.start,
                  end: item.end,
                  strand: item.strand,
                  species: item.genome_id
                }
                //console.log(`添加基因信息到 geneInfoMap: ${item.id_id}`, geneInfoMap[item.id_id])
              } else if (item.type === 'mRNA') {
                let transcriptId = ''
                if (item.attributes) {
                  //console.log(`  处理 mRNA attributes: ${item.attributes}`)
                  // 尝试从 attributes 中提取 ID，支持多种格式
                  // 格式1: ID=xxx
                  // 格式2: type=mRNA;ID=xxx
                  try {
                    const idMatch = item.attributes.match(/(?:^|;)ID=([^;]+)/)
                    if (idMatch) {
                      transcriptId = idMatch[1]
                      //console.log(`  提取到转录本 ID: ${transcriptId}`)
                    } else {
                      console.log(`  无法从 attributes 中提取转录本 ID: ${item.attributes}`)
                    }
                  } catch (e) {
                    console.error(`  解析 attributes 时出错:`, e)
                  }
                } else {
                  //console.log(`  mRNA 条目没有 attributes 字段:`, item)
                }
                //console.log(`处理 mRNA 条目: db_id=${item.id_id}, transcriptId=${transcriptId}, attributes=${item.attributes || 'undefined'}`)
                if (transcriptId) {
                  mrnaInfoMap[transcriptId] = {
                    start: item.start,
                    end: item.end,
                    strand: item.strand,
                    species: item.genome_id,
                    db_id: item.id_id
                  }
                } else {
                  // 如果没有提取到转录本 ID，使用 db_id 作为键
                  //console.log(`  使用 db_id 作为转录本键: ${item.db_id}`)
                  mrnaInfoMap[item.db_id] = {
                    start: item.start,
                    end: item.end,
                    strand: item.strand,
                    species: item.genome_id,
                    db_id: item.id_id
                  }
                }
              } else {
                //console.log(`跳过未知类型的条目:`, item.type, item)
              }
            } catch (e) {
              console.error(`处理 geneInfoResult[${index}] 时出错:`, e)
            }
          })
        } else {
          console.warn('geneInfoResult 不是有效数组:', geneInfoResult)
        }
        
        console.log('处理后的 geneInfoMap:', geneInfoMap)
        console.log('处理后的 mrnaInfoMap:', mrnaInfoMap)
        console.log('searchMap keys:', Object.keys(searchMap))

        this.results = []
        if (searchMap && typeof searchMap === 'object') {
          for (const [originalId, info] of Object.entries(searchMap)) {
            //console.log(`处理 searchMap 条目: originalId=${originalId}, info=`, info)
            if (info && typeof info === 'object') {
              //console.log(`  info.db_id: ${info.db_id}, info.geneid: ${info.geneid}`)
              //console.log(`  geneInfoMap 中是否存在 info.db_id (${info.db_id}):`, !!geneInfoMap[info.db_id])
              if (geneInfoMap[info.db_id]) {
                //console.log(`  geneInfoMap[${info.db_id}]:`, geneInfoMap[info.db_id])
              }
              
              let speciesInfo = this.t('unknown_species')
              
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
              
              //console.log(`  开始匹配转录本，info.db_id=${info.db_id}`)
              //console.log(`  mrnaInfoMap keys:`, Object.keys(mrnaInfoMap))
              
              for (const [transcriptId, mrnaInfo] of Object.entries(mrnaInfoMap)) {
                //console.log(`    检查转录本: transcriptId=${transcriptId}, mrnaInfo.db_id=${mrnaInfo.db_id}, 是否匹配=${mrnaInfo.db_id === info.db_id}`)
                if (mrnaInfo.db_id === info.db_id) {
                  mrnaTranscripts.push({
                    id: transcriptId,
                    seqid: mrnaInfo.db_id,
                    start: mrnaInfo.start,
                    end: mrnaInfo.end,
                    strand: mrnaInfo.strand
                  })
                  //console.log(`      添加转录本:`, transcriptId)
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
                mrna_transcripts: mrnaTranscripts,
                jbrowse_url: '',
                gff_data: []
              })
            }
          }
        }
        
        this.has_sequences = this.results.length > 0
        this.scheduleSequencePreload()
        
      } catch (error) {
        console.error('获取数据失败:', error)
        this.error = this.t('failed_to_fetch_data') + ': ' + (error.message || this.t('unknown_error'))
      } finally {
        this.loading = false
      }
    },

    async scheduleSequencePreload() {
      if (!this.results?.length) return

      const upLen = this.selectedUpstreamLength || 500
      const downLen = this.selectedDownstreamLength || 500

      // 获取所有唯一的 db_id
      const dbIds = [...new Set(this.results.map(geneData => geneData.db_id).filter(Boolean))]

      if (dbIds.length === 0) {
        console.warn('No db_ids found for sequence extraction')
        return
      }

      const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''

      // 按照后端期望的格式传递参数
      const apiPayload = {
        db_id: dbIds
      }

      console.log('Sending batch sequence request with db_ids:', dbIds)

      try {
        const res = await httpInstance.post(
          '/CottonOGD_api/extract_seq/',
          apiPayload,
          { headers: { 'X-CSRFToken': csrfToken } }
        )

        // 处理后端返回的数据
        console.log('Extract seq response:', res)

        // 解析返回的序列数据并存储到缓存
        const seqData = res.seq || {}
        console.log('seqData:', seqData)
        console.log('seqData keys:', Object.keys(seqData))

        // 为每个基因、每个转录本、每种类型缓存序列数据
        const typesToCache = ['genomic', 'upstream', 'downstream', 'mrna', 'cdna', 'cds', 'protein']

        this.results.forEach(geneData => {
          const geneId = geneData.IDs

          // 处理 genomic 类型（只处理一次，与转录本无关）
          const genomicType = 'genomic'
          const genomicCacheKey = `${geneId}|${genomicType}|${geneId}|${upLen}|${downLen}`
          
          // 如果 genomic 类型未缓存，则缓存
          if (!this.geneSearchStore.sequenceCache[genomicCacheKey]) {
            let genomicSequence = this.t('sequence_not_found')
            if (seqData.genome_seq && seqData.genome_seq.length > 0) {
              genomicSequence = seqData.genome_seq[0].seq
              //console.log('获取到基因组序列，长度:', genomicSequence.length)
            }
            //console.log('缓存基因组序列:', genomicCacheKey, '序列长度:', genomicSequence.length)
            this.geneSearchStore.sequenceCache[genomicCacheKey] = genomicSequence
          } else {
            console.log('基因组序列已缓存，跳过:', genomicCacheKey)
          }

          // 统一 transcript 粒度
          const transcripts = geneData.mrna_transcripts?.length
            ? geneData.mrna_transcripts
            : [{ id: geneId }]

          // 处理非 genomic 类型（按转录本处理）
          const nonGenomicTypes = typesToCache.filter(type => type !== 'genomic')
          
          transcripts.forEach(t => {
            const transcriptId = t.id || t.transcript_id || geneId

            nonGenomicTypes.forEach(type => {
              // 对于上游和下游序列，缓存键不包含长度参数，以便在不同长度下都能获取完整序列
              const cacheKey = (type === 'upstream' || type === 'downstream')
                ? `${geneId}|${type}|${transcriptId}`
                : `${geneId}|${type}|${transcriptId}|${upLen}|${downLen}`

              // 如果已经缓存，跳过
              if (this.geneSearchStore.sequenceCache[cacheKey]) {
                return
              }

              // 根据类型获取对应的序列
              let sequence = this.t('sequence_not_found')
              switch (type) {
                case 'mrna':
                  if (seqData.mrna_seq && seqData.mrna_seq.length > 0) {
                    // 尝试找到匹配的转录本
                    const mrnaSeq = seqData.mrna_seq.find(item =>
                      item.mrna_id === transcriptId
                    )
                    sequence = mrnaSeq ? mrnaSeq.seq : seqData.mrna_seq[0].seq
                    //console.log('获取到mRNA序列，长度:', sequence.length, 'transcriptId:', transcriptId, 'mrnaSeq:', mrnaSeq)
                  }
                  break
                case 'upstream':
                  if (seqData.upstream_seq && seqData.upstream_seq.length > 0) {
                    sequence = seqData.upstream_seq[0].seq
                    //console.log('获取到上游序列，长度:', sequence.length)
                  }
                  break
                case 'downstream':
                  if (seqData.downstream_seq && seqData.downstream_seq.length > 0) {
                    sequence = seqData.downstream_seq[0].seq
                    //console.log('获取到下游序列，长度:', sequence.length)
                  }
                  break
                case 'cdna':
                  if (seqData.cdna_seq && seqData.cdna_seq.length > 0) {
                    // 尝试找到匹配的转录本
                    const cdnaSeq = seqData.cdna_seq.find(item =>
                      item.mrna_id === transcriptId
                    )
                    sequence = cdnaSeq ? cdnaSeq.seq : seqData.cdna_seq[0].seq
                    //console.log('获取到cDNA序列，长度:', sequence.length, 'transcriptId:', transcriptId)
                  }
                  break
                case 'cds':
                  if (seqData.cds_seq && seqData.cds_seq.length > 0) {
                    // 尝试找到匹配的转录本
                    const cdsSeq = seqData.cds_seq.find(item =>
                      item.mrna_id === transcriptId
                    )
                    sequence = cdsSeq ? cdsSeq.seq : seqData.cds_seq[0].seq
                    //console.log('获取到CDS序列，长度:', sequence.length, 'transcriptId:', transcriptId)
                  }
                  break
                case 'protein':
                  if (seqData.protein_seq && seqData.protein_seq.length > 0) {
                    // 尝试找到匹配的转录本
                    const proteinSeq = seqData.protein_seq.find(item =>
                      item.mrna_id === transcriptId
                    )
                    sequence = proteinSeq ? proteinSeq.seq : seqData.protein_seq[0].seq
                    //console.log('获取到蛋白序列，长度:', sequence.length, 'transcriptId:', transcriptId)
                  }
                  break
              }

              // 缓存序列
              //console.log('缓存序列:', cacheKey, '序列长度:', sequence.length)
              this.geneSearchStore.sequenceCache[cacheKey] = sequence
            })
          })
        })

        console.log('缓存完成，缓存键数量:', Object.keys(this.geneSearchStore.sequenceCache).length)
      } catch (err) {
        console.error('批量热加载失败', err)
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
        
        // 如果是 genomic 类型，只处理一次，与转录本无关
        if (type === 'genomic') {
          // 尝试使用 geneData.gene_seq
          if (geneData.gene_seq && geneData.gene_seq !== 'N/A') {
            allFastaContent += `>${geneId} genomic\n${this.formatSequence(geneData.gene_seq)}\n\n`
          } else {
            // 如果 geneData.gene_seq 不存在，从缓存获取
            const finalTranscriptId = geneId
            try {
              const sequence = await this.geneSearchStore.fetchSequence(geneId, finalTranscriptId, type, upLen, downLen)
              if (sequence && sequence !== '未找到序列' && sequence !== 'N/A') {
                allFastaContent += `>${geneId} ${type}\n${this.formatSequence(sequence)}\n\n`
              } else {
                allFastaContent += `>${geneId} ${type}\n${sequence}\n\n`
              }
            } catch (error) {
              console.error('Error fetching sequence:', error)
              allFastaContent += `>${geneId} ${type}\n序列获取失败\n\n`
            }
          }
          // 跳过转录本循环，确保只处理一次
          continue
        }

        // 处理非 genomic 类型，按转录本处理
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

      this.modalContent = allFastaContent.trim() || this.t('no_sequence_of_this_type_found')
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
        this.$message.success(this.t('sequence_copied_to_clipboard'))
      }).catch(err => {
        console.error('复制失败:', err)
        this.$message.error(this.t('copy_failed_please_copy_manually'))
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
          // 如果是 genomic 类型，只处理一次，与转录本无关
          if (type === 'genomic') {
            // 尝试使用 geneData.gene_seq
            if (geneData.gene_seq && geneData.gene_seq !== 'N/A') {
              allContent += `>${geneId} genomic\n${this.formatSequence(geneData.gene_seq)}\n\n`
            } else {
              // 如果 geneData.gene_seq 不存在，从缓存获取
              const finalTranscriptId = geneId
              try {
                const sequence = await this.geneSearchStore.fetchSequence(geneId, finalTranscriptId, type, upLen, downLen)
                if (sequence && sequence !== this.t('sequence_not_found') && sequence !== 'N/A') {
                  allContent += `>${geneId} ${type}\n${this.formatSequence(sequence)}\n\n`
                } else {
                  allContent += `>${geneId} ${type}\n${sequence}\n\n`
                }
              } catch (error) {
                console.error('Error fetching sequence:', error)
                allContent += `>${geneId} ${type}\n${this.t('sequence_fetch_failed')}\n\n`
              }
            }
            // 跳过当前类型的后续处理，确保只处理一次
            continue
          }

          // 处理非 genomic 类型，按转录本处理
          const transcripts = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts : [geneData]
          for (const transcript of transcripts) {
            const transcriptId = transcript.id || transcript.transcript_id || geneId
            try {
              const sequence = await this.geneSearchStore.fetchSequence(geneId, transcriptId, type, upLen, downLen)
              if (sequence && sequence !== this.t('sequence_not_found') && sequence !== 'N/A') {
                allContent += `>${transcriptId} ${type}\n${this.formatSequence(sequence)}\n\n`
              } else {
                allContent += `>${transcriptId} ${type}\n${sequence}\n\n`
              }
            } catch (error) {
              console.error('Error fetching sequence:', error)
              allContent += `>${transcriptId} ${type}\n${this.t('sequence_fetch_failed')}\n\n`
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