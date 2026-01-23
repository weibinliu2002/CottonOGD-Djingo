<template>
  <div class="container mt-4">
    <h2 class="mb-4">KEGG通路富集分析结果</h2>
    
    <!-- 返回按钮 -->
    <router-link to="/tools/kegg-enrichment" class="mb-3">
      <el-button type="default">返回</el-button>
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
    
    <!-- 结果显示 -->
    <div v-else>
      <!-- 无结果提示 -->
      <el-alert
        v-if="!hasResults"
        type="warning"
        title="未找到显著的KEGG通路富集结果"
        show-icon
        class="mb-4"
      />
      
      <!-- 图表区域 (即使无显著结果也显示) -->
      <el-card v-if="plotImage" class="mb-4">
        <template #header>
          <div class="card-header">
            <span>KEGG Enrichment Plot</span>
          </div>
        </template>
        <div class="text-center">
          <el-image
            :src="'data:image/png;base64,' + plotImage"
            alt="KEGG Enrichment Plot"
            fit="contain"
            class="w-full"
          />
        </div>
      </el-card>
      
      <!-- 显著结果表格 (只有有结果时才显示) -->
      <div v-if="hasResults">
        <!-- 每页显示控制 -->
        <el-form @submit.prevent="handlePerPageChange" class="mb-3" id="per-page-form">
          <el-row :gutter="20" align="middle">
            <el-col :span="6">
              <el-form-item label="每页显示:" label-width="80px">
                <el-select 
                  v-model.number="pageSize"
                  class="w-40" 
                  @change="changePageSize"
                >
                  <el-option value="5" label="5"></el-option>
                  <el-option value="10" label="10"></el-option>
                  <el-option value="25" label="25"></el-option>
                  <el-option value="50" label="50"></el-option>
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <span class="text-gray-500">条记录</span>
            </el-col>
          </el-row>
        </el-form>
        
        <el-card class="mb-5">
          <template #header>
            <div class="d-flex justify-content-between align-items-center">
              <h4 class="text-danger m-0">KEGG通路</h4>
              <el-tag type="info">(共 {{ totalItems }} 条)</el-tag>
            </div>
          </template>
          
          <!-- 表格区域 -->
          <el-table :data="paginatedResults" style="width: 100%">
            <el-table-column prop="pathway_id" label="通路ID" width="120"></el-table-column>
            <el-table-column prop="description.name" label="描述">
              <template #default="scope">
                <div>
                  {{ scope.row.description.name || '' }}
                  <el-tooltip v-if="scope.row.description.definition" :content="scope.row.description.definition" placement="top">
                    <i class="el-icon-info text-muted ml-1"></i>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="gene_ratio" label="GeneRatio" width="120"></el-table-column>
            <el-table-column prop="bg_ratio" label="BgRatio" width="120"></el-table-column>
            <el-table-column label="RichFactor" width="120">
              <template #default="scope">
                {{ scope.row.rich_factor.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column label="FoldEnrichment" width="150">
              <template #default="scope">
                {{ scope.row.fold_enrichment.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column label="zScore" width="100">
              <template #default="scope">
                {{ scope.row.z_score.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column label="pvalue" width="150">
              <template #default="scope">
                {{ scope.row.p_value.toFixed(6) }}
              </template>
            </el-table-column>
          </el-table>
          
          <!-- 分页控件 -->
          <el-pagination
            v-if="totalPages > 1"
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[5, 10, 25, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="totalItems"
            @size-change="changePageSize"
            @current-change="changePage"
            class="mt-4"
          />
        </el-card>
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