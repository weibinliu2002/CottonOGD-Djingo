import { ref, type Ref } from 'vue'

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

  return {
    showModal,
    modalTitle,
    modalContent,
    currentSeqType,
    currentGeneId,
    openModal,
    showSequenceModal,
    closeModal,
    resetModal
  }
}
