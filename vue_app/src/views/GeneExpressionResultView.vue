<template>
  <div class="container mt-4">
    <h2 class="mb-4">Gene Expression Analysis Results</h2>
    
    <form @submit.prevent="handlePerPageChange" class="mb-3">
      <div class="row g-2 align-items-center">
        <div class="col-auto">
          <label for="per_page" class="col-form-label">Results per page:</label>
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
          <span class="form-text">records</span>
        </div>
      </div>
    </form>
    
    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border" role="status">
        <span class="sr-only">Loading...</span>
      </div>
    </div>
    
    <div v-else-if="results.length > 0">
      <div class="table-responsive">
        <table class="table table-bordered table-hover">
          <thead class="bg-light">
            <tr>
              <th>Gene ID</th>
              <!--<th>基因名称</th>-->
              <th v-for="tissue in tissues" :key="tissue.value">
                {{ tissue.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in results" :key="item.gene_id">
              <td>{{ item.gene_id }}</td>
              <!--<td>{{ item.gene_name || '-' }}</td>-->
              <td v-for="tissue in tissues" :key="tissue.value">
                <div v-if="item.expression[tissue.value] !== undefined">
                  {{ item.expression[tissue.value].toFixed(4) }}
                </div>
                <div v-else>-</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-4">
        <h4>Expression Level Visualization</h4>
        <div v-if="heatmapImage" class="heatmap-container mt-3 text-center">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <h5 class="mb-0">Gene Expression Heatmap</h5>
            <div>
              <button class="btn btn-sm btn-primary me-2" @click="downloadHeatmap">Download Image</button>
            </div>
          </div>
          <div class="mt-2">
            <img :src="`data:image/png;base64,${heatmapImage}`" alt="Gene Expression Heatmap" class="img-fluid" style="max-width: 100%; height: auto;" />
          </div>
        </div>
        <div v-else-if="visualizationData.length > 0" class="alert alert-info text-center mt-3">
          No heatmap image available
        </div>
        
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
              First
            </a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <a 
              class="page-link" 
              href="#" 
              @click.prevent="changePage(currentPage - 1)"
              :aria-disabled="currentPage === 1"
            >
              Previous
            </a>
          </li>
          
          <li class="page-item active">
            <span class="page-link">
              Page {{ currentPage }} / {{ totalPages }}
            </span>
          </li>
          
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <a 
              class="page-link" 
              href="#" 
              @click.prevent="changePage(currentPage + 1)"
              :aria-disabled="currentPage === totalPages"
            >
              Next
            </a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <a 
              class="page-link" 
              href="#" 
              @click.prevent="changePage(totalPages)"
              :aria-disabled="currentPage === totalPages"
            >
              Last
            </a>
          </li>
        </ul>
      </nav>
    </div>
    
    <div v-else class="alert alert-info">No expression data available</div>
    
    <div class="mt-3">
      <router-link to="/tools/gene-expression" class="btn btn-secondary">Back</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import httpInstance from '../utils/http'
// @ts-ignore - heatmap.js doesn't have proper type definitions
import heatmap from 'heatmap.js'

const route = useRoute()

// 页面数据
const perPage = ref(10)
const geneList = ref('')
const selectedTissue = ref('')
const results = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const total = ref(0)
const heatmapImage = ref<string>('') // 存储后端生成的热图
const heatmapContainer = ref<HTMLElement | null>(null) // 保留用于下载功能
const hoverInfo = ref<{ gene: string; tissue: string; value: number } | null>(null)

// 组织列表 - 与后端保持一致
const allTissues = [
  // Top tissues
  { value: 'Root', label: 'Root' },
  { value: 'Stem', label: 'Stem' },
  { value: 'Cotyledon', label: 'Cotyledon' },
  { value: 'Leaf', label: 'Leaf' },
  { value: 'Pholem', label: 'Pholem' },
  { value: 'Sepal', label: 'Sepal' },
  { value: 'Bract', label: 'Bract' },
  { value: 'Petal', label: 'Petal' },
  { value: 'Anther', label: 'Anther' },
  { value: 'Stigma', label: 'Stigma' },
  // Bottom left tissues
  { value: '0_DPA_ovules', label: '0_DPA_ovules' },
  { value: '3_DPA_fibers', label: '3_DPA_fibers' },
  { value: '6_DPA_fibers', label: '6_DPA_fibers' },
  { value: '9_DPA_fibers', label: '9_DPA_fibers' },
  { value: '12_DPA_fibers', label: '12_DPA_fibers' },
  { value: '15_DPA_fibers', label: '15_DPA_fibers' },
  { value: '18_DPA_fibers', label: '18_DPA_fibers' },
  { value: '21_DPA_fibers', label: '21_DPA_fibers' },
  { value: '24_DPA_fibers', label: '24_DPA_fibers' },
  // Bottom right tissues
  { value: 'DPA0', label: 'DPA0' },
  { value: '5_DPA_ovules', label: '5_DPA_ovules' },
  { value: '10_DPA_ovules', label: '10_DPA_ovules' },
  { value: '20_DPA_ovules', label: '20_DPA_ovules' },
  { value: 'Seed', label: 'Seed' }
]

// 使用用户检索指定的组织
const tissues = computed(() => {
  // 从路由参数获取指定的组织
  const tissueParam = route.query.tissue as string || ''
  
  if (tissueParam) {
    // 如果指定了特定组织，返回该组织
    const selectedTissue = allTissues.find(t => t.value === tissueParam)
    return selectedTissue ? [selectedTissue] : allTissues
  } else {
    // 如果没有指定，返回所有组织
    return allTissues
  }
})

// 总页数
const totalPages = computed(() => Math.ceil(total.value / perPage.value))

// 可视化数据
const visualizationData = computed(() => {
  return results.value.map(item => ({
    gene_id: item.gene_id,
    expression: item.expression
  }))
})



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

// 热图相关功能已迁移到后端，前端不再需要绘制热图
// 使用后端生成的热图图片进行展示

// 下载热图
const downloadHeatmap = () => {
  if (!heatmapImage.value) {
    alert('No heatmap available for download')
    return
  }

  // Create download link
  const link = document.createElement('a')
  link.href = `data:image/png;base64,${heatmapImage.value}`
  link.download = 'gene_expression_heatmap.png'
  
  // Trigger download
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// 测试热图绘制
// 测试热图功能已移除，改为使用后端生成的热图

// 监听数据变化，更新热图
watch([results, tissues, visualizationData], () => {
  // 当数据变化时，热图会通过loadResults重新获取，无需手动绘制
  console.log('数据变化，热图将通过API重新获取')
}, { deep: true })

// 加载结果数据
const loadResults = async () => {
  loading.value = true
  
  try {
    // 从路由参数获取查询条件
    const geneListParam = route.query.gene_list as string || ''
    const tissueParam = route.query.tissue as string || ''
    geneList.value = geneListParam
    selectedTissue.value = tissueParam
    
    // 解析用户输入的基因ID
    const userGeneIds = geneListParam.trim().split(/[,\s]+/).filter(gene => gene.trim())
    
    if (userGeneIds.length === 0) {
      results.value = []
      total.value = 0
      heatmapImage.value = ''
      loading.value = false
      return
    }
    
    console.log('用户输入的基因ID:', userGeneIds)
    
    // 调用后端API获取数据和热图
    // 准备表单数据 - 使用URL编码格式而非JSON，避免CSRF问题
    let formDataParts = [`gene_ids=${encodeURIComponent(userGeneIds.join('\n'))}`]
    
    // 根据路由参数确定要请求的组织
    if (selectedTissue.value) {
      // 如果指定了特定组织，只请求该组织
      formDataParts.push(`top_columns=${encodeURIComponent(selectedTissue.value)}`)
    } else {
      // 如果没有指定，请求所有组织
      // 注意：这里应该与后端保持一致，使用相同的组织列表
      const allTissues = ['Root', 'Stem', 'Cotyledon', 'Leaf', 'Pholem', 'Sepal', 'Bract', 'Petal', 'Anther', 'Stigma', '0_DPA_ovules', '3_DPA_fibers', '6_DPA_fibers', '9_DPA_fibers', '12_DPA_fibers', '15_DPA_fibers', '18_DPA_fibers', '21_DPA_fibers', '24_DPA_fibers', 'DPA0', '5_DPA_ovules', '10_DPA_ovules', '20_DPA_ovules', 'Seed']
      allTissues.forEach(tissue => {
        formDataParts.push(`top_columns=${encodeURIComponent(tissue)}`)
      })
    }
    
    const formDataString = formDataParts.join('&')
    
    // 使用httpInstance发送请求，与IdSearchView.vue保持一致
    const response = await httpInstance.post('/tools/gene_expression/gene_expression/', formDataString, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json' // 添加Accept头，确保后端识别为API请求
      }
    })
    
    console.log('API响应:', response)
    
    // 由于httpInstance的响应拦截器已经处理了response.data，添加类型断言
    const apiResponse = response as any
    
    if (apiResponse.success) {
      const data = apiResponse.data
      
      // 处理结果数据
      const apiResults = userGeneIds.map(geneId => {
        // 查找当前基因的数据索引
        const geneIndex = data.gene_ids?.indexOf(geneId) ?? -1
        
        if (geneIndex >= 0) {
          // 构建表达数据对象
          const expression: Record<string, number> = {}
          data.columns?.forEach((col: string, index: number) => {
            expression[col] = data.heatmap_data?.[geneIndex]?.[index] || 0
          })
          
          return {
            gene_id: geneId,
            gene_name: geneId,
            expression
          }
        } else {
          return {
            gene_id: geneId,
            gene_name: geneId,
            expression: {}
          }
        }
      })
      
      results.value = apiResults
      total.value = apiResults.length
      heatmapImage.value = data.heatmap_image // 设置后端生成的热图
      
      console.log('处理后的结果数据:', results.value)
      console.log('后端生成的热图:', heatmapImage.value ? '已获取' : '未获取')
    } else {
      console.error('API请求失败:', apiResponse.error)
      results.value = []
      total.value = 0
      heatmapImage.value = ''
    }
  } catch (error) {
    console.error('加载结果失败:', error)
    results.value = []
    total.value = 0
    heatmapImage.value = ''
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

/* 热图容器样式 */
.heatmap-container {
  margin-top: 1rem;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  padding: 1rem;
  background-color: #f8f9fa;
  overflow-x: auto;
  min-height: 250px;
  width: 100%;
  max-width: 100%;
}

.heatmap-wrapper {
  display: flex;
  width: 100%;
  overflow-x: auto;
}

.heatmap-wrapper > div {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
}

/* 基因标签样式 */
.gene-labels {
  margin-right: 10px;
  white-space: nowrap;
  min-width: 150px;
}

.gene-label {
  height: 25px; /* 每个基因固定高度 */
  line-height: 25px;
  font-size: 11px;
  text-align: right;
  padding-right: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
}

/* 热图内容样式 */
.heatmap-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 组织标签样式 */
.tissue-labels {
  display: flex;
  margin-bottom: 5px;
  transform-origin: left top;
  overflow: visible;
  padding-bottom: 50px; /* 为倾斜标签预留空间 */
}

.tissue-label {
  width: 60px; /* 增加宽度以容纳倾斜文本 */
  height: 25px;
  line-height: 25px;
  font-size: 11px;
  text-align: center;
  margin-right: 0;
  white-space: nowrap;
  overflow: visible;
  transform: rotate(-45deg); /* 倾斜45度 */
  transform-origin: left bottom;
  position: relative;
  left: 0;
  top: 0;
  box-sizing: border-box;
  padding: 0 5px;
}

/* 热图样式 */
.heatmap {
  display: flex;
  flex-direction: column;
  border: 1px solid #dee2e6;
  background-color: white;
  position: relative;
  overflow: hidden;
  padding: 0;
  margin: 0;
  width: auto;
  min-width: 0;
  min-height: 200px;
}

/* 确保热图表格和单元格正确显示 */
.heatmap table {
  border-collapse: collapse;
  width: auto;
  height: auto;
  margin: 0;
  padding: 0;
  display: block;
}

.heatmap td {
  width: 25px !important; /* 固定每个单元格宽度 */
  height: 25px !important; /* 固定每个单元格高度，与基因标签高度一致 */
  padding: 0 !important;
  border: 1px solid #eee !important;
  cursor: pointer !important;
  box-sizing: border-box !important;
  background-color: #f0f0f0 !important;
  font-size: 0; /* 隐藏单元格内容，只显示颜色 */
}

.heatmap tr {
  height: 25px !important; /* 固定每行高度，与基因标签高度一致 */
  display: table-row !important;
  box-sizing: border-box !important;
}

/* 颜色刻度样式 */
.color-scale {
  margin-top: 10px;
  display: flex;
  align-items: center;
}

.color-scale-label {
  font-size: 12px;
  margin-right: 10px;
  white-space: nowrap;
}

.color-scale-gradient {
  flex: 1;
  height: 20px;
  background: linear-gradient(to right, #0000ff, #00ffff, #00ff00, #ffff00, #ff8800, #ff0000);
  border: 1px solid #dee2e6;
}

.color-scale-values {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  width: 100%;
}

.color-scale-values span {
  font-size: 10px;
  min-width: 30px;
  text-align: center;
}
</style>