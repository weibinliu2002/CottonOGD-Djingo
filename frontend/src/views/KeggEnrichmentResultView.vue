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
          <el-table :data="results" style="width: 100%">
            <el-table-column prop="pathway_id" :label="t('pathway_id')" width="120"></el-table-column>
            <el-table-column prop="description.name" :label="t('description')">
              <template #default="scope">
                <div>
                  {{ scope.row.description.name || '' }}
                  <el-tooltip v-if="scope.row.description.definition" :content="scope.row.description.definition" placement="top">
                    <i class="el-icon-info text-muted ml-1"></i>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="gene_ratio" :label="t('gene_ratio')" width="120"></el-table-column>
            <el-table-column prop="bg_ratio" :label="t('bg_ratio')" width="120"></el-table-column>
            <el-table-column :label="t('rich_factor')" width="120">
              <template #default="scope">
                {{ scope.row.rich_factor.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column :label="t('fold_enrichment')" width="150">
              <template #default="scope">
                {{ scope.row.fold_enrichment.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column :label="t('z_score')" width="100">
              <template #default="scope">
                {{ scope.row.z_score.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column :label="t('pvalue')" width="150">
              <template #default="scope">
                {{ scope.row.p_value.toFixed(6) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

// 页面数据
const results = ref<any[]>([])
const hasResults = ref(true)
const isLoading = ref(false)
const errorMessage = ref('')
const executionTime = ref(0)
const plotImage = ref<string | null>(null)
const totalItems = ref(0)

// 使用统一的axios实例
import axios from '../utils/http'

const fetchResults = async () => {
  showLoading?.()
  isLoading.value = true
  try {
    // 从URL参数获取gene_id和p_value_threshold
    const geneId = route.query.gene_id as string || ''
    const pValueThreshold = parseFloat(route.query.p_value_threshold as string || '0.05')
    
    if (!geneId) {
      errorMessage.value = 'Missing gene_id parameter'
      hasResults.value = false
      return
    }
    
    // 使用配置好的axios实例调用后端API获取结果
    const data = await axios.get('/CottonOGD_api/kegg_enrichment/', {
      params: {
        gene_id: geneId,
        p_value_threshold: pValueThreshold
      }
    }) as unknown as any
    console.log('KEGG富集API响应:', data)
    
    // 确保data是一个对象并且有status属性
    if (typeof data === 'object' && data !== null) {
      if (data.status === 'success') {
        const resultData = data.data
        results.value = resultData.results || []
        totalItems.value = results.value.length
        hasResults.value = results.value.length > 0
        executionTime.value = 0
        plotImage.value = resultData.plot_image || null
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
