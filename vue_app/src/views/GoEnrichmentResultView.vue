<template>
  <div class="container mt-4">
    <h2 class="mb-4">GO富集分析结果</h2>
    
    <!-- 返回按钮 -->
    <router-link to="/tools/go-enrichment" class="btn btn-secondary mb-4">返回</router-link>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="text-center py-4">
      <div class="spinner-border" role="status">
        <span class="sr-only">加载中...</span>
      </div>
    </div>
    
    <!-- 错误信息 -->
    <div v-else-if="errorMessage" class="alert alert-danger" role="alert">
      {{ errorMessage }}
    </div>
    
    <!-- 无结果提示 -->
    <div v-else-if="!hasResults" class="alert alert-warning" role="alert">
      暂无富集结果
    </div>
    
    <!-- 结果显示 -->
    <div v-else>
      <!-- 每页显示控制 -->
      <form @submit.prevent="handlePerPageChange" class="mb-3" id="per-page-form">
        <div class="row g-2 align-items-center">
          <div class="col-auto">
            <label for="per_page" class="col-form-label">每页显示:</label>
          </div>
          <div class="col-auto">
            <select 
              name="per_page" 
              id="per_page" 
              class="form-select"
              v-model.number="perPage"
            >
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
            </select>
          </div>
          <div class="col-auto">
            <span class="form-text">条记录</span>
          </div>
        </div>
      </form>
      
      <!-- 按类别展示结果 -->
      <template v-for="(categoryData, category) in results" :key="category">
        <div 
          class="mb-5" 
          :id="`category-${category}`"
        >
          <h4 class="text-danger">
            <!-- 类别名称 -->
            <span v-if="category === 'MF'">Molecular Function</span>
            <span v-else-if="category === 'BP'">Biological Process</span>
            <span v-else-if="category === 'CC'">Cellular Component</span>
            <small class="text-muted">
              (共 {{ categoryData.total }} 条)
            </small>
          </h4>
          
          <!-- 结果表格 -->
          <div class="table-responsive">
            <table class="table table-bordered table-hover">
              <thead class="bg-light">
                <tr>
                  <th>GO ID</th>
                  <th>Description</th>
                  <th>GeneRatio</th>
                  <th>BgRatio</th>
                  <th>RichFactor</th>
                  <th>FoldEnrichment</th>
                  <th>zScore</th>
                  <th>pvalue</th>
                  <th>Genes</th>
                </tr>
              </thead>
              <tbody :id="`tbody-${category}`">
                <tr v-for="item in categoryData.results" :key="item.go_id">
                  <td>{{ item.go_id }}</td>
                  <td>
                    {{ getDescriptionName(item.description) }}
                    <i 
                      v-if="getDescriptionDefinition(item.description)" 
                      class="fas fa-info-circle text-muted" 
                      :title="getDescriptionDefinition(item.description)"
                      data-bs-toggle="tooltip"
                    ></i>
                  </td>
                  <td>{{ item.gene_ratio }}</td>
                  <td>{{ item.bg_ratio }}</td>
                  <td>{{ parseFloat(item.rich_factor).toFixed(4) }}</td>
                  <td>{{ parseFloat(item.fold_enrichment).toFixed(4) }}</td>
                  <td>{{ parseFloat(item.z_score).toFixed(4) }}</td>
                  <td>{{ parseFloat(item.p_value).toFixed(6) }}</td>
                  <td>{{ item.genes }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- 可视化结果 -->
    <div v-if="plotImages && (plotImages[category] || plotImages[category.toLowerCase()] || plotImages[category.toUpperCase()])" class="mt-4">
      <h5>可视化结果</h5>
      <!-- 尝试多种可能的键名，确保能匹配到图像数据 -->
      <img 
        :src="`data:image/png;base64,${plotImages[category] || plotImages[category.toLowerCase()] || plotImages[category.toUpperCase()]}`" 
        class="img-fluid" 
        :alt="`${category} Plot`"
        @error="handleImageError($event)" 
      >

    </div>
          
          <!-- 分页控件 -->
          <nav aria-label="Page navigation">
            <ul :id="`pagination-${category}`" class="pagination justify-content-center">
              <!-- 首页和上一页 -->
              <li class="page-item" :class="{ disabled: !categoryData.has_previous }">
                <a 
                  v-if="categoryData.has_previous" 
                  class="page-link pagination-link" 
                  href="#" 
                  @click.prevent="changePage(category, 1)"
                  :data-category="category"
                >
                  首页
                </a>
                <span v-else class="page-link">首页</span>
              </li>
              <li class="page-item" :class="{ disabled: !categoryData.has_previous }">
                <a 
                  v-if="categoryData.has_previous" 
                  class="page-link pagination-link" 
                  href="#" 
                  @click.prevent="changePage(category, categoryData.previous_page_number)"
                  :data-category="category"
                >
                  上一页
                </a>
                <span v-else class="page-link">上一页</span>
              </li>
              
              <!-- 当前页信息 -->
              <li class="page-item active">
                <span :id="`current-page-${category}`" class="page-link">
                  第 {{ categoryData.current_page }} 页 / 共 {{ categoryData.num_pages }} 页
                </span>
              </li>
              
              <!-- 下一页和末页 -->
              <li class="page-item" :class="{ disabled: !categoryData.has_next }">
                <a 
                  v-if="categoryData.has_next" 
                  class="page-link pagination-link" 
                  href="#" 
                  @click.prevent="changePage(category, categoryData.next_page_number)"
                  :data-category="category"
                >
                  下一页
                </a>
                <span v-else class="page-link">下一页</span>
              </li>
              <li class="page-item" :class="{ disabled: !categoryData.has_next }">
                <a 
                  v-if="categoryData.has_next" 
                  class="page-link pagination-link" 
                  href="#" 
                  @click.prevent="changePage(category, categoryData.num_pages)"
                  :data-category="category"
                >
                  末页
                </a>
                <span v-else class="page-link">末页</span>
              </li>
            </ul>
          </nav>
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
      errorMessage.value = '缺少任务ID'
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
      // 如果任务仍在处理中，等待一段时间后重试
      setTimeout(() => fetchResults(), 1000)
    } else {
      errorMessage.value = response.error || '获取结果失败'
      hasResults.value = false
    }
  } catch (error: any) {
    errorMessage.value = '获取结果失败: ' + (error.message || error)
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