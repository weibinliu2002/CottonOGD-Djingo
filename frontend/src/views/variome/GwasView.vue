<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('variome_gwas') }}</h2>
    <p class="text-muted mb-4">{{ t('module_variome_desc') }}</p>

    <el-card class="mb-4">
      <template #header><div class="card-header">{{ t('trait') }}</div></template>
      <el-form @submit.prevent="handleLoad" label-width="180px">
        <el-form-item :label="t('trait')">
          <el-select v-model="traitCode" :placeholder="t('trait')" style="width: 100%" :loading="traitsLoading" filterable>
            <el-option v-for="tr in traits" :key="tr.code" :label="`${tr.code} · ${tr.name} (${tr.unit})`" :value="tr.code" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('select_dataset')">
          <el-select v-model="setId" :placeholder="t('select_dataset')" style="width: 100%" :loading="setsLoading" clearable>
            <el-option v-for="s in sets" :key="s.id" :label="`${s.name}`" :value="s.id" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" class="ms-2" @click="handleLoad">
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
        <el-table-column prop="id" :label="'ID'" width="100" sortable="custom" />
        <el-table-column prop="chrom" :label="t('chromosome')" width="140" sortable="custom" />
        <el-table-column prop="pos" :label="t('position')" width="140" sortable="custom" />
        <el-table-column prop="svtype" :label="t('variation_type')" width="140" sortable="custom" />
        <el-table-column prop="ref" :label="t('ref')" width="90" />
        <el-table-column prop="alt" :label="t('alt')" width="90" />
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
  getVariantSets,
  type GwasTrait,
  type VariantSet,
  type GwasMarker,
  type GwasPhenotypeRow,
} from '@/api/index'
import { useEnhancedTable } from '@/composables/core/useEnhancedTable'
import type { ExportColumn } from '@/utils/exportTable'

const { t } = useI18n()

const traits = ref<GwasTrait[]>([])
const traitsLoading = ref(false)
const traitCode = ref('')
const sets = ref<VariantSet[]>([])
const setsLoading = ref(false)
const setId = ref<number | undefined>(undefined)
const loading = ref(false)
const error = ref('')

const markers = ref<GwasMarker[]>([])
const markersTotal = ref(0)
const markersSearched = ref(false)
const assocSearched = ref(false)
const associations = ref<GwasMarker[]>([])
const showPhenotype = ref(false)

const phenoRef = ref<HTMLElement | null>(null)
const manhattanRef = ref<HTMLElement | null>(null)
let phenoChart: echarts.ECharts | null = null
let manhattanChart: echarts.ECharts | null = null

type MarkerRow = Record<string, any>
const markerTable = useEnhancedTable<MarkerRow>(() => markers.value as MarkerRow[], {
  pageSize: 10,
  pageSizes: [10, 20, 50, 100],
  searchFields: ['chrom', 'svtype'],
})

const markerColumns: ExportColumn<MarkerRow>[] = [
  { key: 'id', label: 'ID' },
  { key: 'chrom', label: 'Chrom' },
  { key: 'pos', label: 'Pos' },
  { key: 'svtype', label: 'Type' },
  { key: 'ref', label: 'Ref' },
  { key: 'alt', label: 'Alt' },
]

onMounted(async () => {
  traitsLoading.value = true
  try {
    const res = await getGwasTraits()
    traits.value = res.data ?? []
    if (traits.value.length) traitCode.value = traits.value[0].code
  } catch (e) {
    error.value = String(e)
  } finally {
    traitsLoading.value = false
  }
  setsLoading.value = true
  try {
    const res = await getVariantSets()
    sets.value = res.data ?? []
    if (sets.value.length) setId.value = sets.value[0].id
  } catch (e) {
    error.value = String(e)
  } finally {
    setsLoading.value = false
  }
})

const handleLoad = async () => {
  if (!traitCode.value) {
    error.value = t('trait')
    return
  }
  loading.value = true
  error.value = ''
  try {
    const m = await getGwasMarkers({ set_id: setId.value ?? 0, code: traitCode.value })
    markers.value = m.data?.rows ?? []
    markersTotal.value = m.data?.count ?? markers.value.length
    markersSearched.value = true

    const a = await getGwasAssociations({ code: traitCode.value })
    associations.value = a.data?.rows ?? []
    assocSearched.value = true
    nextTick(renderManhattan)
  } catch (e: any) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}

const handlePhenotype = async () => {
  if (!traitCode.value) {
    error.value = t('trait')
    return
  }
  try {
    const res = await getGwasPhenotype({ code: traitCode.value })
    const data = res.data
    if (data && data.rows?.length) {
      showPhenotype.value = true
      const labels = data.rows.map((r: GwasPhenotypeRow) => r.accession)
      const values = data.rows.map((r: GwasPhenotypeRow) => r.value)
      nextTick(() => {
        if (!phenoRef.value) return
        phenoChart = echarts.init(phenoRef.value)
        phenoChart.setOption({
          tooltip: { trigger: 'axis' },
          grid: { left: '3%', right: '5%', containLabel: true },
          xAxis: { type: 'category', data: labels, axisLabel: { rotate: 45 } },
          yAxis: { type: 'value', name: t('phenotype') },
          series: [
            { name: t('phenotype'), type: 'bar', data: values, itemStyle: { color: '#3a6ea5', borderRadius: [4, 4, 0, 0] } },
          ],
        })
      })
    } else {
      error.value = t('no_data')
    }
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}

function renderManhattan() {
  if (!manhattanRef.value || !associations.value.length) return
  const chrOrder: string[] = []
  associations.value.forEach((d) => {
    if (!chrOrder.includes(d.chrom)) chrOrder.push(d.chrom)
  })
  const xData = associations.value.map((d) => `${d.chrom}:${d.pos}`)
  const dataPts = associations.value.map((d) => ({
    value: [chrOrder.indexOf(d.chrom), d.pos, d.chrom, d.pos],
    itemStyle: { color: chrOrder.indexOf(d.chrom) % 2 === 0 ? '#3a6ea5' : '#E6A23C' },
  }))
  manhattanChart = echarts.init(manhattanRef.value)
  manhattanChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: { value: any[] }) =>
        `${t('chromosome')}: ${p.value[2]}<br/>${t('position')}: ${p.value[3]}`,
    },
    grid: { left: '3%', right: '5%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: xData, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: t('position') },
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
