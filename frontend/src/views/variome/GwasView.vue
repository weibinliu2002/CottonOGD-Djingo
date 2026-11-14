<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('variome_gwas') }}</h2>
    <p class="text-muted mb-4">{{ t('module_variome_desc') }}</p>

    <el-card class="mb-4">
      <template #header><div class="card-header">{{ t('trait') }}</div></template>
      <el-form @submit.prevent="handleLoad" label-width="180px">
        <el-form-item :label="t('trait')">
          <el-select v-model="trait" :placeholder="t('trait')" style="width: 100%" :loading="traitsLoading" filterable>
            <el-option v-for="tr in traits" :key="tr.trait" :label="tr.trait" :value="tr.trait" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" class="ms-2">
            <el-icon><Search /></el-icon>{{ t('view_markers') }}
          </el-button>
          <el-button type="success" size="small" class="ms-2" @click="handlePhenotype">{{ t('view_phenotype') }}</el-button>
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" show-icon class="mt-3" @close="error = ''" />
      </el-form>
    </el-card>

    <el-card v-if="showPhenotype" class="mb-4">
      <template #header><div class="card-header">{{ t('single_trait_distribution') }}</div></template>
      <div ref="phenoRef" class="chart-box"></div>
    </el-card>

    <el-card v-if="markers.length" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>{{ t('gwas_markers') }}</span>
          <el-tag type="info">{{ t('found') }} {{ markersTotal }} {{ t('records') }}</el-tag>
        </div>
      </template>

      <el-table :data="markerTable.pagedData" style="width: 100%" @sort-change="markerTable.handleSortChange">
        <el-table-column prop="snp" :label="t('snp')" width="200" sortable="custom" />
        <el-table-column prop="chr" :label="t('chromosome')" width="140" sortable="custom" />
        <el-table-column prop="pos" :label="t('position')" width="140" sortable="custom" />
        <el-table-column prop="pvalue" :label="t('pvalue')" width="140" sortable="custom" />
        <el-table-column prop="effect" :label="t('effect')" width="120" sortable="custom" />
        <el-table-column prop="maf" :label="t('maf')" width="100" sortable="custom" />
      </el-table>

      <TableToolbar
        v-model="markerTable.keyword"
        :total="markerTable.total"
        :columns="markerColumns"
        :rows="markerTable.sortedRows"
        filename="gwas_markers.csv"
        class="mt-3"
      />

      <div v-if="markerTable.total > markerTable.pageSize" class="pagination-container">
        <el-pagination
          v-model:current-page="markerTable.currentPage"
          v-model:page-size="markerTable.pageSize"
          :page-sizes="markerTable.pageSizes"
          layout="total, sizes, prev, pager, next, jumper"
          :total="markerTable.total"
        />
      </div>
    </el-card>

    <el-empty v-else-if="markersSearched && !loading" :description="t('no_data')" />

    <el-card v-if="associations.length" class="mb-4">
      <template #header><div class="card-header">{{ t('gwas_associations') }}</div></template>
      <div ref="manhattanRef" class="chart-box"></div>
    </el-card>
    <el-alert
      v-else-if="assocSearched && !loading && !associations.length"
      :title="t('gwas_no_association')"
      type="info"
      :closable="false"
      class="mb-4"
    />

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import echarts from '@/utils/echarts'
import {
  getGwasTraits,
  getGwasMarkers,
  getGwasAssociations,
  getGwasPhenotype,
  type GwasTrait,
  type GwasAssociation,
} from '@/api/index'
import { useEnhancedTable } from '@/composables/core/useEnhancedTable'
import type { ExportColumn } from '@/utils/exportTable'

const { t } = useI18n()

const traits = ref<GwasTrait[]>([])
const traitsLoading = ref(false)
const trait = ref('')
const loading = ref(false)
const error = ref('')

const markers = ref<GwasAssociation[]>([])
const markersTotal = ref(0)
const markersSearched = ref(false)
const assocSearched = ref(false)
const associations = ref<GwasAssociation[]>([])
const showPhenotype = ref(false)

const phenoRef = ref<HTMLElement | null>(null)
const manhattanRef = ref<HTMLElement | null>(null)
let phenoChart: echarts.ECharts | null = null
let manhattanChart: echarts.ECharts | null = null

type MarkerRow = Record<string, any>
const markerTable = useEnhancedTable<MarkerRow>(() => markers.value as MarkerRow[], {
  pageSize: 10,
  pageSizes: [10, 20, 50, 100],
  searchFields: ['snp', 'chr'],
})

const markerColumns: ExportColumn<MarkerRow>[] = [
  { key: 'snp', label: 'SNP' },
  { key: 'chr', label: 'Chr' },
  { key: 'pos', label: 'Pos' },
  { key: 'pvalue', label: 'P-value' },
  { key: 'effect', label: 'Effect' },
  { key: 'maf', label: 'MAF' },
]

onMounted(async () => {
  traitsLoading.value = true
  try {
    const res = await getGwasTraits()
    traits.value = res.data ?? []
    if (traits.value.length) trait.value = traits.value[0].trait
  } catch (e) {
    error.value = String(e)
  } finally {
    traitsLoading.value = false
  }
})

const handleLoad = async () => {
  if (!trait.value) {
    error.value = t('trait')
    return
  }
  loading.value = true
  error.value = ''
  try {
    const m = await getGwasMarkers({ trait: trait.value })
    markers.value = m.data?.records ?? []
    markersTotal.value = m.data?.total ?? markers.value.length
    markersSearched.value = true

    const a = await getGwasAssociations({ trait: trait.value })
    associations.value = a.data ?? []
    assocSearched.value = true
    nextTick(renderManhattan)
  } catch (e: any) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}

const handlePhenotype = async () => {
  if (!trait.value) {
    error.value = t('trait')
    return
  }
  try {
    const res = await getGwasPhenotype({ trait: trait.value })
    const data = res.data
    if (data && data.labels?.length) {
      showPhenotype.value = true
      nextTick(() => {
        if (!phenoRef.value) return
        phenoChart = echarts.init(phenoRef.value)
        phenoChart.setOption({
          tooltip: { trigger: 'axis' },
          grid: { left: '3%', right: '5%', containLabel: true },
          xAxis: { type: 'category', data: data.labels, axisLabel: { rotate: 45 } },
          yAxis: { type: 'value', name: t('phenotype') },
          series: [
            { name: t('phenotype'), type: 'bar', data: data.values, itemStyle: { color: '#3a6ea5', borderRadius: [4, 4, 0, 0] } },
          ],
        })
      })
    }
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}

function renderManhattan() {
  if (!manhattanRef.value || !associations.value.length) return
  // 染色体分组 x 坐标
  const chrOrder: string[] = []
  associations.value.forEach((d) => {
    if (!chrOrder.includes(d.chr)) chrOrder.push(d.chr)
  })
  const xData = associations.value.map((d) => `${d.chr}:${d.pos}`)
  const dataPts = associations.value.map((d) => ({
    value: [-Math.log10(Math.max(d.pvalue, 1e-300)), d.chr, d.pos, d.snp, d.pvalue],
    itemStyle: { color: chrOrder.indexOf(d.chr) % 2 === 0 ? '#3a6ea5' : '#E6A23C' },
  }))
  manhattanChart = echarts.init(manhattanRef.value)
  manhattanChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: { value: any[] }) =>
        `${p.value[3]}<br/>${t('chromosome')}: ${p.value[1]}<br/>${t('position')}: ${p.value[2]}<br/>${t('pvalue')}: ${p.value[4]}`,
    },
    grid: { left: '3%', right: '5%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: xData, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: '-log10(p)' },
    series: [{ type: 'scatter', data: dataPts, symbolSize: 6 }],
  })
}

function handleResize() {
  phenoChart?.resize()
  manhattanChart?.resize()
}

onMounted(() => window.addEventListener('resize', handleResize))
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  phenoChart?.dispose()
  manhattanChart?.dispose()
})
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 0 15px; }
.mt-4 { margin-top: 1.5rem; }
.mb-4 { margin-bottom: 1.5rem; }
.mt-3 { margin-top: 1rem; }
.card-header { font-size: 16px; font-weight: 500; }
.text-muted { color: #6c757d; font-size: 0.85rem; }
.ms-2 { margin-left: 0.5rem; }
.chart-box { width: 100%; height: 420px; }
.pagination-container { display: flex; justify-content: center; margin-top: 1rem; }
</style>
