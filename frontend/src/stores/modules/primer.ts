// 引入Pinia
import { defineStore } from 'pinia'

interface Parameters {
  productSizeMin: number
  productSizeMax: number
  primerSizeMin: number
  primerSizeMax: number
  primerTmMin: number
  primerTmMax: number
  primerGCMin: number
  primerGCMax: number
}

export const usePrimerDesignStore = defineStore('primerDesign', {
  state: () => ({
    sequenceId: '',
    sequenceType: 'mrna' as 'mrna' | 'cds',
    sequenceTemplate: '',
    parameters: {
      productSizeMin: 100,
      productSizeMax: 250,
      primerSizeMin: 18,
      primerSizeMax: 27,
      primerTmMin: 57,
      primerTmMax: 63,
      primerGCMin: 20,
      primerGCMax: 80
    } as Parameters,
    designResults: [] as any[],
    isLoading: false,
    isFetching: false,
    error: null as string | null
  }),
  
  actions: {
    setSequence(sequenceId: string, sequenceTemplate: string) {
      this.sequenceId = sequenceId
      this.sequenceTemplate = sequenceTemplate
    },
    
    setSequenceType(type: 'mrna' | 'cds') {
      this.sequenceType = type
    },
    
    setParameters(newParams: Partial<Parameters>) {
      this.parameters = { ...this.parameters, ...newParams }
    },
    
    setDesignResults(results: any[]) {
      this.designResults = results
    },
    
    setLoading(isLoading: boolean) {
      this.isLoading = isLoading
    },
    
    setFetching(isFetching: boolean) {
      this.isFetching = isFetching
    },
    
    setError(error: string | null) {
      this.error = error
    },
    
    clearDesignResults() {
      this.designResults = []
      this.error = null
    },
    
    clearState() {
      this.sequenceId = ''
      this.sequenceType = 'mrna'
      this.sequenceTemplate = ''
      this.designResults = []
      this.error = null
    }
  }
})