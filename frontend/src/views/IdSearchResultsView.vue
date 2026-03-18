<template>
  <div class="container mt-4">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="18">
        <h2>{{ t('search_results') }}</h2>
      </el-col>
      <el-col :span="6" class="text-right">
        <router-link to="/tools/id-search/id-search-summary/">
          <el-button type="default">{{ t('return_to_search') }}</el-button>
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
    <div v-else-if="result" class="result-container">
      <!-- 左侧固定锚点导航 -->
      <div class="anchor-sidebar">
        <el-anchor direction="vertical" :offset="80">
          <el-anchor-link href="#basic-info" :title="t('gene_basic_information')" />
          <el-anchor-link v-if="jbrowse_url" href="#jbrowse-view" :title="t('jbrowse_view')" />
          <el-anchor-link href="#sequence" :title="t('sequence')" />
          <el-anchor-link v-if="expressionData.length > 0" href="#expression" :title="t('gene_expression')" />
          <el-anchor-link v-if="Object.keys(annotations).length > 0" href="#annotations" :title="'Annotations'" />
          <el-anchor-link v-if="hasGffData" href="#gff-data" :title="'GFF Data'" />
        </el-anchor>
      </div>
      
      <!-- 主内容区域 -->
      <div class="main-content">
          <!-- 基本信息卡片 - 使用 GeneInfoCard 组件 -->
          <gene-info-card 
            :gene-data="result" 
            :title="t('gene_basic_information')"
            class="mb-4"
            id="basic-info"
          />
      
          <!-- JBrowse View -->
          <el-card v-if="jbrowse_url" class="mb-4" id="jbrowse-view">
            <template #header>
              <div class="d-flex justify-content-between align-items-center">
                <h3>{{ t('jbrowse_view') }}</h3>
              </div>
            </template>
            <div class="card-body">
              <iframe :src="jbrowse_url" style="width: 100%; height: 400px; border: 1px solid #ddd; border-radius: 4px;"></iframe>
            </div>
          </el-card>
          
          <!-- 序列信息卡片 -->
          <el-card  class="mb-4" id="sequence">
        <template #header>
          <div class="d-flex justify-content-between align-items-center">
            <h3>{{ t('sequence') }}</h3>
          </div>
        </template>
        <div class="card-body">
            <!-- 转录本选择器 -->
            <div v-if="hasMultipleTranscripts" class="mb-4">
              <h4 class="h6 mb-2">{{ t('transcript_selector') }}</h4>
              <el-select v-model="selectedTranscriptIndex" @change="switchTranscript" class="w-auto" style="min-width: 400px;">
                <el-option
                  v-for="(transcript, index) in result.mrna_transcripts"
                  :key="index"
                  :label="`${transcript.id} (Protein Length: ${transcript.protein_seq && transcript.protein_seq !== 'N/A' && transcript.protein_seq !== 'unavailable' && transcript.protein_seq !== 'Protein sequence not found' ? transcript.protein_seq.length : 'N/A'} aa)`"
                  :value="index"
                />
              </el-select>
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
            <el-button type="success" @click="showDownloadDialog">Download Data</el-button>
            <el-button
              v-if="hasMultipleTranscripts"
              type="primary"
              class="ml-2"
              @click="showCurrentTranscriptDownloadDialog"
            >
              Download Current Transcript Sequences
            </el-button>
          </div>
          
          <!-- 下载参数弹窗 -->
          <el-dialog
            v-model="downloadDialogVisible"
            title="Download Parameters"
            width="500px"
          >
            <el-form :model="downloadForm" label-width="120px">
              <el-form-item label="Data Type">
                <el-checkbox-group v-model="downloadForm.dataTypes">
                  <el-checkbox label="genomic">Genomic</el-checkbox>
                  <el-checkbox label="mrna">mRNA</el-checkbox>
                  <el-checkbox label="upstream">Upstream</el-checkbox>
                  <el-checkbox label="downstream">Downstream</el-checkbox>
                  <el-checkbox label="cdna">cDNA</el-checkbox>
                  <el-checkbox label="cds">CDS</el-checkbox>
                  <el-checkbox label="protein">Protein</el-checkbox>
                </el-checkbox-group>
              </el-form-item>
              <el-form-item label="Format">
                <el-radio-group v-model="downloadForm.format">
                  <el-radio label="fasta">FASTA</el-radio>
                  <el-radio label="txt">TXT</el-radio>
                </el-radio-group>
              </el-form-item>
            </el-form>
            <template #footer>
              <span class="dialog-footer">
                <el-button @click="downloadDialogVisible = false">Cancel</el-button>
                <el-button type="primary" @click="downloadSelectedData">Download</el-button>
              </span>
            </template>
          </el-dialog>
        </div>
      </el-card>
      
      <!-- 基因表达量表格 -->
      <el-card v-if="expressionData.length > 0" class="mb-4" id="expression">
        <template #header>
          <div class="d-flex justify-content-between align-items-center">
            <h3>{{ t('gene_expression') }}</h3>
            <el-button type="success" size="small" @click="downloadExpressionData">
              {{ t('download_data') }}
            </el-button>
          </div>
        </template>
        <div class="card-body">
          <el-table
            :data="expressionData"
            style="width: 100%"
            stripe
            border
          >
            <el-table-column label="{{ t('gene_id') }}" width="180">
              <template #default="scope">
                <router-link :to="{
                  path: '/tools/gene-expression-efp/',
                  query: {
                    gene_id: scope.row.geneid,
                    genome_id: result?.genome_id
                  }
                }">
                  {{ scope.row.geneid }}
                </router-link>
              </template>
            </el-table-column>
            <el-table-column 
              v-for="tissue in expressionTissues" 
              :key="tissue"
              :prop="tissue" 
              :label="tissue"
              min-width="100"
            >
              <template #default="scope">
                <div v-if="scope.row[tissue] !== undefined">
                  {{ scope.row[tissue].toFixed(4) }}
                </div>
                <div v-else>-</div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>
      
      <!-- 注释信息卡片 -->
      <el-card
        v-if="Object.keys(annotations).length > 0"
        class="mb-4"
        id="annotations"
      >
        <template #header>
          <div class="d-flex justify-content-between align-items-center">
            <h3>Annotations</h3>
          </div>
        </template>
        <div class="card-body">
          <!-- 特殊处理GO注释，使用表格展示 -->
          <div v-if="parsedGoAnnotations.length > 0" class="mb-3">
            <h4>GO annotation</h4>
            <el-table :data="parsedGoAnnotations" border>
              <el-table-column label="GO ID" width="150">
                <template #default="scope">
                  <a :href="`https://www.ebi.ac.uk/QuickGO/term/${scope.row.id}`" target="_blank" rel="noopener noreferrer">
                    {{ scope.row.id }}
                  </a>
                </template>
              </el-table-column>
              <el-table-column prop="type" label="GO Type" width="150" />
              <el-table-column prop="term" label="Term" />
            </el-table>
          </div>
          
          <!-- 特殊处理KEGG注释，使用表格展示 -->
          <div v-if="parsedKeggAnnotations.length > 0" class="mb-3">
            <h4>KEGG annotation</h4>
            <el-table :data="parsedKeggAnnotations" border>
              <el-table-column label="KEGG ID" width="150">
                <template #default="scope">
                  <a :href="`https://www.ebi.ac.uk/QuickGO/term/${scope.row.id}`" target="_blank" rel="noopener noreferrer">
                    {{ scope.row.id }}
                  </a>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="Description" />
            </el-table>
          </div>
          
          <!-- 其他注释类型使用表格展示 -->
          <div v-for="(annotationList, annotationType) in annotations" :key="annotationType" class="mb-3">
            <div v-if="annotationType !== 'GO_annotation' && annotationType !== 'KEGG_annotation' && annotationList.length > 0">
              <h4>{{ String(annotationType).replace(/_/g, ' ') }}</h4>
              <el-table :data="annotationList" border>
                <el-table-column label="Annotation ID" width="150">
                  <template #default="scope">
                    <a 
                      v-if="scope.row.annotation_source === 'InterProScan' && scope.row.annoation_id"
                      :href="`https://www.ebi.ac.uk/interpro/entry/InterPro/${scope.row.annoation_id}`" 
                      target="_blank" 
                      rel="noopener noreferrer"
                    >
                      {{ scope.row.annoation_id }}
                    </a>
                    <span v-else>{{ scope.row.annoation_id || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="annotation" label="Annotation" />
              </el-table>
            </div>
          </div>
        </div>
      </el-card>
      
      <!-- GFF数据表格 -->
      <el-card v-if="hasGffData" class="mb-4" id="gff-data">
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
              :total="currentTranscriptGffData.length"
            />
          </div>
        </div>
      </el-card>
    </div>
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
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" target=".container" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import httpInstance from '@/utils/http'
import SequenceDisplay from '@/components/SequenceDisplay.vue'
import SequenceModal from '@/components/SequenceModal.vue'
import GeneInfoCard from '@/components/GeneInfoCard.vue'
import { v4 as uuidv4 } from 'uuid'
import { ElMessage } from 'element-plus'
import { useGeneSearchStore } from '@/stores/geneSearch'
import { useNavigationStore } from '@/stores/navigationStore.ts'

const { t } = useI18n()

// 定义类型
interface Annotation {
  annotation: string
  annoation_id?: string
  annotation_source?: string
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
  genome_id?: string
  mrna_transcripts?: Transcript[]
  gene_go_result?: any[]
  gene_kegg_result?: any[]
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

// 基因表达量数据
const expressionData = ref<any[]>([])
const expressionTissues = ref<string[]>([])
const expressionLoading = ref(false)

// 计算属性
const parsedGoAnnotations = computed(() => {
  const goAnnotations = result.value?.gene_go_result || []
  console.log('goAnnotations:', goAnnotations)
  const parsed: { type: string; term: string; id: string }[] = []
  
  goAnnotations.forEach((item: any) => {
    if (item && item.go_type && item.go_description && item.go_id) {
      parsed.push({
        type: item.go_type,
        term: item.go_description,
        id: item.go_id
      })
    }
  })
  
  return parsed
})

// 解析KEGG注释数据
const parsedKeggAnnotations = computed(() => {
  const keggAnnotations = result.value?.gene_kegg_result || []
  const parsed: { id: string; description: string }[] = []
  
  keggAnnotations.forEach((item: any) => {
    if (item && item.kegg_id && item.kegg_description) {
      parsed.push({
        id: item.kegg_id,
        description: item.kegg_description
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
  //console.log('selectedTranscriptIndex.value:', selectedTranscriptIndex.value)
  return result.value.mrna_transcripts[selectedTranscriptIndex.value]
})
console.log('currentTranscript:', currentTranscript)
// 转录本数量
const hasMultipleTranscripts = computed(() => {
  return result.value && result.value.mrna_transcripts && result.value.mrna_transcripts.length > 1
})

// 当前页GFF数据
const currentPageGffData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return currentTranscriptGffData.value.slice(start, end)
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
    return gffData.value.sort((a: GffItem, b: GffItem) => {
      return (Number(a.start) || 0) - (Number(b.start) || 0)
    })
  }
  
  // 过滤当前转录本的GFF数据
  const filtered = gffData.value.filter((item: GffItem) => {
    if (item.attributes && currentId) {
      const matches = item.attributes.indexOf(currentId) !== -1
      //console.log(`GFF item attributes: ${item.attributes}, currentId: ${currentId}, matches: ${matches}`)
      return matches
    }
    return false
  })
  
  console.log('currentTranscriptGffData - filtered count:', filtered.length)
  
  return filtered.sort((a: GffItem, b: GffItem) => {
    return (Number(a.start) || 0) - (Number(b.start) || 0)
  })
})
console.log('currentTranscriptGffData',currentTranscriptGffData)

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
    .filter((item: GffItem) => item.start !== undefined && item.end !== undefined) as ValidGffItem[]
})

// 基因起始位置
const geneStart = computed(() => {
  if (!validTranscriptGffData.value || validTranscriptGffData.value.length === 0) {
    return 0
  }
  return Math.min(...validTranscriptGffData.value.map((item: ValidGffItem) => Number(item.start)))
})

// 基因结束位置
const geneEnd = computed(() => {
  if (!validTranscriptGffData.value || validTranscriptGffData.value.length === 0) {
    return 0
  }
  return Math.max(...validTranscriptGffData.value.map((item: ValidGffItem) => Number(item.end)))
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
          annoation_id: item.annoation_id,
          annotation_source: annotationSource,
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
    const navigationData = navigationStore.getNavigationData('geneDetail')
    
    // 检查是否需要从后端获取数据
    // 根据 jbrowse_url 是否为空来决定是否从后端获取数据
    // 如果 jbrowse_url 不为空，说明是从 summary 继承的数据，直接使用
    // 如果 jbrowse_url 为空，说明需要从后端获取数据
    const needFetchFromBackend = !navigationData || !navigationData.results || !navigationData.results.jbrowse_url
    
    if (navigationData && navigationData.results && !needFetchFromBackend) {
      console.log('从 navigationStore 获取基因数据（从 summary 继承）:', navigationData.results)
      
      // 直接使用 navigationStore 中的数据
      result.value = navigationData.results
      
      // 处理注释数据（如果有的话）
      if (navigationData.results.geneid_result && Array.isArray(navigationData.results.geneid_result)) {
        processAnnotations(navigationData.results.geneid_result)
      } else {
        processAnnotations([])
      }
      
      // 处理 GO 注释数据（如果有的话）
      if (navigationData.results.gene_go_result && Array.isArray(navigationData.results.gene_go_result)) {
        const goAnnotations = navigationData.results.gene_go_result.map((item: any) => ({
          annotation: `${item.go_type}: ${item.go_description} (${item.go_id})`,
          geneid_id: item.geneid_id,
          genome_id: item.genome_id,
          id_id: item.id_id
        }))
        if (!annotations.value.GO_annotation) {
          annotations.value.GO_annotation = []
        }
        annotations.value.GO_annotation = [...annotations.value.GO_annotation, ...goAnnotations]
      }
      
      // 处理 KEGG 注释数据（如果有的话）
      if (navigationData.results.gene_kegg_result && Array.isArray(navigationData.results.gene_kegg_result)) {
        const keggAnnotations = navigationData.results.gene_kegg_result.map((item: any) => ({
          annotation: `${item.kegg_type}: ${item.kegg_description} (${item.kegg_id})`,
          geneid_id: item.geneid_id,
          genome_id: item.genome_id,
          id_id: item.id_id
        }))
        if (!annotations.value.KEGG_annotation) {
          annotations.value.KEGG_annotation = []
        }
        annotations.value.KEGG_annotation = [...annotations.value.KEGG_annotation, ...keggAnnotations]
      }
      
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
      
      // 加载基因表达量数据
      const geneId = result.value?.IDs
      if (geneId) {
        loadExpressionData(geneId)
      }
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
    const responseData = response as any
    const data = JSON.parse(responseData.results) as any
    console.log('从后端获取基因数据，响应数据:', data)
    console.log('从后端获取基因数据，mrna_transcripts:', data.mrna_transcripts)
    if (data.status === 'error' || data.status === 'not_found') {
      throw new Error(data.error || 'Gene information not found')
    }
    
    // 更新数据 - 从results数组中获取type为gene的数据
    if (data.gff_data && data.gff_data.length > 0) {
      // 查找 type 为 gene 的基因信息
      const geneInfo = data.gff_data.find((item: any) => item.type === 'gene') || data.gff_data[0]
      
      // 如果有导航数据，合并导航数据和后端数据，确保所有字段都存在
      if (navigationData && navigationData.results) {
        result.value = {
          ...navigationData.results,
          ...geneInfo,
          gene_seq: data.gene_seq || '',
          IDs: data.IDs || geneInfo.IDs || '',
          jbrowse_url: data.jbrowse_url || '',
          gff_data: data.gff_data || [],
          mrna_transcripts: data.mrna_transcripts || [],
          gene_go_result: data.gene_go_result || [],
          gene_kegg_result: data.gene_kegg_result || []
        }
      } else {
        result.value = {
          ...geneInfo,
          gene_seq: data.gene_seq || '',
          IDs: data.IDs || geneInfo.IDs || '',
          jbrowse_url: data.jbrowse_url || '',
          gff_data: data.gff_data || [],
          mrna_transcripts: data.mrna_transcripts || [],
          gene_go_result: data.gene_go_result || [],
          gene_kegg_result: data.gene_kegg_result || []
        }
      }
      
      // 处理注释数据
      processAnnotations(data.geneid_result || [])
      
      // 处理 GO 注释数据
      if (data.gene_go_result && data.gene_go_result.length > 0) {
        const goAnnotations = data.gene_go_result.map((item: any) => ({
          annotation: `${item.go_type}: ${item.go_description} (${item.go_id})`,
          geneid_id: item.geneid_id,
          genome_id: item.genome_id,
          id_id: item.id_id
        }))
        if (!annotations.value.GO_annotation) {
          annotations.value.GO_annotation = []
        }
        annotations.value.GO_annotation = [...annotations.value.GO_annotation, ...goAnnotations]
      }
      
      // 处理 KEGG 注释数据
      if (data.gene_kegg_result && data.gene_kegg_result.length > 0) {
        const keggAnnotations = data.gene_kegg_result.map((item: any) => ({
          annotation: `${item.kegg_type}: ${item.kegg_description} (${item.kegg_id})`,
          geneid_id: item.geneid_id,
          genome_id: item.genome_id,
          id_id: item.id_id
        }))
        if (!annotations.value.KEGG_annotation) {
          annotations.value.KEGG_annotation = []
        }
        annotations.value.KEGG_annotation = [...annotations.value.KEGG_annotation, ...keggAnnotations]
      }
      
      jbrowse_url.value = data.jbrowse_url || ''
      
    } else {
      throw new Error('No gene information found')
    }
    
    // 设置GFF数据 - 检查是否有专门的gff数据字段
    gffData.value = data.gff_data || data.gene_info_result || []
    hasGffData.value = gffData.value.length > 0
    // 重置页码到第一页
    currentPage.value = 1
    
    // 存储基因详细信息到 navigationStore 的 geneDetail 中，确保返回时数据不丢失
    if (result.value) {
      navigationStore.setNavigationData('geneDetail', {
        results: {
          ...result.value,
          jbrowse_url: jbrowse_url.value,
          gff_data: gffData.value
        },
        dbId: db_id
      })
      console.log('基因数据已存储到 navigationStore:', result.value.IDs)
      
      // 加载基因表达量数据
      const geneId = result.value?.IDs
      if (geneId) {
        loadExpressionData(geneId, undefined, db_id)
      }
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
  const fastaContent = `${content}`
  
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
  const fastaContent = `${content}`
  
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

// 下载参数弹窗相关
const downloadDialogVisible = ref(false)
const downloadForm = ref({
  dataTypes: [],
  format: 'fasta'
})

// 显示下载参数弹窗
const showDownloadDialog = () => {
  // 重置下载模式为默认（所有转录本）
  downloadMode.value = 'all'
  downloadDialogVisible.value = true
}

// 显示当前转录本的下载参数弹窗
const showCurrentTranscriptDownloadDialog = () => {
  // 设置下载模式为当前转录本
  downloadMode.value = 'current'
  downloadDialogVisible.value = true
}

// 下载模式：'all' 表示下载所有转录本，'current' 表示只下载当前转录本
const downloadMode = ref('all')

// 下载选定的数据
const downloadSelectedData = () => {
  if (!result.value) {
    ElMessage.error('无法获取基因数据')
    return
  }
  
  const { dataTypes, format } = downloadForm.value
  if (dataTypes.length === 0) {
    ElMessage.error('请选择至少一种数据类型')
    return
  }
  
  // 这里可以根据选择的参数实现下载逻辑
  // 每种类型一个文件，包含该基因该类型的所有数据
  dataTypes.forEach(type => {
    let sequences = ''
    if (!result.value) return
    
    const geneId = result.value.IDs
    
    // 收集该类型的所有序列
  if (type === 'genomic') {
    // 基因组序列 - 只有一个
    if (result.value.gene_seq && result.value.gene_seq !== 'N/A') {
      sequences += `>${geneId} genomic\n${formatSequence(result.value.gene_seq)}\n\n`
    }
  } else if (result.value.mrna_transcripts) {
    // 根据下载模式决定处理哪些转录本
    if (downloadMode.value === 'current') {
      // 只处理当前转录本
      if (currentTranscript.value) {
        let sequence: string = ''
        
        switch (type) {
          case 'mrna':
            sequence = currentTranscript.value.mrna_seq || ''
            break
          case 'upstream':
            sequence = currentTranscript.value.upstream_seq || ''
            break
          case 'downstream':
            sequence = currentTranscript.value.downstream_seq || ''
            break
          case 'cdna':
            sequence = currentTranscript.value.cdna_seq || ''
            break
          case 'cds':
            sequence = currentTranscript.value.cds_seq || ''
            break
          case 'protein':
            sequence = currentTranscript.value.protein_seq || ''
            break
        }
        
        if (sequence && sequence !== 'N/A' && sequence !== 'unavailable' && sequence !== 'CDS sequence not found' && sequence !== 'Protein sequence not found') {
          sequences += `>${currentTranscript.value.id} ${type}\n${formatSequence(sequence)}\n\n`
        }
      }
    } else {
      // 处理所有转录本
      result.value.mrna_transcripts.forEach(transcript => {
        let sequence: string = ''
        
        switch (type) {
          case 'mrna':
            sequence = transcript.mrna_seq || ''
            break
          case 'upstream':
            sequence = transcript.upstream_seq || ''
            break
          case 'downstream':
            sequence = transcript.downstream_seq || ''
            break
          case 'cdna':
            sequence = transcript.cdna_seq || ''
            break
          case 'cds':
            sequence = transcript.cds_seq || ''
            break
          case 'protein':
            sequence = transcript.protein_seq || ''
            break
        }
        
        if (sequence && sequence !== 'N/A' && sequence !== 'unavailable' && sequence !== 'CDS sequence not found' && sequence !== 'Protein sequence not found') {
          sequences += `>${transcript.id} ${type}\n${formatSequence(sequence)}\n\n`
        }
      })
    }
  }
    
    if (sequences) {
      // 创建并下载文件
      const blob = new Blob([sequences], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      // 根据下载模式调整文件名
      const fileName = downloadMode.value === 'current' && currentTranscript.value 
        ? `${currentTranscript.value.id}_${type}.${format}` 
        : `${geneId}_${type}.${format}`
      a.download = fileName
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
  })
  
  downloadDialogVisible.value = false
  ElMessage.success(`已下载 ${dataTypes.length} 个文件`)
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
    
    gffData.value.forEach((item: GffItem) => {
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
    
    gffData.value.forEach((item: GffItem) => {
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

// 加载基因表达量数据
const loadExpressionData = async (geneId: string, genomeId?: string, dbId?: string) => {
  if (!geneId && !dbId) return
  
  expressionLoading.value = true
  try {
    const params: any = {}
    if (dbId) {
      params.db_id = dbId
    } else {
      params.gene_id = geneId
      params.genome_id = genomeId || route.query.genome_id
    }
    
    const response = await httpInstance.post('/CottonOGD_api/extract_expression/', params) as any
    
    if (response.expression && response.expression.length > 0) {
      expressionData.value = response.expression
      // 提取组织列表（排除id_id和geneid列）
      if (response.expression.length > 0) {
        const firstItem = response.expression[0]
        expressionTissues.value = Object.keys(firstItem).filter(key => 
          key !== 'id_id' && key !== 'geneid' && typeof firstItem[key] === 'number'
        )
      }
    }
  } catch (error) {
    console.error('获取基因表达量数据失败:', error)
  } finally {
    expressionLoading.value = false
  }
}

// 下载表达量数据
const downloadExpressionData = () => {
  if (expressionData.value.length === 0) {
    ElMessage.warning('No expression data available for download')
    return
  }

  // 获取所有组织列名
  const tissueColumns = expressionTissues.value
  
  // 构建CSV表头
  const headers = ['Gene ID', ...tissueColumns]
  
  // 构建CSV行
  const rows = expressionData.value.map(item => {
    const row = [item.geneid]
    tissueColumns.forEach(col => {
      row.push(item[col] !== undefined ? item[col] : '-')
    })
    return row
  })
  
  // 组合表头和行
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n')
  
  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', 'gene_expression_data.csv')
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}

// 处理基因ID和基因组ID的函数
const fetchGeneDataWithGeneId = async (gene_id: string, genome_id: string) => {
  // 添加延迟显示加载状态
  const loadingTimeout = setTimeout(() => {
    isLoading.value = true
  }, 300)
  
  errorMessage.value = ''
  selectedTranscriptIndex.value = 0
  
  try {
    console.log('从后端获取基因数据，gene_id:', gene_id, 'genome_id:', genome_id)
    const formData = {
      gene_id: gene_id,
      genome_id: genome_id
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
    const responseData = response as any
    const data = JSON.parse(responseData.results) as any
    console.log('从后端获取基因数据，响应数据:', data)
    
    if (data.status === 'error' || data.status === 'not_found') {
      throw new Error(data.error || 'Gene information not found')
    }
    
    // 更新数据 - 从results数组中获取type为gene的数据
    if (data.gff_data && data.gff_data.length > 0) {
      // 查找 type 为 gene 的基因信息
      const geneInfo = data.gff_data.find((item: any) => item.type === 'gene') || data.gff_data[0]
      
      result.value = {
        ...geneInfo,
        gene_seq: data.gene_seq || '',
        IDs: data.IDs || geneInfo.IDs || '',
        jbrowse_url: data.jbrowse_url || '',
        gff_data: data.gff_data || [],
        mrna_transcripts: data.mrna_transcripts || [],
        gene_go_result: data.gene_go_result || [],
        gene_kegg_result: data.gene_kegg_result || []
      }
    } else {
      throw new Error('No gene information found')
    }
    
    // 处理注释数据
    processAnnotations(data.geneid_result || [])
    
    jbrowse_url.value = data.jbrowse_url || ''
    
    // 设置GFF数据
    gffData.value = data.gff_data || data.gene_info_result || []
    hasGffData.value = gffData.value.length > 0
    // 重置页码到第一页
    currentPage.value = 1
    
    // 存储基因详细信息到 navigationStore 的 geneDetail 中
    if (result.value) {
      navigationStore.setNavigationData('geneDetail', {
        results: {
          ...result.value,
          jbrowse_url: jbrowse_url.value,
          gff_data: gffData.value
        },
        dbId: gene_id
      })
      console.log('基因数据已存储到 navigationStore:', result.value.IDs)
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

// 生命周期钩子
onMounted(() => {
  // 首先检查 URL 参数
  const db_id = route.query.db_id as string
  const gene_id = route.query.gene_id as string
  const genome_id = route.query.genome_id as string
  
  console.log('URL params:', { db_id, gene_id, genome_id })
  
  // 然后检查 navigationStore 中的基因详细信息
  const geneDetailData = navigationStore.getNavigationData('geneDetail')
  console.log('从 navigationStore 获取基因详细信息:', geneDetailData)
  
  if (db_id && !hasFetched.value) {
    // 如果有 URL 参数，使用参数获取数据
    hasFetched.value = true
    fetchGeneData(db_id)
    // 加载基因表达量数据
    if (gene_id) {
      loadExpressionData(gene_id, genome_id)
    }
  } else if (gene_id && genome_id && !hasFetched.value) {
    // 如果有基因ID和基因组ID参数，使用这些参数获取数据
    hasFetched.value = true
    fetchGeneDataWithGeneId(gene_id, genome_id)
    // 加载基因表达量数据
    loadExpressionData(gene_id, genome_id)
  } else if (geneDetailData && geneDetailData.results) {
    // 如果没有 URL 参数但有导航数据，使用导航数据
    console.log('从 navigationStore 加载基因数据:', geneDetailData.results.IDs)
    
    // 直接使用导航数据
    result.value = geneDetailData.results
    
    // 处理注释数据
    processAnnotations([])
    
    // 设置 jbrowse_url
    jbrowse_url.value = geneDetailData.results.jbrowse_url || ''
    
    // 设置 GFF 数据
    gffData.value = geneDetailData.results.gff_data || []
    hasGffData.value = gffData.value.length > 0
    
    // 重置页码到第一页
    currentPage.value = 1
    
    // 加载基因表达量数据
    const geneId = geneDetailData.results.IDs
    const genomeIdFromResult = geneDetailData.results.genome_id || route.query.genome_id
    if (geneId) {
      loadExpressionData(geneId, genomeIdFromResult as string)
    }
    
    // 标记为已获取
    hasFetched.value = true
  } else {
    // 既没有 URL 参数也没有导航数据
    errorMessage.value = 'Database ID not provided'
  }
})
</script>

<style scoped>
/* 自定义样式 */
.container {
  max-width: 1300px;
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

/* 结果容器样式 */
.result-container {
  position: relative;
}

/* 锚点侧边栏样式 */
.anchor-sidebar {
  position: fixed;
  left: 10px;
  top: 280px;
  width: 140px;
  z-index: 200;
}

/* 主内容区域样式 */
.main-content {
  margin-left: 0;
  width: 100%;
}

/* 锚点导航样式 */
:deep(.el-anchor) {
  background: #fff;
  padding: 8px;
  border-radius: 4px;
  box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.1);
  font-size: 24px;
}

:deep(.el-anchor-link) {
  padding: 4px 0;
}

:deep(.el-anchor-link__title) {
  font-size: 18px;
}

:deep(.el-anchor__marker) {
  display: none;
}

/* 响应式布局：小屏幕时隐藏锚点 */
@media (max-width: 1400px) {
  .anchor-sidebar {
    display: none;
  }
}
</style>