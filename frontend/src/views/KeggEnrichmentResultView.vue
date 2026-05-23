<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('kegg_pathway_enrichment_analysis_results') }}</h2>
    
    <!-- 返回按钮 -->
    <router-link to="/tools/kegg-enrichment" class="mb-3">
      <el-button type="default">{{ t('back') }}</el-button>
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
        :title="t('no_kegg_enrichment_results')"
        show-icon
        class="mb-4"
      />
      
      <!-- 图表区域 (即使无显著结果也显示) -->
      <el-card v-if="plotImage" class="mb-4">
        <template #header>
          <div class="card-header">
            <span>{{ t('kegg_enrichment_plot') }}</span>
          </div>
        </template>
        <div class="text-center">
          <el-image
            :src="'data:image/png;base64,' + plotImage"
            :alt="t('kegg_enrichment_plot')"
            fit="contain"
            class="w-full"
          />
        </div>
      </el-card>
      
      <!-- 显著结果表格 (只有有结果时才显示) -->
      <div v-if="hasResults">
        <el-card class="mb-5">
          <template #header>
            <div class="d-flex justify-content-between align-items-center">
              <h4 class="text-danger m-0">{{ t('kegg_pathways') }}</h4>
            <el-tag type="info">({{ t('total') }} {{ totalItems }} {{ t('records') }})</el-tag>
            </div>
          </template>
          
          <!-- 表格区域 -->
          <el-table :data="paginatedResults" style="width: 100%">
            <el-table-column prop="pathway_id" :label="t('pathway_id')" width="120"></el-table-column>
            <el-table-column prop="description.name" :label="t('description')">
              <template #default="scope">
                <div>
                  {{ scope.row.description?.name || '' }}
                  <el-tooltip v-if="scope.row.description?.definition" :content="scope.row.description.definition" placement="top">
                    <i class="el-icon-info text-muted ml-1"></i>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="gene_ratio" :label="t('gene_ratio')" width="120"></el-table-column>
            <el-table-column prop="bg_ratio" :label="t('bg_ratio')" width="120"></el-table-column>
            <el-table-column :label="t('rich_factor')" width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.rich_factor || 0).toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column :label="t('fold_enrichment')" width="150">
              <template #default="scope">
                {{ parseFloat(scope.row.fold_enrichment || 0).toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column :label="t('z_score')" width="100">
              <template #default="scope">
                {{ parseFloat(scope.row.z_score || 0).toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column :label="t('pvalue')" width="150">
              <template #default="scope">
                {{ parseFloat(scope.row.p_value || 0).toFixed(6) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
        
        <!-- 分页组件 (只有总数大于10时显示) -->
        <div v-if="totalItems > 10" class="pagination-container">
          <el-pagination
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
            :current-page="currentPage"
            :page-sizes="[10, 25, 50]"
            :page-size="perPage"
            :total="totalItems"
            layout="total, sizes, prev, pager, next, jumper"
          />
        </div>
      </div>
    </div>
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useEnrichmentStore } from '@/stores/enrichmentStore'

const { t } = useI18n()
const router = useRouter()
const enrichmentStore = useEnrichmentStore()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

// 页面数据
const allResults = ref<any[]>([])
const hasResults = ref(true)
const isLoading = ref(false)
const errorMessage = ref('')
const executionTime = ref(0)
const plotImage = ref<string | null>(null)
const totalItems = ref(0)

// 分页数据
const currentPage = ref(1)
const perPage = ref(10)

// 分页后的结果
const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * perPage.value
  const end = start + perPage.value
  return allResults.value.slice(start, end)
})

// 使用统一的axios实例
import axios from '../utils/http'

const fetchResults = async () => {
  showLoading?.()
  isLoading.value = true
  try {
    // 从Pinia store获取数据
    const geneId = enrichmentStore.geneList || ''
    const genomeId = enrichmentStore.selectedGenome || ''
    const pValueThreshold = enrichmentStore.pValue || 0.05
    const qValueThreshold = enrichmentStore.qValue || 0.05
    
    console.log('从store获取的数据:', { geneId, genomeId, pValueThreshold, qValueThreshold })
    
    if (!geneId) {
      errorMessage.value = 'Missing gene_id parameter'
      hasResults.value = false
      // 如果store中没有数据，返回上一页
      router.push({ name: 'KeggEnrichment' })
      return
    }
    
    // 使用multipart/form-data格式发送请求（根据API文档）
    const formData = new FormData()
    formData.append('gene_id', geneId)
    formData.append('genome_id', genomeId)
    formData.append('p_value_threshold', String(pValueThreshold))
    formData.append('q_value_threshold', String(qValueThreshold))
    
    // 使用配置好的axios实例调用后端API获取结果
    const data = await axios.post('/CottonOGD_api/kegg_enrichment/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }) as unknown as any
    console.log('KEGG富集API响应:', data)
    
    // 确保data是一个对象并且有status属性
    if (typeof data === 'object' && data !== null) {
      if (data.status === 'success') {
        const resultData = data.data
        // 解析description字段（如果是字符串）
        allResults.value = (resultData.results || []).map((item: any) => {
          if (typeof item.description === 'string') {
            try {
              item.description = JSON.parse(item.description)
            } catch (error) {
              console.error('解析description失败:', error)
              item.description = { name: item.description, definition: '' }
            }
          }
          return item
        })
        totalItems.value = allResults.value.length
        hasResults.value = allResults.value.length > 0
        executionTime.value = 0
        plotImage.value = resultData.plot_image || null
        
        console.log('解析后的结果数据:', allResults.value)
      } else {
        errorMessage.value = data.error || 'Failed to get results'
        hasResults.value = false
      }
    } else {
      errorMessage.value = 'Invalid API response'
      hasResults.value = false
    }
  } catch (error: any) {
    errorMessage.value = 'Failed to get results: ' + (error.message || error)
    console.error('Error fetching results:', error)
    hasResults.value = false
  } finally {
    isLoading.value = false
    hideLoading?.()
  }
}

// 每页条数变更（前端分页，不重新请求）
const handleSizeChange = (size: number) => {
  perPage.value = size
  currentPage.value = 1
}

// 当前页变更（前端分页，不重新请求）
const handleCurrentChange = (page: number) => {
  currentPage.value = page
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

.pagination-container {
  display: flex;
  justify-content: center;
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
