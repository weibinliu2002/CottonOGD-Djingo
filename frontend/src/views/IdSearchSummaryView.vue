<template>
  <div class="container mt-4">
    <el-card class="mt-4">
      <template #header>
        <div class="card-header">
          <h1>{{ t('id') }}</h1>
        </div>
      </template>
      
      <!-- 鐘舵€佷俊鎭?-->
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
      
      <!-- 鍔犺浇鐘舵€?-->
      <div v-if="loading" class="text-center py-5">
        <el-loading :fullscreen="false" :text="t('loading_data_please_wait')" />
      </div>
      
      <!-- 閿欒淇℃伅 -->
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
      
      <!-- 缁撴灉灞曠ず - 鍙湁鍦ㄥ姞杞藉畬鎴愪笖娌℃湁閿欒鏃舵墠鏄剧ず -->
      <template v-else-if="results">
        <!-- 缁撴灉琛ㄦ牸 -->
        <el-table :data="results" style="width: 100%" class="mb-4">
          <el-table-column prop="original_id" :label="t('input_id')" width="200" />
          <el-table-column :label="t('query_id')" width="200">
            <template #default="scope">
              <a href="javascript:void(0)" @click="navigateToResults(scope.row)">
                {{ scope.row.IDs || '-' }}
              </a>
            </template>
          </el-table-column>
          <el-table-column prop="species" :label="t('species')" width="250" />
          <el-table-column prop="seqid" :label="t('chromosome')" width="250" />
          <el-table-column prop="start" :label="t('start')" width="150" />
          <el-table-column prop="end" :label="t('end')" width="150" />
          <el-table-column prop="strand" :label="t('strand')" width="100" />
        </el-table>

        <!-- 琛ㄦ牸涓嬭浇鎸夐挳 -->
        <div class="mt-4">
          <el-button type="primary" @click="downloadTableAsTxt">{{ t('download_table') }}</el-button>
        </div>

        <!-- 搴忓垪灞曠ず鍖哄煙 - 涓烘瘡涓熀鍥犳坊鍔犲簭鍒楁寜閽?-->
        <div v-if="results.length > 0" class="mt-6">
          <h4>{{ t('gene_sequences') }}</h4>
      
            <!-- 浣跨敤閫氱敤搴忓垪灞曠ず缁勪欢 -->
            <sequence-display
              :results="results"
              :loading="false"
              @show-sequence="handleShowSequence"
              @length-change="handleLengthChange"
            />
         
        
          <!-- 鎵归噺鎿嶄綔鎸夐挳 -->
          <div class="mt-4">
            <el-button type="primary" @click="downloadAllSequences">{{ t('download_all_sequences') }}</el-button>
          </div>
        </div>
        <el-empty v-else :description="t('no_gene_sequences_available')" class="mt-4" />
      </template>
      
      <!-- 鍒濆鐘舵€?- 鏈紑濮嬪姞杞芥椂鏄剧ず -->
      <div v-else class="text-center py-5">
        <el-empty :description="t('preparing_to_load_data')" />
      </div>
    </el-card>
    
    <!-- 搴忓垪寮圭獥缁勪欢 -->
    <sequence-modal
      v-model:show-modal="showModal"
      :modal-title="modalTitle"
      :modal-content="modalContent"
      :current-seq-type="currentSeqType"
      :current-gene-id="currentGeneId"
      @download="handleDownload"
      @copy="handleCopy"
    />
    
    <!-- 鍥炲埌椤堕儴 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>
<script>
import { useI18n } from 'vue-i18n'
import httpInstance from '../utils/http'
import SequenceDisplay from '@/components/SequenceDisplay.vue'
import SequenceModal from '@/components/SequenceModal.vue'
import { useGeneSearchStore } from '@/stores/geneSearch.ts'
import { useNavigationStore } from '@/stores/navigationStore.ts'
import { resolveSequenceLengths } from '@/utils/sequenceLength'

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
      const { upstreamLength, downstreamLength } = resolveSequenceLengths(
        lengths,
        this.selectedUpstreamLength,
        this.selectedDownstreamLength
      )

      this.selectedUpstreamLength = upstreamLength
      this.selectedDownstreamLength = downstreamLength

      // 涓嶅啀娓呯悊缂撳瓨鍜岄噸鏂拌姹傚簭鍒楋紝鑰屾槸鍦ㄥ睍绀烘椂鏍规嵁闀垮害杩涜鎴柇
    },

    // 瀵艰埅鍒扮粨鏋滆鎯呴〉
    async navigateToResults(geneData) {
      // 浠?navigationStore 鑾峰彇瀹屾暣鐨勬悳绱㈢粨鏋滄暟鎹?
      const navigationData = this.navigationStore.getNavigationData('geneSearch')
      
      if (!navigationData || !navigationData.results) {
        console.error('娌℃湁鎵惧埌鎼滅储缁撴灉鏁版嵁')
        return
      }

      const searchResults = navigationData.results
      const geneInfoResult = searchResults.gene_info_result || []
      const geneidResult = searchResults.geneid_result || []
      const geneGoResult = searchResults.gene_go_result || []
      const geneKeggResult = searchResults.gene_kegg_result || []
      
      // 鏍规嵁褰撳墠鍩哄洜鐨?db_id 杩囨护鍑哄搴旂殑 geneInfoResult 鍜?geneidResult
      const currentGeneInfoResult = geneInfoResult.filter(item => item.id_id === geneData.db_id)
      const currentGeneidResult = geneidResult.filter(item => item.id_id === geneData.db_id)
      // 鏍规嵁 id_id 杩囨护鍑哄搴旂殑 GO 鍜?KEGG 娉ㄩ噴鏁版嵁
      const currentGeneGoResult = geneGoResult.filter(item => item.id_id === geneData.db_id)
      const currentGeneKeggResult = geneKeggResult.filter(item => item.id_id === geneData.db_id)
      
      // 鑾峰彇搴忓垪缂撳瓨涓殑鏁版嵁
      const geneId = geneData.IDs
      const transcriptID = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts[0].id : geneId
      console.log('te',transcriptID)
      const upLen = this.selectedUpstreamLength || 500
      const downLen = this.selectedDownstreamLength || 500
      
      // 鑾峰彇鎵€鏈夊簭鍒楁暟鎹?
      const sequenceCache = this.geneSearchStore.sequenceCache
      
      // 鑾峰彇鍩哄洜缁勫簭鍒?
      const genomicCacheKey = `${geneId}|genomic|${geneId}|${upLen}|${downLen}`
      const genomicSequence = sequenceCache[genomicCacheKey] || ''
      
      
      
      console.log('缂撳瓨閿垪琛?', Object.keys(sequenceCache))
      console.log('genomicCacheKey:', genomicCacheKey, '搴忓垪闀垮害:', genomicSequence.length)
     
      
      // 鑾峰彇鎵€鏈夎浆褰曟湰搴忓垪
      const transcriptTypes = ['upstream','downstream','mrna', 'cdna', 'cds', 'protein']
      const mrnaTranscripts = []
      
      // 浣跨敤 geneData.mrna_transcripts 涓殑杞綍鏈?ID
      const transcripts = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts : [{ id: geneId }]
      
      console.log('geneData.mrna_transcripts:', geneData.mrna_transcripts)
      console.log('transcripts:', transcripts)
      
      // 涓烘瘡涓浆褰曟湰鏋勫缓搴忓垪鏁版嵁
      transcripts.forEach(t => {
        const transcriptId = t.id || t.transcript_id || geneId
        console.log('澶勭悊杞綍鏈?', transcriptId)
        
        // 缂撳瓨閿繀椤讳笌 scheduleSequencePreload 鏂规硶涓殑缂撳瓨閿竴鑷?
        const mrnaCacheKey = `${geneId}|mrna|${transcriptId}|${upLen}|${downLen}`
        const cdnaCacheKey = `${geneId}|cdna|${transcriptId}|${upLen}|${downLen}`
        const cdsCacheKey = `${geneId}|cds|${transcriptId}|${upLen}|${downLen}`
        const proteinCacheKey = `${geneId}|protein|${transcriptId}|${upLen}|${downLen}`
        const upstreamCacheKey = `${geneId}|upstream|${transcriptId}`
        const downstreamCacheKey = `${geneId}|downstream|${transcriptId}`
        
        console.log('upstreamCacheKey:', upstreamCacheKey, '搴忓垪闀垮害:', (sequenceCache[upstreamCacheKey] || '').length)
        console.log('downstreamCacheKey:', downstreamCacheKey, '搴忓垪闀垮害:', (sequenceCache[downstreamCacheKey] || '').length)
        console.log('mrnaCacheKey:', mrnaCacheKey, '搴忓垪闀垮害:', (sequenceCache[mrnaCacheKey] || '').length)
        console.log('cdnaCacheKey:', cdnaCacheKey, '搴忓垪闀垮害:', (sequenceCache[cdnaCacheKey] || '').length)
        console.log('cdsCacheKey:', cdsCacheKey, '搴忓垪闀垮害:', (sequenceCache[cdsCacheKey] || '').length)
        console.log('proteinCacheKey:', proteinCacheKey, '搴忓垪闀垮害:', (sequenceCache[proteinCacheKey] || '').length)
        
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
      
      // 鑾峰彇涓昏浆褰曟湰搴忓垪锛堢涓€涓浆褰曟湰锛?
      const mainTranscript = mrnaTranscripts.length > 0 ? mrnaTranscripts[0] : {}
      const mrnaSequence = mainTranscript.mrna_seq || ''
      const cdnaSequence = mainTranscript.cdna_seq || ''
      const cdsSequence = mainTranscript.cds_seq || ''
      const proteinSequence = mainTranscript.protein_seq || ''
      const upstreamSequence = mainTranscript.upstream_seq || ''
      const downstreamSequence = mainTranscript.downstream_seq || ''
      
      console.log('鑾峰彇鍒扮殑搴忓垪鏁版嵁:', {
        genomicSequence: genomicSequence.length,
        upstreamSequence: upstreamSequence.length,
        downstreamSequence: downstreamSequence.length,
        mrnaSequence: mrnaSequence.length,
        cdnaSequence: cdnaSequence.length,
        cdsSequence: cdsSequence.length,
        proteinSequence: proteinSequence.length,
        transcriptCount: mrnaTranscripts.length
      })
      
      // 鏍规嵁宸叉湁鐨?gene_info_result 鏁版嵁鐢熸垚 jbrowse_url 鍜?gff_data
      let jbrowseUrl = ''
      let gffData = []
      
      // 浠?currentGeneInfoResult 涓幏鍙栧熀鍥犱俊鎭?
      if (currentGeneInfoResult && currentGeneInfoResult.length > 0) {
        const geneInfo = currentGeneInfoResult.find(item => item.type === 'gene')
        console.log('geneInfo:', geneInfo)
        const seqid = geneInfo?.seqid || 'Ghir_A01'
        const start = geneInfo?.start || 0
        const end = geneInfo?.end || 0
        const genomeId = geneInfo?.genome_id || geneInfo?.genome || ''
        
        // 鏋勫缓 JBrowse URL
        if (seqid && start && end && genomeId) {
          const gffName = 'GFF'
          const loc = `${seqid}:${Math.max(0, start - 1000)}-${end + 1000}`
          jbrowseUrl = `/assets/jbrowse/index.html?config=data/${genomeId}/config.json&assembly=${genomeId}&loc=${loc}&tracks=${gffName}`
          console.log('鐢熸垚 jbrowse_url:', jbrowseUrl)
        }
        
        // 鎻愬彇 GFF 鏁版嵁
        gffData = currentGeneInfoResult.filter(item => item.type !== 'gene')
        console.log('鎻愬彇 gff_data:', gffData)
      }
      
      // 鏋勫缓瀹屾暣鐨勬暟鎹璞?
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
        gene_go_result: currentGeneGoResult,
        gene_kegg_result: currentGeneKeggResult,
        jbrowse_url: jbrowseUrl,
        gff_data: gffData
      }
      
      // 灏嗗畬鏁寸殑鍩哄洜鏁版嵁瀛樺偍鍒?navigationStore 鐨?geneDetail 閿腑
      this.navigationStore.setNavigationData('geneDetail', {
        results: fullGeneData
      })
      
      console.log('浼犻€掑埌璇︽儏椤电殑鏁版嵁:', fullGeneData)
      
      // 瀵艰埅鍒扮粨鏋滆鎯呴〉
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

        console.log('浠?navigationStore 鑾峰彇鐨勬暟鎹?', searchResults)
        console.log('searchMap:', searchMap)
        console.log('geneInfoResult 闀垮害:', geneInfoResult?.length)
        
        if (geneInfoResult && Array.isArray(geneInfoResult) && geneInfoResult.length > 0) {
          console.log('geneInfoResult[0] 绀轰緥:', geneInfoResult[0])
        }
        
        const geneInfoMap = {}
        const mrnaInfoMap = {}
        
        if (geneInfoResult && Array.isArray(geneInfoResult)) {
          //console.log('寮€濮嬪鐞?geneInfoResult锛岄暱搴?', geneInfoResult.length)
          geneInfoResult.forEach((item, index) => {
            try {
              //console.log(`澶勭悊 geneInfoResult[${index}]:`, item)
              if (!item) {
                //console.warn(`璺宠繃鏃犳晥鏉＄洰 (undefined/null):`, index)
                return
              }
              if (!item.id_id) {
                //console.warn(`璺宠繃娌℃湁 db_id 鐨勬潯鐩?`, item)
                return
              }
              if (item.type === 'gene') {
                geneInfoMap[item.id_id] = {
                  start: item.start,
                  end: item.end,
                  strand: item.strand,
                  species: item.genome_id,
                  seqid: item.seqid || '',
                  db_id: item.id_id
                }
                //console.log(`娣诲姞鍩哄洜淇℃伅鍒?geneInfoMap: ${item.id_id}`, geneInfoMap[item.id_id])
              } else if (item.type === 'mRNA') {
                let transcriptId = ''
                if (item.attributes) {
                  //console.log(`  澶勭悊 mRNA attributes: ${item.attributes}`)
                  // 灏濊瘯浠?attributes 涓彁鍙?ID锛屾敮鎸佸绉嶆牸寮?
                  // 鏍煎紡1: ID=xxx
                  // 鏍煎紡2: type=mRNA;ID=xxx
                  try {
                    const idMatch = item.attributes.match(/(?:^|;)ID=([^;]+)/)
                    if (idMatch) {
                      transcriptId = idMatch[1]
                      //console.log(`  鎻愬彇鍒拌浆褰曟湰 ID: ${transcriptId}`)
                    } else {
                      console.log(`  鏃犳硶浠?attributes 涓彁鍙栬浆褰曟湰 ID: ${item.attributes}`)
                    }
                  } catch (e) {
                    console.error(`  瑙ｆ瀽 attributes 鏃跺嚭閿?`, e)
                  }
                } else {
                  //console.log(`  mRNA 鏉＄洰娌℃湁 attributes 瀛楁:`, item)
                }
                //console.log(`澶勭悊 mRNA 鏉＄洰: db_id=${item.id_id}, transcriptId=${transcriptId}, attributes=${item.attributes || 'undefined'}`)
                if (transcriptId) {
                  mrnaInfoMap[transcriptId] = {
                    start: item.start,
                    end: item.end,
                    strand: item.strand,
                    species: item.genome_id,
                    db_id: item.id_id
                  }
                } else {
                  // 濡傛灉娌℃湁鎻愬彇鍒拌浆褰曟湰 ID锛屼娇鐢?db_id 浣滀负閿?
                  //console.log(`  浣跨敤 db_id 浣滀负杞綍鏈敭: ${item.db_id}`)
                  mrnaInfoMap[item.db_id] = {
                    start: item.start,
                    end: item.end,
                    strand: item.strand,
                    species: item.genome_id,
                    db_id: item.id_id
                  }
                }
              } else {
                //console.log(`璺宠繃鏈煡绫诲瀷鐨勬潯鐩?`, item.type, item)
              }
            } catch (e) {
              console.error(`澶勭悊 geneInfoResult[${index}] 鏃跺嚭閿?`, e)
            }
          })
        } else {
          console.warn('geneInfoResult 涓嶆槸鏈夋晥鏁扮粍:', geneInfoResult)
        }
        
        console.log('澶勭悊鍚庣殑 geneInfoMap:', geneInfoMap)
        console.log('澶勭悊鍚庣殑 mrnaInfoMap:', mrnaInfoMap)
        console.log('searchMap keys:', Object.keys(searchMap))

        this.results = []
        if (searchMap && typeof searchMap === 'object') {
          for (const [originalId, info] of Object.entries(searchMap)) {
            //console.log(`澶勭悊 searchMap 鏉＄洰: originalId=${originalId}, info=`, info)
            if (info && typeof info === 'object') {
              //console.log(`  info.db_id: ${info.db_id}, info.geneid: ${info.geneid}`)
              //console.log(`  geneInfoMap 涓槸鍚﹀瓨鍦?info.db_id (${info.db_id}):`, !!geneInfoMap[info.db_id])
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
              
              //console.log(`  寮€濮嬪尮閰嶈浆褰曟湰锛宨nfo.db_id=${info.db_id}`)
              //console.log(`  mrnaInfoMap keys:`, Object.keys(mrnaInfoMap))
              
              for (const [transcriptId, mrnaInfo] of Object.entries(mrnaInfoMap)) {
                //console.log(`    妫€鏌ヨ浆褰曟湰: transcriptId=${transcriptId}, mrnaInfo.db_id=${mrnaInfo.db_id}, 鏄惁鍖归厤=${mrnaInfo.db_id === info.db_id}`)
                if (mrnaInfo.db_id === info.db_id) {
                  mrnaTranscripts.push({
                    id: transcriptId,
                    seqid: mrnaInfo.db_id,
                    start: mrnaInfo.start,
                    end: mrnaInfo.end,
                    strand: mrnaInfo.strand
                  })
                  //console.log(`      娣诲姞杞綍鏈?`, transcriptId)
                }
              }
              
              console.log(`  鏈€缁?mrnaTranscripts 鏁伴噺: ${mrnaTranscripts.length}`)
              
              if (mrnaTranscripts.length === 0) {
                mrnaTranscripts.push({ id: info.geneid })
                console.log(`  浣跨敤榛樿杞綍鏈? ${info.geneid}`)
              }
              
              this.results.push({
                original_id: originalId,
                IDs: info.geneid,
                db_id: info.db_id,
                species: speciesInfo,
                seqid: geneInfo.seqid,
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
        console.error('鑾峰彇鏁版嵁澶辫触:', error)
        this.error = this.t('failed_to_fetch_data') + ': ' + (error.message || this.t('unknown_error'))
      } finally {
        this.loading = false
      }
    },

    async scheduleSequencePreload() {
      if (!this.results?.length) return

      const upLen = this.selectedUpstreamLength || 500
      const downLen = this.selectedDownstreamLength || 500

      // 鑾峰彇鎵€鏈夊敮涓€鐨?db_id
      const dbIds = [...new Set(this.results.map(geneData => geneData.db_id).filter(Boolean))]

      if (dbIds.length === 0) {
        console.warn('No db_ids found for sequence extraction')
        return
      }

      const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''

      // 鎸夌収鍚庣鏈熸湜鐨勬牸寮忎紶閫掑弬鏁?
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

        // 澶勭悊鍚庣杩斿洖鐨勬暟鎹?
        console.log('Extract seq response:', res)

        // 瑙ｆ瀽杩斿洖鐨勫簭鍒楁暟鎹苟瀛樺偍鍒扮紦瀛?
        const seqData = res.seq || {}
        console.log('seqData:', seqData)
        console.log('seqData keys:', Object.keys(seqData))

        // 涓烘瘡涓熀鍥犮€佹瘡涓浆褰曟湰銆佹瘡绉嶇被鍨嬬紦瀛樺簭鍒楁暟鎹?
        const typesToCache = ['genomic', 'upstream', 'downstream', 'mrna', 'cdna', 'cds', 'protein']

        this.results.forEach(geneData => {
          const geneId = geneData.IDs

          // 澶勭悊 genomic 绫诲瀷锛堝彧澶勭悊涓€娆★紝涓庤浆褰曟湰鏃犲叧锛?
          const genomicType = 'genomic'
          const genomicCacheKey = `${geneId}|${genomicType}|${geneId}|${upLen}|${downLen}`
          
          // 濡傛灉 genomic 绫诲瀷鏈紦瀛橈紝鍒欑紦瀛?
          if (!this.geneSearchStore.sequenceCache[genomicCacheKey]) {
            let genomicSequence = this.t('sequence_not_found')
            if (seqData.genome_seq && seqData.genome_seq.length > 0) {
              genomicSequence = seqData.genome_seq[0].seq
              //console.log('鑾峰彇鍒板熀鍥犵粍搴忓垪锛岄暱搴?', genomicSequence.length)
            }
            //console.log('缂撳瓨鍩哄洜缁勫簭鍒?', genomicCacheKey, '搴忓垪闀垮害:', genomicSequence.length)
            this.geneSearchStore.sequenceCache[genomicCacheKey] = genomicSequence
          } else {
            console.log('鍩哄洜缁勫簭鍒楀凡缂撳瓨锛岃烦杩?', genomicCacheKey)
          }

          // 缁熶竴 transcript 绮掑害
          const transcripts = geneData.mrna_transcripts?.length
            ? geneData.mrna_transcripts
            : [{ id: geneId }]

          // 澶勭悊闈?genomic 绫诲瀷锛堟寜杞綍鏈鐞嗭級
          const nonGenomicTypes = typesToCache.filter(type => type !== 'genomic')
          
          transcripts.forEach(t => {
            const transcriptId = t.id || t.transcript_id || geneId

            nonGenomicTypes.forEach(type => {
              // 瀵逛簬涓婃父鍜屼笅娓稿簭鍒楋紝缂撳瓨閿笉鍖呭惈闀垮害鍙傛暟锛屼互渚垮湪涓嶅悓闀垮害涓嬮兘鑳借幏鍙栧畬鏁村簭鍒?
              const cacheKey = (type === 'upstream' || type === 'downstream')
                ? `${geneId}|${type}|${transcriptId}`
                : `${geneId}|${type}|${transcriptId}|${upLen}|${downLen}`

              // 濡傛灉宸茬粡缂撳瓨锛岃烦杩?
              if (this.geneSearchStore.sequenceCache[cacheKey]) {
                return
              }

              // 鏍规嵁绫诲瀷鑾峰彇瀵瑰簲鐨勫簭鍒?
              let sequence = this.t('sequence_not_found')
              switch (type) {
                case 'mrna':
                  if (seqData.mrna_seq && seqData.mrna_seq.length > 0) {
                    // 灏濊瘯鎵惧埌鍖归厤鐨勮浆褰曟湰
                    const mrnaSeq = seqData.mrna_seq.find(item =>
                      item.mrna_id === transcriptId
                    )
                    sequence = mrnaSeq ? mrnaSeq.seq : seqData.mrna_seq[0].seq
                    //console.log('鑾峰彇鍒癿RNA搴忓垪锛岄暱搴?', sequence.length, 'transcriptId:', transcriptId, 'mrnaSeq:', mrnaSeq)
                  }
                  break
                case 'upstream':
                  if (seqData.upstream_seq && seqData.upstream_seq.length > 0) {
                    sequence = seqData.upstream_seq[0].seq
                    //console.log('鑾峰彇鍒颁笂娓稿簭鍒楋紝闀垮害:', sequence.length)
                  }
                  break
                case 'downstream':
                  if (seqData.downstream_seq && seqData.downstream_seq.length > 0) {
                    sequence = seqData.downstream_seq[0].seq
                    //console.log('鑾峰彇鍒颁笅娓稿簭鍒楋紝闀垮害:', sequence.length)
                  }
                  break
                case 'cdna':
                  if (seqData.cdna_seq && seqData.cdna_seq.length > 0) {
                    // 灏濊瘯鎵惧埌鍖归厤鐨勮浆褰曟湰
                    const cdnaSeq = seqData.cdna_seq.find(item =>
                      item.mrna_id === transcriptId
                    )
                    sequence = cdnaSeq ? cdnaSeq.seq : seqData.cdna_seq[0].seq
                    //console.log('鑾峰彇鍒癱DNA搴忓垪锛岄暱搴?', sequence.length, 'transcriptId:', transcriptId)
                  }
                  break
                case 'cds':
                  if (seqData.cds_seq && seqData.cds_seq.length > 0) {
                    // 灏濊瘯鎵惧埌鍖归厤鐨勮浆褰曟湰
                    const cdsSeq = seqData.cds_seq.find(item =>
                      item.mrna_id === transcriptId
                    )
                    sequence = cdsSeq ? cdsSeq.seq : seqData.cds_seq[0].seq
                    //console.log('鑾峰彇鍒癈DS搴忓垪锛岄暱搴?', sequence.length, 'transcriptId:', transcriptId)
                  }
                  break
                case 'protein':
                  if (seqData.protein_seq && seqData.protein_seq.length > 0) {
                    // 灏濊瘯鎵惧埌鍖归厤鐨勮浆褰曟湰
                    const proteinSeq = seqData.protein_seq.find(item =>
                      item.mrna_id === transcriptId
                    )
                    sequence = proteinSeq ? proteinSeq.seq : seqData.protein_seq[0].seq
                    //console.log('鑾峰彇鍒拌泲鐧藉簭鍒楋紝闀垮害:', sequence.length, 'transcriptId:', transcriptId)
                  }
                  break
              }

              // 缂撳瓨搴忓垪
              //console.log('缂撳瓨搴忓垪:', cacheKey, '搴忓垪闀垮害:', sequence.length)
              this.geneSearchStore.sequenceCache[cacheKey] = sequence
            })
          })
        })

        console.log('缂撳瓨瀹屾垚锛岀紦瀛橀敭鏁伴噺:', Object.keys(this.geneSearchStore.sequenceCache).length)
      } catch (err) {
        console.error('鎵归噺鐑姞杞藉け璐?', err)
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
        
        // 濡傛灉鏄?genomic 绫诲瀷锛屽彧澶勭悊涓€娆★紝涓庤浆褰曟湰鏃犲叧
        if (type === 'genomic') {
          // 灏濊瘯浣跨敤 geneData.gene_seq
          if (geneData.gene_seq && geneData.gene_seq !== 'N/A') {
            allFastaContent += `>${geneId} genomic\n${this.formatSequence(geneData.gene_seq)}\n\n`
          } else {
            // 濡傛灉 geneData.gene_seq 涓嶅瓨鍦紝浠庣紦瀛樿幏鍙?
            const finalTranscriptId = geneId
            try {
              const sequence = await this.geneSearchStore.fetchSequence(geneId, finalTranscriptId, type, upLen, downLen)
              if (sequence && sequence !== this.t('sequence_not_found') && sequence !== 'N/A') {
                allFastaContent += `>${geneId} ${type}\n${this.formatSequence(sequence)}\n\n`
              } else {
                allFastaContent += `>${geneId} ${type}\n${sequence}\n\n`
              }
            } catch (error) {
              console.error('Error fetching sequence:', error)
              allFastaContent += `>${geneId} ${type}\n搴忓垪鑾峰彇澶辫触\n\n`
            }
          }
          // 璺宠繃杞綍鏈惊鐜紝纭繚鍙鐞嗕竴娆?
          continue
        }

        // 澶勭悊闈?genomic 绫诲瀷锛屾寜杞綍鏈鐞?
        const transcripts = geneData.mrna_transcripts?.length ? geneData.mrna_transcripts : [geneData]

        for (const transcript of transcripts) {
          const transcriptId = transcript.id || transcript.transcript_id || geneId
          try {
            const sequence = await this.geneSearchStore.fetchSequence(geneId, transcriptId, type, upLen, downLen)
            if (sequence && sequence !== this.t('sequence_not_found') && sequence !== 'N/A') {
              allFastaContent += `>${transcriptId} ${type}\n${this.formatSequence(sequence)}\n\n`
            } else {
              allFastaContent += `>${transcriptId} ${type}\n${sequence}\n\n`
            }
          } catch (error) {
            console.error('Error fetching sequence:', error)
            allFastaContent += `>${transcriptId} ${type}\n搴忓垪鑾峰彇澶辫触\n\n`
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
        console.error('澶嶅埗澶辫触:', err)
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
          // 濡傛灉鏄?genomic 绫诲瀷锛屽彧澶勭悊涓€娆★紝涓庤浆褰曟湰鏃犲叧      
          if (type === 'genomic') {
            // 灏濊瘯浣跨敤 geneData.gene_seq
            if (geneData.gene_seq && geneData.gene_seq !== 'N/A') {
              allContent += `>${geneId} genomic\n${this.formatSequence(geneData.gene_seq)}\n\n`
            } else {
              // 濡傛灉 geneData.gene_seq 涓嶅瓨鍦紝浠庣紦瀛樿幏鍙?
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
            // 璺宠繃褰撳墠绫诲瀷鐨勫悗缁鐞嗭紝纭繚鍙鐞嗕竴娆?
            continue
          }

          // 澶勭悊闈?genomic 绫诲瀷锛屾寜杞綍鏈鐞?
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
    },

    downloadTableAsTxt() {
      if (!this.results || this.results.length === 0) {
        this.$message.info(this.t('no_data_to_download'))
        return
      }

      // 鏋勫缓琛ㄥご
      const headers = [
        this.t('input_id'),
        this.t('query_id'),
        this.t('species'),
        this.t('chromosome'),
        this.t('start'),
        this.t('end'),
        this.t('strand')
      ]

      // 鏋勫缓鏁版嵁琛?
      const rows = this.results.map(row => [
        row.original_id || '-',
        row.IDs || '-',
        row.species || '-',
        row.seqid || '-',
        row.start || '-',
        row.end || '-',
        row.strand || '-'
      ])

      // 缁勫悎琛ㄥご鍜屾暟鎹?
      const content = [
        headers.join('\t'),
        ...rows.map(row => row.join('\t'))
      ].join('\n')

      // 鍒涘缓骞朵笅杞芥枃浠?
      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `gene_search_results_${new Date().toISOString().split('T')[0]}.txt`
      a.click()
      URL.revokeObjectURL(url)
    }

  }
}
</script>







<style scoped>
/* 鍙互娣诲姞缁勪欢鐗瑰畾鐨勬牱寮?*/
</style>

