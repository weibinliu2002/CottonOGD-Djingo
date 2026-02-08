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
    // 选择的基因组
    selectedGenome: '',
    // 选择的类别
    selectedClass: '',
    // 加载状态
    loading: false,
    // 错误信息
    error: null as string | null
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
      // 不再自动获取数据，等待基因组选择后再获取
    },
    
    // 从后端获取家族数据
    async fetchFamilies() {
      // 检查是否已选择基因组和类别
      if (!this.selectedGenome || !this.selectedClass) {
        console.log('No genome or class selected, skipping fetch')
        return
      }
      
      this.loading = true
      this.error = null
      try {
        // 构建请求参数
        const requestParams = {
          selectedGenome: this.selectedGenome,
          Class: this.selectedClass
        }
        
        console.log('Family request params:', requestParams)
        
        const data = await httpInstance.post('/CottonOGD_api/get_family_info/', requestParams) as ApiResponse
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
      }
    },
    
    // 重置store
    reset() {
      this.familyInfo = []
      this.familyList = []
      this.selectedGenome = ''
      this.selectedClass = ''
      this.loading = false
      this.error = null
    }
  }
})
