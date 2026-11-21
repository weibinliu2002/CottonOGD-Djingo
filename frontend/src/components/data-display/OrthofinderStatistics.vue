<template>
  <div class="ofs">
    <el-tabs v-model="activeTab" class="ofs-tabs" @tab-change="onTabChange">
      <!-- ==================== 总体统计 ==================== -->
      <el-tab-pane :label="t('stats_tab_overall')" name="overall">
        <div v-loading="overallLoading">
          <el-alert v-if="overallError" type="warning" :title="overallError" show-icon :closable="false" class="ofs-alert" />
          <el-descriptions v-else-if="overallKv.length" :column="2" border size="small">
            <el-descriptions-item
              v-for="item in overallKv"
              :key="item.key"
              :label="item.key"
            >{{ item.value }}</el-descriptions-item>
          </el-descriptions>
          <el-empty v-else-if="!overallLoading && !overallError" :description="t('no_data')" />
        </div>
        <el-alert
          class="ofs-alert ofs-alert--top"
          type="info"
          :closable="false"
          :title="t('stats_single_copy_note')"
        />
      </el-tab-pane>

      <!-- ==================== 每物种统计 ==================== -->
      <el-tab-pane :label="t('stats_tab_per_species')" name="per_species">
        <div class="ofs-toolbar">
          <el-select
            v-model="perSpeciesMetric"
            :placeholder="t('stats_metric')"
            size="small"
            class="ofs-toolbar__select"
            filterable
            :loading="perSpeciesLoading"
            @change="renderPerSpecies"
          >
            <el-option v-for="m in perSpeciesMetrics" :key="m.metric" :label="m.metric" :value="m.metric" />
          </el-select>
        </div>
        <el-alert v-if="perSpeciesError" type="warning" :title="perSpeciesError" show-icon :closable="false" class="ofs-alert" />
        <div v-show="perSpeciesSpecies.length && perSpeciesMetric" ref="perSpeciesRef" class="ofs-chart" />
        <el-table
          v-if="perSpeciesSpecies.length"
          :data="perSpeciesTable"
          stripe
          border
          size="small"
          max-height="320"
        >
          <el-table-column :label="t('ortholog_species')" prop="species" min-width="220" />
          <el-table-column :label="perSpeciesMetric || t('stats_metric')" prop="value" min-width="160" />
        </el-table>
        <el-empty
          v-else-if="perSpeciesLoaded && !perSpeciesLoading && !perSpeciesError"
          :description="t('no_data')"
        />
      </el-tab-pane>

      <!-- ==================== Ortholog 统计 ==================== -->
      <el-tab-pane :label="t('stats_tab_orthologs')" name="orthologs">
        <div class="ofs-toolbar">
          <el-select v-model="orthologsKind" size="small" class="ofs-toolbar__select">
            <el-option v-for="k in orthologKinds" :key="k" :label="k" :value="k" />
          </el-select>
          <el-select v-model="orthologsSpeciesA" size="small" class="ofs-toolbar__select" filterable :placeholder="t('stats_species_a')">
            <el-option v-for="s in speciesList" :key="s" :label="s" :value="s" />
          </el-select>
          <el-select v-model="orthologsSpeciesB" size="small" class="ofs-toolbar__select" filterable :placeholder="t('stats_species_b')">
            <el-option v-for="s in speciesList" :key="s" :label="s" :value="s" />
          </el-select>
          <el-button type="primary" size="small" :loading="orthologsLoading" @click="loadOrthologsPair">
            {{ t('stats_query') }}
          </el-button>
          <el-button size="small" :loading="matrixLoading" @click="loadOrthologsMatrix">
            {{ t('stats_load_matrix') }}
          </el-button>
        </div>

        <el-alert v-if="orthologsError" type="warning" :title="orthologsError" show-icon :closable="false" class="ofs-alert" />
        <el-descriptions v-if="orthologsPairValue" :column="2" border size="small" class="ofs-desc">
          <el-descriptions-item :label="t('stats_kind')">{{ orthologsKind }}</el-descriptions-item>
          <el-descriptions-item :label="t('stats_pair_value')">{{ orthologsPairValue }}</el-descriptions-item>
        </el-descriptions>

        <div v-show="matrixLoaded" ref="matrixRef" class="ofs-chart ofs-chart--matrix" v-loading="matrixLoading" />
        <el-alert
          v-if="matrixLoaded"
          class="ofs-alert"
          type="info"
          :closable="false"
          :title="t('stats_matrix_hint')"
        />
      </el-tab-pane>

      <!-- ==================== 复制事件统计 ==================== -->
      <el-tab-pane :label="t('stats_tab_duplications')" name="duplications">
        <div class="ofs-toolbar">
          <el-select v-model="dupScope" size="small" class="ofs-toolbar__select">
            <el-option :label="t('stats_scope_orthogroup')" value="orthogroup" />
            <el-option :label="t('stats_scope_species_node')" value="species_node" />
          </el-select>
          <el-input
            v-if="dupScope === 'orthogroup'"
            v-model="dupOgCode"
            size="small"
            class="ofs-toolbar__input"
            :placeholder="t('og_code')"
            clearable
          />
          <el-button type="primary" size="small" :loading="dupLoading" @click="loadDuplications">
            {{ t('stats_query') }}
          </el-button>
        </div>

        <el-alert v-if="dupError" type="warning" :title="dupError" show-icon :closable="false" class="ofs-alert" />
        <el-descriptions v-if="dupValue" :column="2" border size="small">
          <el-descriptions-item :label="t('stats_scope')">{{ dupScope }}</el-descriptions-item>
          <el-descriptions-item :label="t('stats_pair_value')">{{ dupValue }}</el-descriptions-item>
        </el-descriptions>
        <el-table
          v-if="dupRows.length"
          :data="dupRows"
          stripe
          border
          size="small"
          max-height="420"
        >
          <el-table-column
            v-for="col in dupColumns"
            :key="col"
            :label="col"
            :prop="col"
            min-width="140"
            show-overflow-tooltip
          />
        </el-table>
        <el-empty
          v-else-if="dupLoaded && !dupLoading && !dupError && !dupValue"
          :description="t('no_data')"
        />
      </el-tab-pane>

      <!-- ==================== 物种重叠 ==================== -->
      <el-tab-pane :label="t('stats_tab_overlaps')" name="overlaps">
        <div v-loading="overlapsLoading">
          <el-alert v-if="overlapsError" type="warning" :title="overlapsError" show-icon :closable="false" class="ofs-alert" />
          <el-alert
            v-else-if="overlapsLoaded"
            type="info"
            :closable="false"
            :title="t('stats_overlaps_unavailable')"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ==================== 两个 Genome 的共享 OG ==================== -->
    <el-divider content-position="left">{{ t('stats_genome_pair_title') }}</el-divider>
    <div class="ofs-toolbar">
      <el-select v-model="pairA" size="small" class="ofs-toolbar__select" filterable :placeholder="t('stats_species_a')">
        <el-option v-for="s in speciesList" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select v-model="pairB" size="small" class="ofs-toolbar__select" filterable :placeholder="t('stats_species_b')">
        <el-option v-for="s in speciesList" :key="s" :label="s" :value="s" />
      </el-select>
      <el-button type="primary" size="small" :loading="pairLoading" @click="submitPair">
        {{ t('stats_query') }}
      </el-button>
    </div>
    <el-alert
      class="ofs-alert"
      type="info"
      :closable="false"
      :title="t('stats_shared_og_note')"
    />
    <el-alert v-if="pairError" type="warning" :title="pairError" show-icon :closable="false" class="ofs-alert" />
    <template v-if="pairResult">
      <div class="ofs-toolbar ofs-toolbar--meta">
        <span>{{ t('stats_shared_og_total') }}: {{ pairResult.total }}</span>
      </div>
      <el-table :data="pairResult.orthogroups" stripe border size="small" max-height="360">
        <el-table-column :label="t('og_code')" prop="og_code" min-width="150" />
        <el-table-column :label="t('gene_count')" prop="gene_count" width="120" align="center" />
        <el-table-column :label="t('species_count')" prop="species_count" width="120" align="center" />
        <el-table-column :label="t('stats_pair_genes_a')" min-width="240">
          <template #default="scope">{{ (scope.row.genes_a || []).join(', ') }}</template>
        </el-table-column>
        <el-table-column :label="t('stats_pair_genes_b')" min-width="240">
          <template #default="scope">{{ (scope.row.genes_b || []).join(', ') }}</template>
        </el-table-column>
      </el-table>
      <div class="ofs-pager">
        <el-pagination
          v-model:current-page="pairPage"
          :page-size="pairPageSize"
          :total="pairResult.total"
          layout="prev, pager, next"
          background
          small
          :disabled="pairLoading"
          @current-change="loadPair"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * OrthoFinder 统计面板（直接读取 Comparative_Genomics_Statistics，不在前端重算）。
 *
 * 对接 docs/COMPARATIVE_ANALYSIS_API_HANDOFF.md C.15 / C.11：
 *  - statistics?type=overall / per_species / orthologs / duplications / species_overlaps
 *  - genome_pair：两个 Genome 的“共享 OG”，不是 Ortholog 对。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from '@/utils/echarts'
import {
  getGenomePair,
  getOrthofinderStatistics,
  type GenomePairResponse,
  type StatisticsDuplicationScope,
  type StatisticsOrthologKind,
} from '@/api/index'

const props = defineProps<{
  /** 可选物种名列表（来自 orthofinder/meta） */
  speciesList: string[]
}>()

const { t } = useI18n()
const activeTab = ref('overall')

// ==================== 总体 ====================
const overallLoading = ref(false)
const overallLoaded = ref(false)
const overallError = ref('')
const overallKv = ref<Array<{ key: string; value: string }>>([])

async function loadOverall(): Promise<void> {
  if (overallLoaded.value) return
  overallLoading.value = true
  overallError.value = ''
  try {
    const res = await getOrthofinderStatistics({ type: 'overall' })
    if (res.error) {
      overallError.value = res.error
      return
    }
    const kv = (res.kv ?? {}) as Record<string, unknown>
    overallKv.value = Object.entries(kv).map(([key, value]) => ({
      key,
      value: value == null ? '' : String(value),
    }))
    overallLoaded.value = true
  } finally {
    overallLoading.value = false
  }
}

// ==================== 每物种 ====================
interface MetricRow {
  metric: string
  values: Array<string | number>
}
const perSpeciesLoading = ref(false)
const perSpeciesLoaded = ref(false)
const perSpeciesError = ref('')
const perSpeciesSpecies = ref<string[]>([])
const perSpeciesMetrics = ref<MetricRow[]>([])
const perSpeciesMetric = ref('')
const perSpeciesRef = ref<HTMLElement | null>(null)
let perSpeciesChart: ReturnType<typeof echarts.init> | null = null

const perSpeciesTable = computed(() => {
  const metric = perSpeciesMetrics.value.find((m) => m.metric === perSpeciesMetric.value)
  if (!metric) return []
  return perSpeciesSpecies.value.map((species, i) => ({
    species,
    value: metric.values[i] ?? '',
  }))
})

async function loadPerSpecies(): Promise<void> {
  if (perSpeciesLoaded.value) return
  perSpeciesLoading.value = true
  perSpeciesError.value = ''
  try {
    const res = await getOrthofinderStatistics({ type: 'per_species' })
    if (res.error) {
      perSpeciesError.value = res.error
      return
    }
    perSpeciesSpecies.value = (res.species ?? []) as string[]
    perSpeciesMetrics.value = (res.metrics ?? []) as MetricRow[]
    perSpeciesMetric.value = perSpeciesMetrics.value[0]?.metric ?? ''
    perSpeciesLoaded.value = true
    await nextTick()
    renderPerSpecies()
  } finally {
    perSpeciesLoading.value = false
  }
}

function toNumber(value: unknown): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function renderPerSpecies(): void {
  if (!perSpeciesRef.value || !perSpeciesMetric.value) return
  const metric = perSpeciesMetrics.value.find((m) => m.metric === perSpeciesMetric.value)
  if (!metric) return
  if (!perSpeciesChart) perSpeciesChart = echarts.init(perSpeciesRef.value)
  perSpeciesChart.setOption({
    grid: { left: 8, right: 16, top: 24, bottom: 64, containLabel: true },
    tooltip: { trigger: 'axis' },
    dataZoom: [
      { type: 'inside', start: 0, end: Math.min(100, (60 / Math.max(1, perSpeciesSpecies.value.length)) * 100) },
      { type: 'slider', height: 18, bottom: 8 },
    ],
    xAxis: {
      type: 'category',
      data: perSpeciesSpecies.value,
      axisLabel: { rotate: 45, fontSize: 10, interval: 0 },
    },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: metric.values.map(toNumber),
      itemStyle: { color: '#3a6ea5' },
    }],
  }, true)
}

// ==================== Ortholog 统计 ====================
const orthologKinds: StatisticsOrthologKind[] = [
  'one-to-one', 'one-to-many', 'many-to-one', 'many-to-many', 'totals',
]
const orthologsKind = ref<StatisticsOrthologKind>('one-to-one')
const orthologsSpeciesA = ref('')
const orthologsSpeciesB = ref('')
const orthologsLoading = ref(false)
const orthologsError = ref('')
const orthologsPairValue = ref('')
const matrixRef = ref<HTMLElement | null>(null)
const matrixLoading = ref(false)
const matrixLoaded = ref(false)
let matrixChart: ReturnType<typeof echarts.init> | null = null

async function loadOrthologsPair(): Promise<void> {
  if (!orthologsSpeciesA.value || !orthologsSpeciesB.value) {
    orthologsError.value = t('stats_pair_required')
    return
  }
  orthologsLoading.value = true
  orthologsError.value = ''
  orthologsPairValue.value = ''
  try {
    const res = await getOrthofinderStatistics({
      type: 'orthologs',
      kind: orthologsKind.value,
      species_a: orthologsSpeciesA.value,
      species_b: orthologsSpeciesB.value,
    })
    if (res.error) {
      orthologsError.value = res.error
      return
    }
    orthologsPairValue.value = res.value == null ? '' : String(res.value)
  } finally {
    orthologsLoading.value = false
  }
}

async function loadOrthologsMatrix(): Promise<void> {
  matrixLoading.value = true
  orthologsError.value = ''
  try {
    const res = await getOrthofinderStatistics({
      type: 'orthologs',
      kind: orthologsKind.value,
    })
    if (res.error) {
      orthologsError.value = res.error
      return
    }
    const species = (res.species ?? []) as string[]
    const matrix = (res.matrix ?? {}) as Record<string, Record<string, string>>
    matrixLoaded.value = true
    await nextTick()
    renderMatrix(species, matrix)
  } finally {
    matrixLoading.value = false
  }
}

function renderMatrix(species: string[], matrix: Record<string, Record<string, string>>): void {
  if (!matrixRef.value) return
  if (!matrixChart) matrixChart = echarts.init(matrixRef.value)
  const data: Array<[number, number, number]> = []
  let max = 0
  species.forEach((a, i) => {
    const row = matrix[a] ?? {}
    species.forEach((b, j) => {
      const raw = row[b]
      if (raw == null || raw === '') return
      const v = toNumber(raw)
      if (v > max) max = v
      data.push([j, i, v])
    })
  })
  matrixChart.setOption({
    grid: { left: 80, right: 24, top: 16, bottom: 80 },
    tooltip: {
      formatter: (p: { value: [number, number, number] }) =>
        `${species[p.value[1]]} → ${species[p.value[0]]}: ${p.value[2]}`,
    },
    xAxis: {
      type: 'category',
      data: species,
      axisLabel: { rotate: 60, fontSize: 9, interval: 0 },
    },
    yAxis: {
      type: 'category',
      data: species,
      axisLabel: { fontSize: 9, interval: 0 },
    },
    visualMap: {
      min: 0,
      max: max || 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#eef3f8', '#3a6ea5'] },
    },
    series: [{
      type: 'heatmap',
      data,
      progressive: 2000,
    }],
  }, true)
}

// ==================== 复制事件统计 ====================
const dupScope = ref<StatisticsDuplicationScope>('orthogroup')
const dupOgCode = ref('')
const dupLoading = ref(false)
const dupLoaded = ref(false)
const dupError = ref('')
const dupValue = ref('')
const dupRows = ref<Array<Record<string, string>>>([])

const dupColumns = computed(() => {
  const first = dupRows.value[0]
  return first ? Object.keys(first).slice(0, 8) : []
})

async function loadDuplications(): Promise<void> {
  dupLoading.value = true
  dupLoaded.value = true
  dupError.value = ''
  dupValue.value = ''
  dupRows.value = []
  try {
    const res = await getOrthofinderStatistics({
      type: 'duplications',
      scope: dupScope.value,
      og_code: dupScope.value === 'orthogroup' ? (dupOgCode.value.trim() || undefined) : undefined,
    })
    if (res.error) {
      dupError.value = res.error
      return
    }
    if (res.value != null) dupValue.value = String(res.value)
    if (Array.isArray(res.rows)) {
      dupRows.value = (res.rows as Array<Record<string, unknown>>).map((row) => {
        const out: Record<string, string> = {}
        for (const [k, v] of Object.entries(row)) out[k] = v == null ? '' : String(v)
        return out
      })
    }
  } finally {
    dupLoading.value = false
  }
}

// ==================== 物种重叠 ====================
const overlapsLoading = ref(false)
const overlapsLoaded = ref(false)
const overlapsError = ref('')

async function loadOverlaps(): Promise<void> {
  if (overlapsLoaded.value) return
  overlapsLoading.value = true
  overlapsError.value = ''
  try {
    const res = await getOrthofinderStatistics({ type: 'species_overlaps' })
    if (res.error) overlapsError.value = res.error
    overlapsLoaded.value = true
  } finally {
    overlapsLoading.value = false
  }
}

// ==================== Genome Pair ====================
const pairA = ref('')
const pairB = ref('')
const pairPage = ref(1)
const pairPageSize = 20
const pairLoading = ref(false)
const pairError = ref('')
const pairResult = ref<GenomePairResponse | null>(null)

/** 新查询从第 1 页开始；翻页沿用当前页 */
function submitPair(): void {
  pairPage.value = 1
  void loadPair()
}

async function loadPair(): Promise<void> {
  if (!pairA.value || !pairB.value) {
    pairError.value = t('stats_pair_required')
    return
  }
  pairLoading.value = true
  pairError.value = ''
  try {
    const res = await getGenomePair({
      genome_a: pairA.value,
      genome_b: pairB.value,
      limit: pairPageSize,
      offset: (pairPage.value - 1) * pairPageSize,
    })
    if (res.error) {
      pairError.value = res.error
      pairResult.value = null
      return
    }
    pairResult.value = res
  } finally {
    pairLoading.value = false
  }
}

// ==================== 标签页按需加载 ====================
function onTabChange(name: string | number): void {
  if (name === 'overall') void loadOverall()
  if (name === 'per_species') void loadPerSpecies()
  if (name === 'overlaps') void loadOverlaps()
}

function handleResize(): void {
  perSpeciesChart?.resize()
  matrixChart?.resize()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  void loadOverall()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  perSpeciesChart?.dispose()
  matrixChart?.dispose()
  perSpeciesChart = null
  matrixChart = null
})
</script>

<style scoped>
.ofs {
  width: 100%;
}
.ofs-tabs {
  --el-color-primary: #3a6ea5;
}
.ofs-alert {
  margin-bottom: 0.75rem;
}
.ofs-alert--top {
  margin-top: 0.75rem;
}
.ofs-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}
.ofs-toolbar--meta {
  color: #6c757d;
  font-size: 0.85rem;
}
.ofs-toolbar__select {
  width: 220px;
}
.ofs-toolbar__input {
  width: 160px;
}
.ofs-chart {
  width: 100%;
  height: 360px;
  margin-bottom: 0.75rem;
}
.ofs-chart--matrix {
  height: 620px;
}
.ofs-desc {
  margin-bottom: 0.75rem;
}
.ofs-pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.75rem;
}
</style>
