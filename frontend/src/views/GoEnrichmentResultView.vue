<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('go_enrichment_analysis_results') }}</h2>
    
    <!-- 返回按钮 -->
    <router-link to="/tools/go-enrichment" class="mb-4">
      <el-button type="default">{{ t('back') }}</el-button>
    </router-link>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="mb-4">
      <el-skeleton :rows="10" animated />
    </div>
    
    <!-- 错误信息 -->
    <el-alert
      v-else-if="errorMessage"
      type="error"
      :title="errorMessage"
      show-icon
      class="mb-4"
    />
    
    <!-- 无结果提示 -->
    <el-alert
      v-else-if="!hasResults"
      type="warning"
      :title="t('no_enrichment_results_found')"
      show-icon
      class="mb-4"
    />
    
    <!-- 结果显示 -->
    <div v-else>
      <!-- 图表区域 -->
      <template v-for="(imageData, category) in plotImages" :key="category">
        <el-card v-if="imageData" class="mb-4">
          <template #header>
            <div class="card-header">
              <span>
                <span v-if="category === 'MF'">{{ t('molecular_function') }}</span>
                <span v-else-if="category === 'BP'">{{ t('biological_process') }}</span>
                <span v-else-if="category === 'CC'">{{ t('cellular_component') }}</span>
                {{ t('enrichment_plot') }}
              </span>
            </div>
          </template>
          <div class="text-center">
            <el-image
              :src="'data:image/png;base64,' + imageData"
              :alt="t('go_enrichment_plot')"
              fit="contain"
              class="w-full"
            />
          </div>
        </el-card>
      </template>
      
      <!-- 按类别展示结果 -->
      <template v-for="(categoryData, category) in paginatedResults" :key="category">
        <div 
          class="mb-5" 
          v-if="categoryData.results.length > 0"
        >
          <h4 class="text-danger mb-3">
            <!-- 类别名称 -->
            <span v-if="category === 'MF'">{{ t('molecular_function') }}</span>
            <span v-else-if="category === 'BP'">{{ t('biological_process') }}</span>
            <span v-else-if="category === 'CC'">{{ t('cellular_component') }}</span>
            <small class="text-muted">
              ({{ t('total') }} {{ allResults[category]?.total || 0 }} {{ t('records') }})
            </small>
          </h4>
          
          <!-- 结果表格 -->
          <el-card class="mb-4">
            <el-table :data="categoryData.results" style="width: 100%">
              <el-table-column prop="go_id" :label="t('go_id')" width="150"></el-table-column>
              <el-table-column prop="description" :label="t('description')">
                <template #default="scope">
                  {{ scope.row.description?.name || '' }}
                </template>
              </el-table-column>
              <el-table-column prop="gene_ratio" :label="t('gene_ratio')" width="120"></el-table-column>
              <el-table-column prop="bg_ratio" :label="t('bg_ratio')" width="120"></el-table-column>
              <el-table-column :label="t('rich_factor')" width="120">
                <template #default="scope">
                  {{ parseFloat(scope.row.rich_factor || 0).toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column :label="t('fold_enrichment')" width="120">
                <template #default="scope">
                  {{ parseFloat(scope.row.fold_enrichment || 0).toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column :label="t('z_score')" width="100">
                <template #default="scope">
                  {{ parseFloat(scope.row.z_score || 0).toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column :label="t('p_value')" width="120">
                <template #default="scope">
                  {{ parseFloat(scope.row.p_value || 0).toFixed(6) }}
                </template>
              </el-table-column>
              <el-table-column prop="genes" :label="t('number_of_genes')"></el-table-column>
            </el-table>
          </el-card>
          
          <!-- Element Plus 分页组件 -->
          <div class="pagination-container">
            <el-pagination
              @size-change="(size: number) => handleSizeChange(category, size)"
              @current-change="(page: number) => handleCurrentChange(category, page)"
              :current-page="currentPages[category] ?? 1"
              :page-sizes="[5, 10, 25, 50]"
              :page-size="perPage"
              :total="allResults[category]?.total || 0"
              layout="total, sizes, prev, pager, next, jumper"
            />
          </div>
        </div>
      </template>
    </div>
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useEnrichmentStore } from '@/stores/enrichmentStore'

const router = useRouter()
const { t } = useI18n()
const enrichmentStore = useEnrichmentStore()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

// 页面数据
const perPage = ref(10)
const currentPages = ref<Record<string, number>>({
  BP: 1,
  MF: 1,
  CC: 1
})

// 完整的结果数据（不分页）
const allResults = ref<Record<string, any>>({
  BP: { results: [], total: 0 },
  MF: { results: [], total: 0 },
  CC: { results: [], total: 0 }
})

// 图表数据
const plotImages = ref<Record<string, string | null>>({
  BP: null,
  MF: null,
  CC: null
})

const hasResults = ref(true)
const isLoading = ref(false)
const errorMessage = ref('')

// 使用配置好的axios实例
import axios from '../utils/http'

// 分页后的结果
const paginatedResults = computed(() => {
  const result: Record<string, any> = {
    BP: { results: [], total: 0 },
    MF: { results: [], total: 0 },
    CC: { results: [], total: 0 }
  }
  
  const categories = ['BP', 'MF', 'CC']
  categories.forEach(category => {
    const currentPage = currentPages.value[category] ?? 1
    const start = (currentPage - 1) * perPage.value
    const end = start + perPage.value
    result[category] = {
      results: allResults.value[category]?.results.slice(start, end) || [],
      total: allResults.value[category]?.total || 0
    }
  })
  
  return result
})

// 获取结果数据（只在初始化时调用一次）
const fetchResults = async () => {
  showLoading?.()
  isLoading.value = true
  try {
    // 从Pinia store获取数据
    const geneId = enrichmentStore.geneList || ''
    const genomeId = enrichmentStore.selectedGenome || 'G.kirkii_ISU_ISU_v3.0'
    const pValueThreshold = enrichmentStore.pValue || 0.05
    const qValueThreshold = enrichmentStore.qValue || 0.05
    
    console.log('从store获取的数据:', { geneId, genomeId, pValueThreshold, qValueThreshold })
    
    if (!geneId) {
      errorMessage.value = 'Missing gene_id parameter'
      hasResults.value = false
      // 如果store中没有数据，返回上一页
      router.push({ name: 'GoEnrichment' })
      return
    }
    
    // 使用multipart/form-data格式发送请求（根据API文档）
    const formData = new FormData()
    formData.append('gene_id', geneId)
    formData.append('genome_id', genomeId)
    formData.append('p_value_threshold', String(pValueThreshold))
    formData.append('q_value_threshold', String(qValueThreshold))
    
    console.log('请求参数:', { gene_id: geneId, genome_id: genomeId, p_value_threshold: pValueThreshold, q_value_threshold: qValueThreshold })
    
    const response = await axios.post('/CottonOGD_api/go_enrichment/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }) as any
    
    console.log('完整的后端返回数据:', JSON.stringify(response, null, 2))
    
    if (response.status === 'success') {
      const data = response.data
      
      // 按GO类别组织结果
      const categories = ['BP', 'MF', 'CC']
      categories.forEach(category => {
        const categoryResults = data.results.filter((r: any) => r.go_type === category)
        
        // 解析每个结果中的description字段（如果是字符串）
        const parsedResults = categoryResults.map((result: any) => {
          if (typeof result.description === 'string') {
            try {
              result.description = JSON.parse(result.description)
            } catch (error) {
              console.error('解析description失败:', error)
              result.description = { name: result.description, definition: '' }
            }
          }
          return result
        })
        
        allResults.value[category] = {
          results: parsedResults,
          total: categoryResults.length
        }
        
        // 获取图表数据
        if (data.plot_images && data.plot_images[category]) {
          plotImages.value[category] = data.plot_images[category]
        }
      })
      
      // 检查是否有结果
      let anyResults = false
      for (const category in allResults.value) {
        if (allResults.value[category].results.length > 0) {
          anyResults = true
          break
        }
      }
      hasResults.value = anyResults
      
      console.log('最终结果数据:', allResults.value)
      console.log('图表数据:', plotImages.value)
    } else {
      errorMessage.value = response.error || 'Failed to get results'
      hasResults.value = false
    }
  } catch (error: any) {
    errorMessage.value = 'Failed to get results: ' + (error.message || error)
    console.error('Error fetching results:', error)
    hasResults.value = false
  } finally {
    isLoading.value = false
    hideLoading?.()
  }
}

// 每页条数变更（前端分页，不重新请求）
const handleSizeChange = (category: string, size: number) => {
  perPage.value = size
  currentPages.value[category] = 1
}

// 当前页变更（前端分页，不重新请求）
const handleCurrentChange = (category: string, page: number) => {
  currentPages.value[category] = page
}

// 生命周期
onMounted(async () => {
  await fetchResults()
})
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
}

.text-danger {
  color: #dc3545;
}

.text-muted {
  color: #6c757d;
}

.mb-3 {
  margin-bottom: 1rem;
}

.mb-4 {
  margin-bottom: 1.5rem;
}

.mb-5 {
  margin-bottom: 3rem;
}

.mt-4 {
  margin-top: 1.5rem;
}
</style>
