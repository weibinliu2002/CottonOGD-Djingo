<template>
  <div class="transcript-selector" v-if="hasMultipleTranscripts">
    <h3 class="section-title">{{ title }}</h3>
    <el-select 
      :model-value="selectedIndex" 
      @update:model-value="handleSelectedIndexUpdate" 
      class="w-auto"
    >
      <el-option
        v-for="(transcript, index) in transcripts"
        :key="index"
        :label="getTranscriptLabel(transcript)"
        :value="index"
      />
    </el-select>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  transcripts: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: 'Transcript Selector'
  },
  selectedIndex: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:selectedIndex', 'transcript-change'])

const hasMultipleTranscripts = computed(() => {
  return props.transcripts && props.transcripts.length > 1
})

const handleSelectedIndexUpdate = (index) => {
  emit('update:selectedIndex', index)
  emit('transcript-change', index, props.transcripts[index])
}

const getTranscriptLabel = (transcript) => {
  if (!transcript) return 'Unknown Transcript'
  
  const transcriptId = transcript.mrna_id || transcript.id || 'Unknown'
  const proteinLength = transcript.protein_seq && transcript.protein_seq !== 'N/A' && transcript.protein_seq !== 'unavailable' && transcript.protein_seq !== 'Protein sequence not found' 
    ? transcript.protein_seq.length 
    : 'N/A'
  
  return `${transcriptId} (Protein Length: ${proteinLength} aa)`
}
</script>

<style scoped>
.transcript-selector {
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  margin-bottom: 10px;
  color: #343a40;
}

.w-auto {
  min-width: 300px;
}
</style>