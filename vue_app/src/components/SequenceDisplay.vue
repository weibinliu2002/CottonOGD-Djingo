<template>
  <div class="sequence-display-component">
    <!-- 通用按钮模式：显示各个序列类型的按钮，所有按钮在一行 -->
    <div v-if="displayMode === 'buttons' || displayMode === 'full'" class="d-flex flex-wrap gap-3 mb-4">
      <!-- 基因组序列 -->
      <div class="text-center flex-shrink-0">
        <h4 class="h6 mb-2">Genomic</h4>
        <button class="btn btn-sm btn-info" @click="handleButtonClick('genomic', 'Genomic Sequence', getSequence('genomic'), getGeneId())">
          {{ hasSequences('genomic') ? 'Show Sequence' : 'Show Sequence' }}
        </button>
      </div>
      
      <!-- mRNA序列 -->
      <div class="text-center flex-shrink-0">
        <h4 class="h6 mb-2">mRNA</h4>
        <button class="btn btn-sm btn-info" @click="handleButtonClick('mrna', 'mRNA Sequence', getSequence('mrna'), getGeneId())">
          {{ hasSequences('mrna') ? 'Show Sequence' : 'Show Sequence' }}
        </button>
      </div>
    
      <!-- 上游序列 -->            
      <div class="text-center flex-shrink-0">
        <h4 class="h6 mb-2">Upstream</h4>              
        <button class="btn btn-sm btn-info" @click="handleButtonClick('upstream', 'Upstream Sequence', getSequence('upstream'), getGeneId())">
          {{ hasSequences('upstream') ? 'Show Sequence' : 'Show Sequence' }}
        </button>
      </div>
            
      <!-- 下游序列 -->            
      <div class="text-center flex-shrink-0">              
        <h4 class="h6 mb-2">Downstream</h4>              
        <button class="btn btn-sm btn-info" @click="handleButtonClick('downstream', 'Downstream Sequence', getSequence('downstream'), getGeneId())">
          {{ hasSequences('downstream') ? 'Show Sequence' : 'Show Sequence' }}
        </button>
      </div>
            
      <!-- cDNA序列 -->
      <div class="text-center flex-shrink-0">              
        <h4 class="h6 mb-2">cDNA</h4>              
        <button class="btn btn-sm btn-info" @click="handleButtonClick('cdna', 'cDNA Sequence', getSequence('cdna'), getGeneId())">
          {{ hasSequences('cdna') ? 'Show Sequence' : 'Show Sequence' }}
        </button>
      </div>
      
      <!-- CDS序列 -->
      <div class="text-center flex-shrink-0">
        <h4 class="h6 mb-2">CDS</h4>
        <button class="btn btn-sm btn-info" @click="handleButtonClick('cds', 'CDS Sequence', getSequence('cds'), getGeneId())">
          {{ hasSequences('cds') ? 'Show Sequence' : 'Show Sequence' }}
        </button>
      </div>
      
      <!-- 蛋白序列 -->
      <div class="text-center flex-shrink-0">
        <h4 class="h6 mb-2">Protein</h4>
        <button class="btn btn-sm btn-info" @click="handleButtonClick('protein', 'Protein Sequence', getSequence('protein'), getGeneId())">
          {{ hasSequences('protein') ? 'Show Sequence' : 'Show Sequence' }}
        </button>
      </div>
    </div>
    
    <!-- 上下游长度选择器 -->
    <div v-if="displayMode === 'buttons' || displayMode === 'full'" class="mb-4 d-flex justify-content-start">
      <div class="d-flex gap-3 align-items-end w-25">
        <div class="flex-shrink-0 flex-grow-1">
          <label for="upstreamLengthSelect" class="form-label form-label-sm text-center">Upstream</label>
          <select class="form-select form-select-sm" id="upstreamLengthSelect" v-model.number="selectedUpstreamLength">
            <option v-for="option in lengthOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>
        <div class="flex-shrink-0 flex-grow-1">
          <label for="downstreamLengthSelect" class="form-label form-label-sm text-center">Downstream</label>
          <select class="form-select form-select-sm" id="downstreamLengthSelect" v-model.number="selectedDownstreamLength">
            <option v-for="option in lengthOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>
      </div>
    </div>
 
    <!-- full模式特殊功能：按照序列类型分组，以FASTA格式展示，默认隐藏 -->
    <div v-if="displayMode === 'full'">
      <!--button class="btn btn-sm btn-secondary" @click="toggleSequenceDisplay">
        {{ showSequences ? '隐藏序列' : '显示序列' }}
      </button>-->
      
      <div v-if="showSequences" class="mt-6">
        <!-- 序列类型配置 -->
        <div v-for="(seqType, index) in sequenceTypes" :key="index" class="mb-6">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h4>{{ seqType.title }}</h4>
            <div>
              <button class="btn btn-sm btn-primary me-2" @click="$emit('download-all', seqType.key)">下载全部</button>
              <button class="btn btn-sm btn-secondary" @click="$emit('copy-all', seqType.key)">复制全部</button>
            </div>
          </div>
          
          <!-- 以FASTA格式展示该类型的所有序列 -->
          <div class="bg-light p-4 rounded overflow-y-auto" style="max-height: 300px; white-space: pre-wrap; font-family: monospace; text-align: left;">
            <!-- 遍历所有基因，生成FASTA格式序列 -->
            <template v-for="(result, geneIndex) in results" :key="`${seqType.key}-${geneIndex}`">
              <!-- 根据序列类型获取对应序列 -->
              <template v-if="seqType.key === 'genomic' && result.gene_seq && result.gene_seq !== 'N/A'">
                &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} genomic
                <br>{{ result.gene_seq }}
                <br><br>
              </template>
              
              <!-- mRNA序列：显示所有转录本 -->
              <template v-if="seqType.key === 'mrna'">
                <!-- 显示第一个转录本（默认序列） -->
               <!-- <template v-if="result.mrna_seq && result.mrna_seq !== 'N/A'">
                  &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} mrna (默认)
                  <br>{{ result.mrna_seq }}
                  <br><br>
                </template>-->
                
                <!-- 显示所有转录本 -->
                <template v-if="result.mrna_transcripts && result.mrna_transcripts.length > 0">
                  <template v-for="(transcript, transIndex) in result.mrna_transcripts" :key="`${result.IDs}-${transIndex}`">
                    <template v-if="transcript.mrna_seq && transcript.mrna_seq !== 'N/A'">
                      &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} mrna (转录本 {{ transIndex + 1 }}: {{ transcript.id }})
                      <br>{{ transcript.mrna_seq }}
                      <br><br>
                    </template>
                  </template>
                </template>
              </template>

              <!-- 上游序列 -->
              <template v-else-if="seqType.key === 'upstream'">
                <!-- 显示第一个转录本的上游序列（默认序列） -->
               <!-- <template v-if="result.upstream_seq && result.upstream_seq !== 'N/A'">
                  &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} upstream (默认, {{ selectedUpstreamLength }}bp)
                  <br>{{ result.upstream_seq.slice(0, selectedUpstreamLength) }}
                  <br><br>
                </template>-->
                
                <!-- 显示所有转录本的上游序列 -->
                <template v-if="result.mrna_transcripts && result.mrna_transcripts.length > 0">
                  <template v-for="(transcript, transIndex) in result.mrna_transcripts" :key="`${result.IDs}-${transIndex}`">
                    <template v-if="transcript.upstream_seq && transcript.upstream_seq !== 'N/A'">
                      &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} upstream (转录本 {{ transIndex + 1 }}: {{ transcript.id }}, {{ selectedUpstreamLength }}bp)
                      <br>{{ transcript.upstream_seq.slice(0, selectedUpstreamLength) }}
                      <br><br>
                    </template>
                  </template>
                </template>
              </template>

              <!-- 下游序列 -->
              <template v-else-if="seqType.key === 'downstream'">
                <!-- 显示第一个转录本的下游序列（默认序列） -->
                <!--<template v-if="result.downstream_seq && result.downstream_seq !== 'N/A'">
                  &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} downstream (默认, {{ selectedDownstreamLength }}bp)
                  <br>{{ result.downstream_seq.slice(0, selectedDownstreamLength) }}
                  <br><br>
                </template>-->
                
                <!-- 显示所有转录本的下游序列 -->
                <template v-if="result.mrna_transcripts && result.mrna_transcripts.length > 0">
                  <template v-for="(transcript, transIndex) in result.mrna_transcripts" :key="`${result.IDs}-${transIndex}`">
                    <template v-if="transcript.downstream_seq && transcript.downstream_seq !== 'N/A'">
                      &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} downstream (转录本 {{ transIndex + 1 }}: {{ transcript.id }}, {{ selectedDownstreamLength }}bp)
                      <br>{{ transcript.downstream_seq.slice(0, selectedDownstreamLength) }}
                      <br><br>
                    </template>
                  </template>
                </template>
              </template>

              <!-- cDNA序列 -->
              <template v-else-if="seqType.key === 'cdna'">
               <!-- 显示第一个转录本的cDNA序列（默认序列） -->
               <!--  <template v-if="result.cdna_seq && result.cdna_seq !== 'N/A' && result.cdna_seq !== 'unavailable'">
                  &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} cdna (默认)
                  <br>{{ result.cdna_seq }}
                  <br><br>
                </template>-->
                
                <!-- 显示所有转录本的cDNA序列 -->
                <template v-if="result.mrna_transcripts && result.mrna_transcripts.length > 0">
                  <template v-for="(transcript, transIndex) in result.mrna_transcripts" :key="`${result.IDs}-${transIndex}`">
                    <template v-if="transcript.cdna_seq && transcript.cdna_seq !== 'N/A' && transcript.cdna_seq !== 'unavailable'">
                      &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} cdna (转录本 {{ transIndex + 1 }}: {{ transcript.id }})
                      <br>{{ transcript.cdna_seq }}
                      <br><br>
                    </template>
                  </template>
                </template>
              </template>
              
              <!-- CDS序列 -->
              <template v-else-if="seqType.key === 'cds'">
                <!-- 显示第一个转录本的CDS序列（默认序列） -->
                <!--<template v-if="result.cds_seq && result.cds_seq !== 'N/A' && result.cds_seq !== '未找到CDS序列'">
                  &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} cds (默认)
                  <br>{{ result.cds_seq }}
                  <br><br>
                </template>-->
                
                <!-- 显示所有转录本的CDS序列 -->
                <template v-if="result.mrna_transcripts && result.mrna_transcripts.length > 0">
                  <template v-for="(transcript, transIndex) in result.mrna_transcripts" :key="`${result.IDs}-${transIndex}`">
                    <template v-if="transcript.cds_seq && transcript.cds_seq !== 'N/A' && transcript.cds_seq !== '未找到CDS序列'">
                      &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} cds (转录本 {{ transIndex + 1 }}: {{ transcript.id }})
                      <br>{{ transcript.cds_seq }}
                      <br><br>
                    </template>
                  </template>
                </template>
              </template>
              
              <!-- 蛋白序列 -->
              <template v-else-if="seqType.key === 'protein'">
                <!-- 显示第一个转录本的蛋白序列（默认序列） -->
               <!-- <template v-if="result.protein_seq && result.protein_seq !== 'N/A' && result.protein_seq !== '未找到蛋白序列'">
                  &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} protein (默认)
                  <br>{{ result.protein_seq }}
                  <br><br>
                </template>-->
                
                <!-- 显示所有转录本的蛋白序列 -->
                <template v-if="result.mrna_transcripts && result.mrna_transcripts.length > 0">
                  <template v-for="(transcript, transIndex) in result.mrna_transcripts" :key="`${result.IDs}-${transIndex}`">
                    <template v-if="transcript.protein_seq && transcript.protein_seq !== 'N/A' && transcript.protein_seq !== '未找到蛋白序列'">
                      &gt;{{ result.IDs || `基因 ${geneIndex + 1}` }} protein (转录本 {{ transIndex + 1 }}: {{ transcript.id }})
                      <br>{{ transcript.protein_seq }}
                      <br><br>
                    </template>
                  </template>
                </template>
              </template>
            </template>
            
            <!-- 如果该类型没有序列 -->
            <template v-if="!hasSequences(seqType.key)">
              <em>该类型没有可用序列</em>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  // 显示模式：'buttons'（显示按钮）或 'full'（显示完整序列）
  displayMode: {
    type: String,
    default: 'buttons',
    validator: (value) => ['buttons', 'full'].includes(value)
  },
  // 序列数据（buttons模式使用）
  gene_seq: String,
  mrna_seq: String,
  upstream_seq: String,
  downstream_seq: String,
  cdna_seq: String,
  cds_seq: String,
  protein_seq: String,
  gene_id: String,
  // 当前转录本（buttons模式使用，支持多个转录本）
  currentTranscript: {
    type: Object,
    default: null
  },
  // 结果列表（full模式使用）
  results: {
    type: Array,
    default: () => []
  },
  // 加载状态
  loading: {
    type: Boolean,
    default: false
  },
  // 上下游长度选择
  upstreamLength: {
    type: Number,
    default: 10000
  },
  downstreamLength: {
    type: Number,
    default: 10000
  }
})

const emit = defineEmits(['show-sequence', 'download-all', 'copy-all'])

// 定义序列类型配置
const sequenceTypes = [
  { key: 'genomic', title: '基因组序列' },
  { key: 'mrna', title: 'mRNA序列' },
  { key: 'upstream', title: '上游序列' },
  { key: 'downstream', title: '下游序列' },
  { key: 'cdna', title: 'cDNA序列' },
  { key: 'cds', title: 'CDS序列' },
  { key: 'protein', title: '蛋白序列' }
]

// 控制序列显示/隐藏的状态 - full模式默认显示
const showSequences = ref(false)
// 本地长度选择状态，默认使用props中的值，用户可以在前端调整
const selectedUpstreamLength = ref(props.upstreamLength)
const selectedDownstreamLength = ref(props.downstreamLength)
// 可选长度选项
const lengthOptions = [500, 1000, 2000, 3000, 4000, 5000, 10000]

// 切换序列显示/隐藏状态
const toggleSequenceDisplay = () => {
  showSequences.value = !showSequences.value
}

// 获取指定类型的序列内容
const getSequenceTypeContent = (seqType) => {
  let sequenceContent = ''
  
  // 遍历所有基因，收集该类型的序列
  props.results.forEach((result, geneIndex) => {
    const currentGeneId = result.IDs || `基因 ${geneIndex + 1}`
    
    // 根据序列类型获取对应序列
    if (seqType === 'genomic' && result.gene_seq && result.gene_seq !== 'N/A') {
      sequenceContent += `>${currentGeneId} genomic\n${result.gene_seq}\n\n`
    }
    
    // mRNA序列：显示所有转录本，使用转录本ID作为FASTA头部
    else if (seqType === 'mrna' && result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach((transcript, transIndex) => {
        if (transcript.mrna_seq && transcript.mrna_seq !== 'N/A') {
          sequenceContent += `>${transcript.id} mrna (基因: ${currentGeneId})\n${transcript.mrna_seq}\n\n`
        }
      })
    }
    
    // 上游序列：显示所有转录本，使用转录本ID作为FASTA头部
    else if (seqType === 'upstream' && result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach((transcript, transIndex) => {
        if (transcript.upstream_seq && transcript.upstream_seq !== 'N/A') {
          sequenceContent += `>${transcript.id} upstream (基因: ${currentGeneId}, ${selectedUpstreamLength.value}bp)\n${transcript.upstream_seq.slice(0, selectedUpstreamLength.value)}\n\n`
        }
      })
    }
    
    // 下游序列：显示所有转录本，使用转录本ID作为FASTA头部
    else if (seqType === 'downstream' && result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach((transcript, transIndex) => {
        if (transcript.downstream_seq && transcript.downstream_seq !== 'N/A') {
          sequenceContent += `>${transcript.id} downstream (基因: ${currentGeneId}, ${selectedDownstreamLength.value}bp)\n${transcript.downstream_seq.slice(0, selectedDownstreamLength.value)}\n\n`
        }
      })
    }
    
    // cDNA序列：显示所有转录本，使用转录本ID作为FASTA头部
    else if (seqType === 'cdna' && result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach((transcript, transIndex) => {
        if (transcript.cdna_seq && transcript.cdna_seq !== 'N/A' && transcript.cdna_seq !== 'unavailable') {
          sequenceContent += `>${transcript.id} cdna (基因: ${currentGeneId})\n${transcript.cdna_seq}\n\n`
        }
      })
    }
    
    // CDS序列：显示所有转录本，使用转录本ID作为FASTA头部
    else if (seqType === 'cds' && result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach((transcript, transIndex) => {
        if (transcript.cds_seq && transcript.cds_seq !== 'N/A' && transcript.cds_seq !== '未找到CDS序列') {
          sequenceContent += `>${transcript.id} cds (基因: ${currentGeneId})\n${transcript.cds_seq}\n\n`
        }
      })
    }
    
    // 蛋白序列：显示所有转录本，使用转录本ID作为FASTA头部
    else if (seqType === 'protein' && result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach((transcript, transIndex) => {
        if (transcript.protein_seq && transcript.protein_seq !== 'N/A' && transcript.protein_seq !== '未找到蛋白序列') {
          sequenceContent += `>${transcript.id} protein (基因: ${currentGeneId})\n${transcript.protein_seq}\n\n`
        }
      })
    }
  })
  
  return sequenceContent
}

// 下载指定类型的序列
const downloadSequenceType = (seqType) => {
  let sequenceContent = getSequenceTypeContent(seqType)
  
  if (!sequenceContent) {
    alert('该类型没有可用序列')
    return
  }
  
  // 创建下载链接
  const blob = new Blob([sequenceContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${seqType}_sequences.fasta`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 复制指定类型的序列
const copySequenceType = (seqType) => {
  let sequenceContent = getSequenceTypeContent(seqType)
  
  if (!sequenceContent) {
    alert('该类型没有可用序列')
    return
  }
  
  // 使用Clipboard API复制文本
  navigator.clipboard.writeText(sequenceContent).then(() => {
    alert('序列已复制到剪贴板')
  }).catch(err => {
    console.error('复制失败:', err)
    alert('复制失败，请手动复制序列内容')
  })
}

// 检查是否有该类型的序列
const hasSequences = (seqType) => {
  // 1. 检查直接传入的序列属性（单个基因情况）
  let hasDirectSeq = false
  if (seqType === 'genomic') {
    hasDirectSeq = props.gene_seq && props.gene_seq !== '' && props.gene_seq !== 'N/A'
  } else if (seqType === 'mrna') {
    hasDirectSeq = props.mrna_seq && props.mrna_seq !== '' && props.mrna_seq !== 'N/A'
  } else if (seqType === 'upstream') {
    hasDirectSeq = props.upstream_seq && props.upstream_seq !== '' && props.upstream_seq !== 'N/A'
  } else if (seqType === 'downstream') {
    hasDirectSeq = props.downstream_seq && props.downstream_seq !== '' && props.downstream_seq !== 'N/A'
  } else if (seqType === 'cdna') {
    hasDirectSeq = props.cdna_seq && props.cdna_seq !== '' && props.cdna_seq !== 'N/A' && props.cdna_seq !== 'unavailable'
  } else if (seqType === 'cds') {
    hasDirectSeq = props.cds_seq && props.cds_seq !== 'N/A' && props.cds_seq !== '未找到CDS序列'
  } else if (seqType === 'protein') {
    hasDirectSeq = props.protein_seq && props.protein_seq !== 'N/A' && props.protein_seq !== '未找到蛋白序列'
  }
  
  // 2. 检查currentTranscript中的序列（转录本情况）
  let hasTranscriptSeq = false
  if (props.currentTranscript) {
    if (seqType === 'mrna') {
      hasTranscriptSeq = props.currentTranscript.mrna_seq && props.currentTranscript.mrna_seq !== 'N/A'
    } else if (seqType === 'upstream') {
      hasTranscriptSeq = props.currentTranscript.upstream_seq && props.currentTranscript.upstream_seq !== 'N/A'
    } else if (seqType === 'downstream') {
      hasTranscriptSeq = props.currentTranscript.downstream_seq && props.currentTranscript.downstream_seq !== 'N/A'
    } else if (seqType === 'cdna') {
      hasTranscriptSeq = props.currentTranscript.cdna_seq && props.currentTranscript.cdna_seq !== 'N/A' && props.currentTranscript.cdna_seq !== 'unavailable'
    } else if (seqType === 'cds') {
      hasTranscriptSeq = props.currentTranscript.cds_seq && props.currentTranscript.cds_seq !== 'N/A' && props.currentTranscript.cds_seq !== '未找到CDS序列'
    } else if (seqType === 'protein') {
      hasTranscriptSeq = props.currentTranscript.protein_seq && props.currentTranscript.protein_seq !== 'N/A' && props.currentTranscript.protein_seq !== '未找到蛋白序列'
    }
  }
  
  // 3. 检查results数组中的序列（多基因情况）
  let hasResultsSeq = false
  if (props.results && props.results.length > 0) {
    hasResultsSeq = props.results.some(result => {
      if (seqType === 'genomic') {
        return result.gene_seq && result.gene_seq !== '' && result.gene_seq !== 'N/A'
      } else if (seqType === 'mrna') {
        return result.mrna_seq && result.mrna_seq !== '' && result.mrna_seq !== 'N/A'
      } else if (seqType === 'upstream') {
        return result.upstream_seq && result.upstream_seq !== '' && result.upstream_seq !== 'N/A'
      } else if (seqType === 'downstream') {
        return result.downstream_seq && result.downstream_seq !== '' && result.downstream_seq !== 'N/A'
      } else if (seqType === 'cdna') {
        return result.cdna_seq && result.cdna_seq !== '' && result.cdna_seq !== 'N/A' && result.cdna_seq !== 'unavailable'
      } else if (seqType === 'cds') {
        return result.cds_seq && result.cds_seq !== 'N/A' && result.cds_seq !== '未找到CDS序列'
      } else if (seqType === 'protein') {
        return result.protein_seq && result.protein_seq !== 'N/A' && result.protein_seq !== '未找到蛋白序列'
      }
      return false
    })
  }
  
  // 只要其中一种情况有序列，就返回true
  return hasDirectSeq || hasTranscriptSeq || hasResultsSeq
}

// 获取序列数据，优先从currentTranscript获取，其次从直接传入的序列属性获取，最后从results数组获取
const getSequence = (seqType) => {
  // 1. 优先从currentTranscript获取序列（转录本情况）
  if (props.currentTranscript) {
    if (seqType === 'mrna') return props.currentTranscript.mrna_seq
    if (seqType === 'upstream') return props.currentTranscript.upstream_seq ? props.currentTranscript.upstream_seq.slice(0, selectedUpstreamLength.value) : ''
    if (seqType === 'downstream') return props.currentTranscript.downstream_seq ? props.currentTranscript.downstream_seq.slice(0, selectedDownstreamLength.value) : ''
    if (seqType === 'cdna') return props.currentTranscript.cdna_seq
    if (seqType === 'cds') return props.currentTranscript.cds_seq
    if (seqType === 'protein') return props.currentTranscript.protein_seq
  }
  
  // 2. 从直接传入的序列属性获取（单个基因情况）
  if (seqType === 'genomic') return props.gene_seq
  if (seqType === 'mrna') return props.mrna_seq
  if (seqType === 'upstream') return props.upstream_seq ? props.upstream_seq.slice(0, selectedUpstreamLength.value) : ''
  if (seqType === 'downstream') return props.downstream_seq ? props.downstream_seq.slice(0, selectedDownstreamLength.value) : ''
  if (seqType === 'cdna') return props.cdna_seq
  if (seqType === 'cds') return props.cds_seq
  if (seqType === 'protein') return props.protein_seq
  
  // 3. 从results数组获取（多基因情况，只取第一个结果）
  if (props.results && props.results.length > 0) {
    const result = props.results[0]
    if (seqType === 'genomic') return result.gene_seq
    if (seqType === 'mrna') return result.mrna_seq
    if (seqType === 'upstream') return result.upstream_seq ? result.upstream_seq.slice(0, selectedUpstreamLength.value) : ''
    if (seqType === 'downstream') return result.downstream_seq ? result.downstream_seq.slice(0, selectedDownstreamLength.value) : ''
    if (seqType === 'cdna') return result.cdna_seq
    if (seqType === 'cds') return result.cds_seq
    if (seqType === 'protein') return result.protein_seq
  }
  
  return ''
}

// 获取基因ID，优先从results数组中获取，其次从gene_id属性中获取
const getGeneId = () => {
  // 1. 优先从results数组中获取（无论结果数量）
  if (props.results && props.results.length > 0) {
    return props.results[0].IDs || props.results[0].gene_id || ''
  }
  // 2. 从currentTranscript获取（转录本情况）
  else if (props.currentTranscript) {
    return props.currentTranscript.id || props.currentTranscript.gene_id || ''
  }
  // 3. 从直接传入的gene_id属性获取（单个基因情况）
  else if (props.gene_id) {
    return props.gene_id
  }
  // 4. 最后返回空字符串
  else {
    return ''
  }
}

// 统一处理按钮点击事件
const handleButtonClick = (type, title, content, id) => {
  let sequenceContent = ''
  const geneId = getGeneId()
  
  // 1. 处理单基因情况：从直接传入的序列属性或currentTranscript获取序列
  if (!props.results || props.results.length === 0) {
    // 处理基因组序列
    if (type === 'genomic' && props.gene_seq && props.gene_seq !== 'N/A') {
      sequenceContent += `>${geneId} ${type}\n${props.gene_seq}\n\n`
    }
    
    // 检查是否有多个转录本
    const hasMultipleTranscripts = props.mrna_transcripts && props.mrna_transcripts.length > 0
    
    if (hasMultipleTranscripts) {
      // 处理多个转录本的情况：遍历所有转录本
      props.mrna_transcripts.forEach((transcript, transIndex) => {
        let currentSeq = ''
        let lengthInfo = ''
        
        if (type === 'mrna') currentSeq = transcript.mrna_seq
        else if (type === 'upstream') {
          currentSeq = transcript.upstream_seq ? transcript.upstream_seq.slice(0, selectedUpstreamLength.value) : ''
          lengthInfo = ` (${selectedUpstreamLength.value}bp)`
        } else if (type === 'downstream') {
          currentSeq = transcript.downstream_seq ? transcript.downstream_seq.slice(0, selectedDownstreamLength.value) : ''
          lengthInfo = ` (${selectedDownstreamLength.value}bp)`
        } else if (type === 'cdna') currentSeq = transcript.cdna_seq
        else if (type === 'cds') currentSeq = transcript.cds_seq
        else if (type === 'protein') currentSeq = transcript.protein_seq
        
        // 添加当前转录本的序列，使用转录本ID作为FASTA头部
        if (currentSeq && currentSeq !== 'N/A' && currentSeq !== '' && 
            currentSeq !== 'unavailable' && currentSeq !== '未找到CDS序列' && currentSeq !== '未找到蛋白序列') {
          const transcriptId = transcript.id || `transcript_${transIndex + 1}`
          sequenceContent += `>${transcriptId} ${type}${lengthInfo} (基因: ${geneId})\n${currentSeq}\n\n`
        }
      })
    } else {
      // 处理单个转录本或无转录本的情况：优先使用currentTranscript，否则使用直接传入的序列属性
      let currentSeq = ''
      let lengthInfo = ''
      if (props.currentTranscript) {
        if (type === 'mrna') currentSeq = props.currentTranscript.mrna_seq
        else if (type === 'upstream') {
          currentSeq = props.currentTranscript.upstream_seq ? props.currentTranscript.upstream_seq.slice(0, selectedUpstreamLength.value) : ''
          lengthInfo = ` (${selectedUpstreamLength.value}bp)`
        } else if (type === 'downstream') {
          currentSeq = props.currentTranscript.downstream_seq ? props.currentTranscript.downstream_seq.slice(0, selectedDownstreamLength.value) : ''
          lengthInfo = ` (${selectedDownstreamLength.value}bp)`
        } else if (type === 'cdna') currentSeq = props.currentTranscript.cdna_seq
        else if (type === 'cds') currentSeq = props.currentTranscript.cds_seq
        else if (type === 'protein') currentSeq = props.currentTranscript.protein_seq
      } else {
        if (type === 'mrna') currentSeq = props.mrna_seq
        else if (type === 'upstream') {
          currentSeq = props.upstream_seq ? props.upstream_seq.slice(0, selectedUpstreamLength.value) : ''
          lengthInfo = ` (${selectedUpstreamLength.value}bp)`
        } else if (type === 'downstream') {
          currentSeq = props.downstream_seq ? props.downstream_seq.slice(0, selectedDownstreamLength.value) : ''
          lengthInfo = ` (${selectedDownstreamLength.value}bp)`
        } else if (type === 'cdna') currentSeq = props.cdna_seq
        else if (type === 'cds') currentSeq = props.cds_seq
        else if (type === 'protein') currentSeq = props.protein_seq
      }
      
      // 添加当前序列，优先使用转录本ID作为FASTA头部
      if (currentSeq && currentSeq !== 'N/A' && currentSeq !== '' && 
          currentSeq !== 'unavailable' && currentSeq !== '未找到CDS序列' && currentSeq !== '未找到蛋白序列') {
        const transcriptId = props.currentTranscript ? props.currentTranscript.id : ''
        if (transcriptId) {
          // 有转录本ID时，使用转录本ID作为FASTA头部
          sequenceContent += `>${transcriptId} ${type}${lengthInfo} (基因: ${geneId})\n${currentSeq}\n\n`
        } else {
          // 没有转录本ID时，使用基因ID作为FASTA头部
          sequenceContent += `>${geneId} ${type}${lengthInfo}\n${currentSeq}\n\n`
        }
      }
    }
  }
  // 2. 处理多基因情况：遍历所有基因收集序列
  else {
    // 遍历所有基因，收集该类型的序列
    props.results.forEach(result => {
      const currentGeneId = result.IDs || ''
      
      // 处理基因组序列
      if (type === 'genomic' && result.gene_seq && result.gene_seq !== '' && result.gene_seq !== 'N/A') {
        sequenceContent += `>${currentGeneId} ${type}\n${result.gene_seq}\n\n`
      }
      
      // 处理mRNA序列：同时显示直接序列和所有转录本序列
      if (type === 'mrna') {
        // 显示直接mRNA序列
        if (result.mrna_seq && result.mrna_seq !== '' && result.mrna_seq !== 'N/A') {
          sequenceContent += `>${currentGeneId} ${type}\n${result.mrna_seq}\n\n`
        }
        // 显示所有转录本的mRNA序列
        if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
          result.mrna_transcripts.forEach((transcript, transIndex) => {
            if (transcript.mrna_seq && transcript.mrna_seq !== 'N/A') {
              sequenceContent += `>${transcript.id} ${type} (基因: ${currentGeneId})\n${transcript.mrna_seq}\n\n`
            }
          })
        }
      }
      
      // 处理上游序列：同时显示直接序列和所有转录本序列
      if (type === 'upstream') {
        // 显示直接上游序列
        if (result.upstream_seq && result.upstream_seq !== '' && result.upstream_seq !== 'N/A') {
          const upstreamSeq = result.upstream_seq.slice(0, selectedUpstreamLength.value)
          sequenceContent += `>${currentGeneId} ${type} (${selectedUpstreamLength.value}bp)\n${upstreamSeq}\n\n`
        }
        // 显示所有转录本的上游序列
        if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
          result.mrna_transcripts.forEach((transcript, transIndex) => {
            if (transcript.upstream_seq && transcript.upstream_seq !== 'N/A') {
              sequenceContent += `>${transcript.id} ${type} (基因: ${currentGeneId}, ${selectedUpstreamLength.value}bp)\n${transcript.upstream_seq.slice(0, selectedUpstreamLength.value)}\n\n`
            }
          })
        }
      }
      
      // 处理下游序列：同时显示直接序列和所有转录本序列
      if (type === 'downstream') {
        // 显示直接下游序列
        if (result.downstream_seq && result.downstream_seq !== '' && result.downstream_seq !== 'N/A') {
          const downstreamSeq = result.downstream_seq.slice(0, selectedDownstreamLength.value)
          sequenceContent += `>${currentGeneId} ${type} (${selectedDownstreamLength.value}bp)\n${downstreamSeq}\n\n`
        }
        // 显示所有转录本的下游序列
        if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
          result.mrna_transcripts.forEach((transcript, transIndex) => {
            if (transcript.downstream_seq && transcript.downstream_seq !== 'N/A') {
              sequenceContent += `>${transcript.id} ${type} (基因: ${currentGeneId}, ${selectedDownstreamLength.value}bp)\n${transcript.downstream_seq.slice(0, selectedDownstreamLength.value)}\n\n`
            }
          })
        }
      }
      
      // 处理cDNA序列：同时显示直接序列和所有转录本序列
      if (type === 'cdna') {
        // 显示直接cDNA序列
        if (result.cdna_seq && result.cdna_seq !== '' && result.cdna_seq !== 'N/A' && result.cdna_seq !== 'unavailable') {
          sequenceContent += `>${currentGeneId} ${type}\n${result.cdna_seq}\n\n`
        }
        // 显示所有转录本的cDNA序列
        if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
          result.mrna_transcripts.forEach((transcript, transIndex) => {
            if (transcript.cdna_seq && transcript.cdna_seq !== 'N/A' && transcript.cdna_seq !== 'unavailable') {
              sequenceContent += `>${transcript.id} ${type} (基因: ${currentGeneId})\n${transcript.cdna_seq}\n\n`
            }
          })
        }
      }
      
      // 处理CDS序列：同时显示直接序列和所有转录本序列
      if (type === 'cds') {
        // 显示直接CDS序列
        if (result.cds_seq && result.cds_seq !== 'N/A' && result.cds_seq !== '未找到CDS序列') {
          sequenceContent += `>${currentGeneId} ${type}\n${result.cds_seq}\n\n`
        }
        // 显示所有转录本的CDS序列
        if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
          result.mrna_transcripts.forEach((transcript, transIndex) => {
            if (transcript.cds_seq && transcript.cds_seq !== 'N/A' && transcript.cds_seq !== '未找到CDS序列') {
              sequenceContent += `>${transcript.id} ${type} (基因: ${currentGeneId})\n${transcript.cds_seq}\n\n`
            }
          })
        }
      }
      
      // 处理蛋白序列：同时显示直接序列和所有转录本序列
      if (type === 'protein') {
        // 显示直接蛋白序列
        if (result.protein_seq && result.protein_seq !== 'N/A' && result.protein_seq !== '未找到蛋白序列') {
          sequenceContent += `>${currentGeneId} ${type}\n${result.protein_seq}\n\n`
        }
        // 显示所有转录本的蛋白序列
        if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
          result.mrna_transcripts.forEach((transcript, transIndex) => {
            if (transcript.protein_seq && transcript.protein_seq !== 'N/A' && transcript.protein_seq !== '未找到蛋白序列') {
              sequenceContent += `>${transcript.id} ${type} (基因: ${currentGeneId})\n${transcript.protein_seq}\n\n`
            }
          })
        }
      }
    })
  }
  
  // 使用emit触发事件
  emit('show-sequence', {
    type,
    title,
    content: sequenceContent,
    id: (props.results && props.results.length > 1) ? 'multiple_genes' : geneId
  })
}
</script>

<style scoped>
/* 组件特定样式 */
.sequence-display-component {
  margin: 1rem 0;
}

.sequence-container {
  margin-top: 0.5rem;
}
</style>