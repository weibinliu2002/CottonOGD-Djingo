<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('gene_expression_analysis_results') }}</h2>

    <el-form class="mb-3">
      <el-row :gutter="20" align="middle">
        <el-col :span="6">
          <el-form-item :label="t('results_per_page')" label-width="120px">
            <el-select v-model.number="perPage" class="w-32" @change="handlePerPageChange">
              <el-option :value="5" label="5" />
              <el-option :value="10" label="10" />
              <el-option :value="25" label="25" />
              <el-option :value="50" label="50" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="4">
          <span class="text-gray-500">{{ t('records') }}</span>
        </el-col>
      </el-row>
    </el-form>

    <div v-loading="loading" element-loading-text="Loading..." class="mb-4">
      <template v-if="expressionRows.length > 0">
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <span>{{ t('expression_data') }}</span>
              <el-button type="primary" size="small" @click="downloadExpressionData">
                <el-icon><Download /></el-icon>
                {{ t('download_data') }}
              </el-button>
            </div>
          </template>

          <el-table :data="paginatedResults" style="width: 100%">
            <el-table-column prop="geneid" :label="t('gene_id')" width="220" />
            <el-table-column
              v-for="tissue in tissueColumns"
              :key="tissue"
              :label="tissue"
              min-width="110"
            >
              <template #default="scope">
                <span v-if="scope.row[tissue] !== undefined && scope.row[tissue] !== null">
                  {{ Number(scope.row[tissue]).toFixed(4) }}
                </span>
                <span v-else>-</span>
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
            <div class="card-header">
              <span>{{ t('expression_level_visualization') }}</span>
              <div class="card-actions">
                <el-button type="primary" size="small" @click="renderHeatmap" :loading="heatmapLoading">
                  <el-icon><Refresh /></el-icon>
                  {{ t('regenerate') }}
                </el-button>
                <el-button type="primary" size="small" @click="downloadHeatmapAsSvg">
                  <el-icon><Download /></el-icon>
                  {{ t('download_image') }}
                </el-button>
              </div>
            </div>
          </template>

          <el-alert
            v-if="heatmapError"
            type="error"
            :title="heatmapError"
            show-icon
            class="mb-3"
          />

          <div class="heatmap-wrapper">
            <div ref="heatmapContainer" id="clustergrammer-root" class="heatmap-container"></div>
          </div>
        </el-card>
      </template>

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
        <el-button>{{ t('back') }}</el-button>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Download, Refresh } from '@element-plus/icons-vue'
import { useGeneExpressionStore } from '@/stores/geneExpressionStore'

declare global {
  interface Window {
    d3: any
    Clustergrammer: (args: any) => any
  }
}

// 检查Clustergrammer是否已加载（从index.html加载）
const checkClustergrammerLoaded = (): boolean => {
  return typeof window !== 'undefined' && 
         typeof window.d3 !== 'undefined' && 
         typeof window.Clustergrammer === 'function'
}

type ExpressionRow = Record<string, number | string | null | undefined>

const { t } = useI18n()
const router = useRouter()
const geneExpressionStore = useGeneExpressionStore()

const perPage = ref(10)
const currentPage = ref(1)
const heatmapContainer = ref<HTMLElement | null>(null)
const clustergrammerInstance = ref<any>(null)
const heatmapLoading = ref(false)
const heatmapError = ref('')
const renderToken = ref(0)
const clustergrammerReady = ref(false)

const loading = computed(() => geneExpressionStore.loading)
const rawResults = computed<any>(() => geneExpressionStore.results)

const expressionRows = computed<ExpressionRow[]>(() => {
  if (rawResults.value && Array.isArray(rawResults.value.expression)) {
    return rawResults.value.expression
  }
  if (Array.isArray(rawResults.value)) {
    return rawResults.value
  }
  return []
})

const tissueColumns = computed<string[]>(() => {
  if (rawResults.value && Array.isArray(rawResults.value.tissues)) {
    return rawResults.value.tissues
  }
  const first = expressionRows.value[0]
  if (!first) return []
  return Object.keys(first).filter((key) => key !== 'id_id' && key !== 'geneid' && key !== 'gene_id')
})

const total = computed(() => expressionRows.value.length)

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * perPage.value
  return expressionRows.value.slice(start, start + perPage.value)
})

const backendClustergrammerData = computed<any | null>(() => {
  if (rawResults.value && rawResults.value.clustergrammer_data) {
    return rawResults.value.clustergrammer_data
  }
  return null
})

const handlePerPageChange = () => {
  currentPage.value = 1
}

const changePage = (page: number) => {
  currentPage.value = page
}

const cleanupHeatmap = () => {
  if (clustergrammerInstance.value && typeof clustergrammerInstance.value.destroy === 'function') {
    try {
      clustergrammerInstance.value.destroy()
    } catch {
      // ignore destroy failures from third-party library
    }
  }
  clustergrammerInstance.value = null
  if (heatmapContainer.value) {
    heatmapContainer.value.innerHTML = ''
  }
}

const buildNetworkDataFromExpression = () => {
  const rows = expressionRows.value
  const cols = tissueColumns.value
  return {
    row_nodes: rows.map((row, index) => ({
      name: String(row.geneid ?? row.gene_id ?? `gene_${index + 1}`),
      ini: index
    })),
    col_nodes: cols.map((name, index) => ({
      name,
      ini: index
    })),
    mat: rows.map((row) =>
      cols.map((col) => {
        const value = Number(row[col] ?? 0)
        return Number.isFinite(value) ? value : 0
      })
    )
  }
}

const renderHeatmap = async () => {
  renderToken.value += 1
  const token = renderToken.value

  heatmapLoading.value = true
  heatmapError.value = ''

  await nextTick()
  if (token !== renderToken.value) return

  if (!heatmapContainer.value) {
    heatmapLoading.value = false
    heatmapError.value = 'Heatmap container not found.'
    return
  }

  if (expressionRows.value.length === 0 || tissueColumns.value.length === 0) {
    heatmapLoading.value = false
    heatmapError.value = t('no_expression_data_available')
    cleanupHeatmap()
    return
  }

  if (!checkClustergrammerLoaded()) {
    heatmapLoading.value = false
    heatmapError.value = 'Clustergrammer is not loaded. Please refresh the page.'
    return
  }

  try {
    cleanupHeatmap()

    const networkData = backendClustergrammerData.value ?? buildNetworkDataFromExpression()
    clustergrammerInstance.value = window.Clustergrammer({
      root: '#clustergrammer-root',
      network_data: networkData
    })
  } catch (error: any) {
    heatmapError.value = error?.message || 'Failed to render heatmap.'
  } finally {
    heatmapLoading.value = false
  }
}

const downloadExpressionData = () => {
  if (expressionRows.value.length === 0) return

  const headers = ['geneid', ...tissueColumns.value]
  const lines = expressionRows.value.map((row) => {
    const values = [String(row.geneid ?? row.gene_id ?? '')]
    for (const col of tissueColumns.value) {
      const value = row[col]
      values.push(value === undefined || value === null ? '' : String(value))
    }
    return values.join(',')
  })

  const csv = [headers.join(','), ...lines].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'gene_expression_data.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const downloadHeatmapAsSvg = () => {
  if (!heatmapContainer.value) return
  const svg = heatmapContainer.value.querySelector('svg')
  if (!svg) return

  const serializer = new XMLSerializer()
  const source = serializer.serializeToString(svg)
  const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'gene_expression_heatmap.svg'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const ensureResultsExist = () => {
  if (expressionRows.value.length === 0) {
    router.push({ path: '/tools/gene-expression' })
  }
}

watch([expressionRows, tissueColumns, backendClustergrammerData], () => {
  if (expressionRows.value.length > 0) {
    renderHeatmap()
  }
})

onMounted(() => {
  ensureResultsExist()
  if (expressionRows.value.length > 0) {
    renderHeatmap()
  }
})

onBeforeUnmount(() => {
  cleanupHeatmap()
})
</script>

<style scoped>
.container {
  max-width: 1200px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.heatmap-wrapper {
  width: 100%;
  min-height: 640px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: auto;
}

.heatmap-container {
  width: 100%;
  min-width: 1200px;
  min-height: 620px;
}

/* Clustergrammer sidebar control styles */
:deep(.clustergrammer-container .sidebar_wrapper) {
  min-width: 180px !important;
  width: 180px !important;
}

:deep(.clustergrammer-container .sidebar_wrapper .sidebar_text) {
  font-size: 12px !important;
}

:deep(.clustergrammer-container .sidebar_wrapper button) {
  font-size: 11px !important;
  padding: 4px 8px !important;
}
</style>