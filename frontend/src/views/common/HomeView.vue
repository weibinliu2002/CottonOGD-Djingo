<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Loading } from '@element-plus/icons-vue'
import httpInstance from '@/utils/http.js'
import { useNavigationStore } from '@/stores/modules/navigation'
import {
  searchGenes,
  MeiliSearchError,
  sanitizeHighlight,
  escapeHtml,
  MEILI_MAX_WINDOW,
  type MeiliGeneHit,
} from '@/utils/meiliSearchApi'
import { useGenomeStore } from '@/stores/modules/genome'
import * as echarts from 'echarts'

const genomeStore = useGenomeStore()
const router = useRouter()
const navigationStore = useNavigationStore()

// ECharts 实例
let pieChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null
let scatterChart: echarts.ECharts | null = null
const pieChartRef = ref<HTMLElement>()
const barChartRef = ref<HTMLElement>()
const scatterChartRef = ref<HTMLElement>()

// 统计数据（从 genome store 动态计算，后续可扩展）
const stats = computed(() => {
  const genomeCount = genomeStore.allGenomes.length
  const genomeTypeCount = genomeStore.genomeOptions.length
  const speciesCount = genomeStore.speciesData.length

  return [
    {
      icon: 'fas fa-dna',
      value: genomeCount > 0 ? genomeCount.toString() : '...',
      label: 'Genomes',
    },
    {
      icon: 'fas fa-leaf',
      value: speciesCount > 0 ? speciesCount.toString() : '...',
      label: 'Cotton Species',
    },
    {
      icon: 'fas fa-layer-group',
      value: genomeTypeCount > 0 ? genomeTypeCount.toString() : '...',
      label: 'Genome Types',
    },
    // 预留：基因数、转录因子数等，后续接入新 API 后填充
    {
      icon: 'fas fa-gene',
      value: '200,000+',
      label: 'Annotated Genes',
    },
    {
      icon: 'fas fa-users',
      value: '15,000+',
      label: 'Orthogroups',
    },
    {
      icon: 'fas fa-book',
      value: '5,000+',
      label: 'Literature References',
    },
  ]
})

onMounted(() => {
  genomeStore.fetchGenomes()
})

// BUSCO 分布（饼图用）：按 ≥95 / 90-95 / 80-90 / 70-80 / <70 五区间统计
const pieBuscoData = computed(() => {
  const buckets = [
    { name: '≥95', min: 95, max: Infinity, count: 0 },
    { name: '90-95', min: 90, max: 95, count: 0 },
    { name: '80-90', min: 80, max: 90, count: 0 },
    { name: '70-80', min: 70, max: 80, count: 0 },
    { name: '<70', min: -Infinity, max: 70, count: 0 },
  ]
  genomeStore.speciesData.forEach((s) => {
    if (!s.Busco) return
    const v = parseFloat(s.Busco)
    if (isNaN(v)) return
    const pct = v <= 1 ? v * 100 : v
    for (const b of buckets) {
      // 区间为左闭右开：[95, ∞) / [90,95) / [80,90) / [70,80) / (-∞,70)
      if (pct >= b.min && pct < b.max) {
        b.count++
        break
      }
    }
  })
  return buckets.filter((b) => b.count > 0).map((b) => ({ name: b.name, value: b.count }))
})

// 各棉花物种的基因组数量（柱状图用）：按 Cotton_Species 聚合，降序排列
const barSpeciesData = computed(() => {
  const count: Record<string, number> = {}
  genomeStore.speciesData.forEach((s) => {
    const name = s.Cotton_Species || s.name || s.alias || 'Unknown'
    count[name] = (count[name] || 0) + 1
  })
  const sorted = Object.entries(count).sort((a, b) => b[1] - a[1])
  return {
    species: sorted.map(([name]) => name),
    counts: sorted.map(([, c]) => c),
  }
})

// 各基因组的 Genome Size 与 BUSCO（散点图用，按物种分组）
const scatterSizeData = computed(() => {
  return genomeStore.speciesData
    .map((s) => {
      const genomeName = s.alias || s.name || 'Unknown'
      const species = s.Cotton_Species || 'Unknown'
      // 基因组大小 bp → Gb
      const sizeGb =
        typeof s.Genome_size === 'number' && s.Genome_size > 0
          ? +(s.Genome_size / 1e9).toFixed(3)
          : null
      // BUSCO "0.952" → 95.2 (%)
      let buscoPct: number | null = null
      if (s.Busco) {
        const v = parseFloat(s.Busco)
        if (!isNaN(v)) {
          buscoPct = v <= 1 ? +(v * 100).toFixed(2) : +v.toFixed(2)
        }
      }
      return { species, genomeName, sizeGb, buscoPct }
    })
    .filter((it) => it.sizeGb !== null)
})

// 散点图 x 轴：去重后的物种列表（Cotton_Species）
const scatterSpecies = computed(() => {
  const set = new Set<string>()
  scatterSizeData.value.forEach((it) => set.add(it.species))
  return Array.from(set)
})

/** 初始化饼图：BUSCO 分布（5 区间） */
function initPieChart() {
  if (!pieChartRef.value || pieBuscoData.value.length === 0) return
  pieChart = echarts.init(pieChartRef.value)
  pieChart.setOption({
    title: {
      text: 'BUSCO Distribution',
      left: 'center',
      textStyle: { fontSize: 16 },
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle',
      textStyle: { fontSize: 12 },
    },
    // 颜色由高到低：绿、蓝、橙、红、灰
    color: ['#67C23A', '#409EFF', '#E6A23C', '#F56C6C', '#909399'],
    series: [
      {
        name: 'BUSCO',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '55%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}: {c}',
        },
        data: pieBuscoData.value,
      },
    ],
  })
}

/** 初始化柱状图：各棉花物种的基因组数量 */
function initBarChart() {
  if (!barChartRef.value || barSpeciesData.value.species.length === 0) return
  barChart = echarts.init(barChartRef.value)
  barChart.setOption({
    title: {
      text: 'Genomes per Cotton Species',
      left: 'center',
      textStyle: { fontSize: 16 },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: {
      left: '3%',
      right: '5%',
      bottom: '20%',
      containLabel: true,
    },
    // 基因组数量较多时支持横向缩放
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', height: 18, bottom: 8, start: 0, end: 100 },
    ],
    xAxis: {
      type: 'category',
      data: barSpeciesData.value.species,
      axisLabel: {
        rotate: 45,
        fontSize: 11,
        interval: 0,
      },
    },
    yAxis: {
      type: 'value',
      name: 'Count',
      minInterval: 1,
    },
    series: [
      {
        name: 'Genomes',
        type: 'bar',
        data: barSpeciesData.value.counts,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#409EFF' },
            { offset: 1, color: '#67C23A' },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
        label: {
          show: true,
          position: 'top',
          fontSize: 12,
        },
      },
    ],
  })
}

/** 响应窗口大小变化 */
function handleResize() {
  pieChart?.resize()
  barChart?.resize()
  scatterChart?.resize()
}

/** 初始化散点图（类火山图）：按物种分组聚集，每点为一个基因组，y=Genome Size (Gb)，颜色按 BUSCO 映射 */
function initScatterChart() {
  if (!scatterChartRef.value || scatterSizeData.value.length === 0) return
  scatterChart = echarts.init(scatterChartRef.value)
  const speciesList = scatterSpecies.value
  // 同物种点之间的间距（数值 x 轴单位）：点数多时自动缩小，保证聚簇不超出 ±1 边界
  const maxCount = Math.max(
    ...scatterSizeData.value.reduce((acc: number[], it) => {
      const i = speciesList.indexOf(it.species)
      acc[i] = (acc[i] || 0) + 1
      return acc
    }, []),
  )
  const step = maxCount > 1 ? Math.min(0.18, 1.8 / (maxCount - 1)) : 0.18

  // 先统计每个物种的基因组总数，用于居中散布
  const speciesCounts: Record<string, number> = {}
  scatterSizeData.value.forEach((it) => {
    speciesCounts[it.species] = (speciesCounts[it.species] || 0) + 1
  })
  const speciesSeen: Record<string, number> = {}

  // 数据项：name=基因组名（tooltip 显示），value=[x, Genome Size (Gb), BUSCO (%), 物种名]
  // x 轴为类目轴，类目 i 的槽中心在 i + 0.5；同物种点在槽内居中散开并叠加随机左右抖动
  const data = scatterSizeData.value.map((it) => {
    const speciesIdx = speciesList.indexOf(it.species)
    const total = speciesCounts[it.species] || 0
    const j = speciesSeen[it.species] || 0
    speciesSeen[it.species] = j + 1
    const jitter = (Math.random() - 0.5) * 1.8
    const x = speciesIdx + 0.5 + (j - (total - 1) / 2) * step + jitter
    return {
      name: it.genomeName,
      value: [x, it.sizeGb, it.buscoPct, it.species],
    }
  })

  scatterChart.setOption({
    title: {
      text: 'Genome Size per Species (colored by BUSCO)',
      left: 'center',
      textStyle: { fontSize: 16 },
    },
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => {
        const [, size, busco, species] = p.value as [number, number, number | null, string]
        const buscoTxt = busco === null || busco === undefined ? 'N/A' : `${busco}%`
        // 鼠标悬停显示基因组名称（p.name）
        return `${p.name}<br/>Species: ${species}<br/>Genome Size: <b>${size} Gb</b><br/>BUSCO: <b>${buscoTxt}</b>`
      },
    },
    grid: {
      left: '4%',
      right: '12%',
      bottom: '18%',
      top: '15%',
      containLabel: true,
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', height: 18, bottom: 8, start: 0, end: 100 },
    ],
    xAxis: {
      type: 'category',
      data: speciesList,
      // 类目轴 boundaryGap 两端自动各留半槽宽（比例边距），首尾物种不贴 y 轴
      axisLabel: {
        rotate: 30,
        fontSize: 11,
        interval: 0,
      },
      axisTick: { alignWithLabel: true },
      // y 轴线不画在第一个类目处，而是贴绘图区左边缘
      axisLine: { onZero: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      // 不从 0 开始：取数据最小值向下留 0.2 Gb 边距（保留一位小数），避免规整到 0
      min: (value: { min: number; max: number }) =>
        Math.floor((value.min - 0.2) * 10) / 10,
      name: 'Genome Size (Gb)',
      nameTextStyle: { color: '#3a6ea5' },
      axisLabel: { color: '#3a6ea5', formatter: '{value} Gb' },
      splitLine: { lineStyle: { type: 'dashed', color: '#eee' } },
    },
    // 按 BUSCO（value[2]）映射颜色：红 → 橙 → 蓝 → 绿
    visualMap: {
      min: 70,
      max: 100,
      dimension: 2,
      orient: 'vertical',
      right: 10,
      top: 'middle',
      text: ['High', 'Low'],
      calculable: true,
      itemHeight: 120,
      inRange: {
        color: ['#F56C6C', '#E6A23C', '#409EFF', '#67C23A'],
      },
    },
    series: [
      {
        name: 'Genome Size',
        type: 'scatter',
        data,
        symbolSize: 12,
        clip: false,
        itemStyle: { opacity: 0.85 },
        emphasis: {
          focus: 'self',
          itemStyle: { borderWidth: 2, borderColor: '#333', shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.3)' },
        },
      },
    ],
  })
}

// 当 genome 数据加载完成后初始化图表
watch(
  () => genomeStore.genomeOptions,
  (newVal) => {
    if (newVal.length > 0) {
      nextTick(() => {
        initPieChart()
        initBarChart()
        initScatterChart()
      })
    }
  },
)

onMounted(() => {
  window.addEventListener('resize', handleResize)
  // 如果数据已加载，直接初始化
  if (genomeStore.genomeOptions.length > 0) {
    nextTick(() => {
      initPieChart()
      initBarChart()
      initScatterChart()
    })
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
  barChart?.dispose()
  scatterChart?.dispose()
})

// ==================== Meilisearch 即时搜索 ====================
const PAGE_SIZE = 20
const searchQuery = ref('')
const selectedGenomes = ref<string[]>([])
const genomeFacets = ref<Record<string, number>>({})
const searchHits = ref<MeiliGeneHit[]>([])
const totalHits = ref(0)
const processingTimeMs = ref(0)
const isSearching = ref(false)
const searchError = ref('')
const currentPage = ref(1)

/** 物种过滤下拉选项：按命中数降序 */
const genomeFilterOptions = computed(() =>
  Object.entries(genomeFacets.value)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({ label: `${name} (${count})`, value: name })),
)

/** 当前页起始 offset */
const currentOffset = computed(() => (currentPage.value - 1) * PAGE_SIZE)
/** offset + limit 不能超过 Meilisearch 的分页窗口上限（默认 1000） */
const reachWindowLimit = computed(() => currentOffset.value + PAGE_SIZE >= MEILI_MAX_WINDOW)
const hasPrevPage = computed(() => currentPage.value > 1)
const hasNextPage = computed(
  () => !reachWindowLimit.value && currentOffset.value + searchHits.value.length < totalHits.value,
)
const pageInfo = computed(() => {
  if (totalHits.value === 0) return ''
  const from = currentOffset.value + 1
  const to = currentOffset.value + searchHits.value.length
  return `${from}-${to} / ~${totalHits.value.toLocaleString()}`
})

/** 请求序号：仅采纳最后一次请求的结果，防止竞态覆盖 */
let searchSeq = 0
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let abortController: AbortController | null = null

async function doSearch(): Promise<void> {
  const seq = ++searchSeq
  const q = searchQuery.value.trim()

  // 空关键词：清空结果面板
  if (!q) {
    searchHits.value = []
    totalHits.value = 0
    processingTimeMs.value = 0
    searchError.value = ''
    isSearching.value = false
    return
  }

  abortController?.abort()
  abortController = new AbortController()
  isSearching.value = true
  searchError.value = ''

  try {
    const data = await searchGenes({
      q,
      offset: currentOffset.value,
      limit: PAGE_SIZE,
      genomeIds: selectedGenomes.value,
      signal: abortController.signal,
    })
    if (seq !== searchSeq) return // 已有更新的请求，丢弃过期结果
    searchHits.value = data.hits
    totalHits.value = data.estimatedTotalHits
    processingTimeMs.value = data.processingTimeMs
    // 分面计数仅在无过滤条件时刷新，避免选择某物种后下拉选项塌缩成只剩该项
    if (data.offset === 0 && selectedGenomes.value.length === 0) {
      genomeFacets.value = data.genomeFacets
    }
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') return
    if (seq !== searchSeq) return
    searchHits.value = []
    totalHits.value = 0
    searchError.value = e instanceof MeiliSearchError ? e.message : '搜索失败，请稍后重试'
  } finally {
    if (seq === searchSeq) isSearching.value = false
  }
}

// 输入 / 过滤变更：重置到第 1 页并防抖 300ms 后搜索
watch([searchQuery, selectedGenomes], () => {
  currentPage.value = 1
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(doSearch, 300)
})

function searchNow(): void {
  if (debounceTimer) clearTimeout(debounceTimer)
  currentPage.value = 1
  doSearch()
}

function goPrevPage(): void {
  if (hasPrevPage.value) {
    currentPage.value--
    doSearch()
  }
}

function goNextPage(): void {
  if (hasNextPage.value) {
    currentPage.value++
    doSearch()
  }
}

/** 渲染高亮字段：优先用 Meilisearch 返回的 _formatted（仅保留 <em> 标签），否则转义原文 */
function renderHitField(hit: MeiliGeneHit, field: 'geneid' | 'alias'): string {
  const formatted = hit._formatted?.[field]
  return formatted ? sanitizeHighlight(formatted) : escapeHtml(hit[field] || '')
}

/**
 * 点击结果 → 基因详情页。
 * 复用项目既有的 geneid_summary 流程（与 RegionSearchView 一致）：
 * 拉取基因摘要写入 navigation store，再跳转到 idSearchSummary 详情页。
 */
async function goToGeneDetail(hit: MeiliGeneHit): Promise<void> {
  const requestId = `meili_home_${Date.now()}`
  try {
    const response = await httpInstance.post('/CottonOGD_api/geneid_summary/', {
      gene_id: hit.geneid,
      genome_id: hit.genome_id,
      request_id: requestId,
    }) as any

    if (response && response.geneid_result) {
      const searchResults = {
        geneid_result:
          typeof response.geneid_result === 'string'
            ? JSON.parse(response.geneid_result)
            : response.geneid_result,
        gene_info_result:
          typeof response.gene_info_result === 'string'
            ? JSON.parse(response.gene_info_result)
            : response.gene_info_result,
        search_map:
          typeof response.search_map === 'string'
            ? JSON.parse(response.search_map)
            : response.search_map,
        gene_go_result: response.gene_go_result || [],
        gene_kegg_result: response.gene_kegg_result || [],
      }
      const dbIds = searchResults.search_map
        ? Object.values(searchResults.search_map)
            .map((item: any) => item.db_id)
            .filter(Boolean)
        : []

      navigationStore.setNavigationData('geneSearch', {
        results: searchResults,
        dbIds: dbIds,
        requestId: requestId,
      })
      router.push({ name: 'idSearchSummary' })
    } else {
      ElMessage.error('未找到该基因的详细信息')
    }
  } catch (e) {
    console.error('Failed to open gene detail:', e)
    ElMessage.error('打开基因详情失败，请稍后重试')
  }
}

const fillExample = (example: string) => {
  searchQuery.value = example
  searchNow()
}
</script>

<template>
  <div class="home">
    <!-- 英雄区域 -->
    <section class="hero-section">
      <div class="container">
        <div class="hero-content">
          <h1>{{ t('welcome_to_cottonogd') }}</h1>
          <p class="hero-subtitle">{{ t('a_comprehensive_cotton_orthogroups_database') }}</p>
          <p class="hero-description">{{ t('cottonogd_description') }}</p>
         
          
          <!-- 水平布局搜索框 -->
          <div class="search-box-container">
            <!-- 水平排列：物种过滤 + 输入框 + 搜索按钮 -->
            <div class="search-row">
              <el-select
                v-model="selectedGenomes"
                class="database-select"
                size="large"
                multiple
                filterable
                collapse-tags
                collapse-tags-tooltip
                clearable
                placeholder="All Genomes"
              >
                <el-option
                  v-for="option in genomeFilterOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>

              <el-input
                v-model="searchQuery"
                placeholder="Search by gene ID or alias, e.g. Gano_001"
                clearable
                size="large"
                class="search-input"
                :suffix-icon="isSearching ? Loading : Search"
                @keyup.enter="searchNow"
              />

              <el-button
                type="primary"
                size="large"
                :loading="isSearching"
                class="search-btn"
                @click="searchNow"
              >
                <el-icon v-if="!isSearching"><Search /></el-icon>
                {{ t('search') }}
              </el-button>
            </div>

            <!-- 即时搜索结果面板 -->
            <el-collapse-transition>
              <div v-if="searchQuery.trim()" class="search-results-panel">
                <!-- 加载中 -->
                <div v-if="isSearching && searchHits.length === 0" class="results-state">
                  <el-icon class="is-loading" :size="20"><Loading /></el-icon>
                  <span>Searching...</span>
                </div>

                <!-- 错误提示 -->
                <el-alert
                  v-else-if="searchError"
                  :title="searchError"
                  type="error"
                  show-icon
                  :closable="false"
                />

                <!-- 空状态 -->
                <div v-else-if="searchHits.length === 0" class="results-state empty">
                  <el-icon :size="20"><Search /></el-icon>
                  <span>
                    No results for "{{ searchQuery.trim() }}". Try a shorter keyword, or filter by
                    genome.
                  </span>
                </div>

                <!-- 结果列表 -->
                <template v-else>
                  <div class="results-meta">
                    <span>About {{ totalHits.toLocaleString() }} hits</span>
                    <el-tag size="small" type="info" effect="plain">{{ processingTimeMs }} ms</el-tag>
                  </div>

                  <!-- 深分页提示：Meilisearch 默认 offset+limit 上限 1000 -->
                  <el-alert
                    v-if="reachWindowLimit"
                    type="warning"
                    :closable="false"
                    class="window-limit-alert"
                    title="Too many hits: only the first 1000 results are browsable. Refine your keyword or filter by genome."
                  />

                  <ul class="results-list">
                    <li
                      v-for="hit in searchHits"
                      :key="hit.id"
                      class="result-item"
                      @click="goToGeneDetail(hit)"
                    >
                      <div class="result-main">
                        <!-- geneid（高亮） -->
                        <span class="result-geneid" v-html="renderHitField(hit, 'geneid')"></span>
                        <!-- alias（高亮） -->
                        <span class="result-alias" v-html="renderHitField(hit, 'alias')"></span>
                      </div>
                      <!-- genome_id：geneid 在不同基因组下可能重复，必须同时展示 -->
                      <el-tag size="small" type="success" effect="light" class="result-genome">
                        {{ hit.genome_id }}
                      </el-tag>
                    </li>
                  </ul>

                  <div class="results-pagination">
                    <el-button
                      size="small"
                      :disabled="!hasPrevPage || isSearching"
                      @click="goPrevPage"
                    >
                      Prev
                    </el-button>
                    <span class="page-info">{{ pageInfo }}</span>
                    <el-button
                      size="small"
                      :disabled="!hasNextPage || isSearching"
                      @click="goNextPage"
                    >
                      Next
                    </el-button>
                  </div>
                </template>
              </div>
            </el-collapse-transition>
            
            <!-- 搜索提示 -->
            <div class="search-tips">
              <span class="tip-label">{{ t('example') }}:</span>
              <el-tag size="small" class="tip-tag" @click="fillExample('Ghir_A01G000100')">Ghir_A01G000100</el-tag>
              <el-tag size="small" class="tip-tag" @click="fillExample('Transcription Factor')">Transcription Factor</el-tag>
              <el-tag size="small" class="tip-tag" @click="fillExample('ABC transporter')">ABC transporter</el-tag>
            </div>
          </div>
        </div>
      </div>
    </section>
    <!-- 数据库统计区域 -->
     <!--
      <section class="stats-section bg-light">
      <div class="container">
        <h2 class="section-title">{{ t('database_statistics') }}</h2>
        <el-row :gutter="30">
          <el-col v-for="(stat, index) in stats" :key="index" :xs="12" :sm="8" :md="4">
            <div class="stats-card">
              <div class="stats-icon">
                <i :class="stat.icon"></i>
              </div>
              <div class="stats-content">
                <div class="stats-value">{{ stat.value }}</div>
                <div class="stats-label">{{ stat.label }}</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </section>
    -->
    <!-- 图表可视化区域 -->
    <section class="charts-section">
      <div class="container">
        <h2 class="section-title">{{ t('data_visualization') || 'Data Visualization' }}</h2>
        <el-row :gutter="30">
          <el-col :xs="24" :md="12">
            <el-card shadow="hover">
              <div ref="pieChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-card shadow="hover">
              <div ref="barChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
        </el-row>
        <el-row :gutter="30" class="mt-3">
          <el-col :span="24">
            <el-card shadow="hover">
              <div ref="scatterChartRef" class="chart-container chart-container-wide"></div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </section>
    <!-- 核心功能区域 -->
    <section class="features-section">
      <div class="container">
        <h2 class="section-title">{{ t('core_features') }}</h2>
        <el-row :gutter="24">
          <!-- 浏览功能 -->
          <el-col :span="8">
            <el-card shadow="hover" class="feature-card">
              <div class="feature-icon">
                <i class="fas fa-database"></i>
              </div>
              <h3 class="feature-title">{{ t('browse') }}</h3>
              <p class="feature-description">
                Explore cotton genome data, species information, transcription factors, and transposable elements 
                through intuitive browsing interfaces.
              </p>
              <div class="feature-actions">
                <router-link to="/browse/tf">
                  <el-button type="primary" plain size="medium">TF Database</el-button>
                </router-link>
                <router-link to="/browse/tr">
                  <el-button type="primary" plain size="medium" class="ml-2">TR Database</el-button>
                </router-link>
              </div>
            </el-card>
          </el-col>
          
          <!-- 分析工具 -->
          <el-col :span="8">
            <el-card shadow="hover" class="feature-card">
              <div class="feature-icon">
                <i class="fas fa-tools"></i>
              </div>
              <h3 class="feature-title">Analysis {{ t('tools') }}</h3>
              <p class="feature-description">
                Utilize a suite of powerful tools for sequence analysis, functional annotation, 
                expression analysis, and pathway enrichment.
              </p>
              <div class="feature-actions">
                <router-link to="/tools/blastp">
                  <el-button type="primary" plain size="medium">BLAST</el-button>
                </router-link>
                <router-link to="/tools/go-enrichment">
                  <el-button type="primary" plain size="medium" class="ml-2">{{ t('go_enrichment') }}</el-button>
                </router-link>
              </div>
            </el-card>
          </el-col>
          
          <!-- 可视化功能 -->
          <el-col :span="8">
            <el-card shadow="hover" class="feature-card">
              <div class="feature-icon">
                <i class="fas fa-chart-pie"></i>
              </div>
              <h3 class="feature-title">Visualization</h3>
              <p class="feature-description">
                {{ t('view') }} genomic data interactively with {{ t('jbrowse') }}, explore gene expression patterns, 
                and visualize pathway networks.
              </p>
              <div class="feature-actions">
                <router-link to="/jbrowse">
                  <el-button type="primary" plain size="medium">{{ t('jbrowse') }}</el-button>
                </router-link>
                <router-link to="/tools/gene-expression">
                  <el-button type="primary" plain size="medium" class="ml-2">Expression</el-button>
                </router-link>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </section>
    
    
    
    <!-- 快速访问区域 -->
    <!--<section class="quick-access-section">
      <div class="container">
        <h2 class="section-title">{{ t('quick_access') }}</h2>
        <el-row :gutter="24">
          <el-col :span="6">
            <router-link to="/jbrowse" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-chromosome"></i>
                </div>
                <h4 class="quick-link-title">{{ t('genome') }} Browser</h4>
                <p class="quick-link-description">Interactive genome visualization with {{ t('jbrowse') }}</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/blastp" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-search"></i>
                </div>
                <h4 class="quick-link-title">{{ t('blast_search') }}</h4>
                <p class="quick-link-description">{{ t('sequence') }} similarity search across genomes</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/go-enrichment" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-project-diagram"></i>
                </div>
                <h4 class="quick-link-title">{{ t('go_enrichment') }}</h4>
                <p class="quick-link-description">Gene ontology enrichment analysis</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/gene-expression" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-chart-line"></i>
                </div>
                <h4 class="quick-link-title">{{ t('gene_expression') }}</h4>
                <p class="quick-link-description">Explore gene expression patterns</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/download" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-download"></i>
                </div>
                <h4 class="quick-link-title">Data {{ t('download') }}</h4>
                <p class="quick-link-description">{{ t('download') }} genome assemblies and annotations</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/primer-design" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-dna"></i>
                </div>
                <h4 class="quick-link-title">{{ t('primer_design') }}</h4>
                <p class="quick-link-description">Design PCR primers for gene amplification</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/browse/tf" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-user-tie"></i>
                </div>
                <h4 class="quick-link-title">TF Database</h4>
                <p class="quick-link-description">Transcription factor families and functions</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/id-search" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-id-card"></i>
                </div>
                <h4 class="quick-link-title">ID {{ t('search') }}</h4>
                <p class="quick-link-description">{{ t('search') }} genes by ID or symbol</p>
              </el-card>
            </router-link>
          </el-col>
        </el-row>
      </div>
    </section>-->
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<style scoped>
.home {
  padding-bottom: 0;
}

/* 图表区域 */
.charts-section {
  padding: 60px 0;
  background-color: #f8f9fa;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.chart-container-wide {
  height: 460px;
}

.mt-3 {
  margin-top: 20px;
}

/* 英雄区域 */
.hero-section {
  background: linear-gradient(135deg, #3a6ea5 0%, #7297bd 100%);
  color: #ffffff;
  padding: 60px 0;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: url('data:image/svg+xml;charset=utf-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%25%22 height=%22100%25%22%3E%3Cdefs%3E%3Cpattern id=%22grid%22 width=%2240%22 height=%2240%22 patternUnits=%22userSpaceOnUse%22%3E%3Cpath d=%22M 40 0 L 0 0 0 40%22 fill=%22none%22 stroke=%22rgba(255,255,255,0.1)%22 stroke-width=%221%22/%3E%3C/pattern%3E%3C/defs%3E%3Crect width=%22100%25%22 height=%22100%25%22 fill=%22url(%23grid)%22/%3E%3C/svg%3E');
  opacity: 0.3;
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 900px;
  margin: 0 auto;
}

.hero-section h1 {
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #ffffff;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.hero-subtitle {
  font-size: 24px;
  font-weight: 500;
  margin-bottom: 24px;
  color: rgba(255, 255, 255, 0.9);
}

.hero-description {
  font-size: 16px;
  line-height: 1.6;
  margin-bottom: 32px;
  color: rgba(255, 255, 255, 0.85);
}

/* 水平布局搜索框 */
.search-box-container {
  max-width: 800px;
  margin: 0 auto;
  background-color: rgba(255, 255, 255, 0.95);
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

/* 水平排列的搜索行 */
.search-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

/* 物种过滤选择器 */
.database-select {
  width: 210px;
  flex-shrink: 0;
}

.database-select :deep(.el-input__wrapper) {
  background-color: #f5f7fa;
  border-radius: 6px;
}

/* 搜索输入框 */
.search-input {
  flex: 1;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 6px;
}

/* 搜索按钮 */
.search-btn {
  flex-shrink: 0;
  background-color: #3a6ea5;
  border-color: #3a6ea5;
  border-radius: 6px;
  padding: 0 24px;
}

.search-btn:hover {
  background-color: #2c5282;
  border-color: #2c5282;
}

/* 即时搜索结果面板 */
.search-results-panel {
  text-align: left;
  margin-top: 4px;
}

.results-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 12px;
  color: #6c757d;
  font-size: 14px;
}

.results-state.empty {
  flex-direction: column;
}

.results-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #495057;
  padding: 8px 4px;
}

.window-limit-alert {
  margin: 8px 0;
}

.results-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 420px;
  overflow-y: auto;
  border-top: 1px solid #e9ecef;
}

.result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid #f1f3f5;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.result-item:hover {
  background-color: #f0f6ff;
}

.result-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.result-geneid {
  font-weight: 600;
  color: #2c3e50;
  font-size: 14px;
}

.result-geneid :deep(em),
.result-alias :deep(em) {
  font-style: normal;
  color: #e6a23c;
  font-weight: 700;
}

.result-alias {
  font-size: 12px;
  color: #6c757d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-genome {
  flex-shrink: 0;
}

.results-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding-top: 12px;
}

.page-info {
  font-size: 13px;
  color: #495057;
}

/* 搜索提示 */
.search-tips {
  margin-top: 12px;
  text-align: left;
  font-size: 14px;
  color: #666;
}

.tip-label {
  font-weight: 500;
  margin-right: 10px;
}

.tip-tag {
  cursor: pointer;
  margin-right: 8px;
  transition: all 0.3s ease;
}

.tip-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* 通用 section 样式 */
.features-section,
.quick-access-section,
.partners-section {
  padding: 60px 0;
  background-color: #ffffff;
}

.stats-section,
.news-research-section {
  padding: 60px 0;
  background-color: #f8f9fa;
}

.section-title {
  font-size: 32px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 40px;
  text-align: center;
  position: relative;
  padding-bottom: 16px;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 3px;
  background-color: #3a6ea5;
  border-radius: 2px;
}

/* 功能卡片 */
.feature-card {
  text-align: center;
  padding: 30px 20px;
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid #e9ecef;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
  border-color: #3a6ea5;
}

.feature-icon {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60px;
}

.feature-icon i {
  font-size: 48px;
  color: #3a6ea5;
}

.feature-title {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.feature-description {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 24px;
  min-height: 80px;
}

.feature-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* 统计卡片 */
.stats-card {
  background-color: #ffffff;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  text-align: center;
  border: 1px solid #e9ecef;
}

.stats-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
}

.stats-icon {
  font-size: 48px;
  color: #3a6ea5;
  margin-bottom: 16px;
}

.stats-value {
  font-size: 32px;
  font-weight: 700;
  color: #3a6ea5;
  margin-bottom: 8px;
}

.stats-label {
  font-size: 14px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* 快速访问卡片 */
.quick-link {
  text-decoration: none;
  display: block;
}

.quick-link-card {
  text-align: center;
  padding: 24px 16px;
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid #e9ecef;
  height: 100%;
}

.quick-link-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
  border-color: #3a6ea5;
}

.quick-link-icon {
  font-size: 40px;
  color: #3a6ea5;
  margin-bottom: 16px;
}

.quick-link-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.quick-link-description {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  margin: 0;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .hero-section h1 {
    font-size: 32px;
  }
  
  .hero-subtitle {
    font-size: 18px;
  }
  
  /* 移动端垂直布局 */
  .search-row {
    flex-direction: column;
    gap: 12px;
  }
  
  .database-select {
    width: 100%;
  }
  
  .search-btn {
    width: 100%;
  }
  
  .search-box-container {
    padding: 16px;
  }

  .results-list {
    max-height: 320px;
  }
}
</style>
