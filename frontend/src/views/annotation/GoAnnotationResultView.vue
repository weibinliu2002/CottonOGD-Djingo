<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('go_annotation_result') }}</h2>
    
    <!-- 可视化图表 -->
    <el-card class="mb-4" v-if="chart">
      <template #header>
        <div class="card-header">
          <span>{{ t('go_annotation') }}</span>
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
          <el-form-item :label="t('per_page')" label-width="80px">
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
    
    <div v-loading="loading" :element-loading-text="t('loading')" class="mb-4">
      <div v-if="allResults.length > 0">
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <span>{{ t('annotation_results') }}</span>
            </div>
          </template>
          <el-table
            :data="table.pagedData"
            style="width: 100%"
            @sort-change="table.handleSortChange"
          >
            <el-table-column prop="Chr" :label="t('chromosome')" width="80" sortable="custom" />
            <el-table-column prop="Start" :label="t('start_position')" width="100" sortable="custom" />
            <el-table-column prop="End" :label="t('end_position')" width="100" sortable="custom" />
            <el-table-column prop="Gene_ID" :label="t('gene_id')" width="150" sortable="custom" />
            <el-table-column prop="GO_ID" :label="t('go_id')" width="150" sortable="custom" />
            <el-table-column prop="Description" :label="t('description')" sortable="custom" />
            <el-table-column prop="Gene_Ontology" :label="t('go_category')" width="150" sortable="custom" />
          </el-table>
        </el-card>

        <!-- 关键词筛选 + 计数 + 导出（阶段 3.2 新增，不改变下方原有分页行为） -->
        <TableToolbar
          v-model="table.keyword"
          :total="table.total"
          :columns="exportColumns"
          :rows="table.sortedRows"
          filename="go_annotation_results.csv"
          class="mt-4"
        />

        <el-pagination
          v-if="table.total > table.pageSize"
          v-model:current-page="table.currentPage"
          v-model:page-size="table.pageSize"
          :page-sizes="table.pageSizes"
          layout="total, sizes, prev, pager, next, jumper"
          :total="table.total"
          @size-change="table.handleSizeChange"
          @current-change="table.handleCurrentChange"
          class="mt-4"
        />
      </div>
      
      <el-alert
        v-else
        type="info"
        :title="t('no_annotation_results')"
        show-icon
        class="mb-4"
      />
    </div>
    
    <div class="mt-3">
      <router-link to="/tools/go-annotation">
        <el-button type="default">{{ t('back') }}</el-button>
      </router-link>
    </div>
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { ref, computed, onMounted, inject, watch } from 'vue'
import { useRoute } from 'vue-router'
import httpInstance from '@/utils/http.js'
import { useEnrichmentStore } from '@/stores/modules/enrichment'
import { useEnhancedTable } from '@/composables/core/useEnhancedTable'
import type { ExportColumn } from '@/utils/exportTable'

const route = useRoute()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined
const enrichmentStore = useEnrichmentStore()

// 页面数据
const perPage = ref(10)
const geneList = ref('')
const allResults = ref<any[]>([])  // 存储全部数据
const loading = ref(false)
const currentPage = ref(1)
const total = ref(0)
const chart = ref<string>('')
const hasResults = ref<boolean>(true)

// 分页后的结果（前端分页，不重新请求）
const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * perPage.value
  const end = start + perPage.value
  return allResults.value.slice(start, end)
})

/**
 * 表格增强（阶段 3.2）
 *
 * 在原分页逻辑之上叠加「关键词筛选 + 列排序 + 导出」。
 * 保留 perPage/currentPage/total/paginatedResults 等原有状态，
 * 仅将 el-table 与 el-pagination 改绑到 table.*，行为保持一致。
 */
type GoRow = Record<string, any>

const table = useEnhancedTable<GoRow>(allResults, {
  pageSize: perPage.value,
  pageSizes: [5, 10, 25, 50],
  searchFields: ['Gene_ID', 'GO_ID', 'Description', 'Gene_Ontology', 'Chr'],
})

// 与原 perPage 联动：原下拉修改 perPage 时同步到增强分页
watch(perPage, (size) => {
  table.pageSize.value = size
})

/** 导出列定义 */
const exportColumns: ExportColumn<GoRow>[] = [
  { key: 'Chr', label: 'Chr' },
  { key: 'Start', label: 'Start' },
  { key: 'End', label: 'End' },
  { key: 'Gene_ID', label: 'Gene ID' },
  { key: 'GO_ID', label: 'GO ID' },
  { key: 'Description', label: 'Description' },
  { key: 'Gene_Ontology', label: 'Gene Ontology' },
]

// 总页数
const totalPages = computed(() => Math.ceil(total.value / perPage.value))

// 处理每页显示条数变更（前端分页，不重新请求）
const handlePerPageChange = () => {
  currentPage.value = 1
  // 不需要重新请求，只更新分页显示
}

// 切换页面（前端分页，不重新请求）
const changePage = (page: number) => {
  currentPage.value = page
  // 不需要重新请求，只更新分页显示
}

// 加载结果数据（只在初始化时调用一次）
const loadResults = async () => {
  showLoading?.()
  loading.value = true
  
  // 从路由参数获取查询条件
  const geneListParam = route.query.gene_id as string || ''
  geneList.value = geneListParam
  
  // 添加调试信息
  console.log('=== GO注释结果页面调试信息 ===')
  console.log('路由参数:', route.query)
  console.log('获取的gene_id参数:', geneListParam)
  console.log('gene_id参数长度:', geneListParam.length)
  
  try {
    // 检查是否有基因列表参数
    if (!geneListParam) {
      console.log('没有获取到gene_list参数')
      allResults.value = []
      total.value = 0
      chart.value = ''
      hasResults.value = false
      return
    }
    
    // 从 store 获取基因组信息
    const genomeId = enrichmentStore.selectedGenome || ''
    console.log('获取的基因组:', genomeId)
    
    // 调用后端API获取数据（只调用一次）
    console.log('准备调用API')
    const responseData = await httpInstance.get('/CottonOGD_api/go_annotation/', {
      params: {
        gene_id: geneListParam,
        genome_id: genomeId
      }
    }) as any
    
    console.log('API调用成功')
    console.log('API响应数据:', responseData)
    
    // 由于axios拦截器直接返回response.data，所以responseData就是后端返回的data对象
    if (responseData && responseData.status === 'success') {
      console.log('API响应成功')
      const data = responseData.data
      console.log('数据对象:', data)
      console.log('结果数组:', data.results)
      console.log('结果数量:', data.results ? data.results.length : 0)
      console.log('是否有图表:', data.chart ? '是' : '否')
      
      // 存储全部结果数据（用于前端分页）
      allResults.value = data.results || []
      total.value = allResults.value.length || 0
      chart.value = data.chart || ''
      
      // 更新hasResults变量
      hasResults.value = allResults.value.length > 0
      console.log('是否有结果:', hasResults.value)
    } else {
      console.log('API响应失败或success为false')
      console.log('响应数据:', responseData)
      allResults.value = []
      total.value = 0
      chart.value = ''
      hasResults.value = false
    }
  } catch (error) {
    console.error('加载结果失败:', error)
    allResults.value = []
    total.value = 0
    chart.value = ''
    hasResults.value = false
  } finally {
    loading.value = false
    hideLoading?.()
  }
}

// 组件挂载时加载数据（只加载一次）
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
