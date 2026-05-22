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
        <el-button @click="closeModal">{{ t('close') }}</el-button>
        <el-button type="primary" @click="downloadFasta">{{ t('download_fasta') }}</el-button>
        <el-button type="success" @click="copySequence">{{ t('copy_sequence') }}</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import {} from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

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

const emit = defineEmits(['update:showModal', 'close'])

const closeModal = () => {
  emit('update:showModal', false)
  emit('close')
}

const handleModalUpdate = (value: boolean) => {
  emit('update:showModal', value)
}

// 下载FASTA文件
const downloadFasta = () => {
  const content = props.modalContent
  if (!content) {
    ElMessage.warning('没有可下载的序列内容')
    return
  }
  
  // 构建文件名
  const geneId = props.currentGeneId || 'sequence'
  const seqType = props.currentSeqType || 'unknown'
  const filename = `${geneId}_${seqType}.fasta`
  
  // 创建下载链接
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  ElMessage.success('序列文件已下载')
}

// 复制序列到剪贴板
const copySequence = () => {
  const content = props.modalContent
  if (!content) {
    ElMessage.warning('没有可复制的序列内容')
    return
  }
  
  // 尝试使用现代剪贴板API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(content)
      .then(() => {
        ElMessage.success('序列已复制到剪贴板')
      })
      .catch((err) => {
        console.warn('现代剪贴板API失败，尝试降级方案:', err)
        fallbackCopyToClipboard(content)
      })
  } else {
    // 浏览器不支持现代剪贴板API，使用传统方法
    fallbackCopyToClipboard(content)
  }
}

// 降级复制方法：使用textarea和execCommand
const fallbackCopyToClipboard = (text: string) => {
  // 创建临时textarea元素
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '-9999px'
  textarea.style.width = '1px'
  textarea.style.height = '1px'
  document.body.appendChild(textarea)
  
  // 选中textarea内容
  textarea.select()
  textarea.setSelectionRange(0, text.length) // 支持移动设备
  
  try {
    // 执行复制命令
    const successful = document.execCommand('copy')
    if (successful) {
      ElMessage.success('序列已复制到剪贴板')
    } else {
      ElMessage.error('复制失败，请手动复制')
    }
  } catch (err) {
    console.error('降级复制方法失败:', err)
    ElMessage.error('复制失败，请手动复制')
  } finally {
    // 清理临时元素
    document.body.removeChild(textarea)
  }
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
