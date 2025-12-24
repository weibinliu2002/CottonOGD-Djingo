<template>
  <div class="container mt-4">
    <h2 class="mb-4">GO注释结果</h2>
    
    <!-- 可视化图表 -->
    <div v-if="chart" class="card mb-4">
      <div class="card-body">
        <h5 class="card-title">GO注释分布</h5>
        <img :src="`data:image/png;base64,${chart}`" alt="GO Annotation Chart" class="img-fluid">
      </div>
    </div>
    
    <form @submit.prevent="handlePerPageChange" class="mb-3">
      <div class="row g-2 align-items-center">
        <div class="col-auto">
          <label for="per_page" class="col-form-label">每页显示:</label>
        </div>
        <div class="col-auto">
          <select name="per_page" id="per_page" class="form-select" v-model.number="perPage">
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
    
    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border" role="status">
        <span class="sr-only">加载中...</span>
      </div>
    </div>
    
    <div v-else-if="results.length > 0">
      <div class="table-responsive">
        <table class="table table-bordered table-hover">
          <thead class="bg-light">
            <tr>
              <th>Chr</th>
              <th>Start</th>
              <th>End</th>
              <th>ID</th>
              <th>GO ID</th>
              <th>Description</th>
              <th>Gene Ontology</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in results" :key="`${item.ID}-${item.GO_ID}`">
              <td>{{ item.Chr }}</td>
              <td>{{ item.Start }}</td>
              <td>{{ item.End }}</td>
              <td>{{ item.ID }}</td>
              <td>{{ item.GO_ID }}</td>
              <td>{{ item.Description }}</td>
              <td>{{ item.Gene_Ontology }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <nav v-if="total > perPage" aria-label="Page navigation">
        <ul class="pagination justify-content-center">
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <a 
              class="page-link" 
              href="#" 
              @click.prevent="changePage(1)"
              :aria-disabled="currentPage === 1"
            >
              首页
            </a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <a 
              class="page-link" 
              href="#" 
              @click.prevent="changePage(currentPage - 1)"
              :aria-disabled="currentPage === 1"
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
              :aria-disabled="currentPage === totalPages"
            >
              下一页
            </a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <a 
              class="page-link" 
              href="#" 
              @click.prevent="changePage(totalPages)"
              :aria-disabled="currentPage === totalPages"
            >
              末页
            </a>
          </li>
        </ul>
      </nav>
    </div>
    
    <div v-else class="alert alert-info">暂无注释结果</div>
    
    <div class="mt-3">
      <router-link to="/tools/go-annotation" class="btn btn-secondary">返回</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../utils/http'

const route = useRoute()

// 页面数据
const perPage = ref(10)
const geneList = ref('')
const results = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const total = ref(0)
const chart = ref<string>('')
const hasResults = ref<boolean>(true)

// 总页数
const totalPages = computed(() => Math.ceil(total.value / perPage.value))



// 处理每页显示条数变更
const handlePerPageChange = () => {
  currentPage.value = 1
  loadResults()
}

// 切换页面
const changePage = (page: number) => {
  currentPage.value = page
  loadResults()
}

// 加载结果数据
const loadResults = async () => {
  loading.value = true
  
  // 从路由参数获取查询条件
  const geneListParam = route.query.gene_list as string || ''
  geneList.value = geneListParam
  
  // 添加调试信息
  console.log('=== GO注释结果页面调试信息 ===')
  console.log('路由参数:', route.query)
  console.log('获取的gene_list参数:', geneListParam)
  console.log('gene_list参数长度:', geneListParam.length)
  console.log('当前页码:', currentPage.value)
  console.log('每页显示条数:', perPage.value)
  
  try {
    // 检查是否有基因列表参数
    if (!geneListParam) {
      console.log('没有获取到gene_list参数')
      results.value = []
      total.value = 0
      chart.value = ''
      hasResults.value = false
      return
    }
    
    // 调用后端API获取数据
    console.log('准备调用API')
    const responseData = await axios.get('/tools/go_annotation/', {
      params: {
        gene_id: geneListParam,
        per_page: perPage.value,
        page: currentPage.value,
        api: 'true'
      }
    }) as any
    
    console.log('API调用成功')
    console.log('API响应数据:', responseData)
    
    // 由于axios拦截器直接返回response.data，所以responseData就是后端返回的data对象
    if (responseData && responseData.success) {
      console.log('API响应成功')
      const data = responseData.data
      console.log('数据对象:', data)
      console.log('结果数组:', data.results)
      console.log('结果数量:', data.results ? data.results.length : 0)
      console.log('是否有图表:', data.chart ? '是' : '否')
      results.value = data.results || []
      total.value = data.results.length || 0
      chart.value = data.chart || ''
      
      // 更新hasResults变量
      hasResults.value = results.value.length > 0
      console.log('是否有结果:', hasResults.value)
    } else {
      console.log('API响应失败或success为false')
      console.log('响应数据:', responseData)
      results.value = []
      total.value = 0
      chart.value = ''
      hasResults.value = false
    }
  } catch (error) {
    console.error('加载结果失败:', error)
    results.value = []
    total.value = 0
    chart.value = ''
    hasResults.value = false
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadResults()
})
</script>

<style scoped>
.pagination {
  margin-top: 1rem;
}

.btn-secondary {
  background-color: #6c757d;
  border-color: #6c757d;
}

.btn-secondary:hover {
  background-color: #5a6268;
  border-color: #545b62;
}

.spinner-border {
  width: 3rem;
  height: 3rem;
}
</style>