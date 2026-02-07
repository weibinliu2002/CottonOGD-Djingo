<template>
  <div class="sequence-display-component">
    <!-- 通用按钮模式：显示各个序列类型的按钮 -->
    <div class="d-flex flex-wrap gap-3 mb-4">
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
    <div class="mb-4 d-flex justify-content-start">
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
  { key: 'genomic', title: 'Genomic Sequence' },
  { key: 'mrna', title: 'mRNA Sequence' },
  { key: 'upstream', title: 'Upstream Sequence' },
  { key: 'downstream', title: 'Downstream Sequence' },
  { key: 'cdna', title: 'cDNA Sequence' },
  { key: 'cds', title: 'CDS Sequence' },
  { key: 'protein', title: 'Protein Sequence' }
]

const lengthOptions = [500, 1000, 2000, 3000, 4000, 5000, 10000]

// 初始值设置为10000，优先使用10000作为默认值
const selectedUpstreamLength = ref(10000)
const selectedDownstreamLength = ref(10000)

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
  const checkSeq = (seq) => seq && seq !== '' && seq !== 'N/A' && seq !== 'unavailable' && seq !== 'CDS sequence not found' && seq !== 'Protein sequence not found'
  if (seqType === 'genomic') return checkSeq(props.gene_seq)
  if (seqType === 'mrna') return checkSeq(props.mrna_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.mrna_seq))
  if (seqType === 'upstream') return checkSeq(props.upstream_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.upstream_seq))
  if (seqType === 'downstream') return checkSeq(props.downstream_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.downstream_seq))
  if (seqType === 'cdna') return checkSeq(props.cdna_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.cdna_seq))
  if (seqType === 'cds') return checkSeq(props.cds_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.cds_seq))
  if (seqType === 'protein') return checkSeq(props.protein_seq) || (props.currentTranscript && checkSeq(props.currentTranscript.protein_seq))
  return false
}

const getSequence = (seqType) => {
  const ct = props.currentTranscript

  // 1. 检查top-level props（单个基因情况）- 优先检查
  if (seqType === 'genomic' && props.gene_seq) return props.gene_seq
  if (seqType === 'mrna' && props.mrna_seq) return props.mrna_seq
  if (seqType === 'upstream' && props.upstream_seq) return props.upstream_seq
  if (seqType === 'downstream' && props.downstream_seq) return props.downstream_seq
  if (seqType === 'cdna' && props.cdna_seq) return props.cdna_seq
  if (seqType === 'cds' && props.cds_seq) return props.cds_seq
  if (seqType === 'protein' && props.protein_seq) return props.protein_seq
  
  // 2. 检查currentTranscript（单个转录本情况）
  if (ct) {
    if (seqType === 'genomic' && ct.gene_seq) return ct.gene_seq
    if (seqType === 'mrna' && ct.mrna_seq) return ct.mrna_seq
    if (seqType === 'upstream' && ct.upstream_seq) return ct.upstream_seq
    if (seqType === 'downstream' && ct.downstream_seq) return ct.downstream_seq
    if (seqType === 'cdna' && ct.cdna_seq) return ct.cdna_seq
    if (seqType === 'cds' && ct.cds_seq) return ct.cds_seq
    if (seqType === 'protein' && ct.protein_seq) return ct.protein_seq
  }

  // 3. 检查props.results（多个基因情况）
  if (props.results && props.results.length > 0) {
    for (const result of props.results) {
      if (seqType === 'genomic' && result.gene_seq) return result.gene_seq
      if (seqType === 'mrna' && result.mrna_seq) return result.mrna_seq
      if (seqType === 'upstream' && result.upstream_seq) return result.upstream_seq
      if (seqType === 'downstream' && result.downstream_seq) return result.downstream_seq
      if (seqType === 'cdna' && result.cdna_seq) return result.cdna_seq
      if (seqType === 'cds' && result.cds_seq) return result.cds_seq
      if (seqType === 'protein' && result.protein_seq) return result.protein_seq
    }
  }

  // 对于其他序列类型，返回空字符串，让父组件在弹窗中展示所有序列
  return ''
}

// 辅助函数：将序列按每行80个字符换行
const formatSequence = (seq) => {
  if (!seq) return ''
  // 使用正则表达式将序列按每80个字符分割
  return seq.replace(/(.{1,80})/g, '$1\n')
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
  emit('show-sequence', { type, title, content, id })
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
