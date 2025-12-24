<template>
  <div class="container mt-4">
    <h2 class="mb-4">KEGG通路富集分析结果</h2>
    
    <!-- 返回按钮 -->
    <router-link to="/tools/kegg-enrichment" class="btn btn-secondary mb-3">返回</router-link>
    
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
    
    <!-- 结果显示 -->
    <div v-else>
      <!-- 无结果提示 -->
      <div v-if="!hasResults" class="alert alert-warning mb-4" role="alert">
        未找到显著的KEGG通路富集结果
      </div>
      
      <!-- 图表区域 (即使无显著结果也显示) -->
      <div v-if="plotImage" class="mb-4">
        <h4 class="mb-3">KEGG Enrichment Plot</h4>
        <div class="text-center">
          <img :src="'data:image/png;base64,' + plotImage" alt="KEGG Enrichment Plot" class="img-fluid">
        </div>
      </div>
      
      <!-- 显著结果表格 (只有有结果时才显示) -->
      <div v-if="hasResults">
        <!-- 每页显示控制 -->
        <form @submit.prevent="handlePerPageChange" class="mb-3" id="per-page-form">
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
        
        <div class="mb-5">
          <h4 class="text-danger">
            KEGG通路
            <small class="text-muted">(共 {{ totalItems }} 条)</small>
          </h4>
          
          <!-- 表格区域 -->
          <div class="table-responsive">
            <table class="table table-bordered table-hover">
              <thead class="bg-light">
                <tr>
                  <th>通路ID</th>
                  <th>描述</th>
                  <th>GeneRatio</th>
                  <th>BgRatio</th>
                  <th>RichFactor</th>
                  <th>FoldEnrichment</th>
                  <th>zScore</th>
                  <th>pvalue</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in paginatedResults" :key="item.pathway_id">
                  <td>{{ item.pathway_id }}</td>
                  <td>
                    {{ item.description.name || '' }}
                    <i v-if="item.description.definition" 
                       class="fas fa-info-circle text-muted" 
                       data-bs-toggle="tooltip" 
                       :title="item.description.definition"></i>
                  </td>
                  <td>{{ item.gene_ratio }}</td>
                  <td>{{ item.bg_ratio }}</td>
                  <td>{{ item.rich_factor.toFixed(4) }}</td>
                  <td>{{ item.fold_enrichment.toFixed(4) }}</td>
                  <td>{{ item.z_score.toFixed(4) }}</td>
                  <td>{{ item.p_value.toFixed(6) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- 分页控件 -->
          <nav v-if="totalPages > 1" aria-label="Page navigation">
            <ul class="pagination justify-content-center" id="pagination-results">
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
              
              <li class="page-item active">
                <span class="page-link">
                  第 {{ currentPage }} 页 / 共 {{ totalPages }} 页
                </span>
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
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// 页面数据
const results = ref<any[]>([])
const pageSize = ref(10)
const currentPage = ref(1)
const hasResults = ref(true)
const isLoading = ref(false)
const errorMessage = ref('')
const executionTime = ref(0)
const plotImage = ref<string | null>(null)
const totalItems = ref(0)

// 计算属性
const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value))

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return results.value.slice(start, end)
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
    // 注意：axios实例已经在response interceptor中返回了response.data
    // 类型断言：强制告诉TypeScript这是API返回的实际数据，不是AxiosResponse对象
    const data = await axios.get('/tools/kegg_enrichment/api/results/', {
      params: {
        task_id: taskId,
        page_size: pageSize.value,
        page: currentPage.value
      }
    }) as unknown as any
    console.log('KEGG富集API响应:', data)
    
    // 确保data是一个对象并且有status属性
    if (typeof data === 'object' && data !== null) {
      if (data.status === 'success') {
        results.value = data.results || []
        totalItems.value = data.total || results.value.length
        hasResults.value = results.value.length > 0
        executionTime.value = data.execution_time || 0
        plotImage.value = data.plot_image || null
      } else if (data.status === 'processing') {
        // 如果任务仍在处理中，等待一段时间后重试
        setTimeout(() => fetchResults(), 1000)
      } else {
        errorMessage.value = data.error || '获取结果失败'
        hasResults.value = false
      }
    } else {
      errorMessage.value = '无效的API响应'
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
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
}

.table {
  margin-bottom: 0;
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
</style>