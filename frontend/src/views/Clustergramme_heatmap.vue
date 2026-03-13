﻿<template>
  <div class="fullscreen-container">
    <div ref="heatmapContainer" id="clustergrammer-root" class="fullscreen-heatmap"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useGeneExpressionStore } from '@/stores/geneExpressionStore'

declare global {
  interface Window {
    d3: any
    Clustergrammer: (args: any) => any
  }
}

const checkClustergrammerLoaded = (): boolean => {
  return typeof window !== 'undefined' && 
         typeof window.d3 !== 'undefined' && 
         typeof window.Clustergrammer === 'function'
}

type ExpressionRow = Record<string, number | string | null | undefined>

const { t } = useI18n()
const router = useRouter()
const geneExpressionStore = useGeneExpressionStore()

const heatmapContainer = ref<HTMLElement | null>(null)
const clustergrammerInstance = ref<any>(null)
const heatmapError = ref('')
const renderToken = ref(0)

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

const backendClustergrammerData = computed<any | null>(() => {
  if (rawResults.value && rawResults.value.clustergrammer_data) {
    return rawResults.value.clustergrammer_data
  }
  return null
})

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

  await nextTick()
  if (token !== renderToken.value) return

  if (!heatmapContainer.value) {
    heatmapError.value = 'Heatmap container not found.'
    return
  }

  if (expressionRows.value.length === 0 || tissueColumns.value.length === 0) {
    heatmapError.value = t('no_expression_data_available')
    cleanupHeatmap()
    return
  }

  if (!checkClustergrammerLoaded()) {
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
  }
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
.fullscreen-container {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  margin: 0;
  padding: 0;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 1000;
}

.fullscreen-heatmap {
  width: 100%;
  height: 100%;
}
</style>
