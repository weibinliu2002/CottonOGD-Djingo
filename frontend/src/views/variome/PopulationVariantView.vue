<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('variome_variant') }}</h2>
    <p class="text-muted mb-4">{{ t('module_variome_desc') }}</p>

    <el-card class="mb-4">
      <template #header>
        <div class="card-header">{{ t('variome_variant') }}</div>
      </template>

      <el-form @submit.prevent="handleSubmit" label-width="180px">
        <el-form-item :label="t('select_dataset')">
          <el-select v-model="dataset" :placeholder="t('select_dataset')" style="width: 100%" :loading="setsLoading">
            <el-option v-for="s in sets" :key="s.dataset" :label="s.dataset" :value="s.dataset" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('chromosome')">
          <el-input v-model="chromosome" :placeholder="t('chromosome')" />
        </el-form-item>

        <el-form-item>
          <div class="d-flex gap-2">
            <el-input v-model="start" :placeholder="t('region_start')" style="width: 180px" />
            <span class="align-self-center">-</span>
            <el-input v-model="end" :placeholder="t('region_end')" style="width: 180px" />
          </div>
        </el-form-item>

        <el-form-item :label="t('variation_type')">
          <el-select v-model="svtype" clearable :placeholder="t('variation_type')" style="width: 100%">
            <el-option v-for="ty in availableTypes" :key="ty" :label="ty" :value="ty" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('select_limit')">
          <el-input-number v-model="limit" :min="1" :max="5000" :step="100" />
        </el-form-item>

        <el-form-item>
          <el-button type="info" size="small" @click="fillExample">{{ t('load_example') }}</el-button>
          <el-button type="primary" native-type="submit" :loading="loading" class="ms-2">
            <el-icon><Search /></el-icon>{{ t('search') }}
          </el-button>
          <el-button type="success" size="small" class="ms-2" @click="handleDensity">{{ t('variant_density') }}</el-button>
        </el-form-item>

        <el-alert v-if="error" :title="error" type="error" show-icon class="mt-3" @close="error = ''" />
      </el-form>
    </el-card>

    <el-card v-if="records.length" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>{{ t('variome_variant') }}</span>
          <el-tag type="info">{{ t('found') }} {{ total }} {{ t('records') }}</el-tag>
        </div>
      </template>

      <el-table :data="table.pagedData" style="width: 100%" @sort-change="table.handleSortChange">
        <el-table-column prop="id" :label="'ID'" width="200" sortable="custom">
          <template #default="scope">
            <a href="javascript:void(0)" @click="openDetail(scope.row)">{{ scope.row.id }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="chromosome" :label="t('chromosome')" width="140" sortable="custom" />
        <el-table-column prop="position" :label="t('position')" width="140" sortable="custom" />
        <el-table-column prop="ref" :label="t('ref')" width="90" />
        <el-table-column prop="alt" :label="t('alt')" width="90" />
        <el-table-column prop="type" :label="t('variation_type')" width="140" sortable="custom" />
        <el-table-column prop="maf" :label="t('maf')" width="100" sortable="custom" />
        <el-table-column prop="effect" :label="t('effect')" width="140" sortable="custom" />
        <el-table-column prop="gene" :label="t('gene')" width="160" sortable="custom" />
      </el-table>

      <TableToolbar
        v-model="table.keyword"
        :total="table.total"
        :columns="exportColumns"
        :rows="table.sortedRows"
        filename="population_variants.csv"
        class="mt-3"
      />

      <div v-if="table.total > table.pageSize" class="pagination-container">
        <el-pagination
          v-model:current-page="table.currentPage"
          v-model:page-size="table.pageSize"
          :page-sizes="table.pageSizes"
          layout="total, sizes, prev, pager, next, jumper"
          :total="table.total"
        />
      </div>
    </el-card>

    <el-empty v-else-if="searched && !loading" :description="t('no_data')" />

    <el-card v-if="typeStat.length" class="mb-4">
      <template #header><div class="card-header">{{ t('type_stat') }}</div></template>
      <div ref="pieRef" class="chart-box"></div>
    </el-card>

    <el-card v-if="density.length" class="mb-4">
      <template #header><div class="card-header">{{ t('variant_density') }}</div></template>
      <div ref="barRef" class="chart-box"></div>
    </el-card>

    <el-dialog v-model="detailVisible" :title="t('view')" width="40%">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item :label="'ID'">{{ detail.id }}</el-descriptions-item>
        <el-descriptions-item :label="t('chromosome')">{{ detail.chromosome }}</el-descriptions-item>
        <el-descriptions-item :label="t('position')">{{ detail.position }}</el-descriptions-item>
        <el-descriptions-item :label="t('ref')">{{ detail.ref }}</el-descriptions-item>
        <el-descriptions-item :label="t('alt')">{{ detail.alt }}</el-descriptions-item>
        <el-descriptions-item :label="t('variation_type')">{{ detail.type }}</el-descriptions-item>
        <el-descriptions-item :label="t('effect')">{{ detail.effect }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import echarts from '@/utils/echarts'
import {
  getVariantSets,
  getVariantRegion,
  getVariantById,
  getVariantDensity,
  type VariantSet,
  type VariantRecord,
  type VariantDensity,
} from '@/api/index'
import { useEnhancedTable } from '@/composables/core/useEnhancedTable'
import type { ExportColumn } from '@/utils/exportTable'

const { t } = useI18n()

const sets = ref<VariantSet[]>([])
const setsLoading = ref(false)
const dataset = ref('')
const chromosome = ref('')
const start = ref<number | undefined>(undefined)
const end = ref<number | undefined>(undefined)
const svtype = ref('')
const limit = ref(500)
const availableTypes = ref<string[]>([])

const records = ref<VariantRecord[]>([])
const total = ref(0)
const typeStat = ref<{ type: string; count: number }[]>([])
const density = ref<VariantDensity[]>([])
const loading = ref(false)
const searched = ref(false)
const error = ref('')

const detailVisible = ref(false)
const detail = ref<VariantRecord | null>(null)

const pieRef = ref<HTMLElement | null>(null)
const barRef = ref<HTMLElement | null>(null)
let pieChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null

type Row = Record<string, any>
const table = useEnhancedTable<Row>(() => records.value as Row[], {
  pageSize: 10,
  pageSizes: [10, 20, 50, 100],
  searchFields: ['id', 'chromosome', 'type', 'gene', 'effect'],
})

const exportColumns: ExportColumn<Row>[] = [
  { key: 'id', label: 'ID' },
  { key: 'chromosome', label: 'Chromosome' },
  { key: 'position', label: 'Position' },
  { key: 'ref', label: 'Ref' },
  { key: 'alt', label: 'Alt' },
  { key: 'type', label: 'Type' },
  { key: 'maf', label: 'MAF' },
  { key: 'effect', label: 'Effect' },
  { key: 'gene', label: 'Gene' },
]

onMounted(async () => {
  setsLoading.value = true
  try {
    const res = await getVariantSets()
    sets.value = res.data ?? []
    if (sets.value.length) dataset.value = sets.value[0].dataset
  } catch (e) {
    error.value = String(e)
  } finally {
    setsLoading.value = false
  }
})

const fillExample = () => {
  if (sets.value.length) dataset.value = sets.value[0].dataset
  chromosome.value = 'Ghir_A01'
  start.value = 1
  end.value = 1000000
}

const handleSubmit = async () => {
  if (!dataset.value) {
    error.value = t('select_dataset')
    return
  }
  loading.value = true
  searched.value = false
  error.value = ''
  try {
    const res = await getVariantRegion({
      dataset: dataset.value,
      chromosome: chromosome.value,
      start: start.value ?? 1,
      end: end.value ?? 1000000,
      svtype: svtype.value || undefined,
      limit: limit.value,
    })
    records.value = res.data?.records ?? []
    total.value = res.data?.total ?? records.value.length
    typeStat.value = res.data?.type_stat ?? []
    availableTypes.value = Array.from(new Set(records.value.map((r) => r.type ?? '').filter(Boolean)))
    searched.value = true
    nextTick(renderPie)
  } catch (e: any) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}

const handleDensity = async () => {
  if (!dataset.value || !chromosome.value) {
    error.value = t('select_dataset') + ' / ' + t('chromosome')
    return
  }
  try {
    const res = await getVariantDensity({
      dataset: dataset.value,
      chromosome: chromosome.value,
      start: start.value,
      end: end.value,
    })
    density.value = res.data ?? []
    nextTick(renderBar)
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}

const openDetail = async (row: VariantRecord) => {
  try {
    const res = await getVariantById(row.id)
    detail.value = res.data ?? row
    detailVisible.value = true
  } catch (e) {
    detail.value = row
    detailVisible.value = true
  }
}

function renderPie() {
  if (!pieRef.value || !typeStat.value.length) return
  pieChart = echarts.init(pieRef.value)
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [
      {
        name: t('type_stat'),
        type: 'pie',
        radius: ['40%', '70%'],
        data: typeStat.value.map((s) => ({ name: s.type, value: s.count })),
      },
    ],
  })
}

function renderBar() {
  if (!barRef.value || !density.value.length) return
  barChart = echarts.init(barRef.value)
  barChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '5%', bottom: '20%', containLabel: true },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', height: 18, bottom: 8 }],
    xAxis: { type: 'category', data: density.value.map((d) => `${d.start}-${d.end}`) },
    yAxis: { type: 'value', name: t('density') },
    series: [
      {
        name: t('density'),
        type: 'bar',
        data: density.value.map((d) => d.count),
        itemStyle: { color: '#3a6ea5', borderRadius: [4, 4, 0, 0] },
      },
    ],
  })
}

function handleResize() {
  pieChart?.resize()
  barChart?.resize()
}

onMounted(() => window.addEventListener('resize', handleResize))
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
  barChart?.dispose()
})
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 0 15px; }
.mt-4 { margin-top: 1.5rem; }
.mb-4 { margin-bottom: 1.5rem; }
.mt-3 { margin-top: 1rem; }
.card-header { font-size: 16px; font-weight: 500; }
.text-muted { color: #6c757d; font-size: 0.85rem; }
.d-flex { display: flex; }
.gap-2 { gap: 0.5rem; }
.align-self-center { align-self: center; }
.ms-2 { margin-left: 0.5rem; }
.chart-box { width: 100%; height: 360px; }
.pagination-container { display: flex; justify-content: center; margin-top: 1rem; }
</style>
