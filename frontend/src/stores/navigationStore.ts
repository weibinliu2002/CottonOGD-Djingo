// 引入Pinia
import { defineStore } from 'pinia'

// 创建导航store，用于存储跨页面传递的数据
export const useNavigationStore = defineStore('navigation', {
  state: () => ({
    // 存储跨页面传递的数据
    navigationData: {
      // BLAST相关数据
      blast: {
        results: null,
        blastType: null
      },
      // 富集分析相关数据
      enrichment: {
        results: null,
        type: null
      },
      // 注释相关数据
      annotation: {
        results: null,
        type: null
      },
      // 基因搜索相关数据
      geneSearch: {
        results: null,
        dbIds: null,
        requestId: null
      },
      // 单个基因详细信息
      geneDetail: {
        results: null,
        dbId: null
      },
      // 基因表达相关数据
      geneExpression: {
        results: null,
        params: null
      },
      // TF相关数据
      tf: {
        results: null,
        params: null
      },
      // TR相关数据
      tr: {
        results: null,
        params: null
      }
    }
  }),
  
  actions: {
    /**
     * 设置导航数据
     * @param key - 数据类型键
     * @param data - 要存储的数据
     */
    setNavigationData(key: string, data: any) {
      const navData = this.navigationData as any
      if (navData[key]) {
        navData[key] = { ...navData[key], ...data }
      } else {
        navData[key] = data
      }
    },
    
    /**
     * 获取导航数据
     * @param key - 数据类型键
     * @returns 存储的数据
     */
    getNavigationData(key: string) {
      const navData = this.navigationData as any
      return navData[key] || null
    },
    
    /**
     * 清除导航数据
     * @param key - 数据类型键（可选，不提供则清除所有数据）
     */
    clearNavigationData(key?: string) {
      const navData = this.navigationData as any
      if (key) {
        // 完全重置指定的键，不保留任何旧属性
        navData[key] = {
          results: null,
          dbId: null
        }
      } else {
        // 重置所有导航数据
        Object.keys(navData).forEach(k => {
          navData[k] = {
            results: null,
            dbId: null
          }
        })
      }
    }
  }
})
