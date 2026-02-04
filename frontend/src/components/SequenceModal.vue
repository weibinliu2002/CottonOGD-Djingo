<template>
  <el-dialog
    :model-value="showModal"
    @update:model-value="handleModalUpdate"
    :title="modalTitle"
    width="80%"
    destroy-on-close
  >
    <el-scrollbar height="400px">
      <pre class="bg-light p-3 rounded" style="white-space: pre-wrap; font-family: monospace; margin: 0; padding: 10px;">{{ modalContent }}</pre>
    </el-scrollbar>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="closeModal">Close</el-button>
        <el-button type="primary" @click="downloadFasta">Download FASTA</el-button>
        <el-button type="success" @click="copySequence">Copy Sequence</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  showModal: {
    type: Boolean,
    default: false
  },
  modalTitle: {
    type: String,
    default: ''
  },
  modalContent: {
    type: String,
    default: ''
  },
  currentSeqType: {
    type: String,
    default: ''
  },
  currentGeneId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:showModal', 'close', 'download', 'copy'])

const closeModal = () => {
  emit('update:showModal', false)
  emit('close')
}

const handleModalUpdate = (value) => {
  emit('update:showModal', value)
}

const downloadFasta = () => {
  emit('download', {
    content: props.modalContent,
    type: props.currentSeqType,
    geneId: props.currentGeneId
  })
}

const copySequence = () => {
  emit('copy', {
    content: props.modalContent,
    type: props.currentSeqType,
    geneId: props.currentGeneId
  })
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>