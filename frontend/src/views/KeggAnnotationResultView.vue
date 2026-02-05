<template>
  <div class="container mt-4">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="18">
        <h2>{{ t('kegg_annotation') }} {{ t('results') }}</h2>
      </el-col>
      <el-col :span="6" class="text-right">
        <el-tag type="info" v-if="executionTime">Executed in {{ executionTime }} seconds</el-tag>
      </el-col>
    </el-row>
    
    <!-- 返回按钮 -->
    <router-link to="/tools/kegg-annotation" class="mb-4">
      <el-button type="default">返回搜索</el-button>
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
      title="{{ t('no_results') }}. Please try with different gene IDs."
      show-icon
      class="mb-4"
    />
    
    <!-- 结果显示 -->
    <div v-else class="mb-4">
      <!-- 图表区域 -->
      <el-card class="mt-5" v-if="chartData.labels && chartData.labels.length > 0">
        <template #header>
          <div class="card-header">
            <span>{{ t('kegg_pathway') }}</span>
          </div>
        </template>
        <div class="chart-container" style="height: 400px;">
          <canvas id="keggChart"></canvas>
        </div>
      </el-card>
      
      <!-- 每页显示控制 -->
      <el-form @submit.prevent="handlePerPageChange" class="mb-3">
        <el-row :gutter="20" align="middle">
          <el-col :span="6">
            <el-form-item label="每页显示:" label-width="80px">
              <el-select v-model.number="pageSize" class="w-40" @change="changePageSize">
                <el-option value="10" label="10"></el-option>
                <el-option value="25" label="25"></el-option>
                <el-option value="50" label="50"></el-option>
                <el-option value="100" label="100"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <span class="text-gray-500">条记录</span>
          </el-col>
        </el-row>
      </el-form>
      
      <!-- 表格区域 -->
      <el-card class="mb-4">
        <template #header>
          <div class="d-flex justify-content-between align-items-center">
            <span>Annotation {{ t('results') }}</span>
            <el-tag type="primary">{{ totalItems }} results</el-tag>
          </div>
        </template>
        <el-table :data="paginatedResults" style="width: 100%">
          <el-table-column prop="Chr" label="Chr" width="80"></el-table-column>
          <el-table-column prop="Start" label="Start" width="100"></el-table-column>
          <el-table-column prop="End" label="End" width="100"></el-table-column>
          <el-table-column prop="ID" label="ID" width="150"></el-table-column>
          <el-table-column prop="match" label="KO" width="120"></el-table-column>
          <el-table-column prop="{{ t('description') }}" label="{{ t('pathway_name') }}"></el-table-column>
        </el-table>
        
        <!-- 分页控件 -->
        <el-pagination
          v-if="totalPages > 1"
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 25, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalItems"
          @size-change="changePageSize"
          @current-change="changePage"
          class="mt-4"
        />
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
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
    console.error(t('error') + ' fetching results:', error)
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