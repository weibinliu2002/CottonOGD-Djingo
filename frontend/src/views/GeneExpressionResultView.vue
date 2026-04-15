<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('gene_expression_analysis_results') }}</h2>
    
    <el-form @submit.prevent="handlePerPageChange" class="mb-3">
      <el-row :gutter="20" align="middle">
        <el-col :span="6">
          <el-form-item :label="t('results_per_page')" label-width="120px">
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
    
    <div v-loading="loading" element-loading-text="Loading..." class="mb-4">
      <div v-if="results.length > 0">
        <el-card class="mb-4">
          <template #header>
            <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
              <span>{{ t('expression_data') }}</span>
              <el-button 
                type="primary" 
                size="small" 
                @click="downloadExpressionData"
                icon="el-icon-download"
              >
                {{ t('download_data') }}
              </el-button>
            </div>
          </template>
          <el-table :data="paginatedResults" style="width: 100%">
            <el-table-column :prop="'geneid'" :label="t('gene_id')" width="180"></el-table-column>
            <el-table-column 
              v-for="tissue in tissues" 
              :key="tissue.value"
              :label="tissue.label"
              min-width="100"
            >
              <template #default="scope">
                <div v-if="scope.row[tissue.value] !== undefined">
                  {{ scope.row[tissue.value].toFixed(4) }}
                </div>
                <div v-else>-</div>
              </template>
            </el-table-column>
          </el-table>
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
        </el-card>
        

        <el-card class="mb-4">
          <template #header>
            <div class="d-flex justify-content-between align-items-center">
              <span>{{ t('expression_level_visualization') }}</span>
              <div>
                <el-button type="primary" size="small" @click="regenerateHeatmap" :loading="heatmapLoading">
                  <el-icon><Refresh /></el-icon> {{ t('regenerate') }}
                </el-button>
                <el-button type="primary" size="small" @click="downloadHeatmap" v-if="heatmapImage">
                  <el-icon><Download /></el-icon> {{ t('download_image') }}
                </el-button>
              </div>
            </div>
          </template>
          
          <!-- 热图控制面板 -->
          <el-collapse class="heatmap-controls mb-3" v-model="activeCollapseItems">
            <el-collapse-item :title="t('heatmap_settings')" name="1">
              <el-form :model="heatmapConfig" label-position="left" label-width="120px" size="small">
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-form-item :label="t('low_color')">
                      <el-color-picker v-model="heatmapConfig.lowColor" show-alpha />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item :label="t('mid_color')">
                      <el-color-picker v-model="heatmapConfig.midColor" show-alpha />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item :label="t('high_color')">
                      <el-color-picker v-model="heatmapConfig.highColor" show-alpha />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="20">
                  <!--<el-col :span="12">
                    <el-form-item :label="t('font_family')">
                      <el-select v-model="heatmapConfig.fontFamily" class="w-full">
                        <el-option label="Arial" value="Arial" />
                        <el-option label="Times New Roman" value="Times New Roman" />
                        <el-option label="Helvetica" value="Helvetica" />
                        <el-option label="SimSun" value="SimSun" />
                        <el-option label="Microsoft YaHei" value="Microsoft YaHei" />
                      </el-select>
                    </el-form-item>
                  </el-col>-->
                  <el-col :span="12">
                    <el-form-item :label="t('font_size')">
                      <el-slider v-model="heatmapConfig.fontSize" :min="8" :max="24" :step="1" show-stops />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item :label="t('use_log2')">
                      <el-switch v-model="heatmapConfig.useLog2" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="Show Values">
                      <el-switch v-model="heatmapConfig.showValues" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="20" v-if="heatmapConfig.useLog2 && heatmapConfig.showValues">
                  <el-col :span="12">
                    <el-form-item label="Value Type">
                      <el-select v-model="heatmapConfig.valueType" class="w-full">
                        <el-option label="Original FPKM" value="original" />
                        <el-option label="Log2(FPKM+1)" value="log2" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
            </el-collapse-item>
          </el-collapse>
          
          <div v-if="heatmapImage" class="heatmap-container mt-3" style="overflow: auto; width: 100%; max-height: 600px; border: 1px solid #e4e7ed; border-radius: 4px;">
            <div style="min-width: 800px; min-height: 500px; display: flex; justify-content: center; align-items: center;">
              <el-image
                :src="`data:image/png;base64,${heatmapImage}`"
                :alt="t('gene_expression_heatmap')"
                fit="contain"
                style="max-width: none; max-height: none;"
              />
            </div>
          </div>
          <el-alert
            v-else-if="visualizationData.length > 0"
            type="info"
            :title="t('no_heatmap_image_available')"
            show-icon
            class="mt-3"
          />
        </el-card>

        
      </div>
      
      <el-alert
        v-else
        type="info"
        :title="t('no_expression_data_available')"
        show-icon
        class="mb-4"
      />
    </div>
    
    <div class="mt-3">
      <router-link to="/tools/gene-expression">
        <el-button type="default">{{ t('back') }}</el-button>
      </router-link>
    </div>
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import httpInstance from '../utils/http'
import { Download } from '@element-plus/icons-vue'
// @ts-ignore - heatmap.js doesn't have proper type definitions
import heatmap from 'heatmap.js'
import { useGeneExpressionStore } from '@/stores/geneExpressionStore'
import { Refresh } from '@element-plus/icons-vue'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()
const geneExpressionStore = useGeneExpressionStore()

// 页面数据
const perPage = ref(10)
const geneList = ref('')
const selectedTissue = ref('')
const currentPage = ref(1)
const total = ref(0)
const heatmapContainer = ref<HTMLElement | null>(null) // 保留用于下载功能
const hoverInfo = ref<{ gene: string; tissue: string; value: number } | null>(null)
const heatmapLoading = ref(false)

// 热图配置
const heatmapConfig = ref({
  lowColor: '#0000FF',
  midColor: '#00FF00',
  highColor: '#FF0000',
  fontFamily: 'Arial',
  fontSize: 12,
  useLog2: false,
  showValues: false,
  valueType: 'original' // 'original' 或 'log2'
})

// 折叠面板默认展开
const activeCollapseItems = ref(['1'])

// 从 store 获取响应式数据
const results = computed(() => {
  const storeResults = geneExpressionStore.results
  // 如果结果是对象且包含expression字段，返回expression数组
  if (typeof storeResults === 'object' && !Array.isArray(storeResults) && storeResults.expression) {
    return storeResults.expression
  }
  // 否则返回原始结果
  return storeResults
})
const loading = computed(() => geneExpressionStore.loading)
const heatmapImage = computed(() => geneExpressionStore.heatmapImage)

// 分页后的数据
const paginatedResults = computed(() => {
  if (!Array.isArray(results.value)) return []
  
  const start = (currentPage.value - 1) * perPage.value
  const end = start + perPage.value
  return results.value.slice(start, end)
})

// 从后端返回的数据中动态获取组织列表
const allTissues = computed(() => {
  // 从 store 获取结果
  const storeResults = geneExpressionStore.results
  
  // 如果结果为空，返回空数组
  if (!storeResults) {
    return []
  }
  
  // 处理对象格式的结果
  if (typeof storeResults === 'object' && !Array.isArray(storeResults)) {
    // 如果对象包含tissues字段，直接使用
    if (storeResults.tissues && Array.isArray(storeResults.tissues)) {
      return storeResults.tissues.map((tissue: string) => ({
        value: tissue,
        label: tissue
      }))
    }
    // 如果对象包含expression字段，从expression中提取
    if (storeResults.expression && Array.isArray(storeResults.expression) && storeResults.expression.length > 0) {
      const firstResult = storeResults.expression[0]
      if (firstResult) {
        // 提取所有非 ID 列名
        const tissueColumns = Object.keys(firstResult).filter(key => 
          key !== 'id_id' && key !== 'geneid' && typeof firstResult[key] === 'number'
        )
        // 转换为组织列表格式
        return tissueColumns.map(col => ({
          value: col,
          label: col
        }))
      }
    }
    return []
  }
  
  // 处理数组格式的结果
  if (Array.isArray(storeResults) && storeResults.length > 0) {
    // 从第一个结果对象中提取列名，排除 id_id 和 geneid
    const firstResult = storeResults[0]
    if (!firstResult) {
      return []
    }
    
    // 提取所有非 ID 列名
    const tissueColumns = Object.keys(firstResult).filter(key => 
      key !== 'id_id' && key !== 'geneid' && typeof firstResult[key] === 'number'
    )
    
    // 转换为组织列表格式
    return tissueColumns.map(col => ({
      value: col,
      label: col
    }))
  }
  
  return []
})

// 使用用户检索指定的组织
const tissues = computed(() => {
  // 从路由参数获取指定的组织
  const tissueParam = route.query.tissue as string || ''
  
  if (tissueParam) {
    // 如果指定了特定组织，返回该组织
    const selectedTissue = allTissues.value.find((t: { value: string; label: string }) => t.value === tissueParam)
    return selectedTissue ? [selectedTissue] : allTissues.value
  } else {
    // 如果没有指定，返回所有组织
    return allTissues.value
  }
})

// 总页数
const totalPages = computed(() => Math.ceil(total.value / perPage.value))

// 可视化数据
const visualizationData = computed(() => {
  // 确保 results.value 是一个数组
  if (!Array.isArray(results.value)) {
    return []
  }
  
  return results.value.map(item => ({
    gene_id: item.geneid || item.gene_id,
    expression: item
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

// 重新生成热图
const regenerateHeatmap = async () => {
  if (!results.value || results.value.length === 0) {
    alert(t('no_expression_data_available'))
    return
  }
  
  heatmapLoading.value = true
  
  try {
    // 准备热图数据
    const heatmapData = {
      genes: results.value.map((item: { geneid: string }) => ({
        gene_id: item.geneid,
        expression: item
      })),
      tissues: tissues.value.map((t: { value: string; label: string }) => t.value),
      config: {
        low_color: heatmapConfig.value.lowColor,
        mid_color: heatmapConfig.value.midColor,
        high_color: heatmapConfig.value.highColor,
        font_family: heatmapConfig.value.fontFamily,
        font_size: heatmapConfig.value.fontSize,
        use_log2: heatmapConfig.value.useLog2,
        show_values: heatmapConfig.value.showValues,
        value_type: heatmapConfig.value.valueType
      }
    }
    
    // 调用后端API重新生成热图
    const response = await httpInstance.post('/CottonOGD_api/regenerate_heatmap/', heatmapData) as any
    
    if (response.success) {
      geneExpressionStore.setHeatmapImage(response.image)
    } else {
      console.error('重新生成热图失败:', response.error)
      alert(t('heatmap_regeneration_failed'))
    }
  } catch (error) {
    console.error('重新生成热图出错:', error)
    alert(t('heatmap_regeneration_error'))
  } finally {
    heatmapLoading.value = false
  }
}

// 下载热图
const downloadHeatmap = () => {
  if (!heatmapImage.value) {
    alert(t('no_heatmap_available_for_download'))
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

// 下载表达量数据
const downloadExpressionData = () => {
  if (!Array.isArray(results.value) || results.value.length === 0) {
    alert(t('no_expression_data_available_for_download'))
    return
  }

  // 获取所有组织列名
  const tissueColumns = tissues.value.map((t: { value: string; label: string }) => t.value)
  
  // 构建CSV表头
  const headers = ['Gene ID', ...tissueColumns]
  
  // 构建CSV行
  const rows = results.value.map((item: { geneid: string; [key: string]: any }) => {
    const row = [item.geneid]
    tissueColumns.forEach((col: string) => {
      row.push(item[col] !== undefined ? item[col] : '-')
    })
    return row
  })
  
  // 组合表头和行
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n')
  
  const bom = new Uint8Array([0xEF, 0xBB, 0xBF])
  const blob = new Blob([bom, csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', 'gene_expression_data.csv')
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
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
  // 从 store 获取查询参数和结果
  const queryParams = geneExpressionStore.queryParams
  const storeResults = geneExpressionStore.results
  
  geneList.value = queryParams.geneList
  selectedTissue.value = queryParams.tissue
  
  // 解析用户输入的基因ID
  const userGeneIds = queryParams.geneList.trim().split(/[\s,]+/).filter(gene => gene.trim())
  
  if (userGeneIds.length === 0) {
    total.value = 0
    return
  }
  
  console.log('用户输入的基因ID:', userGeneIds)
  console.log('从 store 获取的结果:', storeResults)
  console.log('storeResults 是否为数组:', Array.isArray(storeResults))
  
  // 处理结果数据
  if (Array.isArray(storeResults) && storeResults.length > 0) {
    // 假设 storeResults 已经是正确的格式
    total.value = storeResults.length
    console.log('处理后的结果数据:', storeResults)
    console.log('total数据:', total)
  } else if (storeResults && typeof storeResults === 'object') {
    // 如果 storeResults 是一个对象，检查是否包含expression字段
    try {
      if (storeResults.expression && Array.isArray(storeResults.expression)) {
        // 使用expression数组作为结果
        total.value = storeResults.expression.length
        console.log('使用expression数组作为结果:', storeResults.expression)
      } else if (storeResults.genes && Array.isArray(storeResults.genes)) {
        // 使用genes数组作为结果
        total.value = storeResults.genes.length
        console.log('使用genes数组作为结果:', storeResults.genes)
      } else {
        console.error('无效的结果数据格式:', storeResults)
        total.value = 0
      }
    } catch (error) {
      console.error('解析结果数据失败:', error)
      total.value = 0
    }
  } else {
    console.error('没有可用的结果数据')
    total.value = 0
  }
}

// 检查是否有结果数据，如果没有则重定向回输入页面
const checkResults = () => {
  const results = geneExpressionStore.results
  if (!results) {
    console.warn('没有结果数据，重定向回输入页面')
    router.push({
      path: '/tools/gene-expression'
    })
  } else if (Array.isArray(results) && results.length === 0) {
    console.warn('结果数组为空，重定向回输入页面')
    router.push({
      path: '/tools/gene-expression'
    })
  } else if (typeof results === 'object') {
    // 检查对象是否包含有效的数据
    if (!results.expression && !results.genes) {
      console.warn('结果对象不包含有效数据，重定向回输入页面')
      router.push({
        path: '/tools/gene-expression'
      })
    }
  }
}

// 组件挂载时加载数据
onMounted(() => {
  // 先检查是否有结果数据
  checkResults()
  // 然后加载结果数据
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