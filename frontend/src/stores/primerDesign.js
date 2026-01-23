// 引入Pinia
import { defineStore } from 'pinia'

// 定义并导出引物设计的store
export const usePrimerDesignStore = defineStore('primerDesign', {
  // 状态
  state: () => ({
    // 序列信息
    sequenceId: '',
    sequenceType: 'mrna', // mrna或cds
    sequenceTemplate: '',
    
    // 设计参数
    parameters: {
      productSizeMin: 100,
      productSizeMax: 250,
      primerSizeMin: 18,
      primerSizeMax: 27,
      primerTmMin: 57,
      primerTmMax: 63,
      primerGCMin: 20,
      primerGCMax: 80
    },
    
    // 设计结果
    designResults: [],
    
    // 状态
    isLoading: false,
    isFetching: false,
    error: null
  }),
  
  // 操作
  actions: {
    // 设置序列信息
    setSequence(sequenceId, sequenceTemplate) {
      this.sequenceId = sequenceId
      this.sequenceTemplate = sequenceTemplate
    },
    
    // 设置序列类型
    setSequenceType(type) {
      this.sequenceType = type
    },
    
    // 设置设计参数
    setParameters(newParams) {
      this.parameters = { ...this.parameters, ...newParams }
    },
    
    // 设置设计结果
    setDesignResults(results) {
      this.designResults = results
    },
    
    // 设置加载状态
    setLoading(isLoading) {
      this.isLoading = isLoading
    },
    
    // 设置获取序列状态
    setFetching(isFetching) {
      this.isFetching = isFetching
    },
    
    // 设置错误信息
    setError(error) {
      this.error = error
    },
    
    // 清空状态
    clearState() {
      this.sequenceId = ''
      this.sequenceType = 'mrna'
      this.sequenceTemplate = ''
      this.designResults = []
      this.error = null
    }
  }
})