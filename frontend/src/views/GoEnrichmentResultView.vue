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
      <!-- 无结果提示 -->
      <el-alert
        v-if="!hasResults"
        type="warning"
        :title="t('no_enrichment_results_found')"
        show-icon
        class="mb-4"
      />
      
      <!-- 按类别展示结果 -->
      <template v-for="(categoryData, category) in results" :key="category">
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
              ({{ t('total') }} {{ categoryData.total }} {{ t('records') }})
            </small>
          </h4>
          
          <!-- 结果表格 -->
          <el-card class="mb-4">
            <el-table :data="categoryData.results" style="width: 100%">
              <el-table-column prop="go_id" :label="t('go_id')" width="150"></el-table-column>
              <el-table-column prop="description" :label="t('description')">
                <template #default="scope">
                  {{ scope.row.description.name }}
                </template>
              </el-table-column>
              <el-table-column prop="gene_ratio" :label="t('gene_ratio')" width="120"></el-table-column>
              <el-table-column prop="bg_ratio" :label="t('bg_ratio')" width="120"></el-table-column>
              <el-table-column :label="t('rich_factor')" width="120">
                <template #default="scope">
                  {{ parseFloat(scope.row.rich_factor).toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column :label="t('fold_enrichment')" width="120">
                <template #default="scope">
                  {{ parseFloat(scope.row.fold_enrichment).toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column :label="t('z_score')" width="100">
                <template #default="scope">
                  {{ parseFloat(scope.row.z_score).toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column :label="t('p_value')" width="120">
                <template #default="scope">
                  {{ parseFloat(scope.row.p_value).toFixed(6) }}
                </template>
              </el-table-column>
              <el-table-column prop="genes" :label="t('number_of_genes')"></el-table-column>
            </el-table>
          </el-card>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const route = useRoute()
const { t } = useI18n()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

// 页面数据
const perPage = ref(10)
const currentPages = ref<Record<string, number>>({
  BP: 1,
  MF: 1,
  CC: 1
})
const results = ref<Record<string, any>>({
  BP: { results: [], total: 0, num_pages: 1, current_page: 1, has_next: false, has_previous: false },
  MF: { results: [], total: 0, num_pages: 1, current_page: 1, has_next: false, has_previous: false },
  CC: { results: [], total: 0, num_pages: 1, current_page: 1, has_next: false, has_previous: false }
})
const plotImages = ref<Record<string, string>>({})
const hasResults = ref(true)
const isLoading = ref(false)
const errorMessage = ref('')
const executionTime = ref(0)

// 使用配置好的axios实例
import axios from '../utils/http'

// 处理description对象，获取名称
const getDescriptionName = (description: any) => {
  if (typeof description === 'object' && description !== null && 'name' in description) {
    return description.name
  } else if (typeof description === 'string') {
    return description
  }
  return ''
}

// 处理description对象，获取定义
const getDescriptionDefinition = (description: any) => {
  if (typeof description === 'object' && description !== null && 'definition' in description) {
    return description.definition
  }
  return ''
}

// 处理图像加载错误
const handleImageError = (event: Event) => {
  const target = event.target as HTMLElement
  if (target) {
    target.style.display = 'none'
  }
}

// 提交每页显示条数变更
const handlePerPageChange = async () => {
  // 重置所有类别到第一页
  currentPages.value = {
    BP: 1,
    MF: 1,
    CC: 1
  }
  
  // 重新获取结果
  await fetchResults()
}

// 切换页面
const changePage = async (category: string, page: number) => {
  // 更新当前类别页码
  currentPages.value[category] = page
  
  // 重新获取结果
  await fetchResults()
}

// 获取结果数据
const fetchResults = async () => {
  showLoading?.()
  isLoading.value = true
  try {
    // 从URL参数获取gene_id
    const geneId = route.query.gene_id as string || ''
    const pValueThreshold = parseFloat(route.query.p_value_threshold as string || '0.05')
    
    if (!geneId) {
      errorMessage.value = 'Missing gene_id parameter'
      hasResults.value = false
      return
    }
    
    // 使用直接导入的axios实例调用后端API获取结果
    console.log('请求参数:', { gene_id: geneId, p_value_threshold: pValueThreshold })
    const response = await axios.get('/CottonOGD_api/go_enrichment/', {
      params: {
        gene_id: geneId,
        p_value_threshold: pValueThreshold
      }
    }) as any
    
    // 详细打印后端返回的数据，包括所有字段
    console.log('完整的后端返回数据:', JSON.stringify(response, null, 2))
    
    // 检查状态是否为成功
    if (response.status === 'success') {
      const data = response.data
      console.log('处理后的结果对象:', data.results)
      console.log('结果数量:', data.results ? data.results.length : 0)
      
      // 打印每个结果的go_type
      if (data.results && data.results.length > 0) {
        data.results.forEach((r: any, index: number) => {
          console.log(`结果 ${index}: go_id=${r.go_id}, go_type=${r.go_type}, description=${r.description}`)
        })
      }
      
      // 初始化结果对象
      results.value = {
        BP: { results: [], total: 0, num_pages: 1, current_page: 1, has_next: false, has_previous: false },
        MF: { results: [], total: 0, num_pages: 1, current_page: 1, has_next: false, has_previous: false },
        CC: { results: [], total: 0, num_pages: 1, current_page: 1, has_next: false, has_previous: false }
      }
      
      // 按GO类别组织结果
      const categories = ['BP', 'MF', 'CC']
      categories.forEach(category => {
        const categoryResults = data.results.filter((r: any) => r.go_type === category)
        console.log(`类别 ${category} 的结果数量: ${categoryResults.length}`)
        
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
        
        results.value[category] = {
          results: parsedResults,
          total: categoryResults.length,
          num_pages: 1,
          current_page: 1,
          has_next: false,
          has_previous: false
        }
      })
      
      // 检查是否有结果
      let anyResults = false
      for (const category in results.value) {
        if (results.value[category].results.length > 0) {
          anyResults = true
          break
        }
      }
      hasResults.value = anyResults
      
      // 添加调试信息，查看最终结果数据
      console.log('最终结果数据:', results.value)
      
      // 设置执行时间
      executionTime.value = 0
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

// 生命周期
onMounted(async () => {
  await fetchResults()
  // 这里可以添加工具提示的初始化逻辑
  // 由于使用了Bootstrap，可以在模板中直接使用data-bs-toggle="tooltip"
})
</script>

<style scoped>
/* 全局样式 */
.container {
  max-width: 1200px;
  margin: 0 auto;
}

/* 表格样式 */
.table {
  margin-bottom: 1rem;
}

.table-bordered {
  border: 1px solid #dee2e6;
}

.table-bordered th,
.table-bordered td {
  border: 1px solid #dee2e6;
}

.table-hover tbody tr:hover {
  background-color: rgba(0, 0, 0, 0.075);
}

.thead-light {
  background-color: #f8f9fa;
}

/* 分页样式 */
.pagination {
  margin-top: 1rem;
  justify-content: center;
}

.pagination-link {
  cursor: pointer;
}

/* 加载状态 */
.loading-cell {
  text-align: center;
}

/* 工具提示 */
.fas.fa-info-circle {
  cursor: help;
  margin-left: 5px;
  font-size: 14px;
}

/* 结果图片 */
.img-fluid {
  max-width: 100%;
  height: auto;
}
</style>
