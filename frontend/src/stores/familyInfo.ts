// 引入Pinia
import { defineStore } from 'pinia'
import httpInstance from '@/utils/http.js'

// 定义类型
interface FamilyInfo {
  name: string
  count: number
}

interface FamilyItem {
  TF_name?: string
  TF_class?: string
  geneid?: string
  id?: number
  [key: string]: any
}

interface ApiResponse {
  family_info: string
  family_list: string
}

// 创建家族信息store
export const useFamilyStore = defineStore('family', {
  state: () => ({
    // 家族信息列表
    familyInfo: [] as FamilyInfo[],
    // 家族列表数据
    familyList: [] as FamilyItem[],
    // 加载状态
    loading: false,
    // 错误信息
    error: null as string | null,
    // 用于缓存请求的Promise
    _fetchPromise: null as Promise<void> | null
  }),
  
  getters: {
    // 获取所有家族名称
    familyNames: (state) => {
      return state.familyInfo.map(family => family.name)
    },
    
    // 获取家族数量
    familyCount: (state) => {
      return state.familyInfo.length
    }
  },
  
  actions: {
    // 初始化方法
    initialize() {
      this.fetchFamilies()
    },
    
    // 从后端获取家族数据
    async fetchFamilies() {
      // 如果已经有数据，直接返回，不再请求
      if (this.familyInfo.length > 0) {
        console.log('Using cached family data');
        return;
      }
      
      // 如果已经有正在进行的请求，返回该请求的Promise
      if (this._fetchPromise) {
        console.log('Using existing fetch promise for family data');
        return this._fetchPromise;
      }
      
      // 创建新的请求Promise
      this._fetchPromise = (async () => {
        this.loading = true
        this.error = null
        
        try {
          const data = await httpInstance.get('/CottonOGD_api/get_family_info/') as ApiResponse
          console.log('Family data from API:', data)
          
          // 处理后端返回的家族信息
          const familyInfo = JSON.parse(data.family_info) as FamilyInfo[]
          this.familyInfo = familyInfo
          
          // 处理后端返回的家族列表
          const familyList = JSON.parse(data.family_list) as FamilyItem[]
          this.familyList = familyList
          
          console.log('Processed family info:', this.familyInfo)
          console.log('Processed family list:', this.familyList)
        } catch (error: any) {
          console.error('Error fetching families in store:', error)
          this.error = error.message
          this.familyInfo = []
          this.familyList = []
        } finally {
          this.loading = false
          // 清空Promise缓存
          this._fetchPromise = null
        }
      })()
      
      return this._fetchPromise
    },
    
    // 重置store
    reset() {
      this.familyInfo = []
      this.familyList = []
      this.loading = false
      this.error = null
      this._fetchPromise = null
    }
  }
})
