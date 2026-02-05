<template>
  <div class="container mt-4">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="18">
        <h2>Search Results</h2>
      </el-col>
      <el-col :span="6" class="text-right">
        <router-link to="/tools/id-search">
          <el-button type="default">Return to Search</el-button>
        </router-link>
      </el-col>
    </el-row>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="mb-4">
      <el-skeleton :rows="10" animated />
    </div>
    
    <!-- 错误状态 -->
    <el-alert
      v-else-if="errorMessage"
      type="error"
      :title="errorMessage"
      show-icon
      class="mb-4"
    />
    
    <!-- 结果展示 -->
    <div v-else-if="result">
      
      <!-- 基本信息卡片 - 使用 GeneInfoCard 组件 -->
      <gene-info-card 
        :gene-data="result" 
        title="Gene Basic Information"
        class="mb-4"
      />
      
      <!-- JBrowse View -->
      <el-card v-if="jbrowse_url" class="mb-4">
        <template #header>
          <div class="d-flex justify-content-between align-items-center">
            <h3>JBrowse View</h3>
          </div>
        </template>
        <div class="card-body">
          <iframe :src="jbrowse_url" style="width: 100%; height: 400px; border: 1px solid #ddd; border-radius: 4px;"></iframe>
        </div>
      </el-card>
      
      <!-- 序列信息卡片 -->
      <el-card v-if="has_sequences" class="mb-4">
        <template #header>
          <div class="d-flex justify-content-between align-items-center">
            <h3>Sequence</h3>
          </div>
        </template>
        <div class="card-body">
            <!-- 转录本选择器 -->
            <div v-if="hasMultipleTranscripts" class="mb-4">
              <h4 class="h6 mb-2">Transcript Selector</h4>
              <el-select v-model="selectedTranscriptIndex" @change="switchTranscript" class="w-auto">
                <el-option
                  v-for="(transcript, index) in result.mrna_transcripts"
                  :key="index"
                  :label="`${transcript.id} (Protein Length: ${transcript.protein_seq && transcript.protein_seq !== 'N/A' && transcript.protein_seq !== 'unavailable' && transcript.protein_seq !== 'Protein sequence not found' ? transcript.protein_seq.length : 'N/A'} aa)`"
                  :value="index"
                />
              </el-select>
            </div>
            
            <!-- 转录本基因结构图 -->
            <div v-if="gffData.length > 0" class="mb-4">
              <h4 class="h6 mb-2">Transcript Structure</h4>
              <div class="gene-structure-container">
                <svg :width="svgWidth" height="150" class="gene-structure-svg">
                  <!-- 转录本名称 -->
                  <text x="20" y="20" font-size="12" font-weight="bold" fill="#333">
                    {{ currentTranscript ? currentTranscript.id : (result.geneid || result.id || 'Unknown') }}
                  </text>
                  
                  <!-- 绘制基因结构元素 -->
                  <g>
                    <!-- 如果有有效GFF数据，绘制详细结构 -->
                    <template v-if="validTranscriptGffData.length > 0">
                      <!-- 绘制内含子（窄方框）和连接线 -->
                      <g v-for="(item, index) in validTranscriptGffData" :key="'structure-' + index">
                        <template v-if="geneLength > 0">
                          <!-- 绘制当前结构元素 -->
                          <rect
                            v-if="item.type === 'CDS'"
                            :x="20 + (item.start - geneStart) * scale"
                            y="35"
                            :width="(item.end - item.start + 1) * scale"
                            height="50"
                            fill="#34A853"
                            stroke="#227A3D"
                            stroke-width="1"
                          />
                          <rect
                            v-else-if="item.type === 'five_prime_UTR'"
                            :x="20 + (item.start - geneStart) * scale"
                            y="45"
                            :width="(item.end - item.start + 1) * scale"
                            height="30"
                            fill="#FBBC05"
                            stroke="#F29900"
                            stroke-width="1"
                          />
                          <rect
                            v-else-if="item.type === 'three_prime_UTR'"
                            :x="20 + (item.start - geneStart) * scale"
                            y="45"
                            :width="(item.end - item.start + 1) * scale"
                            height="30"
                            fill="#EA4335"
                            stroke="#C5221F"
                            stroke-width="1"
                          />
                          
                          <!-- 绘制与下一个元素的连接线 -->
                          <line
                            v-if="index < validTranscriptGffData.length - 1"
                            :x1="20 + (item.end - geneStart) * scale"
                            y1="60"
                            :x2="20 + (validTranscriptGffData[index + 1]!.start - geneStart) * scale"
                            y2="60"
                            stroke="#333"
                            stroke-width="2"
                          />
                          
                          <!-- 绘制内含子（窄方框） -->
                          <rect
                            v-if="index < validTranscriptGffData.length - 1"
                            :x="20 + (item.end - geneStart) * scale"
                            y="55"
                            :width="(validTranscriptGffData[index + 1]!.start - item.end - 1) * scale"
                            height="10"
                            fill="#E0E0E0"
                            stroke="#BDBDBD"
                            stroke-width="1"
                          />
                        </template>
                      </g>
                      
                      <!-- 转录方向指示 -->
                      <g v-if="validTranscriptGffData.length > 0">
                        <template v-if="geneLength > 0">
                          <!-- 箭头位置：基因结构的右侧 -->
                          <polygon
                            :points="[
                              20 + (validTranscriptGffData[validTranscriptGffData.length - 1]!.end - geneStart) * scale + 10,
                              60 - 10,
                              20 + (validTranscriptGffData[validTranscriptGffData.length - 1]!.end - geneStart) * scale + 20,
                              60,
                              20 + (validTranscriptGffData[validTranscriptGffData.length - 1]!.end - geneStart) * scale + 10,
                              60 + 10
                            ].join(',')"
                            fill="#333"
                          />
                          <text
                            :x="20 + (validTranscriptGffData[validTranscriptGffData.length - 1]!.end - geneStart) * scale + 25"
                            y="65"
                            font-size="12"
                            fill="#333"
                          >
                            Transcription Direction
                          </text>
                        </template>
                      </g>
                    </template>
                    
                    <!-- 如果没有有效GFF数据，显示简单的基因范围 -->
                    <template v-else-if="result && result.start !== undefined && result.end !== undefined">
                      <rect
                        :x="20"
                        y="45"
                        :width="(result.end - result.start + 1) * scale"
                        height="30"
                        fill="#90CAF9"
                        stroke="#2196F3"
                        stroke-width="1"
                      />
                      <text x="25" y="65" font-size="12" fill="#333">
                        {{ result.start }} - {{ result.end }}
                      </text>
                      <!-- 简单的转录方向指示 -->
                      <polygon
                        :points="[
                          20 + (result.end - result.start + 1) * scale + 10,
                          60 - 10,
                          20 + (result.end - result.start + 1) * scale + 20,
                          60,
                          20 + (result.end - result.start + 1) * scale + 10,
                          60 + 10
                        ].join(',')"
                        fill="#333"
                      />
                    </template>
                  </g>
                  
                  <!-- 基因范围标注 -->
                  <text x="20" y="110" font-size="10" fill="#666">
                    {{ geneStart }}
                  </text>
                  <text :x="svgWidth - 20" y="110" font-size="10" fill="#666" text-anchor="end">
                    {{ geneEnd }}
                  </text>
                  
                  <!-- 图注 -->
                  <g transform="translate(20, 130)">
                    <text font-size="11" font-weight="bold" fill="#333">Legend:</text>
                    <g transform="translate(50, 0)">
                      <rect x="0" y="-8" width="15" height="15" fill="#34A853" stroke="#227A3D" stroke-width="1" />
                      <text x="20" y="5" font-size="10" fill="#333">CDS</text>
                    </g>
                    <g transform="translate(120, 0)">
                      <rect x="0" y="-8" width="15" height="15" fill="#FBBC05" stroke="#F29900" stroke-width="1" />
                      <text x="20" y="5" font-size="10" fill="#333">5' UTR</text>
                    </g>
                    <g transform="translate(190, 0)">
                      <rect x="0" y="-8" width="15" height="15" fill="#EA4335" stroke="#C5221F" stroke-width="1" />
                      <text x="20" y="5" font-size="10" fill="#333">3' UTR</text>
                    </g>
                    <g transform="translate(260, 0)">
                      <rect x="0" y="-3" width="30" height="5" fill="#E0E0E0" stroke="#BDBDBD" stroke-width="1" />
                      <text x="35" y="5" font-size="10" fill="#333">Intron</text>
                    </g>
                  </g>
                </svg>
              </div>
            </div>
            
           <!-- 使用通用序列展示组件 -->
              <sequence-display
                display-mode="buttons"
                :gene_seq="result.gene_seq"
                :mrna_seq="result.mrna_seq"
                :upstream_seq="result.upstream_seq"
                :downstream_seq="result.downstream_seq"
                :cdna_seq="result.cdna_seq"
                :cds_seq="result.cds_seq"
                :protein_seq="result.protein_seq"
                :gene_id="result.IDs"
                :current-transcript="currentTranscript || undefined"
                :loading="isLoading"
                @show-sequence="handleShowSequence"
                @length-change="handleLengthChange"
              />
            
          <div class="mb-3">
            <el-button type="success" @click="downloadAllSequences">Download All Sequences</el-button>
            <el-button
              v-if="hasMultipleTranscripts"
              type="primary"
              class="ml-2"
              @click="downloadCurrentTranscriptSequences"
            >
              Download Current Transcript Sequences
            </el-button>
          </div>
        </div>
      </el-card>
      
      <!-- 注释信息卡片 -->
      <el-card
        v-if="Object.keys(annotations).length > 0"
        class="mb-4"
      >
        <template #header>
          <div class="d-flex justify-content-between align-items-center">
            <h3>Annotations</h3>
          </div>
        </template>
        <div class="card-body">
          <!-- 动态展示所有注释类型 -->
          <div v-for="(annotationList, annotationType) in annotations" :key="annotationType" class="mb-3">
            <!-- 特殊处理GO注释，使用表格展示 -->
            <div v-if="annotationType === 'GO_annotation' && annotationList.length > 0">
              <h4>{{ annotationType.replace('_', ' ') }}</h4>
              <el-table :data="parsedGoAnnotations" border>
                <el-table-column prop="type" label="GO Type" width="150" />
                <el-table-column prop="term" label="Term" />
                <el-table-column prop="id" label="GO ID" width="150" />
              </el-table>
            </div>
            
            <!-- 其他注释类型使用简单列表展示 -->
            <div v-else-if="annotationList.length > 0">
              <h4>{{ annotationType.replace('_', ' ') }}</h4>
              <div class="annotation-list">
                <div 
                  v-for="(item, index) in annotationList" 
                  :key="index"
                  class="annotation-item"
                >
                  {{ item.annotation }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-card>
      
      <!-- GFF数据表格 -->
      <el-card v-if="hasGffData" class="mb-4">
        <template #header>
          <div class="d-flex justify-content-between align-items-center">
            <h3>GFF Data</h3>
            <div>
              <el-button type="success" size="small" @click="downloadGff('txt')">Download as TXT</el-button>
              <el-button type="success" size="small" class="ml-2" @click="downloadGff('gff')">Download as GFF</el-button>
            </div>
          </div>
        </template>
        <div class="card-body">
          <!-- 表格内容 -->
          <el-table
            :data="currentPageGffData"
            style="width: 100%"
            stripe
            border
            :default-sort="{ prop: 'start', order: 'ascending' }"
          >
            <el-table-column prop="seqid" label="Seqid" min-width="100" />
            <el-table-column prop="source" label="Source" min-width="100" />
            <el-table-column prop="type" label="Type" min-width="100" />
            <el-table-column prop="start" label="Start" min-width="100" />
            <el-table-column prop="end" label="End" min-width="100" />
            <el-table-column prop="score" label="Score" min-width="50" />
            <el-table-column prop="strand" label="Strand" min-width="50" />
            <el-table-column prop="phase" label="Phase" min-width="50" />
            <el-table-column prop="attributes" label="Attributes" min-width="200" />
          </el-table>

          <!-- 分页 -->
          <div class="d-flex justify-content-between align-items-center mt-3">
            <span class="table-info">
              Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, gffData.length) }} of {{ gffData.length }} entries
            </span>
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              :total="gffData.length"
            />
          </div>
        </div>
      </el-card>
    </div>
    
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

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import httpInstance from '@/utils/http'
import SequenceDisplay from '@/components/SequenceDisplay.vue'
import SequenceModal from '@/components/SequenceModal.vue'
import GeneInfoCard from '@/components/GeneInfoCard.vue'
import { v4 as uuidv4 } from 'uuid'
import { ElMessage } from 'element-plus'
import { useGeneSearchStore } from '@/stores/geneSearch'
import { useNavigationStore } from '@/stores/navigationStore.ts'

// 定义类型
interface Annotation {
  annotation: string
  geneid_id?: number
  genome_id?: number
  id_id?: number
}

interface Transcript {
  id: string
  mrna_seq?: string
  upstream_seq?: string
  downstream_seq?: string
  cdna_seq?: string
  cds_seq?: string
  protein_seq?: string
}

interface GffItem {
  seqid?: string
  source?: string
  type?: string
  start?: number
  end?: number
  score?: string
  strand?: string
  phase?: string
  attributes?: string
}

interface Result {
  IDs: string
  seqid?: string
  start?: number
  end?: number
  strand?: string
  gene_seq?: string
  mrna_seq?: string
  upstream_seq?: string
  downstream_seq?: string
  cdna_seq?: string
  cds_seq?: string
  protein_seq?: string
  geneid?: string
  id?: string
  mrna_transcripts?: Transcript[]
}

// 初始化路由
const route = useRoute()

// 获取store
const geneSearchStore = useGeneSearchStore()
const navigationStore = useNavigationStore()

// 状态管理
const result = ref<Result | null>(null)
const hasFetched = ref(false)
const annotations = ref<Record<string, Annotation[]>>({})
const jbrowse_url = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

// 计算是否有序列信息
const has_sequences = computed(() => {
  if (!result.value) return false
  // 检查是否有直接的序列属性
  const hasDirectSequences = !!(result.value.gene_seq || result.value.mrna_seq || result.value.upstream_seq || result.value.downstream_seq || result.value.cdna_seq || result.value.cds_seq || result.value.protein_seq)
  // 检查是否有转录本序列
  const hasTranscriptSequences = !!(result.value.mrna_transcripts && result.value.mrna_transcripts.length > 0)
  // 检查是否有基因ID（确保至少有基因信息）
  const hasGeneId = !!(result.value.IDs)
  return hasDirectSequences || hasTranscriptSequences || hasGeneId
})

// 转录本选择相关
const selectedTranscriptIndex = ref(0)

// GFF数据相关
const gffData = ref<GffItem[]>([])
const hasGffData = ref(false)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)

// 弹窗相关状态
const showModal = ref(false)
const modalTitle = ref('')
const modalContent = ref('')
const currentSeqType = ref('')
const currentGeneId = ref('')

// 基因结构图相关
const svgWidth = ref(800)

// 上下游序列长度
const upstreamLength = ref(500) // 默认值
const downstreamLength = ref(500) // 默认值

// 计算属性
const parsedGoAnnotations = computed(() => {
  const goAnnotations = annotations.value.GO_annotation || []
  const parsed: { type: string; term: string; id: string }[] = []
  
  goAnnotations.forEach(item => {
    if (item && item.annotation) {
      const cleanAnnotation = item.annotation.replace(/;;+\s*$/, '')
      const goTerms = cleanAnnotation.split(';; ')
      
      goTerms.forEach(term => {
        const match = term.match(/^(\w+\s+\w+):\s*([^(]+)\s*\((GO:\d+)\)$/)
        if (match && match[1] && match[2] && match[3]) {
          parsed.push({
            type: match[1],
            term: match[2].trim(),
            id: match[3]
          })
        }
      })
    }
  })
  
  return parsed
})

// 当前选择的转录本
const currentTranscript = computed(() => {
  if (!result.value || !result.value.mrna_transcripts || result.value.mrna_transcripts.length === 0) {
    return null
  }
  return result.value.mrna_transcripts[selectedTranscriptIndex.value]
})

// 转录本数量
const hasMultipleTranscripts = computed(() => {
  return result.value && result.value.mrna_transcripts && result.value.mrna_transcripts.length > 1
})

// 当前页GFF数据
const currentPageGffData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return gffData.value.slice(start, end)
})

// 当前转录本的GFF数据
const currentTranscriptGffData = computed(() => {
  if (!gffData.value || gffData.value.length === 0) {
    return []
  }
  
  // 获取当前转录本ID或基因ID
  let currentId: string | null = null
  if (currentTranscript.value && currentTranscript.value.id) {
    currentId = currentTranscript.value.id
  } else if (result.value && result.value.geneid) {
    currentId = result.value.geneid
  } else if (result.value && result.value.id) {
    currentId = result.value.id
  }
  
  if (!currentId) {
    return gffData.value.sort((a, b) => {
      return (a.start || 0) - (b.start || 0)
    })
  }
  
  // 过滤当前转录本的GFF数据
  return gffData.value.filter(item => {
    if (item.attributes) {
      return item.attributes.includes(currentId)
    }
    return true
  }).sort((a, b) => {
    return (a.start || 0) - (b.start || 0)
  })
})

// 有效转录本GFF数据（确保所有必要属性都存在）
interface ValidGffItem {
  seqid?: string
  source?: string
  type?: string
  start: number
  end: number
  score?: string
  strand?: string
  phase?: string
  attributes?: string
}

const validTranscriptGffData = computed(() => {
  return currentTranscriptGffData.value
    .filter(item => item.start !== undefined && item.end !== undefined) as ValidGffItem[]
})

// 基因起始位置
const geneStart = computed(() => {
  if (!validTranscriptGffData.value || validTranscriptGffData.value.length === 0) {
    return 0
  }
  return Math.min(...validTranscriptGffData.value.map(item => item.start))
})

// 基因结束位置
const geneEnd = computed(() => {
  if (!validTranscriptGffData.value || validTranscriptGffData.value.length === 0) {
    return 0
  }
  return Math.max(...validTranscriptGffData.value.map(item => item.end))
})

// 基因长度
const geneLength = computed(() => {
  return geneEnd.value - geneStart.value + 1
})

// 缩放比例
const scale = computed(() => {
  const availableWidth = svgWidth.value - 40
  return availableWidth / Math.max(geneLength.value, 1)
})
//console.log('result.value:', result.IDs)
// 基本信息列表
const basicInfoList = computed(() => {
  if (!result.value) return []
  
  return [
    { label: 'Gene ID', value: result.value.IDs },
    { label: 'Chromosome', value: result.value.seqid || 'N/A' },
    { label: 'Start Position', value: result.value.start || 'N/A' },
    { label: 'End Position', value: result.value.end || 'N/A' },
    { label: 'Strand', value: result.value.strand || 'N/A' }
  ]
})

// 方法
const handleLengthChange = (eventData: { upstreamLength: number; downstreamLength: number }) => {
  const { upstreamLength: newUpstream, downstreamLength: newDownstream } = eventData
  upstreamLength.value = newUpstream
  downstreamLength.value = newDownstream
  
  // 当长度变化时，清除所有相关缓存，确保下次请求时使用新长度
  geneSearchStore.clearSequenceCache()
}

const processAnnotations = (geneidResult: any[]) => {
  const newAnnotations: Record<string, Annotation[]> = {}
  if (Array.isArray(geneidResult)) {
    geneidResult.forEach(item => {
      // 注意：后端字段名是 annoation_source（拼写错误，少了一个 't'）
      const annotationSource = item.annoation_source || item.annotation_source
      if (annotationSource && item.annotation) {
        if (!newAnnotations[annotationSource]) {
          newAnnotations[annotationSource] = []
        }
        newAnnotations[annotationSource].push({
          annotation: item.annotation,
          geneid_id: item.geneid_id,
          genome_id: item.genome_id,
          id_id: item.id_id
        })
      }
    })
  }
  annotations.value = newAnnotations
}

const fetchGeneData = async (db_id: string) => {
  // 添加延迟显示加载状态，避免快速请求时显示不必要的加载动画
  const loadingTimeout = setTimeout(() => {
    isLoading.value = true
  }, 300) // 300ms延迟，只有请求超过这个时间才显示加载状态
  
  errorMessage.value = ''
  selectedTranscriptIndex.value = 0 // 重置为默认选择第一个转录本
  
  try {
    // 首先检查 navigationStore 中是否有基因数据（从上一个组件传递过来）
    const navigationData = navigationStore.getNavigationData('geneSearch')
    
    // 检查是否需要从后端获取数据
    // 即使有导航数据，也需要检查是否包含 jbrowse_url 和 gff_data
    const needFetchFromBackend = !navigationData || !navigationData.results || 
                               !navigationData.results.jbrowse_url || 
                               !navigationData.results.gff_data
    
    if (navigationData && navigationData.results && !needFetchFromBackend) {
      console.log('从 navigationStore 获取完整基因数据:', navigationData.results)
      
      // 直接使用 navigationStore 中的数据
      result.value = navigationData.results
      
      // 处理注释数据（如果有的话）
      processAnnotations([]) // 暂时为空，因为我们没有从后端获取注释数据
      
      // 设置jbrowse_url
      jbrowse_url.value = navigationData.results.jbrowse_url || ''
      
      // 设置GFF数据
      gffData.value = navigationData.results.gff_data || []
      hasGffData.value = gffData.value.length > 0
      // 重置页码到第一页
      currentPage.value = 1
      
      // 清除加载超时定时器
      clearTimeout(loadingTimeout)
      isLoading.value = false
      return
    }
    
    // 从后端获取数据
    console.log('从后端获取基因数据，db_id:', db_id)
    const formData = {
      db_id: db_id
    }
    
    const req_uuid = uuidv4()
    await httpInstance.post('/CottonOGD_api/login/', {}, {
      headers: {
        'Content-Type': 'application/json',
        'uuid': req_uuid
      }
    })
    
    const response = await httpInstance.post(
      '/CottonOGD_api/geneid_result/',
      formData,
      {
        headers: {
          'Content-Type': 'application/json',
          'uuid': req_uuid
        }
      }
    )

    // 清除加载超时定时器
    clearTimeout(loadingTimeout)
    
    // 注意：axios interceptor returns response.data directly
    const data = response as any
    
    if (data.status === 'error' || data.status === 'not_found') {
      throw new Error(data.error || 'Gene information not found')
    }
    
    // 更新数据 - 从results数组中获取type为gene的数据
    if (data.gene_info_result && data.gene_info_result.length > 0) {
      // 查找 type 为 gene 的基因信息
      const geneInfo = data.gene_info_result.find((item: any) => item.type === 'gene') || data.gene_info_result[0]
      
      // 如果有导航数据，合并导航数据和后端数据，确保所有字段都存在
      if (navigationData && navigationData.results) {
        result.value = {
          ...navigationData.results,
          ...geneInfo,
          jbrowse_url: data.jbrowse_url || '',
          gff_data: data.gff_data || []
        }
      } else {
        result.value = geneInfo
      }
      
      // 处理注释数据
      processAnnotations(data.geneid_result || [])
      
      jbrowse_url.value = data.jbrowse_url || ''
      
      // 检查是否有序列信息：包括直接序列属性和转录本中的序列
      /*if (result.value) {
        has_sequences.value = !!(result.value.gene_seq || result.value.mrna_seq || (result.value.cds_seq && result.value.cds_seq !== '未找到CDS序列') || (result.value.protein_seq && result.value.protein_seq !== '未找到蛋白序列') || (result.value.mrna_transcripts && result.value.mrna_transcripts.length > 0))
      }
      */
    } else {
      throw new Error('No gene information found')
    }
    
    // 设置GFF数据 - 检查是否有专门的gff数据字段
    gffData.value = data.gff_data || data.gene_info_result || []
    hasGffData.value = gffData.value.length > 0
    // 重置页码到第一页
    currentPage.value = 1
    
    // 更新 navigationStore 中的数据，添加 jbrowse_url 和 gff_data
    if (navigationData && navigationData.results) {
      // 查找 type 为 gene 的基因信息
      const geneInfo = data.gene_info_result.find((item: any) => item.type === 'gene') || data.gene_info_result[0]
      navigationStore.setNavigationData('geneSearch', {
        results: {
          ...navigationData.results,
          ...geneInfo,
          jbrowse_url: jbrowse_url.value,
          gff_data: gffData.value
        }
      })
    }
                                
  } catch (error: any) {
    // 清除加载超时定时器
    clearTimeout(loadingTimeout)
    errorMessage.value = error.message
    console.error('获取基因数据错误:', error)
  } finally {
    isLoading.value = false
  }
}

// 切换转录本
const switchTranscript = (index: number) => {
  selectedTranscriptIndex.value = index
}

// 显示序列弹窗
const showSequenceModal = (title: string, content: string, seqType: string, geneId: string) => {
  modalTitle.value = title
  modalContent.value = content
  currentSeqType.value = seqType
  currentGeneId.value = geneId
  showModal.value = true
}

// 处理SequenceDisplay组件的show-sequence事件
const handleShowSequence = async (eventData: { type: string; title: string; content: string; id: string }) => {
  const { type, title, content, id } = eventData

  // 获取真正的基因ID，而不是可能的转录本ID
  const realGeneId = result.value?.IDs || ''
  // 使用mrnaid替代transcriptId，与后端字段名保持一致
  const mrnaid = currentTranscript.value?.id || id
  // 对于上下游序列，需要包含长度信息
  const upLen = upstreamLength.value
  const downLen = downstreamLength.value

  try {
    let fastaContent = ''
    let seq = content
    let isFromContent = true
    
    // 如果content为空，使用store获取序列
    if (!seq) {
      isFromContent = false
      seq = await geneSearchStore.fetchSequence(realGeneId, mrnaid, type, upLen, downLen)
    }
    
    // 如果返回的是有效序列，添加FASTA格式头部
    if (seq && seq !== 'Sequence not found' && seq !== 'N/A') {
      // 构建FASTA头部，基因组序列使用realGeneId，其他使用mrnaid
      const headerId = type === 'genomic' ? realGeneId : mrnaid
      
      // 根据类型和长度截取序列
      let processedSeq = seq
      if (type === 'upstream') {
        processedSeq = seq.slice(0, upLen)
      } else if (type === 'downstream') {
        processedSeq = seq.slice(0, downLen)
      }
      
      const lengthInfo = (type === 'upstream' || type === 'downstream') ? ` (${processedSeq.length}bp)` : ''
      fastaContent = `>${headerId} ${type}${lengthInfo}\n${processedSeq}\n`
    } else {
      // 无效序列直接使用
      fastaContent = seq
    }

    // 打开弹窗，显示FASTA格式序列
    showSequenceModal(
      title,
      fastaContent,
      type,
      realGeneId
    )
  } catch (err) {
    showSequenceModal(
      title,
      'Sequence loading failed',
      type,
      realGeneId
    )
  }
}

// 处理下载事件
const handleDownload = ({ content, type, geneId }: { content: string; type: string; geneId: string }) => {
  const header = `>${geneId} ${type}`
  const fastaContent = `${header}\n${content}`
  
  const blob = new Blob([fastaContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${geneId}_${type}.fasta`
  // 使用document.createEvent来创建一个自定义事件，避免触发页面刷新
  const event = new MouseEvent('click', {
    bubbles: true,
    cancelable: true,
    view: window
  })
  document.body.appendChild(a)
  a.dispatchEvent(event)
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 处理复制事件
const handleCopy = ({ content, type, geneId }: { content: string; type: string; geneId: string }) => {
  // 按照FASTA格式复制序列，包含基因ID和序列类型
  const header = `>${geneId} ${type}`
  const fastaContent = `${header}\n${content}`
  
  navigator.clipboard.writeText(fastaContent)
    .then(() => {
      ElMessage.success('序列已复制到剪贴板')
    })
    .catch(err => {
      console.error('复制失败:', err)
      ElMessage.error('复制失败，请手动复制')
    })
}

// 辅助函数：将序列按每行80个字符换行
const formatSequence = (seq: string) => {
  if (!seq) return ''
  return seq.replace(/(.{1,80})/g, '$1\n')
}

// 下载当前转录本的所有序列
const downloadCurrentTranscriptSequences = () => {
  if (!result.value || !currentTranscript.value) {
    ElMessage.error('无法获取基因序列数据')
    return
  }
  
  let transcriptSequences = ''
  const geneId = result.value.IDs
  const transcriptId = currentTranscript.value.id
  
  // 收集当前转录本的所有可用序列
  
  // 添加基因组序列
  if (result.value.gene_seq && result.value.gene_seq !== 'N/A') {
    transcriptSequences += `>${geneId} genomic\n${formatSequence(result.value.gene_seq)}\n\n`
  }
  
  // 添加当前转录本的mRNA序列
  if (currentTranscript.value.mrna_seq && currentTranscript.value.mrna_seq !== 'N/A') {
    transcriptSequences += `>${transcriptId} mRNA\n${formatSequence(currentTranscript.value.mrna_seq)}\n\n`
  }
  
  // 添加当前转录本的上游序列
  if (currentTranscript.value.upstream_seq && currentTranscript.value.upstream_seq !== 'N/A') {
    transcriptSequences += `>${transcriptId} upstream\n${formatSequence(currentTranscript.value.upstream_seq)}\n\n`
  }
  
  // 添加当前转录本的下游序列
  if (currentTranscript.value.downstream_seq && currentTranscript.value.downstream_seq !== 'N/A') {
    transcriptSequences += `>${transcriptId} downstream\n${formatSequence(currentTranscript.value.downstream_seq)}\n\n`
  }
  
  // 添加当前转录本的cDNA序列
  if (currentTranscript.value.cdna_seq && currentTranscript.value.cdna_seq !== 'N/A' && currentTranscript.value.cdna_seq !== 'unavailable') {
    transcriptSequences += `>${transcriptId} cDNA\n${formatSequence(currentTranscript.value.cdna_seq)}\n\n`
  }
  
  // 添加其他序列类型（使用当前转录本的序列）
  const transcriptSequenceTypes = [
    { key: 'cds_seq', type: 'cds', label: 'CDS Sequence' },
    { key: 'protein_seq', type: 'protein', label: 'Protein Sequence' }
  ]
  
  transcriptSequenceTypes.forEach(item => {
    // @ts-ignore
    const sequence = currentTranscript.value[item.key]
    if (sequence && sequence !== 'N/A' && sequence !== 'unavailable' && sequence !== 'CDS sequence not found' && sequence !== 'Protein sequence not found') {
      transcriptSequences += `>${transcriptId} ${item.type}\n${formatSequence(sequence)}\n\n`
    }
  })
  
  if (!transcriptSequences) {
    ElMessage.error('No sequence data available')
    return
  }
  
  // 创建并下载文件
  const blob = new Blob([transcriptSequences], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${transcriptId}_all_sequences.fasta`
  // 使用document.createEvent来创建一个自定义事件，避免触发页面刷新
  const event = new MouseEvent('click', {
    bubbles: true,
    cancelable: true,
    view: window
  })
  document.body.appendChild(a)
  a.dispatchEvent(event)
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  ElMessage.success('All sequences for the current transcript have been downloaded')
}

// 下载所有序列
const downloadAllSequences = async () => {
  if (!result.value) {
    ElMessage.error('Cannot retrieve gene sequence data')
    return
  }
  
  isLoading.value = true
  let allSequences = ''
  const geneId = result.value.IDs
  
  // 定义所有需要下载的序列类型
  const allSeqTypes = ['genomic', 'mrna', 'upstream', 'downstream', 'cdna', 'cds', 'protein']
  
  // 获取所有转录本
  const transcripts = result.value.mrna_transcripts || []
  
  try {
    // 添加基因组序列（直接从result获取，不需要请求后端）
    if (result.value.gene_seq && result.value.gene_seq !== 'N/A') {
      const formattedSeq = formatSequence(result.value.gene_seq)
      allSequences += `>${geneId} genomic\n${formattedSeq}\n\n`
    }
    
    // 为每个转录本处理所有序列类型
    for (const transcript of transcripts) {
      const transcriptId = transcript.id
      
      // 为每种序列类型获取序列
      for (const seqType of allSeqTypes) {
        // 跳过基因组序列，因为已经添加过了
        if (seqType === 'genomic') continue
        
        // 尝试从当前转录本获取序列
        let seqContent = ''
        let foundInResult = false
        
        // 根据序列类型从transcript或result中获取
        switch (seqType) {
          case 'mrna':
            if (transcript.mrna_seq && transcript.mrna_seq !== 'N/A') {
              seqContent = transcript.mrna_seq
              foundInResult = true
            }
            break
          case 'upstream':
            if (transcript.upstream_seq && transcript.upstream_seq !== 'N/A') {
              seqContent = transcript.upstream_seq
              foundInResult = true
            }
            break
          case 'downstream':
            if (transcript.downstream_seq && transcript.downstream_seq !== 'N/A') {
              seqContent = transcript.downstream_seq
              foundInResult = true
            }
            break
          case 'cdna':
            if (transcript.cdna_seq && transcript.cdna_seq !== 'N/A' && transcript.cdna_seq !== 'unavailable') {
              seqContent = transcript.cdna_seq
              foundInResult = true
            }
            break
          case 'cds':
            if (transcript.cds_seq && transcript.cds_seq !== 'N/A' && transcript.cds_seq !== 'unavailable' && transcript.cds_seq !== 'CDS sequence not found') {
              seqContent = transcript.cds_seq
              foundInResult = true
            }
            break
          case 'protein':
            if (transcript.protein_seq && transcript.protein_seq !== 'N/A' && transcript.protein_seq !== 'unavailable' && transcript.protein_seq !== 'Protein sequence not found') {
              seqContent = transcript.protein_seq
              foundInResult = true
            }
            break
        }
        
        // 如果在result中没有找到，使用store获取序列
        if (!foundInResult) {
          // 使用store获取序列，自动处理缓存
          seqContent = await geneSearchStore.fetchSequence(geneId, transcriptId, seqType, upstreamLength.value, downstreamLength.value)
        }
        
        // 如果获取到了序列，添加到结果中
        if (seqContent && seqContent !== 'Sequence not found' && seqContent !== 'N/A') {
          const formattedSeq = formatSequence(seqContent)
          // 基因组序列使用gene_id，其他使用transcriptId
          const headerId = seqType === 'genomic' ? geneId : transcriptId
          allSequences += `>${headerId} ${seqType}\n${formattedSeq}\n\n`
        }
      }
    }
    
    // 如果没有获取到任何序列
    if (!allSequences) {
      ElMessage.error('No sequence data available')
      return
    }
    
    // 创建并下载文件
    const blob = new Blob([allSequences], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${geneId}_all_sequences.fasta`
    // 使用document.createEvent来创建一个自定义事件，避免触发页面刷新
    const event = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
      view: window
    })
    document.body.appendChild(a)
    a.dispatchEvent(event)
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    ElMessage.success('All sequences downloaded successfully')
  } catch (error) {
    console.error('Failed to download sequences:', error)
    ElMessage.error('Failed to download sequences, please try again')
  } finally {
    isLoading.value = false
  }
}

// 下载GFF数据
const downloadGff = (format: string) => {
  const geneId = currentGeneId.value || result.value?.IDs || ''
  
  if (format === 'txt') {
    // 生成TXT格式文本
    let txtContent = ''
    
    gffData.value.forEach(item => {
      const fields = [
        item.seqid || '',
        item.source || '',
        item.type || '',
        item.start || '',
        item.end || '',
        item.score || '',
        item.strand || '',
        item.phase || '',
        item.attributes || ''
      ]
      txtContent += fields.join('\t') + '\n'
    })
    
    const blob = new Blob([txtContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${geneId}_gff.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    ElMessage.success('GFF data has been downloaded as TXT format')
  } else if (format === 'gff') {
    // 生成标准GFF格式文本
    let gffContent = ''
    
    gffData.value.forEach(item => {
      const fields = [
        item.seqid || '',
        item.source || '.',
        item.type || '.',
        item.start || '.',
        item.end || '.',
        item.score || '.',
        item.strand || '.',
        item.phase || '.',
        item.attributes || '.'
      ]
      gffContent += fields.join('\t') + '\n'
    })
    
    const blob = new Blob([gffContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${geneId}_gff.gff`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    ElMessage.success('GFF data has been downloaded as GFF format')
  }
}

// 生命周期钩子
onMounted(() => {
  const db_id = route.query.db_id as string
  if (db_id && !hasFetched.value) {
    hasFetched.value = true
    fetchGeneData(db_id)
  } else {
    errorMessage.value = 'Database ID not provided'
  }
})
</script>

<style scoped>
/* 自定义样式 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
}

.mt-4 {
  margin-top: 1.5rem;
}

.mb-3 {
  margin-bottom: 1rem;
}

.mb-4 {
  margin-bottom: 1.5rem;
}

.ml-2 {
  margin-left: 0.5rem;
}

.text-center {
  text-align: center;
}

.py-5 {
  padding: 3rem 0;
}

.card-header {
  font-size: 16px;
  font-weight: 500;
}

.gene-structure-container {
  overflow-x: auto;
}

.gene-structure-svg {
  display: block;
  margin: 0 auto;
}

.table-info {
  font-size: 14px;
  color: #666;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 注释列表样式 */
.annotation-list {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
}

.annotation-item {
  padding: 8px 0;
  border-bottom: 1px solid #e4e7ed;
}

.annotation-item:last-child {
  border-bottom: none;
}
</style>