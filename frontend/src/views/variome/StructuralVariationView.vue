<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('variome_sv') }}</h2>
    <p class="text-muted mb-4">{{ t('module_variome_desc') }}</p>

    <el-card class="mb-4">
      <template #header>
        <div class="card-header">{{ t('structure_variant') }}</div>
      </template>

      <el-form @submit.prevent="handleSubmit" label-width="180px">
        <el-form-item :label="t('pairwise_batch')">
          <el-select v-model="pairId" :placeholder="t('pairwise_batch')" style="width: 100%" :loading="pairsLoading">
            <el-option v-for="p in pairs" :key="p.id" :label="`Ref:${p.ref_genome_id} × Query:${p.query_genome_id} (${p.status})`" :value="p.id" />
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
          <el-select v-model="types" multiple collapse-tags :placeholder="t('variation_type')" style="width: 100%">
            <el-option v-for="ty in availableTypes" :key="ty" :label="ty" :value="ty" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('select_limit')">
          <el-input-number v-model="limit" :min="1" :max="5000" :step="100" />
        </el-form-item>

        <el-form-item>
          <el-button type="info" size="small" @click="fillExample">{{ t('load_example') }}</el-button>
          <el-button type="primary" :loading="loading" class="ms-2" @click="handleSubmit">
            <el-icon><Search /></el-icon>{{ t('search') }}
          </el-button>
        </el-form-item>

        <el-alert v-if="error" :title="error" type="error" show-icon class="mt-3" @close="error = ''" />
      </el-form>
    </el-card>

    <el-card v-if="records.length" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>{{ t('structure_variant') }}</span>
          <el-tag type="info">{{ t('found') }} {{ total }} {{ t('records') }}</el-tag>
        </div>
      </template>

      <el-table :data="table.pagedData" style="width: 100%" @sort-change="table.handleSortChange">
        <el-table-column prop="ref_genome_chr" :label="t('chromosome')" width="150" sortable="custom" />
        <el-table-column prop="ref_start" :label="t('start_position')" width="150" sortable="custom" />
        <el-table-column prop="ref_end" :label="t('end_position')" width="150" sortable="custom" />
        <el-table-column prop="son_type" :label="t('variation_type')" width="150" sortable="custom" />
        <el-table-column prop="query_genome_chr" :label="'Query ' + t('chromosome')" width="150" sortable="custom" />
        <el-table-column prop="sv_length" :label="'Size'" width="120" sortable="custom" />
        <el-table-column prop="event_id" :label="'Event ID'" width="140" />
      </el-table>

      <TableToolbar
        v-model="table.keyword"
        :total="table.total"
        :columns="exportColumns"
        :rows="table.sortedRows"
        filename="syri_structural.csv"
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

    <el-dialog v-model="seqVisible" :title="t('sequence_annotation')" width="80%">
      <el-table :data="seqRecords" style="width: 100%" max-height="400">
        <el-table-column prop="ref_genome_chr" :label="t('chromosome')" width="120" />
        <el-table-column prop="ref_start" :label="t('start_position')" width="120" />
        <el-table-column prop="ref_end" :label="t('end_position')" width="120" />
        <el-table-column prop="son_type" :label="t('variation_type')" width="120" />
        <el-table-column prop="sv_length" :label="'Size'" width="100" />
      </el-table>
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
  getSyriPairs,
  getSyriStructural,
  getSyriSequence,
  type SyriPair,
  type SyriStructural,
  type SyriSequence,
  type TypeStat,
} from '@/api/index'
import { useEnhancedTable } from '@/composables/core/useEnhancedTable'
import type { ExportColumn } from '@/utils/exportTable'

const { t } = useI18n()

const pairs = ref<SyriPair[]>([])
const pairsLoading = ref(false)
const pairId = ref<number | undefined>(undefined)
const chromosome = ref('')
const start = ref<number | undefined>(undefined)
const end = ref<number | undefined>(undefined)
const types = ref<string[]>([])
const limit = ref(500)
const availableTypes = ref<string[]>([])

const records = ref<SyriStructural[]>([])
const total = ref(0)
const typeStat = ref<TypeStat[]>([])
const loading = ref(false)
const searched = ref(false)
const error = ref('')

const seqVisible = ref(false)
const seqRecords = ref<SyriSequence[]>([])

const pieRef = ref<HTMLElement | null>(null)
let pieChart: echarts.ECharts | null = null

type Row = Record<string, any>
const table = useEnhancedTable<Row>(() => records.value as Row[], {
  pageSize: 10,
  pageSizes: [10, 20, 50, 100],
  searchFields: ['ref_genome_chr', 'son_type', 'event_id', 'query_genome_chr'],
})

const exportColumns: ExportColumn<Row>[] = [
  { key: 'ref_genome_chr', label: 'Ref Chr' },
  { key: 'ref_start', label: 'Ref Start' },
  { key: 'ref_end', label: 'Ref End' },
  { key: 'son_type', label: 'Type' },
  { key: 'query_genome_chr', label: 'Query Chr' },
  { key: 'query_start', label: 'Query Start' },
  { key: 'query_end', label: 'Query End' },
  { key: 'sv_length', label: 'Size' },
  { key: 'event_id', label: 'Event ID' },
]

onMounted(async () => {
  pairsLoading.value = true
  try {
    const res = await getSyriPairs()
    pairs.value = res.data ?? []
    if (pairs.value.length) pairId.value = pairs.value[0].id
  } catch (e) {
    error.value = String(e)
  } finally {
    pairsLoading.value = false
  }
})

const fillExample = () => {
  if (pairs.value.length) pairId.value = pairs.value[0].id
  chromosome.value = 'Ghir_A01'
  start.value = 1
  end.value = 1000000
}

const handleSubmit = async () => {
  if (pairId.value === undefined) {
    error.value = t('pairwise_batch')
    return
  }
  loading.value = true
  searched.value = false
  error.value = ''
  try {
    const res = await getSyriStructural({
      pair_id: pairId.value,
      ref_chr: chromosome.value || undefined,
      start: start.value,
      end: end.value,
      types: types.value.length ? types.value : undefined,
      limit: limit.value,
    })
    records.value = res.data?.rows ?? []
    total.value = res.data?.count ?? records.value.length
    typeStat.value = res.data?.type_stat ?? []
    availableTypes.value = Array.from(new Set(typeStat.value.map((s) => s.son_type ?? s.svtype ?? '').filter(Boolean)))
    searched.value = true
    nextTick(renderPie)
  } catch (e: any) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}

const openSequence = async (row: SyriStructural) => {
  if (pairId.value === undefined) return
  seqVisible.value = true
  try {
    const res = await getSyriSequence({
      pair_id: pairId.value,
      ref_chr: row.ref_genome_chr,
      start: row.ref_start,
      end: row.ref_end,
      types: [row.son_type],
    })
    seqRecords.value = res.data?.rows ?? []
  } catch (e: any) {
    seqRecords.value = []
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
        data: typeStat.value.map((s) => ({ name: s.son_type ?? s.svtype ?? '', value: s.count })),
      },
    ],
  })
}

function handleResize() {
  pieChart?.resize()
}

onMounted(() => window.addEventListener('resize', handleResize))
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
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
