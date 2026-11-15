<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('genome_synteny') }}</h2>

    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('genome_variation_search') }}</span>
        </div>
      </template>

      <el-form label-width="200px">
        <el-form-item :label="t('reference_genome')">
          <el-tree-select
            v-model="sourceGenome"
            :data="genomeOptions"
            :props="{ value: 'value', label: 'label', children: 'children' }"
            :placeholder="t('select_reference_genome')"
            style="width: 100%"
            :loading="genomeLoading"
          />
        </el-form-item>

        <el-form-item :label="t('query_genome')">
          <el-tree-select
            v-model="targetGenome"
            :data="genomeOptions"
            :props="{ value: 'value', label: 'label', children: 'children' }"
            :placeholder="t('select_query_genome')"
            style="width: 100%"
            :loading="genomeLoading"
          />
        </el-form-item>

        <!-- 检索方式：全基因组（默认，仅绘制染色体级桑葚图）/ 按区域 / 按基因 -->
        <el-form-item :label="t('synteny_search_mode')">
          <el-radio-group v-model="mode">
            <el-radio value="all">{{ t('synteny_scope_all') }}</el-radio>
            <el-radio value="region">{{ t('synteny_by_region') }}</el-radio>
            <el-radio value="gene">{{ t('synteny_by_gene') }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="mode === 'region'" :label="t('region')">
          <el-input
            v-model="region"
            :placeholder="t('synteny_region_placeholder')"
            clearable
          />
        </el-form-item>

        <el-form-item v-else-if="mode === 'gene'" :label="t('gene_id')">
          <el-input
            v-model="geneId"
            :placeholder="t('synteny_gene_placeholder')"
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button type="info" size="small" @click="fillExample">
            {{ t('load_example') }}
          </el-button>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" class="ms-2" @click="handleSubmit">
            <el-icon><Search /></el-icon>
            {{ t('search') }}
          </el-button>
        </el-form-item>

        <el-alert
          v-if="error"
          :title="error"
          type="error"
          show-icon
          class="mt-3"
          @close="error = ''"
        />
      </el-form>
    </el-card>

    <el-card v-if="view" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center flex-wrap">
          <span>{{ t('synteny_sankey') }}</span>
          <div>
            <el-tag type="info" class="mr-2">
              {{ t('ref') }}: {{ view.sourceId }}
            </el-tag>
            <el-tag type="info" class="mr-2">
              {{ t('query') }}: {{ view.targetId }}
            </el-tag>
            <el-tag type="info" class="mr-2">
              {{ t('region') }}: {{ view.scope }}
            </el-tag>
            <el-tag type="success">
              {{ t('synteny_block_count') }}: {{ view.blockCount }}
            </el-tag>
            <el-tag type="success" class="ml-2">
              {{ t('gene_count') }}: {{ view.geneCount }}
            </el-tag>
          </div>
        </div>
      </template>

      <div ref="sankeyRef" class="sankey-container"></div>

      <el-alert
        v-if="view.links.length === 0"
        :title="t('synteny_no_blocks')"
        type="info"
        :closable="false"
        show-icon
        class="mt-3"
      />
    </el-card>

    <el-card v-if="view && hasFigures" class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('figures') }}</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col v-if="view.figures?.dotplot" :span="8">
          <h6>{{ t('figure_dotplot') }}</h6>
          <img :src="view.figures.dotplot" class="figure-img" alt="dotplot" />
        </el-col>
        <el-col v-if="view.figures?.depth" :span="8">
          <h6>{{ t('figure_depth') }}</h6>
          <img :src="view.figures.depth" class="figure-img" alt="depth" />
        </el-col>
        <el-col v-if="view.figures?.karyotype" :span="8">
          <h6>{{ t('figure_karyotype') }}</h6>
          <img :src="view.figures.karyotype" class="figure-img" alt="karyotype" />
        </el-col>
      </el-row>
    </el-card>

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import echarts from '@/utils/echarts'
import {
  getGenomeSynteny,
  getMicrosynteny,
  getSyntenyPairs,
  type MicrosyntenyResult,
  type SyntenyTrackGene,
} from '@/api'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'

const { t } = useI18n()
const { genomeOptions, genomeLoading, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector()

type SearchMode = 'all' | 'region' | 'gene'

/** 桑葚图节点：name 为展示名（原始染色体 id 或基因 id），genome 标记来源（source/target） */
interface SankeyNode {
  name: string
  genome: string
}
interface SankeyLink {
  source: string
  target: string
  value: number
}

/** 页面统一视图模型：把 genome_synteny（染色体级）与 microsynteny（基因级）两种响应归一化 */
interface SankeyView {
  sourceId: string
  targetId: string
  scope: string
  blockCount: number
  geneCount: number
  nodes: SankeyNode[]
  links: SankeyLink[]
  figures?: { dotplot?: string; depth?: string; karyotype?: string }
}

const sourceGenome = ref('')
const targetGenome = ref('')
const mode = ref<SearchMode>('all')
const region = ref('')
const geneId = ref('')
const loading = ref(false)
const error = ref('')
const view = ref<SankeyView | null>(null)

const sankeyRef = shallowRef<HTMLElement | null>(null)
let chart: ReturnType<typeof echarts.init> | null = null

const hasFigures = computed(
  () =>
    !!view.value?.figures &&
    (!!view.value.figures.dotplot || !!view.value.figures.depth || !!view.value.figures.karyotype),
)

const COLORS = { source: '#3a6ea5', target: '#7297bd' }

/** 渲染桑葚图。
 * 节点 name 直接使用后端返回的原始 id（染色体如 A01，基因如 Ghir_A01G000100），不做 1/2/3 重编号。
 * 默认（全基因组）仅染色体级节点、不含 scaffold/contig；按区域/基因检索时绘制检索到的区块。
 * setOption 使用 notMerge=true，确保切换检索条件时清空上一张图，避免残留连线。 */
function renderSankey() {
  if (!sankeyRef.value) return
  if (!chart) chart = echarts.init(sankeyRef.value)

  if (!view.value || view.value.nodes.length === 0) {
    chart.clear()
    return
  }

  const nodes = view.value.nodes.map((n) => ({
    name: n.name,
    itemStyle: { color: n.genome === 'target' ? COLORS.target : COLORS.source },
  }))
  const links = view.value.links.map((l) => ({
    source: l.source,
    target: l.target,
    value: l.value ?? 1,
  }))

  chart.setOption(
    {
      tooltip: { trigger: 'item', triggerOn: 'mousemove' },
      series: [
        {
          type: 'sankey',
          emphasis: { focus: 'adjacency' },
          nodeAlign: 'left',
          data: nodes,
          links,
          // 节点较少时（如染色体级视图）显示标签；基因级视图节点成百上千，隐藏标签以免拥挤
          label: { show: nodes.length <= 300, fontSize: 12 },
          lineStyle: { color: 'gradient', opacity: 0.5, curveness: 0.5 },
        },
      ],
    },
    true,
  )
  chart.resize()
}

watch(view, () => nextTick(renderSankey))

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  await ensureGenomesLoaded()

  // 用后端可用的共线性基因组对作为默认 source/target（数据驱动），再自动加载一次全基因组桑葚图
  try {
    const pairs = await getSyntenyPairs()
    const p = pairs.data?.pairs?.[0]
    if (p) {
      sourceGenome.value = p.source
      targetGenome.value = p.target
    }
  } catch {
    /* 失败则回退到默认基因组 */
  }
  if (!sourceGenome.value) {
    const def = pickDefaultGenome()
    if (def) sourceGenome.value = def
  }
  if (sourceGenome.value && targetGenome.value && !view.value) {
    await handleSubmit()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})

const fillExample = () => {
  sourceGenome.value = 'G.hirsutumAD1_TM-1_HAU_v1.1'
  targetGenome.value = 'G.hirsutumAD1_TM-1_ZJU_v1.1T2T'
  region.value = 'Ghir_A01:1-1000000'
  geneId.value = 'Ghir_A01G000100'
}

/** 由 microsynteny 的 tracks 构建基因级桑葚图：
 * 源/目标两条轨道按 (block_id, order) 一一配对，形成跨基因组连线；节点为原始基因 id。
 * tracks 为空时回退到 graph，并补齐所有连线端点，避免 ECharts 因缺失节点报错。 */
function buildGeneSankey(data: MicrosyntenyResult): { nodes: SankeyNode[]; links: SankeyLink[] } {
  const nodes: SankeyNode[] = []
  const seen = new Set<string>()
  const add = (id: string, genome: string) => {
    if (!id || seen.has(id)) return
    seen.add(id)
    nodes.push({ name: id, genome })
  }

  const src: SyntenyTrackGene[] = data.tracks?.source ?? []
  const tgt: SyntenyTrackGene[] = data.tracks?.target ?? []
  src.forEach((g) => add(g.id, 'source'))
  tgt.forEach((g) => add(g.id, 'target'))

  const links: SankeyLink[] = []
  if (src.length && tgt.length) {
    const keyOf = (g: SyntenyTrackGene) => `${g.block_id}#${g.order}`
    const tMap = new Map<string, SyntenyTrackGene>()
    tgt.forEach((g) => {
      if (!tMap.has(keyOf(g))) tMap.set(keyOf(g), g)
    })
    src.forEach((s) => {
      const hit = tMap.get(keyOf(s))
      if (hit) links.push({ source: s.id, target: hit.id, value: 1 })
    })
  }

  if (nodes.length === 0) {
    const genomeOf = (id: string) =>
      tgt.some((g) => g.id === id) ? 'target' : src.some((g) => g.id === id) ? 'source' : id.startsWith('Ghir_') ? 'source' : 'target'
    ;(data.graph?.nodes ?? []).forEach((n) => add(n.id, n.genome))
    ;(data.graph?.links ?? []).forEach((l) => {
      add(l.source, genomeOf(l.source))
      add(l.target, genomeOf(l.target))
      links.push({ source: l.source, target: l.target, value: 1 })
    })
  }

  return { nodes, links }
}

const handleSubmit = async () => {
  if (!sourceGenome.value) {
    error.value = t('please_select_reference_genome')
    return
  }
  if (!targetGenome.value) {
    error.value = t('please_select_query_genome')
    return
  }
  if (mode.value === 'region' && !region.value.trim()) {
    error.value = t('please_enter_region')
    return
  }
  if (mode.value === 'gene' && !geneId.value.trim()) {
    error.value = t('please_enter_gene')
    return
  }

  loading.value = true
  error.value = ''
  try {
    if (mode.value === 'gene') {
      const res = await getMicrosynteny({
        source: sourceGenome.value,
        target: targetGenome.value,
        gene_ids: geneId.value.trim(),
      })
      if (res.code !== 0) {
        error.value = res.message
        view.value = null
        return
      }
      const d = res.data
      const { nodes, links } = buildGeneSankey(d)
      const blockIds = new Set(
        [...(d.tracks?.source ?? []), ...(d.tracks?.target ?? [])]
          .map((g) => g.block_id)
          .filter(Boolean),
      )
      view.value = {
        sourceId: d.source_id,
        targetId: d.target_id,
        scope: (d.query_genes ?? []).join(', ') || geneId.value.trim(),
        blockCount: blockIds.size,
        geneCount: nodes.length,
        nodes,
        links,
      }
    } else {
      // 全基因组：不传 chromosome → 后端返回全部染色体级桑葚图
      // 按区域：从 “染色体:起-止” 中解析染色体名后过滤（后端当前按染色体聚合）
      const chromosome = mode.value === 'region' ? region.value.trim().split(':')[0].trim() : undefined
      const res = await getGenomeSynteny({
        source: sourceGenome.value,
        target: targetGenome.value,
        chromosome,
      })
      if (res.code !== 0) {
        error.value = res.message
        view.value = null
        return
      }
      const d = res.data
      view.value = {
        sourceId: d.source_id,
        targetId: d.target_id,
        scope: mode.value === 'all' ? t('synteny_scope_all') : d.chromosome,
        blockCount: d.block_count,
        geneCount: d.gene_count,
        nodes: (d.sankey?.nodes ?? []).map((n) => ({ name: n.name, genome: n.genome })),
        links: (d.sankey?.links ?? []).map((l) => ({
          source: l.source,
          target: l.target,
          value: l.value ?? 1,
        })),
        figures: d.figures,
      }
    }
    await nextTick()
    renderSankey()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
}

.mt-4 { margin-top: 1.5rem; }
.mb-4 { margin-bottom: 1.5rem; }
.mt-3 { margin-top: 1rem; }
.mr-2 { margin-right: 0.5rem; }
.ml-2 { margin-left: 0.5rem; }

.card-header {
  font-size: 16px;
  font-weight: 500;
}

.d-flex { display: flex; }
.flex-wrap { flex-wrap: wrap; }
.justify-content-between { justify-content: space-between; }
.align-items-center { align-items: center; }

.sankey-container {
  width: 100%;
  height: 420px;
}

.figure-img {
  width: 100%;
  border: 1px solid #e9ecef;
  border-radius: 8px;
}
</style>
