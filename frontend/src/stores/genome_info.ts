// 引入Pinia
import { defineStore } from 'pinia'
import httpInstance from '@/utils/http.js'

// 定义类型
interface GenomeOption {
  value: string
  label: string
  children?: GenomeItem[]
}

interface GenomeItem {
  value: string
  label: string
}

interface Species {
  Genome_type?: string
  alias?: string
  name?: string
  Cotton_Species?: string
}

interface ApiResponse {
  species_info: string
}

// 创建基因组信息store
export const useGenomeStore = defineStore('genome', {
  state: () => ({
    // 基因组级联选择器选项
    genomeOptions: [] as GenomeOption[],
    // 基因组加载状态
    loading: false,
    // 原始物种数据
    speciesData: [] as Species[],
    // 错误信息
    error: null as string | null
  }),
  
  getters: {
    // 获取所有基因组类型
    genomeTypes: (state) => {
      return state.genomeOptions.map(option => option.label)
    },
    
    // 获取所有基因组
    allGenomes: (state) => {
      return state.genomeOptions.flatMap(option => 
        option.children?.map((child: GenomeItem) => child.value) || []
      )
    }
  },
  
  actions: {
    // 从后端获取基因组数据
    async fetchGenomes() {
      this.loading = true
      this.error = null
      
      try {
        const data = await httpInstance.get('/CottonOGD_api/get_species_info/') as ApiResponse
        console.log('Species data from store:', data)
        
        // 处理后端返回的species数据
        const speciesData = JSON.parse(data.species_info) as Species[]
        this.speciesData = speciesData
        
        // 按Genome_type分组
        const genomes: Record<string, GenomeItem[]> = {}
        speciesData.forEach((species: Species) => {
          const genomeType = species.Genome_type || 'undefined'
          if (!genomes[genomeType]) {
            genomes[genomeType] = []
          }
          genomes[genomeType].push({
            value: species.alias || species.name || species.Cotton_Species || '',
            label: species.name || species.alias || species.Cotton_Species || ''
          })
        })
        
        // 转换为级联选择器格式
        this.genomeOptions = Object.entries(genomes).map(([type, items]) => ({
          value: type,
          label: type,
          children: items
        }))
        
        console.log('Genome options from store:', this.genomeOptions)
      } catch (error: any) {
        console.error('Error fetching genomes in store:', error)
        this.error = error.message
        this.genomeOptions = []
        this.speciesData = []
      } finally {
        this.loading = false
      }
    },
    
    // 重置store
    reset() {
      this.genomeOptions = []
      this.loading = false
      this.speciesData = []
      this.error = null
    }
  }
})
