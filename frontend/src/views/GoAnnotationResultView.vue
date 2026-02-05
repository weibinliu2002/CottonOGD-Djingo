<template>
  <div class="container mt-4">
    <h2 class="mb-4">GO注释结果</h2>
    
    <!-- 可视化图表 -->
    <el-card class="mb-4" v-if="chart">
      <template #header>
        <div class="card-header">
          <span>{{ t('go') }}</span>
        </div>
      </template>
      <el-image
        :src="`data:image/png;base64,${chart}`"
        alt="{{ t('go_annotation') }} Chart"
        fit="contain"
        class="w-full"
      />
    </el-card>
    
    <el-form @submit.prevent="handlePerPageChange" class="mb-3">
      <el-row :gutter="20" align="middle">
        <el-col :span="6">
          <el-form-item label="每页显示:" label-width="80px">
            <el-select v-model.number="perPage" class="w-32" @change="handlePerPageChange">
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
    
    <div v-loading="loading" element-loading-text="加载中..." class="mb-4">
      <div v-if="results.length > 0">
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <span>注释结果</span>
            </div>
          </template>
          <el-table :data="results" style="width: 100%">
            <el-table-column prop="Chr" label="Chr" width="80"></el-table-column>
            <el-table-column prop="Start" label="Start" width="100"></el-table-column>
            <el-table-column prop="End" label="End" width="100"></el-table-column>
            <el-table-column prop="ID" label="ID" width="150"></el-table-column>
            <el-table-column prop="GO_ID" label="{{ t('go_id') }}" width="150"></el-table-column>
            <el-table-column prop="{{ t('description') }}" label="{{ t('description') }}"></el-table-column>
            <el-table-column prop="Gene_Ontology" label="Gene Ontology" width="150"></el-table-column>
          </el-table>
        </el-card>

        <el-pagination
          v-if="total > perPage"
          v-model:current-page="currentPage"
          v-model:page-size="perPage"
          :page-sizes="[5, 10, 25, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handlePerPageChange"
          @current-change="changePage"
          class="mt-4"
        />
      </div>
      
      <el-alert
        v-else
        type="info"
        title="暂无注释结果"
        show-icon
        class="mb-4"
      />
    </div>
    
    <div class="mt-3">
      <router-link to="/tools/go-annotation">
        <el-button type="default">返回</el-button>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
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