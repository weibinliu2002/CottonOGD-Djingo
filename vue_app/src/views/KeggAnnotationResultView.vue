<template>
  <div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>KEGG Annotation Results</h2>
      <span class="badge bg-info" v-if="executionTime">Executed in {{ executionTime }} seconds</span>
    </div>
    
    <!-- 返回按钮 -->
    <router-link to="/tools/kegg-annotation" class="btn btn-secondary mb-4">返回搜索</router-link>
    
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
      No results found. Please try with different gene IDs.
    </div>
    
    <!-- 结果显示 -->
    <div v-else>
      <!-- 图表区域 -->
      <div v-if="chartData.labels && chartData.labels.length > 0" class="mt-5">
        <h3>KEGG Pathway</h3>
        <div class="chart-container" style="height: 400px;">
          <canvas id="keggChart"></canvas>
        </div>
      </div>
      
      <!-- 每页显示控制 -->
      <form @submit.prevent="handlePerPageChange" class="mb-3">
        <div class="row g-2 align-items-center">
          <div class="col-auto">
            <label for="pageSize" class="col-form-label">每页显示:</label>
          </div>
          <div class="col-auto">
            <select 
              id="pageSize" 
              v-model.number="pageSize"
              class="form-select" 
              @change="changePageSize"
            >
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </div>
          <div class="col-auto">
            <span class="form-text">条记录</span>
          </div>
        </div>
      </form>
      
      <!-- 表格区域 -->
      <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>Annotation Results</span>
          <span class="badge bg-primary">{{ totalItems }} results</span>
        </div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-striped table-bordered mb-0">
              <thead>
                <tr>
                  <th>Chr</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>ID</th>
                  <th>KO</th>
                  <th>Pathway Name</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in paginatedResults" :key="item.ID">
                  <td>{{ item.Chr }}</td>
                  <td>{{ item.Start }}</td>
                  <td>{{ item.End }}</td>
                  <td>{{ item.ID }}</td>
                  <td>{{ item.match }}</td>
                  <td>{{ item.Description }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- 分页控件 -->
          <nav v-if="totalPages > 1" aria-label="Page navigation">
            <ul class="pagination justify-content-center mt-3 mb-0">
              <li class="page-item" :class="{ disabled: currentPage === 1 }">
                <a 
                  class="page-link" 
                  href="#" 
                  @click.prevent="changePage(1)"
                >
                  首页
                </a>
              </li>
              <li class="page-item" :class="{ disabled: currentPage === 1 }">
                <a 
                  class="page-link" 
                  href="#" 
                  @click.prevent="changePage(currentPage - 1)"
                >
                  上一页
                </a>
              </li>
              
              <li 
                v-for="page in visiblePages" 
                :key="page"
                class="page-item" 
                :class="{ active: page === currentPage }"
              >
                <a class="page-link" href="#" @click.prevent="changePage(page)">{{ page }}</a>
              </li>
              
              <li class="page-item" :class="{ disabled: currentPage === totalPages }">
                <a 
                  class="page-link" 
                  href="#" 
                  @click.prevent="changePage(currentPage + 1)"
                >
                  下一页
                </a>
              </li>
              <li class="page-item" :class="{ disabled: currentPage === totalPages }">
                <a 
                  class="page-link" 
                  href="#" 
                  @click.prevent="changePage(totalPages)"
                >
                  末页
                </a>
              </li>
            </ul>
          </nav>
          
          <!-- 分页信息 -->
          <div v-if="totalPages > 1" class="text-center mt-2 mb-3">
            <p class="text-muted mb-0">
              Showing {{ startItem }} to {{ endItem }} of {{ totalItems }} entries
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// 页面数据
const results = ref<any[]>([])
const pageSize = ref(10)
const currentPage = ref(1)
const hasResults = ref(true)
const chart = ref<any>(null)
const isLoading = ref(false)
const errorMessage = ref('')
const executionTime = ref(0)
const totalItems = ref(0)
const totalGenes = ref(0)
const annotatedGenes = ref(0)
const chartData = ref<{ labels: string[], data: number[] }>({ labels: [], data: [] })

// 计算属性
const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value))
const startItem = computed(() => (currentPage.value - 1) * pageSize.value + 1)
const endItem = computed(() => Math.min(currentPage.value * pageSize.value, totalItems.value))

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return results.value.slice(start, end)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages: number[] = []
  
  if (total <= 5) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 3) {
      for (let i = 1; i <= 5; i++) {
        pages.push(i)
      }
    } else if (current >= total - 2) {
      for (let i = total - 4; i <= total; i++) {
        pages.push(i)
      }
    } else {
      for (let i = current - 2; i <= current + 2; i++) {
        pages.push(i)
      }
    }
  }
  return pages
})

// 方法
const handlePerPageChange = () => {
  currentPage.value = 1 // 重置到第一页
  fetchResults()
}

const changePageSize = () => {
  currentPage.value = 1 // 重置到第一页
  fetchResults()
}

const changePage = (page: number) => {
  if (page < 1 || page > totalPages.value) {
    return
  }
  currentPage.value = page
  fetchResults()
}

// 使用统一的axios实例
import axios from '../utils/http'

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
    
    // 使用配置好的axios实例调用后端API获取结果
    const responseData = await axios.get('/tools/kegg_annotation/api/results/', {
      params: {
        task_id: taskId,
        page_size: pageSize.value,
        page: currentPage.value
      }
    }) as any
    
    console.log('KEGG注释API响应:', responseData)
    
    if (responseData && responseData.status === 'success') {
        results.value = responseData.results || []
        totalItems.value = responseData.total || 0
        totalGenes.value = responseData.total_genes || 0
        annotatedGenes.value = responseData.annotated_genes || 0
        
        // 确保chart_data是正确的格式
        if (responseData.chart_data) {
          chartData.value = {
            labels: responseData.chart_data.labels || [],
            data: responseData.chart_data.data || []
          }
        } else {
          chartData.value = { labels: [], data: [] }
        }
        
        hasResults.value = results.value.length > 0
        
        console.log('KEGG注释结果:', results.value)
        console.log('图表数据:', chartData.value)
        console.log('图表标签数量:', chartData.value.labels.length)
        console.log('图表数据数量:', chartData.value.data.length)
        
        // 渲染图表
        renderChart()
    } else if (responseData && responseData.status === 'processing') {
      // 如果任务仍在处理中，等待一段时间后重试
      setTimeout(() => fetchResults(), 1000)
    } else {
      errorMessage.value = responseData.error || '获取结果失败'
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

// 引入Chart.js
import Chart from 'chart.js/auto'

const renderChart = () => {
  console.log('渲染KEGG通路分布图表...')
  console.log('图表数据:', chartData.value)
  
  // 获取canvas元素
  const canvas = document.getElementById('keggChart') as HTMLCanvasElement
  if (!canvas) {
    console.error('没有找到keggChart元素')
    return
  }
  
  // 销毁现有图表（如果存在）
  if (chart.value) {
    chart.value.destroy()
    chart.value = null
  }
  
  // 如果没有图表数据，不渲染
  if (!chartData.value.labels || chartData.value.labels.length === 0) {
    console.log('没有图表数据，不渲染图表')
    return
  }
  
  // 创建新图表
  chart.value = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: chartData.value.labels,
      datasets: [{
        label: '',
        data: chartData.value.data,
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Count'
          }
        },
        x: {
          title: {
            display: true,
            text: ''
          }
        }
      }
    }
  })
}

// 监听chartData变化，确保DOM更新后再渲染图表
watch(
  () => chartData.value,
  async (newData) => {
    if (newData && newData.labels && newData.labels.length > 0) {
      await nextTick() // 等待DOM更新
      renderChart()
    }
  },
  { deep: true }
)

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

.card {
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.card-header {
  background-color: #f8f9fa;
  font-weight: bold;
}

.table {
  margin-bottom: 0;
}

.form-group {
  display: flex;
  align-items: center;
}

.pagination {
  margin-top: 1rem;
}

.gene-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.gene-tag {
  background-color: #e9ecef;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 0.8rem;
  white-space: nowrap;
}

/* 图表容器样式 */
.chart-container {
  position: relative;
  height: 400px;
}

canvas#keggChart {
  height: 100% !important;
  width: 100% !important;
}
</style>