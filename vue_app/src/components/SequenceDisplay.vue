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
  const ct = props.currentTranscript

  // 1. 检查top-level props（单个基因情况）- 优先检查，确保genomic序列能被正确获取
  if (seqType === 'genomic' && props.gene_seq) return props.gene_seq
  
  // 2. 检查currentTranscript（单个转录本情况）
  if (ct && seqType === 'genomic' && ct.gene_seq) return ct.gene_seq

  // 3. 检查props.results（多个基因情况）
  if (seqType === 'genomic' && props.results && props.results.length > 0) {
    for (const result of props.results) {
      if (result.gene_seq) return result.gene_seq
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

const getSequenceTypeContent = (seqType, result, geneIndex) => {
  if (!result) return ''
  const geneId = result.IDs || `基因 ${geneIndex + 1}`
  const upLen = selectedUpstreamLength.value || 500
  const downLen = selectedDownstreamLength.value || 500
  const checkSeq = (seq) => seq && seq !== '' && seq !== 'N/A' && seq !== 'unavailable' && seq !== '未找到CDS序列' && seq !== '未找到蛋白序列'

  let content = ''

  if (seqType === 'genomic' && checkSeq(result.gene_seq)) {
    content += `>${geneId} genomic\n${formatSequence(result.gene_seq)}\n`
  }

  if (seqType === 'mrna') {
    // 直接显示所有转录本的mRNA序列，使用转录本ID作为FASTA头部
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.mrna_seq)) content += `>${t.id} mrna\n${formatSequence(t.mrna_seq)}\n` 
      }) 
    } else if (checkSeq(result.mrna_seq)) {
      // 如果没有transcripts数组但有mrna_seq，使用geneId
      content += `>${geneId} mrna\n${formatSequence(result.mrna_seq)}\n`
    }
  }

  if (seqType === 'upstream') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.upstream_seq)) {
          const seq = t.upstream_seq.slice(0, upLen)
          content += `>${t.id} upstream (${upLen}bp)\n${formatSequence(seq)}\n` 
        }
      })
    } else if (checkSeq(result.upstream_seq)) {
      const seq = result.upstream_seq.slice(0, upLen)
      content += `>${geneId} upstream (${upLen}bp)\n${formatSequence(seq)}\n`
    }
  }

  if (seqType === 'downstream') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.downstream_seq)) {
          const seq = t.downstream_seq.slice(0, downLen)
          content += `>${t.id} downstream (${downLen}bp)\n${formatSequence(seq)}\n` 
        }
      })
    } else if (checkSeq(result.downstream_seq)) {
      const seq = result.downstream_seq.slice(0, downLen)
      content += `>${geneId} downstream (${downLen}bp)\n${formatSequence(seq)}\n`
    }
  }

  if (seqType === 'cdna') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.cdna_seq)) content += `>${t.id} cdna\n${formatSequence(t.cdna_seq)}\n` 
      })
    } else if (checkSeq(result.cdna_seq)) {
      content += `>${geneId} cdna\n${formatSequence(result.cdna_seq)}\n`
    }
  }

  if (seqType === 'cds') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.cds_seq)) content += `>${t.id} cds\n${formatSequence(t.cds_seq)}\n` 
      })
    } else if (checkSeq(result.cds_seq)) {
      content += `>${geneId} cds\n${formatSequence(result.cds_seq)}\n`
    }
  }

  if (seqType === 'protein') {
    if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
      result.mrna_transcripts.forEach(t => { 
        if (checkSeq(t.protein_seq)) content += `>${t.id} protein\n${formatSequence(t.protein_seq)}\n` 
      })
    } else if (checkSeq(result.protein_seq)) {
      content += `>${geneId} protein\n${formatSequence(result.protein_seq)}\n`
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
