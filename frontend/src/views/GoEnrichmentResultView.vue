<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('go_enrichment_analysis_results') }}</h2>
    
    <!-- 返回按钮 -->
    <router-link to="/tools/go-enrichment" class="mb-4">
      <el-button type="default">Back</el-button>
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
      title="{{ t('no_enrichment_results_found') }}"
      show-icon
      class="mb-4"
    />
    
    <!-- 结果显示 -->
    <div v-else class="mb-4">
      <!-- 每页显示控制 -->
      <el-form @submit.prevent="handlePerPageChange" class="mb-3">
        <el-row :gutter="20" align="middle">
          <el-col :span="6">
            <el-form-item label="{{ t('results') }} per page:" label-width="120px">
              <el-select v-model.number="perPage" class="w-32" @change="handlePerPageChange">
                <el-option value="5" label="5"></el-option>
                <el-option value="10" label="10"></el-option>
                <el-option value="25" label="25"></el-option>
                <el-option value="50" label="50"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <span class="text-gray-500">{{ t('records') }}</span>
          </el-col>
        </el-row>
      </el-form>
      
      <!-- 按类别展示结果 -->
      <template v-for="(categoryData, category) in results" :key="category">
        <div 
          class="mb-5" 
          :id="`category-${category}`"
        >
          <h4 class="text-danger mb-3">
            <!-- 类别名称 -->
            <span v-if="category === 'MF'">{{ t('molecular_function') }}</span>
            <span v-else-if="category === 'BP'">{{ t('biological_process') }}</span>
            <span v-else-if="category === 'CC'">{{ t('cellular_component') }}</span>
            <small class="text-muted">
              (Total {{ categoryData.total }} {{ t('records') }})
            </small>
          </h4>
          
          <!-- 结果表格 -->
          <el-card class="mb-4">
            <el-table :data="categoryData.results" style="width: 100%">
              <el-table-column prop="go_id" label="{{ t('go_id') }}" width="150"></el-table-column>
              <el-table-column prop="description" label="{{ t('description') }}">
                <template #default="scope">
                  {{ getDescriptionName(scope.row.description) }}
                </template>
              </el-table-column>
              <el-table-column prop="gene_ratio" label="GeneRatio" width="120"></el-table-column>
              <el-table-column prop="bg_ratio" label="BgRatio" width="120"></el-table-column>
              <el-table-column label="RichFactor" width="120">
                <template #default="scope">
                  {{ parseFloat(scope.row.rich_factor).toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column label="FoldEnrichment" width="120">
                <template #default="scope">
                  {{ parseFloat(scope.row.fold_enrichment).toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column label="zScore" width="100">
                <template #default="scope">
                  {{ parseFloat(scope.row.z_score).toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column label="pvalue" width="120">
                <template #default="scope">
                  {{ parseFloat(scope.row.p_value).toFixed(6) }}
                </template>
              </el-table-column>
              <el-table-column prop="genes" label="Genes"></el-table-column>
            </el-table>
          </el-card>
          
          <!-- 可视化结果 -->
          <el-card class="mb-4" v-if="plotImages && (plotImages[category] || plotImages[category.toLowerCase()] || plotImages[category.toUpperCase()])">
            <template #header>
              <div class="card-header">
                <span>Visualization Results</span>
              </div>
            </template>
            <el-image
              :src="`data:image/png;base64,${plotImages[category] || plotImages[category.toLowerCase()] || plotImages[category.toUpperCase()]}`"
              :alt="`${category} Plot`"
              fit="contain"
              class="w-full"
              @error="handleImageError($event)"
            />
          </el-card>
          
          <!-- 分页控件 -->
          <el-pagination
            v-if="categoryData.num_pages > 1"
            v-model:current-page="currentPages[category]"
            v-model:page-size="perPage"
            :page-sizes="[5, 10, 25, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="categoryData.total"
            @size-change="handlePerPageChange"
            @current-change="(page: number) => changePage(category, page)"
            class="mt-4"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

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
  isLoading.value = true
  try {
    // 从URL参数获取task_id
    const taskId = route.query.task_id
    if (!taskId) {
      errorMessage.value = 'Task ID missing'
      hasResults.value = false
      return
    }
    
    // 准备请求参数
    const params: any = {
      task_id: taskId,
      per_page: perPage.value
    }
    
    // 添加每个类别的当前页码
    for (const category in currentPages.value) {
      params[`${category}_page`] = currentPages.value[category]
    }
    
    // 使用直接导入的axios实例调用后端API获取结果
    console.log('请求参数:', params)
    const response = await axios.get('/tools/go_enrichment/api/results/', {
      params
    }) as any
    
    // 详细打印后端返回的数据，包括所有字段
    console.log('完整的后端返回数据:', JSON.stringify(response, null, 2))
    
    // 检查状态是否为成功
    if (response.status === 'success' || response.code === 200 || !response.error) {
      // 处理返回的结果，按类别组织
      // 修复数据结构问题：真正的富集结果在response.results.results中
      let resultsData = response.results || response.data || {} 
      let resultsObj = resultsData.results || {} 
      let plotImagesObj = response.plot_images || response.images || response.charts || {} 
      
      // 打印处理后的数据结构
      console.log('处理后的结果对象:', resultsObj)
      console.log('处理后的图像对象:', plotImagesObj)
      
      // 初始化结果对象
      results.value = {
        BP: { results: [], total: 0, num_pages: 1, current_page: 1, has_next: false, has_previous: false },
        MF: { results: [], total: 0, num_pages: 1, current_page: 1, has_next: false, has_previous: false },
        CC: { results: [], total: 0, num_pages: 1, current_page: 1, has_next: false, has_previous: false }
      }
      
      // 遍历所有类别，处理结果
      for (const category in resultsObj) {
        const categoryData = resultsObj[category]
        console.log(`处理类别 ${category} 的数据:`, categoryData)
        
        if (categoryData && typeof categoryData === 'object') {
          // 如果categoryData是分页对象，提取results
          if (Array.isArray(categoryData.results)) {
            results.value[category] = {
              results: categoryData.results,
              total: categoryData.total || categoryData.results.length,
              num_pages: categoryData.num_pages || 1,
              current_page: categoryData.current_page || currentPages.value[category] || 1,
              has_next: categoryData.has_next || false,
              has_previous: categoryData.has_previous || false
            }
          } 
          // 如果categoryData直接是结果数组
          else if (Array.isArray(categoryData)) {
            results.value[category] = {
              results: categoryData,
              total: categoryData.length,
              num_pages: 1,
              current_page: currentPages.value[category] || 1,
              has_next: false,
              has_previous: false
            }
          }
        }
      }
      
      // 处理可视化图像
      plotImages.value = plotImagesObj
      
      // 添加调试信息，查看可视化图像数据
      console.log('可视化图像数据:', plotImagesObj)
      
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
      executionTime.value = response.execution_time || response.elapsed_time || response.time || 0
    } else if (response.status === 'processing') {
      // If task is still processing, retry after a short delay
      setTimeout(() => fetchResults(), 1000)
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
  }
}

// 生命周期
onMounted(async () => {
  await fetchResults()
})

// 初始化工具提示
onMounted(() => {
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