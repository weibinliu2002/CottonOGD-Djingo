<template>
  <div class="sequence-display-component">
    <!-- 通用按钮模式：显示各个序列类型的按钮 -->
    <div v-if="displayMode === 'buttons' || displayMode === 'full'" class="d-flex flex-wrap gap-3 mb-4">
      <div v-for="seq in sequenceTypes" :key="seq.key" class="text-center flex-shrink-0">
        <h4 class="h6 mb-2">{{ seq.title }}</h4>
        <button
          class="btn btn-sm btn-info"
          @click="handleButtonClick(seq.key, seq.title, getSequence(seq.key), getGeneId())"
        >
          {{ hasSequences(seq.key) ? 'Show Sequence' : 'Show Sequence' }}
        </button>
      </div>
    </div>

    <!-- 上下游长度选择器 -->
    <div v-if="displayMode === 'buttons' || displayMode === 'full'" class="mb-4 d-flex justify-content-start">
      <div class="d-flex gap-3 align-items-end w-25">
        <div class="flex-shrink-0 flex-grow-1">
          <label for="upstreamLengthSelect" class="form-label form-label-sm text-center">Upstream</label>
          <select class="form-select form-select-sm" id="upstreamLengthSelect" v-model.number="selectedUpstreamLength" @change="handleLengthChange">
            <option v-for="option in lengthOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>
        <div class="flex-shrink-0 flex-grow-1">
          <label for="downstreamLengthSelect" class="form-label form-label-sm text-center">Downstream</label>
          <select class="form-select form-select-sm" id="downstreamLengthSelect" v-model.number="selectedDownstreamLength" @change="handleLengthChange">
            <option v-for="option in lengthOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- full模式展示FASTA -->
    <div v-if="displayMode === 'full' && showSequences" class="mt-6">
      <div v-for="(seqType, index) in sequenceTypes" :key="index" class="mb-6">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h4>{{ seqType.title }}</h4>
          <div>
            <button class="btn btn-sm btn-primary me-2" @click="$emit('download-all', seqType.key)">下载全部</button>
            <button class="btn btn-sm btn-secondary" @click="$emit('copy-all', seqType.key)">复制全部</button>
          </div>
        </div>

        <div class="bg-light p-4 rounded overflow-y-auto" style="max-height: 300px; white-space: pre-wrap; font-family: monospace; text-align: left;">
          <template v-for="(result, geneIndex) in results" :key="`${seqType.key}-${geneIndex}`">
            <!-- 获取对应序列 -->
            <template v-if="getSequenceTypeContent(seqType.key, result, geneIndex)">
              {{ getSequenceTypeContent(seqType.key, result, geneIndex) }}
            </template>
          </template>

          <template v-if="!hasSequences(seqType.key)">
            <em>该类型没有可用序列</em>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  displayMode: { type: String, default: 'buttons', validator: val => ['buttons', 'full'].includes(val) },
  gene_seq: String,
  mrna_seq: String,
  upstream_seq: String,
  downstream_seq: String,
  cdna_seq: String,
  cds_seq: String,
  protein_seq: String,
  gene_id: String,
  currentTranscript: { type: Object, default: null },
  results: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  upstreamLength: { type: Number, default: 10000 },
  downstreamLength: { type: Number, default: 10000 }
})

const emit = defineEmits(['show-sequence', 'download-all', 'copy-all', 'length-change'])

const sequenceTypes = [
  { key: 'genomic', title: '基因组序列' },
  { key: 'mrna', title: 'mRNA序列' },
  { key: 'upstream', title: '上游序列' },
  { key: 'downstream', title: '下游序列' },
  { key: 'cdna', title: 'cDNA序列' },
  { key: 'cds', title: 'CDS序列' },
  { key: 'protein', title: '蛋白序列' }
]

const lengthOptions = [500, 1000, 2000, 3000, 4000, 5000, 10000]

// 初始值设置为10000，优先使用10000作为默认值
const selectedUpstreamLength = ref(10000)
const selectedDownstreamLength = ref(10000)

// full模式下，默认显示序列
const showSequences = ref(true)

// 组件初始化时，将初始长度传递给父组件
emit('length-change', {
  upstreamLength: selectedUpstreamLength.value,
  downstreamLength: selectedDownstreamLength.value
})

const getGeneId = () => {
  if (props.results && props.results.length > 0) return props.results[0].IDs || props.results[0].gene_id || ''
  if (props.currentTranscript) return props.currentTranscript.id || props.currentTranscript.gene_id || ''
  return props.gene_id || ''
}

const hasSequences = (seqType) => {
  // 检查直接属性、currentTranscript和results
  const checkSeq = (seq) => seq && seq !== '' && seq !== 'N/A' && seq !== 'unavailable' && seq !== '未找到CDS序列' && seq !== '未找到蛋白序列'
  if (seqType === 'genomic') return checkSeq(props.gene_seq) || (props.results && props.results.some(r => checkSeq(r.gene_seq)))
  if (seqType === 'mrna') return checkSeq(props.mrna_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.mrna_seq)) || (props.results && props.results.some(r => checkSeq(r.mrna_seq) || (r.mrna_transcripts && r.mrna_transcripts.some(t => checkSeq(t.mrna_seq)))))
  if (seqType === 'upstream') return checkSeq(props.upstream_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.upstream_seq)) || (props.results && props.results.some(r => checkSeq(r.upstream_seq) || (r.mrna_transcripts && r.mrna_transcripts.some(t => checkSeq(t.upstream_seq)))))
  if (seqType === 'downstream') return checkSeq(props.downstream_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.downstream_seq)) || (props.results && props.results.some(r => checkSeq(r.downstream_seq) || (r.mrna_transcripts && r.mrna_transcripts.some(t => checkSeq(t.downstream_seq)))))
  if (seqType === 'cdna') return checkSeq(props.cdna_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.cdna_seq)) || (props.results && props.results.some(r => checkSeq(r.cdna_seq) || (r.mrna_transcripts && r.mrna_transcripts.some(t => checkSeq(t.cdna_seq)))))
  if (seqType === 'cds') return checkSeq(props.cds_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.cds_seq)) || (props.results && props.results.some(r => checkSeq(r.cds_seq) || (r.mrna_transcripts && r.mrna_transcripts.some(t => checkSeq(t.cds_seq)))))
  if (seqType === 'protein') return checkSeq(props.protein_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.protein_seq)) || (props.results && props.results.some(r => checkSeq(r.protein_seq) || (r.mrna_transcripts && r.mrna_transcripts.some(t => checkSeq(t.protein_seq)))))
  return false
}

const getSequence = (seqType) => {
  const upLen = selectedUpstreamLength.value || 500
  const downLen = selectedDownstreamLength.value || 500
  const ct = props.currentTranscript

  // 1. 检查top-level props（单个基因情况）- 优先检查，确保genomic序列能被正确获取
  if (seqType === 'genomic' && props.gene_seq) return props.gene_seq
  
  // 2. 检查currentTranscript（单个转录本情况）
  // 只有当currentTranscript中有对应序列时才返回，否则继续检查其他位置
  if (ct) {
    if (seqType === 'mrna' && ct.mrna_seq) return ct.mrna_seq
    if (seqType === 'upstream' && ct.upstream_seq) return ct.upstream_seq.slice(0, upLen)
    if (seqType === 'downstream' && ct.downstream_seq) return ct.downstream_seq.slice(0, downLen)
    if (seqType === 'cdna' && ct.cdna_seq) return ct.cdna_seq
    if (seqType === 'cds' && ct.cds_seq) return ct.cds_seq
    if (seqType === 'protein' && ct.protein_seq) return ct.protein_seq
  }

  // 3. 检查其他top-level props（单个基因情况）
  if (seqType === 'mrna' && props.mrna_seq) return props.mrna_seq
  if (seqType === 'upstream' && props.upstream_seq) return props.upstream_seq.slice(0, upLen)
  if (seqType === 'downstream' && props.downstream_seq) return props.downstream_seq.slice(0, downLen)
  if (seqType === 'cdna' && props.cdna_seq) return props.cdna_seq
  if (seqType === 'cds' && props.cds_seq) return props.cds_seq
  if (seqType === 'protein' && props.protein_seq) return props.protein_seq

  // 4. 检查props.results（多个基因/转录本情况）
  if (props.results && props.results.length > 0) {
    for (const result of props.results) {
      // 检查result本身的序列
      if (seqType === 'genomic' && result.gene_seq) return result.gene_seq
      if (seqType === 'mrna' && result.mrna_seq) return result.mrna_seq
      if (seqType === 'upstream' && result.upstream_seq) return result.upstream_seq.slice(0, upLen)
      if (seqType === 'downstream' && result.downstream_seq) return result.downstream_seq.slice(0, downLen)
      if (seqType === 'cdna' && result.cdna_seq) return result.cdna_seq
      if (seqType === 'cds' && result.cds_seq) return result.cds_seq
      if (seqType === 'protein' && result.protein_seq) return result.protein_seq
      
      // 检查result.mrna_transcripts中的序列
      if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
        for (const transcript of result.mrna_transcripts) {
          if (seqType === 'mrna' && transcript.mrna_seq) return transcript.mrna_seq
          if (seqType === 'upstream' && transcript.upstream_seq) return transcript.upstream_seq.slice(0, upLen)
          if (seqType === 'downstream' && transcript.downstream_seq) return transcript.downstream_seq.slice(0, downLen)
          if (seqType === 'cdna' && transcript.cdna_seq) return transcript.cdna_seq
          if (seqType === 'cds' && transcript.cds_seq) return transcript.cds_seq
          if (seqType === 'protein' && transcript.protein_seq) return transcript.protein_seq
        }
      }
    }
  }

  return ''
}

const getSequenceTypeContent = (seqType, result, geneIndex) => {
  if (!result) return ''
  const geneId = result.IDs || `基因 ${geneIndex + 1}`
  const upLen = selectedUpstreamLength.value || 500
  const downLen = selectedDownstreamLength.value || 500
  const checkSeq = (seq) => seq && seq !== '' && seq !== 'N/A' && seq !== 'unavailable' && seq !== '未找到CDS序列' && seq !== '未找到蛋白序列'

  let content = ''

  if (seqType === 'genomic' && checkSeq(result.gene_seq)) {
    content += `>${geneId} genomic\n${result.gene_seq}\n\n`
  }

  if (seqType === 'mrna') {
    // 直接显示所有转录本的mRNA序列，使用转录本ID作为FASTA头部
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.mrna_seq)) content += `>${t.id} mrna\n${t.mrna_seq}\n\n` 
      }) 
    } else if (checkSeq(result.mrna_seq)) {
      // 如果没有transcripts数组但有mrna_seq，使用geneId
      content += `>${geneId} mrna\n${result.mrna_seq}\n\n`
    }
  }

  if (seqType === 'upstream') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.upstream_seq)) content += `>${t.id} upstream (${upLen}bp)\n${t.upstream_seq.slice(0, upLen)}\n\n` 
      })
    } else if (checkSeq(result.upstream_seq)) {
      content += `>${geneId} upstream (${upLen}bp)\n${result.upstream_seq.slice(0, upLen)}\n\n`
    }
  }

  if (seqType === 'downstream') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.downstream_seq)) content += `>${t.id} downstream (${downLen}bp)\n${t.downstream_seq.slice(0, downLen)}\n\n` 
      })
    } else if (checkSeq(result.downstream_seq)) {
      content += `>${geneId} downstream (${downLen}bp)\n${result.downstream_seq.slice(0, downLen)}\n\n`
    }
  }

  if (seqType === 'cdna') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.cdna_seq)) content += `>${t.id} cdna\n${t.cdna_seq}\n\n` 
      })
    } else if (checkSeq(result.cdna_seq)) {
      content += `>${geneId} cdna\n${result.cdna_seq}\n\n`
    }
  }

  if (seqType === 'cds') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.cds_seq)) content += `>${t.id} cds\n${t.cds_seq}\n\n` 
      })
    } else if (checkSeq(result.cds_seq)) {
      content += `>${geneId} cds\n${result.cds_seq}\n\n`
    }
  }

  if (seqType === 'protein') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.protein_seq)) content += `>${t.id} protein\n${t.protein_seq}\n\n` 
      })
    } else if (checkSeq(result.protein_seq)) {
      content += `>${geneId} protein\n${result.protein_seq}\n\n`
    }
  }

  return content
}

const handleLengthChange = () => {
  emit('length-change', {
    upstreamLength: selectedUpstreamLength.value,
    downstreamLength: selectedDownstreamLength.value
  })
}

const handleButtonClick = (type, title, content, id) => {
  // 对于基因组序列，直接传递真实的序列内容
  // 对于其他序列类型（特别是上下游序列），传递空字符串，让父组件重新请求
  if (type === 'genomic') {
    emit('show-sequence', { type, title, content, id })
  } else {
    emit('show-sequence', { type, title, content: '', id })
  }
}
</script>

<style scoped>
.sequence-display-component {
  margin: 1rem 0;
}
.sequence-container {
  margin-top: 0.5rem;
}
</style>
