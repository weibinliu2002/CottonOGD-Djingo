<template>
  <div class="container mt-4">
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
      <!-- 顶部区域：基因信息 + 功能注释交集 -->
      <el-row :gutter="20" class="mb-6">
        <!-- 左上：基因信息 -->
        <el-col :span="14">
          <gene-info-card 
            :gene-data="result" 
            :title="t('gene_basic_information')"
            class="h-full"
          />
        </el-col>
        
        <!-- 右上：功能注释交集 -->
        <el-col :span="10">
          <el-card title="Function" class="h-full">
            <template #header>
              <h3 class="card-title">Function</h3>
            </template>
            <div class="function-content">
              <!-- GO注释交集 -->
              <div v-if="intersectionAnnotations.go.length > 0" class="annotation-section">
                <div class="section-header">
                  <el-tag type="primary" size="small">GO</el-tag>
                </div>
                <ul class="annotation-list">
                  <li 
                    v-for="(item, index) in intersectionAnnotations.go.slice(0, 5)" 
                    :key="'go-' + index"
                    class="annotation-list-item"
                  >
                    <a 
                      :href="`https://www.ebi.ac.uk/QuickGO/term/${item.id}`" 
                      target="_blank"
                      class="annotation-link"
                    >
                      {{ item.id }}: {{ item.term }}
                    </a>
                  </li>
                  <li v-if="intersectionAnnotations.go.length > 5" class="annotation-list-item text-muted text-sm">
                    +{{ intersectionAnnotations.go.length - 5 }} more
                  </li>
                </ul>
              </div>
              
              <!-- KEGG注释交集 -->
              <div v-if="intersectionAnnotations.kegg.length > 0" class="annotation-section">
                <div class="section-header">
                  <el-tag type="success" size="small">KEGG</el-tag>
                </div>
                <ul class="annotation-list">
                  <li 
                    v-for="(item, index) in intersectionAnnotations.kegg.slice(0, 5)" 
                    :key="'kegg-' + index"
                    class="annotation-list-item"
                  >
                    <a 
                      :href="`https://www.genome.jp/dbget-bin/www_bget?ko+${item.id}`" 
                      target="_blank"
                      class="annotation-link"
                    >
                      {{ item.id }}: {{ item.description }}
                    </a>
                  </li>
                  <li v-if="intersectionAnnotations.kegg.length > 5" class="annotation-list-item text-muted text-sm">
                    +{{ intersectionAnnotations.kegg.length - 5 }} more
                  </li>
                </ul>
              </div>
              
              <!-- 其他注释交集 -->
              <div v-if="intersectionAnnotations.other.length > 0" class="annotation-section">
                <div class="section-header">
                  <el-tag type="info" size="small">Other</el-tag>
                </div>
                <ul class="annotation-list">
                  <li 
                    v-for="(item, index) in intersectionAnnotations.other.slice(0, 5)" 
                    :key="'other-' + index"
                    class="annotation-list-item"
                  >
                    <span class="annotation-text">{{ item.annotation }}</span>
                  </li>
                  <li v-if="intersectionAnnotations.other.length > 5" class="annotation-list-item text-muted text-sm">
                    +{{ intersectionAnnotations.other.length - 5 }} more
                  </li>
                </ul>
              </div>
              
              <!-- 无数据提示 -->
              <div v-if="isEmptyAnnotations" class="empty-state">
                <el-empty description="No annotation data available" />
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 下方区域：功能模块导航 -->
      <el-card class="mb-4">
        <template #header>
          <div class="nav-tabs-container">
            <el-tabs 
              v-model="activeTab" 
              type="card"
              class="nav-tabs"
            >
              <el-tab-pane label="JBrowse" name="jbrowse" v-if="jbrowse_url">
                <template #label>
                  <span class="tab-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <line x1="9" y1="9" x2="15" y2="9" />
                      <line x1="9" y1="15" x2="15" y2="15" />
                    </svg>
                  </span>
                  JBrowse
                </template>
              </el-tab-pane>
              <el-tab-pane label="GFF" name="gff" v-if="hasGffData">
                <template #label>
                  <span class="tab-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <polyline points="10 9 9 9 8 9" />
                    </svg>
                  </span>
                  GFF
                </template>
              </el-tab-pane>
              <el-tab-pane label="Expression" name="expression" v-if="expressionData.length > 0">
                <template #label>
                  <span class="tab-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M18 20V10" />
                      <path d="M12 20V4" />
                      <path d="M6 20v-6" />
                    </svg>
                  </span>
                  Expression
                </template>
              </el-tab-pane>
              <el-tab-pane label="Sequence" name="sequence">
                <template #label>
                  <span class="tab-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="4 7 4 4 20 4 20 7" />
                      <line x1="9" y1="20" x2="15" y2="20" />
                      <line x1="12" y1="4" x2="12" y2="20" />
                    </svg>
                  </span>
                  Sequence
                </template>
              </el-tab-pane>
              <el-tab-pane label="GO annotation" name="goAnnotation" v-if="goAnnotationData.length > 0">
                  <template #label>
                  <span class="tab-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <polyline points="10 9 9 9 8 9" />
                    </svg>
                  </span>
                  GO annotation
                </template>
              </el-tab-pane>
              <el-tab-pane label="KEGG annotation" name="keggAnnotation" v-if="keggAnnotationData.length > 0">
                  <template #label>
                  <span class="tab-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <polyline points="10 9 9 9 8 9" />
                    </svg>
                  </span>
                  KEGG annotation
                </template>
              </el-tab-pane>
              <el-tab-pane label="Annotations" name="annotations" v-if="Object.keys(annotations).length > 0">
                <template #label>
                  <span class="tab-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M7 21h10" />
                      <path d="M17 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z" />
                      <path d="M9 7h6" />
                      <path d="M9 11h6" />
                      <path d="M9 15h6" />
                    </svg>
                  </span>
                  Annotations
                </template>
              </el-tab-pane>
            </el-tabs>
          </div>
        </template>
        
        <!-- JBrowse 内容 -->
        <div v-if="activeTab === 'jbrowse'" class="tab-content">
          <div class="jbrowse-container">
            <iframe :src="jbrowse_url" class="jbrowse-iframe"></iframe>
          </div>
        </div>
        
        <!-- GFF 内容 -->
        <div v-if="activeTab === 'gff'" class="tab-content">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <span class="table-info">
              Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, gffData.length) }} of {{ gffData.length }} entries
            </span>
            <div>
              <el-button type="success" size="small" @click="downloadGff('txt')">Download as TXT</el-button>
              <el-button type="success" size="small" class="ml-2" @click="downloadGff('gff')">Download as GFF</el-button>
            </div>
          </div>
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
            <el-table-column prop="Strand" label="Strand" min-width="50" />
            <el-table-column prop="phase" label="Phase" min-width="50" />
            <el-table-column prop="attributes" label="Attributes" min-width="200" />
          </el-table>
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="currentTranscriptGffData.length"
            class="mt-3"
          />
        </div>
        
        <!-- Expression 内容 -->
        <div v-if="activeTab === 'expression'" class="tab-content">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <span class="table-info">Gene Expression Data</span>
            <el-button type="success" size="small" @click="downloadExpressionData">
              {{ t('download_data') }}
            </el-button>
          </div>
          <el-table
            :data="expressionData"
            style="width: 100%"
            stripe
            border
          >
            <el-table-column label="Gene ID" width="180">
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
        
        <!-- Sequence 内容 -->
        <div v-if="activeTab === 'sequence'" class="tab-content">
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
        
          <div class="mb-3 mt-4">
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
        
        <!-- GO Annotation 内容 -->
        <div v-if="activeTab === 'goAnnotation'" class="tab-content">
          <div class="mb-4">
            <el-table :data="goAnnotationData" border stripe max-height="600">
              <el-table-column label="GO ID" width="150">
                <template #default="scope">
                  <a :href="`https://www.ebi.ac.uk/QuickGO/term/${scope.row.id}`" target="_blank" rel="noopener noreferrer">
                    {{ scope.row.id }}
                  </a>
                </template>
              </el-table-column>
              <el-table-column prop="type" label="GO Type" width="120" />
              <el-table-column prop="term" label="Term" />
            </el-table>
          </div>
        </div>
        
        <!-- KEGG Annotation 内容 -->
        <div v-if="activeTab === 'keggAnnotation'" class="tab-content">
          <div class="mb-4">
            <el-table :data="keggAnnotationData" border stripe max-height="600">
              <el-table-column label="KEGG ID" width="150">
                <template #default="scope">
                  <a :href="`https://www.genome.jp/dbget-bin/www_bget?ko+${scope.row.id}`" target="_blank" rel="noopener noreferrer">
                    {{ scope.row.id }}
                  </a>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="Description" />
            </el-table>
          </div>
        </div>
        
        <!-- Annotations 内容 -->
        <div v-if="activeTab === 'annotations'" class="tab-content">
          <!-- 其他注释类型 -->
          <div v-for="(annotationList, annotationType) in annotations" :key="annotationType" class="mb-4">
            <div v-if="annotationList.length > 0">
              <h4 class="annotation-title">
                <el-tag type="info" size="small">{{ String(annotationType).replace(/_/g, ' ') }}</el-tag>
              </h4>
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
          
          <!-- 如果没有其他注释类型 -->
          <div v-if="Object.keys(annotations).length === 0" class="text-muted">
            No additional annotations available.
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
    />
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
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
  annotation_id?: string
  annotation_source?: string
  geneid_id?: string
  genome_id?: string
  id_id?: string
  id?: string
  type?: string
  go_id?: string
  go_type?: string
  go_description?: string
  kegg_id?: string
  kegg_type?: string
  kegg_description?: string
}

interface GffItem {
  seqid?: string
  source?: string
  type?: string
  start?: number | string
  end?: number | string
  score?: string
  strand?: string
  phase?: string
  attributes?: string
}

interface Result {
  IDs: string
  geneid?: string
  id?: string
  seqid?: string
  start?: number | string
  end?: number | string
  strand?: string
  gene_seq?: string
  mrna_seq?: string
  mrna_transcripts?: any[]
  upstream_seq?: string
  downstream_seq?: string
  cdna_seq?: string
  cds_seq?: string
  protein_seq?: string
  genome_id?: string
  gene_go_result?: any[]
  gene_kegg_result?: any[]
  geneid_result?: any[]
}

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

// 当前激活的标签页
const activeTab = ref('sequence')

// 计算是否有序列信息
const has_sequences = computed(() => {
  if (!result.value) return false
  const hasDirectSequences = !!(result.value.gene_seq || result.value.mrna_seq || result.value.upstream_seq || result.value.downstream_seq || result.value.cdna_seq || result.value.cds_seq || result.value.protein_seq)
  const hasTranscriptSequences = !!(result.value.mrna_transcripts && result.value.mrna_transcripts.length > 0)
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
const upstreamLength = ref(500)
const downstreamLength = ref(500)

// 基因表达量数据
const expressionData = ref<any[]>([])
const expressionTissues = ref<string[]>([])
const expressionLoading = ref(false)

// 下载相关
const downloadDialogVisible = ref(false)
const downloadForm = ref({
  dataTypes: ['genomic', 'mrna', 'cdna', 'cds', 'protein'],
  format: 'fasta'
})

// 计算属性
const parsedGoAnnotations = computed(() => {
  const goAnnotations = result.value?.gene_go_result || []
  const parsed: { type: string; term: string; id: string }[] = []
  
  goAnnotations.forEach((item: any) => {
    if (item && item.go_id) {
      // 如果有完整的GO信息，使用完整信息
      if (item.go_type && item.go_description) {
        parsed.push({
          type: item.go_type,
          term: item.go_description,
          id: item.go_id
        })
      } else {
        // 如果只有go_id，只显示GO ID
        parsed.push({
          type: 'GO',
          term: 'Click to view details',
          id: item.go_id
        })
      }
    }
  })
  
  return parsed
})

// 解析KEGG注释数据
const parsedKeggAnnotations = computed(() => {
  const keggAnnotations = result.value?.gene_kegg_result || []
  const parsed: { id: string; description: string }[] = []
  
  keggAnnotations.forEach((item: any) => {
    if (item && item.kegg_id) {
      // 如果有完整的KEGG信息，使用完整信息
      if (item.kegg_description) {
        parsed.push({
          id: item.kegg_id,
          description: item.kegg_description
        })
      } else {
        // 如果只有kegg_id，只显示KEGG ID
        parsed.push({
          id: item.kegg_id,
          description: 'Click to view details'
        })
      }
    }
  })
  
  return parsed
})

// 模板中使用的GO注释数据
const goAnnotationData = computed(() => {
  return parsedGoAnnotations.value
})

// 模板中使用的KEGG注释数据
const keggAnnotationData = computed(() => {
  return parsedKeggAnnotations.value
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
  return currentTranscriptGffData.value.slice(start, end)
})

// 当前转录本的GFF数据
const currentTranscriptGffData = computed(() => {
  if (!gffData.value || gffData.value.length === 0) {
    return []
  }
  
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
  
  const filtered = gffData.value.filter((item: GffItem) => {
    if (item.type && item.type.toLowerCase() === 'gene') {
      return true
    }
    if (item.attributes && currentId) {
      return item.attributes.indexOf(currentId) !== -1
    }
    return false
  })
  
  return filtered.sort((a: GffItem, b: GffItem) => {
    return (Number(a.start) || 0) - (Number(b.start) || 0)
  })
})

// 注释交集数据
const intersectionAnnotations = computed(() => {
  const go = parsedGoAnnotations.value.slice(0, 10)
  const kegg = parsedKeggAnnotations.value.slice(0, 10)
  
  const other: Annotation[] = []
  for (const [type, items] of Object.entries(annotations.value)) {
    if (type !== 'GO_annotation' && type !== 'KEGG_annotation' && items.length > 0) {
      other.push(...items.slice(0, 5))
    }
  }
  
  return { go, kegg, other }
})

// 是否为空注释
const isEmptyAnnotations = computed(() => {
  return intersectionAnnotations.value.go.length === 0 && 
         intersectionAnnotations.value.kegg.length === 0 && 
         intersectionAnnotations.value.other.length === 0
})

// 方法
const handleLengthChange = (eventData: { upstreamLength: number; downstreamLength: number }) => {
  const { upstreamLength: newUpstream, downstreamLength: newDownstream } = eventData
  upstreamLength.value = newUpstream
  downstreamLength.value = newDownstream
  geneSearchStore.clearSequenceCache()
}

const processAnnotations = (geneidResult: any[]) => {
  const newAnnotations: Record<string, Annotation[]> = {}
  if (Array.isArray(geneidResult)) {
    geneidResult.forEach(item => {
      const annotationSource = item.annotation_source || item.annoation_source || item.type || 'other'
      let annotationText = item.annotation
      
      // 如果有GO或KEGG特定字段，构建完整的注释文本
      if (item.go_id || item.go_type || item.go_description) {
        annotationText = `${item.go_type || ''}: ${item.go_description || ''} (${item.go_id || ''})`.trim()
      } else if (item.kegg_id || item.kegg_type || item.kegg_description) {
        annotationText = `${item.kegg_type || ''}: ${item.kegg_description || ''} (${item.kegg_id || ''})`.trim()
      }
      
      if (annotationText) {
        if (!newAnnotations[annotationSource]) {
          newAnnotations[annotationSource] = []
        }
        newAnnotations[annotationSource].push({
          annotation: annotationText,
          annotation_id: item.annotation_id || item.annoation_id,
          annotation_source: annotationSource,
          geneid_id: item.geneid_id,
          genome_id: item.genome_id,
          id_id: item.id_id,
          id: item.id,
          type: item.type,
          go_id: item.go_id,
          go_type: item.go_type,
          go_description: item.go_description,
          kegg_id: item.kegg_id,
          kegg_type: item.kegg_type,
          kegg_description: item.kegg_description
        })
      }
    })
  }
  annotations.value = newAnnotations
}

const fetchGeneData = async (db_id: string) => {
  const loadingTimeout = setTimeout(() => {
    isLoading.value = true
  }, 300)
  
  errorMessage.value = ''
  selectedTranscriptIndex.value = 0
  
  try {
    const navigationData = navigationStore.getNavigationData('geneDetail')
    const needFetchFromBackend = !navigationData || !navigationData.results || !navigationData.results.jbrowse_url
    
    if (navigationData && navigationData.results && !needFetchFromBackend) {
      clearTimeout(loadingTimeout)
      result.value = navigationData.results
      
      if (navigationData.results.geneid_result && Array.isArray(navigationData.results.geneid_result)) {
        processAnnotations(navigationData.results.geneid_result)
      } else {
        processAnnotations([])
      }
      
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
      
      jbrowse_url.value = navigationData.results.jbrowse_url || ''
      gffData.value = navigationData.results.gff_data || []
      hasGffData.value = gffData.value.length > 0
      currentPage.value = 1
      
      const geneId = result.value?.IDs
      if (geneId) {
        loadExpressionData(geneId, undefined, db_id)
      }
    } else {
      console.log('=== 开始获取基因数据 ===')
      console.log('db_id:', db_id)
      
      try {
        const response = await httpInstance.post('/CottonOGD_api/geneid_result/', { db_id: db_id })
        console.log('response 对象:', response)
        console.log('response 类型:', typeof response)
        
        const data = response.data !== undefined ? response.data : response
        console.log('数据对象:', data)
        console.log('数据类型:', typeof data)
        console.log('data.results 存在:', data && !!data.results)
        
        if (data && data.results) {
          console.log('开始解析JSON:', data.results)
          try {
            result.value = JSON.parse(data.results)
            console.log('JSON解析成功:', result.value)
            console.log('result.value.geneid_result:', result.value.geneid_result)
            console.log('result.value.gene_go_result:', result.value.gene_go_result)
            console.log('result.value.gene_kegg_result:', result.value.gene_kegg_result)
            console.log('parsedGoAnnotations:', parsedGoAnnotations.value)
            console.log('parsedKeggAnnotations:', parsedKeggAnnotations.value)
          } catch (parseError) {
            console.error('JSON解析失败:', parseError)
            throw new Error('Failed to parse gene data')
          }
          
          if (result.value.geneid_result && Array.isArray(result.value.geneid_result)) {
            processAnnotations(result.value.geneid_result)
          }
          
          if (result.value.gene_go_result && result.value.gene_go_result.length > 0) {
            const goAnnotations = result.value.gene_go_result.map((item: any) => ({
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
          
          if (result.value.gene_kegg_result && result.value.gene_kegg_result.length > 0) {
            const keggAnnotations = result.value.gene_kegg_result.map((item: any) => ({
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
          
          jbrowse_url.value = result.value.jbrowse_url || ''
        } else {
          throw new Error('No gene information found')
        }
        
        gffData.value = result.value.gff_data || []
        hasGffData.value = gffData.value.length > 0
        currentPage.value = 1
        
        if (result.value) {
          navigationStore.setNavigationData('geneDetail', {
            results: {
              ...result.value,
              jbrowse_url: jbrowse_url.value,
              gff_data: gffData.value
            },
            dbId: db_id
          })
          
          const geneId = result.value?.IDs
          if (geneId) {
            loadExpressionData(geneId, undefined, db_id)
          }
        }
        
        clearTimeout(loadingTimeout)
      } catch (requestError) {
        console.error('请求失败:', requestError)
        throw requestError
      }
                                
    }
  } catch (error: any) {
    clearTimeout(loadingTimeout)
    errorMessage.value = error.message
    console.error('获取基因数据错误:', error)
  } finally {
    isLoading.value = false
  }
}

const loadExpressionData = async (geneId: string, tissue?: string, db_id?: string) => {
  console.log('=== 开始加载Expression数据 ===')
  console.log('geneId:', geneId, 'tissue:', tissue, 'db_id:', db_id)
  
  expressionLoading.value = true
  try {
    const response = await httpInstance.get('/CottonOGD_api/gene_expression/', {
      params: {
        gene_id: geneId,
        tissue: tissue || '',
        db_id: db_id || ''
      }
    })
    console.log('Expression响应:', response)
    
    const data = response.data !== undefined ? response.data : response
    console.log('Expression数据:', data)
    
    if (data && data.results) {
      expressionData.value = data.results
      console.log('Expression数据设置成功:', expressionData.value.length, '条')
      if (data.results.length > 0) {
        const firstRow = data.results[0]
        expressionTissues.value = Object.keys(firstRow).filter(key => 
          key !== 'geneid' && key !== 'genome_id' && key !== 'id'
        )
        console.log('Expression tissues:', expressionTissues.value)
      }
    } else {
      console.log('Expression数据为空')
    }
  } catch (error) {
    console.error('获取基因表达数据失败:', error)
  } finally {
    expressionLoading.value = false
  }
}

const switchTranscript = (index: number) => {
  selectedTranscriptIndex.value = index
}

const showSequenceModal = (title: string, content: string, seqType: string, geneId: string) => {
  modalTitle.value = title
  modalContent.value = content
  currentSeqType.value = seqType
  currentGeneId.value = geneId
  showModal.value = true
}

const handleShowSequence = async (eventData: { type: string; title: string; content: string; id: string }) => {
  const { type, title, content, id } = eventData

  const realGeneId = result.value?.IDs || ''
  const mrnaid = currentTranscript.value?.id || id
  const upLen = upstreamLength.value
  const downLen = downstreamLength.value

  try {
    let fastaContent = ''
    let seq = content
    let isFromContent = true
    
    if (!seq) {
      isFromContent = false
      seq = await geneSearchStore.fetchSequence(realGeneId, mrnaid, type, upLen, downLen)
    }
    
    if (seq && seq !== 'Sequence not found' && seq !== 'N/A') {
      const headerId = type === 'genomic' ? realGeneId : mrnaid
      
      let processedSeq = seq
      if (type === 'upstream') {
        processedSeq = seq.slice(20000 - upLen, seq.length)
      } else if (type === 'downstream') {
        processedSeq = seq.slice(0, downLen)
      }
      
      const lengthInfo = (type === 'upstream' || type === 'downstream') ? ` (${processedSeq.length}bp)` : ''
      fastaContent = `>${headerId} ${type}${lengthInfo}\n${processedSeq}\n`
    } else {
      fastaContent = seq
    }

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

const showDownloadDialog = () => {
  downloadDialogVisible.value = true
}

const showCurrentTranscriptDownloadDialog = () => {
  downloadDialogVisible.value = true
}

const downloadSelectedData = () => {
  const dataTypes = downloadForm.value.dataTypes
  const format = downloadForm.value.format
  let content = ''
  
  if (!result.value) return
  
  if (dataTypes.includes('genomic') && result.value.gene_seq) {
    content += `>${result.value.IDs} genomic\n${result.value.gene_seq}\n\n`
  }
  if (dataTypes.includes('mrna') && result.value.mrna_seq) {
    content += `>${result.value.IDs} mrna\n${result.value.mrna_seq}\n\n`
  }
  if (dataTypes.includes('upstream') && result.value.upstream_seq) {
    content += `>${result.value.IDs} upstream\n${result.value.upstream_seq}\n\n`
  }
  if (dataTypes.includes('downstream') && result.value.downstream_seq) {
    content += `>${result.value.IDs} downstream\n${result.value.downstream_seq}\n\n`
  }
  if (dataTypes.includes('cdna') && result.value.cdna_seq) {
    content += `>${result.value.IDs} cdna\n${result.value.cdna_seq}\n\n`
  }
  if (dataTypes.includes('cds') && result.value.cds_seq) {
    content += `>${result.value.IDs} cds\n${result.value.cds_seq}\n\n`
  }
  if (dataTypes.includes('protein') && result.value.protein_seq) {
    content += `>${result.value.IDs} protein\n${result.value.protein_seq}\n\n`
  }
  
  downloadFile(content, `${result.value.IDs}_sequences.${format}`, format === 'fasta' ? 'text/fasta' : 'text/plain')
  downloadDialogVisible.value = false
}

const downloadFile = (content: string, filename: string, type: string) => {
  const blob = new Blob([content], { type: type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const downloadGff = (format: string) => {
  let content = ''
  if (format === 'gff') {
    content = '##gff-version 3\n'
    gffData.value.forEach(item => {
      content += `${item.seqid || '.'}\t${item.source || '.'}\t${item.type || '.'}\t${item.start || '.'}\t${item.end || '.'}\t${item.score || '.'}\t${item.strand || '.'}\t${item.phase || '.'}\t${item.attributes || '.'}\n`
    })
  } else {
    content = 'seqid\tsource\ttype\tstart\tend\tscore\tstrand\tphase\tattributes\n'
    gffData.value.forEach(item => {
      content += `${item.seqid || ''}\t${item.source || ''}\t${item.type || ''}\t${item.start || ''}\t${item.end || ''}\t${item.score || ''}\t${item.strand || ''}\t${item.phase || ''}\t${item.attributes || ''}\n`
    })
  }
  downloadFile(content, `gene_gff.${format}`, 'text/plain')
}

const downloadExpressionData = () => {
  if (expressionData.value.length === 0) return
  
  let content = 'Gene ID\t' + expressionTissues.value.join('\t') + '\n'
  expressionData.value.forEach(row => {
    const values = expressionTissues.value.map(tissue => row[tissue] !== undefined ? row[tissue].toFixed(4) : '-')
    content += `${row.geneid}\t${values.join('\t')}\n`
  })
  downloadFile(content, 'gene_expression.txt', 'text/plain')
}

const router = useRouter()
const route = useRoute()

onMounted(() => {
  const db_id = route.query.db_id as string || route.params.id as string
  if (db_id) {
    fetchGeneData(db_id)
  }
})
</script>

<style scoped>
.result-container {
  position: relative;
}

.function-content {
  max-height: 400px;
  overflow-y: auto;
}

.annotation-section {
  margin-bottom: 16px;
}

.section-header {
  margin-bottom: 8px;
}

.annotation-link {
  color: #409eff;
  text-decoration: none;
  font-size: 14px;
}

.annotation-link:hover {
  text-decoration: underline;
}

.annotation-text {
  font-size: 14px;
  color: #666;
}

.annotation-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.annotation-list-item {
  padding: 4px 0;
  font-size: 14px;
  line-height: 1.5;
}

.empty-state {
  padding: 20px;
  text-align: center;
}

.nav-tabs-container {
  width: 100%;
}

.nav-tabs {
  border-bottom: none;
}

.tab-icon {
  margin-right: 4px;
}

.tab-content {
  padding: 16px 0;
}

.jbrowse-container {
  width: 100%;
  height: 400px;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
}

.jbrowse-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.annotation-title {
  margin-bottom: 12px;
}

.table-info {
  font-size: 14px;
  color: #666;
}
</style>