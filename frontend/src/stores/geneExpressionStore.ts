import { defineStore } from 'pinia'

export const useGeneExpressionStore = defineStore('geneExpression', {
  state: () => ({
    results: {} as any,
    heatmapImage: '' as string,
    loading: false as boolean,
    error: null as any,
    queryParams: {
      geneList: '' as string,
      tissue: '' as string,
      genome: '' as string
    }
  }),
  
  actions: {
    setResults(results: any) {
      this.results = results
    },
    
    setHeatmapImage(image: string) {
      this.heatmapImage = image
    },
    
    setLoading(loading: boolean) {
      this.loading = loading
    },
    
    setError(error: any) {
      this.error = error
    },
    
    setQueryParams(params: {
      geneList: string,
      tissue: string,
      genome: string
    }) {
      this.queryParams = params
    },
    
    clear() {
      this.results = {}
      this.heatmapImage = ''
      this.error = null
      this.queryParams = {
        geneList: '',
        tissue: '',
        genome: ''
      }
    }
  }
})
