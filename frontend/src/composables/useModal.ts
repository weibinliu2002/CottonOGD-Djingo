import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ModalEventData {
  content: string
  type: string
  geneId: string
}

interface UseModalReturn {
  showModal: Ref<boolean>
  modalTitle: Ref<string>
  modalContent: Ref<string>
  currentSeqType: Ref<string>
  currentGeneId: Ref<string>
  openModal: (title: string, content: string, seqType: string, geneId: string) => void
  showSequenceModal: (title: string, content: string, seqType: string, geneId: string) => void
  closeModal: () => void
  resetModal: () => void
  handleDownload: (data: ModalEventData) => void
  handleCopy: (data: ModalEventData) => void
}

export function useModal(): UseModalReturn {
  const showModal = ref(false)
  const modalTitle = ref('')
  const modalContent = ref('')
  const currentSeqType = ref('')
  const currentGeneId = ref('')

  const openModal = (title: string, content: string, seqType: string, geneId: string) => {
    modalTitle.value = title
    modalContent.value = content
    currentSeqType.value = seqType
    currentGeneId.value = geneId
    showModal.value = true
  }

  const closeModal = () => {
    showModal.value = false
  }

  const resetModal = () => {
    showModal.value = false
    modalTitle.value = ''
    modalContent.value = ''
    currentSeqType.value = ''
    currentGeneId.value = ''
  }

  // 显示序列弹窗，与openModal功能相同，只是名称更明确
  const showSequenceModal = (title: string, content: string, seqType: string, geneId: string) => {
    openModal(title, content, seqType, geneId)
  }

  // 处理从SequenceModal组件发出的下载事件
  const handleDownload = (data: ModalEventData) => {
    const header = `>${data.geneId} ${data.type}`
    const fastaContent = `${header}\n${data.content}`
    
    const blob = new Blob([fastaContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${data.geneId}_${data.type}.fasta`
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

  // 处理从SequenceModal组件发出的复制事件
  const handleCopy = (data: ModalEventData) => {
    const header = `>${data.geneId} ${data.type}`
    const fastaContent = `${header}\n${data.content}`
    
    navigator.clipboard.writeText(fastaContent)
      .then(() => {
        ElMessage.success('序列已复制到剪贴板')
      })
      .catch(err => {
        console.error('复制失败:', err)
        ElMessage.error('复制失败，请手动复制')
      })
  }

  return {
    showModal,
    modalTitle,
    modalContent,
    currentSeqType,
    currentGeneId,
    openModal,
    showSequenceModal,
    closeModal,
    resetModal,
    handleDownload,
    handleCopy
  }
}
