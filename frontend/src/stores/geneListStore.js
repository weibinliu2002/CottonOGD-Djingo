import { defineStore } from 'pinia'

export const useGeneListStore = defineStore('geneList', {
  state: () => ({
    geneList: '',
  }),
  actions: {
    setGeneList(genes) {
      this.geneList = genes
    },
  },
})
