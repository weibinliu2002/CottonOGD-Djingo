// 引入Pinia
import { defineStore } from 'pinia'

// 定义基因搜索状态管理store
export const useGeneSearchStore = defineStore('geneSearch', {
  // 状态定义
  state: () => ({
    // 存储搜索的基因ID列表
    geneIds: [],
    // 存储请求ID
    requestId: '',
    // 存储搜索结果
    searchResults: [],
    // 存储加载状态
    isLoading: false,
    // 存储错误信息
    error: null
  }),

  // 动作定义
  actions: {
    // 设置基因ID列表
    setGeneIds(ids) {
      this.geneIds = ids
    },

    // 设置请求ID
    setRequestId(id) {
      this.requestId = id
    },

    // 设置搜索结果
    setSearchResults(results) {
      this.searchResults = results
    },

    // 设置加载状态
    setIsLoading(loading) {
      this.isLoading = loading
    },

    // 设置错误信息
    setError(error) {
      this.error = error
    },

    // 清除状态
    clearState() {
      this.geneIds = []
      this.requestId = ''
      this.searchResults = []
      this.isLoading = false
      this.error = null
    }
  }
})