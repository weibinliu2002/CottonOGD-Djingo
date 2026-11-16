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

    <!-- 基因检索时额外展示染色体级视图：查询基因所在共线性块对应的染色体对 -->
    <el-card v-if="chromosomeView" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center flex-wrap">
          <span>{{ t('synteny_chromosome_level_chart') }}</span>
          <div>
            <el-tag type="info" class="mr-2">
              {{ t('ref') }}: {{ chromosomeView.sourceId }}
            </el-tag>
            <el-tag type="info" class="mr-2">
              {{ t('query') }}: {{ chromosomeView.targetId }}
            </el-tag>
            <el-tag type="info">
              {{ t('chromosome') }}: {{ chromosomeView.scope }}
            </el-tag>
          </div>
        </div>
      </template>

      <div class="sankey-legend">
        <span class="legend-item">
          <i class="legend-dot source"></i>{{ t('ref') }}: {{ chromosomeView.sourceId }}
        </span>
        <span class="legend-item">
          <i class="legend-dot target"></i>{{ t('query') }}: {{ chromosomeView.targetId }}
        </span>
        <span class="legend-hint">{{ t('synteny_chromosome_level_hint') }}</span>
      </div>

      <div ref="chrSankeyRef" class="sankey-container chromosome-sankey"></div>

      <el-alert
        v-if="chromosomeView.links.length === 0"
        :title="t('synteny_no_blocks')"
        type="info"
        :closable="false"
        show-icon
        class="mt-3"
      />
    </el-card>

    <el-alert
      v-if="chromosomeError"
      :title="chromosomeError"
      type="warning"
      :closable="false"
      show-icon
      class="mb-4"
    />

    <el-card v-if="view" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center flex-wrap">
          <span>{{ mode === 'gene' ? t('synteny_gene_level_chart') : t('synteny_sankey') }}</span>
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

      <div class="sankey-legend">
        <span class="legend-item">
          <i class="legend-dot source"></i>{{ t('ref') }}: {{ view.sourceId }}
        </span>
        <span class="legend-item">
          <i class="legend-dot target"></i>{{ t('query') }}: {{ view.targetId }}
        </span>
      </div>

      <!-- 基因级：按 JCVI MCscan Microsynteny visualization 的两条基因轨道 + 共线连线绘制 -->
      <template v-if="mode === 'gene'">
        <div v-if="microLayout" class="microsynteny-wrap">
          <div class="microsynteny-hint">
            {{ t('synteny_micro_window_hint') }} · {{ microLayout.windowLabel }}
          </div>
          <svg
            class="micro-svg"
            viewBox="0 0 1200 380"
            role="img"
            :aria-label="t('synteny_gene_level_chart')"
          >
            <!-- 两条轨道的中轴线与坐标刻度 -->
            <line x1="132" y1="118" x2="1168" y2="118" stroke="#ced4da" />
            <line x1="132" y1="288" x2="1168" y2="288" stroke="#ced4da" />
            <text x="12" y="70" class="track-label">Ref · {{ microLayout.sourceLabel }}</text>
            <text x="12" y="240" class="track-label">Query · {{ microLayout.targetLabel }}</text>
            <g v-for="tick in microLayout.sourceTicks" :key="'st-' + tick.x">
              <line :x1="tick.x" y1="118" :x2="tick.x" y2="124" stroke="#adb5bd" />
              <text :x="tick.x" y="138" class="axis-tick" text-anchor="middle">{{ tick.label }}</text>
            </g>
            <g v-for="tick in microLayout.targetTicks" :key="'tt-' + tick.x">
              <line :x1="tick.x" y1="288" :x2="tick.x" y2="294" stroke="#adb5bd" />
              <text :x="tick.x" y="308" class="axis-tick" text-anchor="middle">{{ tick.label }}</text>
            </g>

            <!-- 共线基因连线：悬停显示两端基因与坐标，点击进入结构变异结果 -->
            <g
              v-for="link in microLayout.links"
              :key="link.id"
              class="micro-link"
              :class="{ query: link.query, inverted: link.inverted }"
            >
              <title>
                {{ link.source.gene.id }} ({{ link.source.gene.chr }}:{{ link.source.gene.start }}-{{ link.source.gene.end }})
                ↔
                {{ link.target.gene.id }} ({{ link.target.gene.chr }}:{{ link.target.gene.start }}-{{ link.target.gene.end }})
                <template v-if="link.inverted">· {{ t('synteny_micro_inversion_hint') }}</template>
              </title>
              <path :d="link.path" class="micro-link-hit" />
              <path :d="link.path" class="micro-link-line" />
            </g>

            <!-- source 轨道基因盒：悬停显示基因 ID，点击进入基因详情 -->
            <g
              v-for="box in microLayout.source"
              :key="'s-' + box.gene.id"
              class="micro-gene"
              role="button"
              tabindex="0"
              @click.stop="openGeneDetail(box)"
              @keydown.enter="openGeneDetail(box)"
            >
              <title>
                {{ box.role }}: {{ box.gene.id }} · {{ box.gene.chr }}:{{ box.gene.start }}-{{ box.gene.end }}
                · {{ box.gene.strand }} · {{ box.gene.block_id }}
              </title>
              <rect
                :x="box.x"
                :y="box.y"
                :width="box.width"
                height="20"
                rx="2"
                fill="#3a6ea5"
                :stroke="box.query ? '#1f2d3d' : 'none'"
                :stroke-width="box.query ? 2 : 0"
              />
              <!-- 基因 ID 只在鼠标悬停（SVG title tooltip）显示，不直接展示在基因块上 -->
            </g>

            <!-- target 轨道基因盒：悬停显示基因 ID，点击进入基因详情 -->
            <g
              v-for="box in microLayout.target"
              :key="'t-' + box.gene.id"
              class="micro-gene"
              role="button"
              tabindex="0"
              @click.stop="openGeneDetail(box)"
              @keydown.enter="openGeneDetail(box)"
            >
              <title>
                {{ box.role }}: {{ box.gene.id }} · {{ box.gene.chr }}:{{ box.gene.start }}-{{ box.gene.end }}
                · {{ box.gene.strand }} · {{ box.gene.block_id }}
              </title>
              <rect
                :x="box.x"
                :y="box.y"
                :width="box.width"
                height="20"
                rx="2"
                fill="#eb6834"
                :stroke="box.query ? '#1f2d3d' : 'none'"
                :stroke-width="box.query ? 2 : 0"
              />
              <!-- 基因 ID 只在鼠标悬停（SVG title tooltip）显示，不直接展示在基因块上 -->
            </g>
          </svg>
          <div class="micro-legend">
            <span><i class="micro-swatch source"></i>{{ t('ref') }} gene</span>
            <span><i class="micro-swatch target"></i>{{ t('query') }} gene</span>
            <span><i class="micro-line-swatch"></i>{{ t('synteny_micro_pair_hint') }}</span>
            <span><i class="micro-line-swatch inverted"></i>{{ t('synteny_micro_inversion_hint') }}</span>
          </div>

          <el-collapse class="micro-table">
            <el-collapse-item :title="t('synteny_micro_pair_table')" name="pairs">
              <el-table :data="microPairRows" size="small" max-height="280" style="width: 100%">
                <el-table-column prop="sourceGene" :label="t('ref') + ' ' + t('gene_id')" min-width="180" />
                <el-table-column prop="sourcePosition" :label="t('ref') + ' ' + t('genome_position')" min-width="190" />
                <el-table-column prop="targetGene" :label="t('query') + ' ' + t('gene_id')" min-width="180" />
                <el-table-column prop="targetPosition" :label="t('query') + ' ' + t('genome_position')" min-width="190" />
                <el-table-column prop="blockId" :label="t('synteny_block_count')" width="110" />
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </div>
        <el-alert
          v-else
          :title="t('synteny_micro_no_pairs')"
          type="info"
          :closable="false"
          show-icon
          class="mt-3"
        />
      </template>

      <div v-else ref="sankeyRef" class="sankey-container"></div>

      <el-alert
        v-if="mode !== 'gene' && view.links.length === 0"
        :title="t('synteny_no_blocks')"
        type="info"
        :closable="false"
        show-icon
        class="mt-3"
      />
    </el-card>

    <!-- JBrowse：单窗口展示这对基因组的 pairwise 共线性（复用站点现有 JBrowse2 静态页，
         通过 ?config= 加载后端提供的 pairwise config；区间/基因检索时 loc 同步定位共线性视图） -->
    <el-card v-if="view && jbrowsePairwiseUrl" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center flex-wrap">
          <span>{{ t('synteny_jbrowse_title') }}</span>
          <span class="jbrowse-hint">{{ t('synteny_jbrowse_hint') }}</span>
        </div>
      </template>
      <iframe
        :key="jbrowsePairwiseUrl"
        :src="jbrowsePairwiseUrl"
        :title="t('synteny_jbrowse_title')"
        class="synteny-jbrowse-frame"
        frameborder="0"
      />
    </el-card>

    <!-- 区间/基因检索：共线性块与共线性基因表格（放在图上方，先展示表格；region/gene 模式下立即渲染，避免图先出现、表格滞后） -->
    <el-card v-if="mode !== 'all'" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center flex-wrap">
          <span>{{ t('synteny_block_gene_table') }}</span>
          <span class="jbrowse-hint">{{ t('synteny_block_gene_hint') }}</span>
        </div>
      </template>
      <el-table
        v-loading="regionBlockLoading"
        :data="blockTableRows"
        size="small"
        max-height="440"
        style="width: 100%"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="block-gene-cell">
              <div class="block-gene-label">{{ t('ref') }} · {{ t('gene_id') }}</div>
              <div class="block-gene-tags">
                <el-tag
                  v-for="gene in row.sourceGenes.slice(0, 80)"
                  :key="'sg-' + row.key + '-' + gene"
                  size="small"
                  class="gene-tag"
                >
                  {{ gene }}
                </el-tag>
                <span v-if="row.sourceGenes.length > 80" class="gene-more">
                  +{{ row.sourceGenes.length - 80 }}
                </span>
              </div>
              <div class="block-gene-label mt-2">{{ t('query') }} · {{ t('gene_id') }}</div>
              <div class="block-gene-tags">
                <el-tag
                  v-for="gene in row.targetGenes.slice(0, 80)"
                  :key="'tg-' + row.key + '-' + gene"
                  size="small"
                  type="warning"
                  class="gene-tag"
                >
                  {{ gene }}
                </el-tag>
                <span v-if="row.targetGenes.length > 80" class="gene-more">
                  +{{ row.targetGenes.length - 80 }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="blockId" :label="t('synteny_block_id')" min-width="160" />
        <el-table-column prop="sourceRegion" :label="t('synteny_reference_interval')" min-width="190" />
        <el-table-column prop="targetRegion" :label="t('synteny_query_interval')" min-width="190" />
        <el-table-column :label="t('synteny_gene_pair_count')" width="150">
          <template #default="{ row }">
            {{ row.sourceGenes.length }} / {{ row.targetGenes.length }}
          </template>
        </el-table-column>
      </el-table>
      <el-alert
        v-if="!regionBlockLoading && blockTableRows.length === 0"
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
        <el-col v-if="view.figures?.dotplot" :span="12" style="min-width:0">
          <h6>{{ t('figure_dotplot') }}</h6>
          <img :src="view.figures.dotplot" class="figure-img" alt="dotplot" />
        </el-col>
        <el-col v-if="view.figures?.depth" :span="12" style="min-width:0">
          <h6>{{ t('figure_depth') }}</h6>
          <img :src="view.figures.depth" class="figure-img" alt="depth" />
        </el-col>
              </el-row>
    </el-card>

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, shallowRef, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import echarts from '@/utils/echarts'
import httpInstance from '@/utils/http.js'
import { useNavigationStore } from '@/stores/modules/navigation'
import {
  getGenomeSynteny,
  getMicrosynteny,
  getSyntenyPairs,
  getChromosomeLengths,
  getGeneGenomicDistribution,
  type ChromosomeLengths,
  type GeneLocationRow,
  type GenomeSyntenyResult,
  type MicrosyntenyResult,
  type SyntenyBlock,
  type SyntenyTrackGene,
} from '@/api'
import { createDefaultLocus, useGenomeSelector } from '@/composables/features/useGenomeBrowser'

const { t } = useI18n()
const router = useRouter()
const navigationStore = useNavigationStore()
const { genomeOptions, genomeLoading, ensureGenomesLoaded, pickDefaultGenome } =
  useGenomeSelector()

type SearchMode = 'all' | 'region' | 'gene'

/** 桑葚图节点：name 为展示名（原始染色体 id 或基因 id），genome 标记来源（source/target）
 * lengthBp 为染色体实际长度（bp），仅染色体级节点有值；用于决定节点高度。 */
interface SankeyNode {
  name: string
  genome: string
  lengthBp?: number
}
interface SankeyLink {
  source: string
  target: string
  value: number
  /** 共线基因数（染色体级）或 1（基因级） */
  geneCount?: number
  /** 基因级连线两端基因的坐标，如 Ghir_A01G000030:65259-68219 */
  sourceRegion?: string
  targetRegion?: string
  blockId?: string
  /** 由 buildSeries 写入，供 ECharts 事件回查原始连线 */
  linkIndex?: number
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
  /** 染色体级视图对应的 source 染色体（全基因组时为空） */
  chromosome?: string
  /** 基因模式下额外高亮的染色体对（来自查询基因所在共线性块） */
  highlightPair?: { source?: string; target?: string }
}

/** 连线对应的区间详情（悬停 tooltip / 点击跳转共用） */
interface LinkIntervalDetail {
  sourceRegion: string
  targetRegion: string
  sourceGenes: { gene_id: string; block_id: string }[]
  targetGenes: { gene_id: string; block_id: string }[]
  blockCount: number
}

/** 基因级微共线性图：两条基因组轨道上的基因盒 + 共线基因连线 */
interface MicroGeneBox {
  gene: SyntenyTrackGene
  role: 'source' | 'target'
  x: number
  width: number
  y: number
  query: boolean
}

interface MicroPairLink {
  id: string
  source: MicroGeneBox
  target: MicroGeneBox
  path: string
  query: boolean
  /** 局部顺序与坐标方向相反（倒位/重排），用不同颜色区分 */
  inverted: boolean
}

interface MicroAxisTick {
  x: number
  label: string
}

interface MicroLayout {
  source: MicroGeneBox[]
  target: MicroGeneBox[]
  links: MicroPairLink[]
  sourceLabel: string
  targetLabel: string
  sourceTicks: MicroAxisTick[]
  targetTicks: MicroAxisTick[]
  windowLabel: string
}

/** 解析后的基因组区间 */
interface RegionRange {
  chr: string
  start: number
  end: number
}

/** 共线性块与基因表格行（区间检索与基因检索共用） */
interface SyntenyBlockRow {
  key: string
  blockId: string
  sourceChr: string
  targetChr: string
  sourceRegion: string
  targetRegion: string
  sourceGenes: string[]
  targetGenes: string[]
}

/** 区间结果页跨页面数据（写入 sessionStorage，避免把上千个基因 id 塞进 URL） */
const INTERVAL_STORAGE_KEY = 'cottonogd_synteny_interval_result'

const sourceGenome = ref('')
const targetGenome = ref('')
const mode = ref<SearchMode>('all')
const region = ref('')
const geneId = ref('')
const loading = ref(false)
const error = ref('')
const chromosomeError = ref('')
const view = ref<SankeyView | null>(null)
/** 基因检索时额外绘制染色体级视图（查询基因所在共线性块对应的染色体） */
const chromosomeView = ref<SankeyView | null>(null)
/** 基因级微共线性原始轨道数据 */
const microData = ref<MicrosyntenyResult | null>(null)
/** 基因级微共线性布局（JCVI MCscan Microsynteny 风格：两条基因轨道 + 共线连线） */
const microLayout = computed(() => buildMicroLayout(microData.value))
/** 区间检索命中的共线性块（仅保留与输入区间相交的块） */
const regionBlockRows = ref<SyntenyBlockRow[]>([])
/** 区间块筛选中的加载状态 */
const regionBlockLoading = ref(false)
/** 各基因组 JBrowse 默认窗口（.fai 首条染色体 1-1Mb），按基因组缓存 */
const defaultLocs = reactive<Record<string, string>>({})
/** 区间检索时同步给目标基因组 JBrowse 的窗口 */
const regionJbrowseTarget = ref('')
const PREFERRED_SOURCE = 'G.hirsutumAD1_TM-1_HAU_v1.1'
const PREFERRED_TARGET = 'G.hirsutumAD1_TM-1_ZJU_v1.1T2T'

const sankeyRef = shallowRef<HTMLElement | null>(null)
const chrSankeyRef = shallowRef<HTMLElement | null>(null)
let chart: ReturnType<typeof echarts.init> | null = null
let chrChart: ReturnType<typeof echarts.init> | null = null

const hasFigures = computed(
  () =>
    !!view.value?.figures &&
    (!!view.value.figures.dotplot || !!view.value.figures.depth || !!view.value.figures.karyotype),
)

// source 用项目主色；target 改用经 dataviz 校验的对比色（#3a6ea5/#7297bd 明度差过近、不达正常视觉区分阈值）
const COLORS = { source: '#3a6ea5', target: '#eb6834' }

/** 染色体自然顺序键：A01…A13、D01…D13 等按“前缀+数字”排序，保证按基因组位置从左到右绘制 */
function chrSortKey(name: string): [string, number, string] {
  const m = name.match(/([A-Za-z]+)[_-]?0*(\d+)$/)
  return m ? [m[1].toUpperCase(), Number(m[2]), name] : ['ZZZ', 0, name]
}

/** 按基因组来源 + 染色体位置排序节点，使 sankey 的水平排布等于基因组顺序 */
function sortNodes(nodes: SankeyNode[]): SankeyNode[] {
  return [...nodes].sort((a, b) => {
    if (a.genome !== b.genome) return a.genome === 'source' ? -1 : 1
    const ka = chrSortKey(a.name)
    const kb = chrSortKey(b.name)
    return ka[0].localeCompare(kb[0]) || ka[1] - kb[1] || ka[2].localeCompare(kb[2])
  })
}

/** .fai 索引按基因组缓存，避免重复检索 */
const chrLengthCache = new Map<string, ChromosomeLengths>()
async function lengthsFor(genome: string): Promise<ChromosomeLengths> {
  const hit = chrLengthCache.get(genome)
  if (hit) return hit
  const fetched = await getChromosomeLengths(genome)
  if (Object.keys(fetched).length) chrLengthCache.set(genome, fetched)
  return fetched
}

/** 把 bp 格式化为友好的 Mb / kb 文案 */
function formatLength(bp?: number): string {
  if (!bp || bp <= 0) return ''
  return bp >= 1e6 ? `${(bp / 1e6).toFixed(1)} Mb` : `${(bp / 1e3).toFixed(1)} kb`
}

/** 微共线性坐标轴刻度：1 位小数足够读数，不堆叠过多标签 */
function formatAxisBp(bp: number): string {
  return bp >= 1e6 ? `${(bp / 1e6).toFixed(1)} Mb` : `${(bp / 1e3).toFixed(0)} kb`
}

/** 基因级微共线性布局：参照 JCVI MCscan Microsynteny visualization，
 * 画两条水平基因轨道（source / target），基因按基因组坐标排布，共线基因对用曲线连接。
 * 查询基因所在的共线性块可能包含数百个基因，这里只截取查询基因上下游各 25 个基因，
 * 保持局部微共线性可读；目标轨道按相同 order 区间对齐。 */
function buildMicroLayout(data: MicrosyntenyResult | null): MicroLayout | null {
  if (!data) return null
  const srcAll = data.tracks?.source ?? []
  const tgtAll = data.tracks?.target ?? []
  if (!srcAll.length && !tgtAll.length) return null

  const queries = new Set(data.query_genes ?? [])
  const queryGene =
    srcAll.find((g) => g.query || queries.has(g.id)) ??
    tgtAll.find((g) => g.query || queries.has(g.id)) ??
    null
  const blockId = queryGene?.block_id || srcAll[0]?.block_id || tgtAll[0]?.block_id
  const srcBlock = srcAll
    .filter((g) => !blockId || g.block_id === blockId)
    .sort((a, b) => a.order - b.order)
  const tgtBlock = tgtAll
    .filter((g) => !blockId || g.block_id === blockId)
    .sort((a, b) => a.order - b.order)
  const queryInSource = !!queryGene && srcBlock.some((g) => g.id === queryGene.id)
  const anchor = queryInSource ? srcBlock : tgtBlock
  const anchorIndex = queryGene ? anchor.findIndex((g) => g.id === queryGene.id) : -1

  let srcShown: SyntenyTrackGene[]
  let tgtShown: SyntenyTrackGene[]
  const flank = 25
  if (anchorIndex >= 0) {
    const start = Math.max(0, anchorIndex - flank)
    const slice = anchor.slice(start, anchorIndex + flank + 1)
    const minOrder = Math.min(...slice.map((g) => g.order))
    const maxOrder = Math.max(...slice.map((g) => g.order))
    srcShown = queryInSource ? slice : srcBlock.filter((g) => g.order >= minOrder && g.order <= maxOrder)
    tgtShown = queryInSource ? tgtBlock.filter((g) => g.order >= minOrder && g.order <= maxOrder) : slice
  } else {
    srcShown = srcBlock.slice(0, flank * 2 + 1)
    tgtShown = tgtBlock.slice(0, flank * 2 + 1)
  }
  if (!srcShown.length) srcShown = srcAll.slice(0, flank * 2 + 1)
  if (!tgtShown.length) tgtShown = tgtAll.slice(0, flank * 2 + 1)

  const PLOT_LEFT = 132
  const PLOT_RIGHT = 1168
  const GENE_HEIGHT = 20
  const SRC_Y = 92
  const TGT_Y = 262
  const plotWidth = PLOT_RIGHT - PLOT_LEFT
  const geneSpan = (genes: SyntenyTrackGene[]) => {
    const starts = genes.map((g) => g.start).filter(Number.isFinite)
    const ends = genes.map((g) => g.end).filter(Number.isFinite)
    if (!starts.length || !ends.length) return { min: 0, max: 1 }
    return { min: Math.min(...starts), max: Math.max(...ends) }
  }
  const srcRange = geneSpan(srcShown)
  const tgtRange = geneSpan(tgtShown)
  const toBox = (
    g: SyntenyTrackGene,
    role: 'source' | 'target',
    range: { min: number; max: number },
    y: number,
  ): MicroGeneBox => {
    const span = Math.max(1, range.max - range.min)
    const x = PLOT_LEFT + ((g.start - range.min) / span) * plotWidth
    const width = Math.max(2.5, Math.min(60, ((g.end - g.start) / span) * plotWidth))
    return {
      gene: g,
      role,
      x,
      width,
      y,
      query: g.query || queries.has(g.id),
    }
  }
  const source = srcShown.map((g) => toBox(g, 'source', srcRange, SRC_Y))
  const target = tgtShown.map((g) => toBox(g, 'target', tgtRange, TGT_Y))
  const tgtByOrder = new Map(target.map((b) => [`${b.gene.block_id}#${b.gene.order}`, b]))
  const links: MicroPairLink[] = []
  // 记录配对顺序，用于判断相邻共线基因在目标基因组上的坐标方向是否反转（倒位/重排）
  const pairTrace: { link: MicroPairLink; sourceStart: number; targetStart: number }[] = []
  for (const s of source) {
    const key = `${s.gene.block_id}#${s.gene.order}`
    const t = tgtByOrder.get(key)
    if (!t) continue
    const sx = s.x + s.width / 2
    const tx = t.x + t.width / 2
    const y1 = SRC_Y + GENE_HEIGHT
    const link: MicroPairLink = {
      id: `${key}-${s.gene.id}-${t.gene.id}`,
      source: s,
      target: t,
      path: `M ${sx} ${y1} C ${sx} 170, ${tx} 205, ${tx} ${TGT_Y}`,
      query: s.query || t.query,
      inverted: false,
    }
    links.push(link)
    pairTrace.push({ link, sourceStart: s.gene.start, targetStart: t.gene.start })
  }
  // 倒位判定：相邻两对共线基因，源基因组坐标同向变化而目标基因组坐标反向变化，
  // 说明这一小段在目标基因组中发生了倒位/重排；把相邻两条连线一起标成倒位色。
  for (let i = 1; i < pairTrace.length; i++) {
    const prev = pairTrace[i - 1]
    const cur = pairTrace[i]
    const sourceDir = Math.sign(cur.sourceStart - prev.sourceStart)
    const targetDir = Math.sign(cur.targetStart - prev.targetStart)
    if (sourceDir !== 0 && targetDir !== 0 && sourceDir !== targetDir) {
      prev.link.inverted = true
      cur.link.inverted = true
    }
  }

  const ticks = (range: { min: number; max: number }): MicroAxisTick[] =>
    Array.from({ length: 5 }, (_, i) => {
      const value = range.min + ((range.max - range.min) * i) / 4
      return {
        x: PLOT_LEFT + (plotWidth * i) / 4,
        label: formatAxisBp(value),
      }
    })
  const srcChr = srcShown[0]?.chr || ''
  const tgtChr = tgtShown[0]?.chr || ''
  return {
    source,
    target,
    links,
    sourceLabel: `${srcChr}:${formatAxisBp(srcRange.min)}-${formatAxisBp(srcRange.max)}`,
    targetLabel: `${tgtChr}:${formatAxisBp(tgtRange.min)}-${formatAxisBp(tgtRange.max)}`,
    sourceTicks: ticks(srcRange),
    targetTicks: ticks(tgtRange),
    windowLabel: `${source.length} ↔ ${target.length}`,
  }
}

/** 基因对表格：微共线性图的无障碍替代视图 */
const microPairRows = computed(() =>
  (microLayout.value?.links ?? []).map((l) => ({
    key: l.id,
    sourceGene: l.source.gene.id,
    sourcePosition: `${l.source.gene.chr}:${l.source.gene.start}-${l.source.gene.end}`,
    targetGene: l.target.gene.id,
    targetPosition: `${l.target.gene.chr}:${l.target.gene.start}-${l.target.gene.end}`,
    blockId: l.source.gene.block_id,
    query: l.query ? t('synteny_query_gene') : '',
  })),
)

/** 基因检索：把 microsynteny 的两条轨道按 block_id 聚合为“块 + 基因”表格行 */
const geneModeBlockRows = computed<SyntenyBlockRow[]>(() => {
  const data = microData.value
  if (!data) return []
  const grouped = new Map<
    string,
    { source: SyntenyTrackGene[]; target: SyntenyTrackGene[] }
  >()
  for (const gene of data.tracks?.source ?? []) {
    const id = gene.block_id || 'unknown'
    const hit = grouped.get(id) ?? { source: [], target: [] }
    hit.source.push(gene)
    grouped.set(id, hit)
  }
  for (const gene of data.tracks?.target ?? []) {
    const id = gene.block_id || 'unknown'
    const hit = grouped.get(id) ?? { source: [], target: [] }
    hit.target.push(gene)
    grouped.set(id, hit)
  }
  return [...grouped.entries()].map(([blockId, genes]) => {
    const sourceGenes = [...genes.source].sort((a, b) => a.order - b.order)
    const targetGenes = [...genes.target].sort((a, b) => a.order - b.order)
    const sourceChr = sourceGenes[0]?.chr || ''
    const targetChr = targetGenes[0]?.chr || ''
    return {
      key: `gene-${blockId}`,
      blockId,
      sourceChr,
      targetChr,
      sourceRegion: spanOfGenes(sourceGenes, sourceChr),
      targetRegion: spanOfGenes(targetGenes, targetChr),
      sourceGenes: sourceGenes.map((g) => g.id),
      targetGenes: targetGenes.map((g) => g.id),
    }
  })
})

/** 当前检索模式对应的“共线性块 + 基因”表格行 */
const blockTableRows = computed<SyntenyBlockRow[]>(() =>
  mode.value === 'gene' ? geneModeBlockRows.value : regionBlockRows.value,
)

/** 基因检索时 JBrowse 的两个基因组窗口：取自查询基因所在区块的完整轨道范围 */
const geneModeSpans = computed(() => {
  const data = microData.value
  const pair = data ? chromosomePairOfQuery(data) : null
  if (!data || !pair) return { source: '', target: '' }
  const sourceGenes = (data.tracks?.source ?? []).filter((g) => g.block_id === pair.blockId)
  const targetGenes = (data.tracks?.target ?? []).filter((g) => g.block_id === pair.blockId)
  return {
    source: spanOfGenes(sourceGenes, pair.source),
    target: spanOfGenes(targetGenes, pair.target),
  }
})

/** 读取基因组 .fai 首条染色体作为默认 JBrowse 窗口（全基因组模式使用） */
async function ensureDefaultLocs(): Promise<void> {
  const genomes = [sourceGenome.value, targetGenome.value].filter(Boolean)
  await Promise.all(
    genomes.map(async (genome) => {
      if (defaultLocs[genome]) return
      defaultLocs[genome] = await createDefaultLocus(genome, '1-1000000', 'Ghir_A01')
    }),
  )
}

/** 复用站点现有 JBrowse2 静态页：config + assembly + loc 由 URL 参数驱动，
 * tracks 与 JbrowseView 保持一致，保证已部署 config 的 track 可用。 */
function jbrowseUrl(genome: string, loc: string): string {
  if (!genome || !loc) return ''
  return `/assets/jbrowse/index.html?config=data/${encodeURIComponent(genome)}/config.json&assembly=${encodeURIComponent(genome)}&tracks=GFF,biological_process_annotation,cellular_component_annotation,molecular_function_annotation,kegg_annotation&loc=${encodeURIComponent(loc)}`
}

const jbrowseSourceLoc = computed(() => {
  if (mode.value === 'region') return region.value.trim()
  if (mode.value === 'gene') return geneModeSpans.value.source
  return defaultLocs[sourceGenome.value] || ''
})
const jbrowseTargetLoc = computed(() => {
  if (mode.value === 'region') return regionJbrowseTarget.value || defaultLocs[targetGenome.value] || ''
  if (mode.value === 'gene') return geneModeSpans.value.target
  return defaultLocs[targetGenome.value] || ''
})

/** 基因组序列 adapter 字段（与站点已部署 config.json 保持一致，供 pairwise session 用） */
function genomeSequenceAdapter(genome: string) {
  const base = `/jbrowse/large/${encodeURIComponent(genome)}/${encodeURIComponent(genome)}`
  return {
    type: 'ReferenceSequenceTrack' as const,
    trackId: `${genome}-ReferenceSequenceTrack`,
    adapter: {
      type: 'BgzipFastaAdapter',
      fastaLocation: { uri: `${base}.genome.fa.gz`, locationType: 'UriLocation' },
      faiLocation: { uri: `${base}.genome.fa.gz.fai`, locationType: 'UriLocation' },
      gziLocation: { uri: `${base}.genome.fa.gz.gzi`, locationType: 'UriLocation' },
    },
  }
}

/** 构建 pairwise 共线性 JBrowse session（自包含，config=none + 内联 session + loc） */
function buildSyntenySession(
  source: string,
  target: string,
  loc: string,
): string {
  const sourceAd = genomeSequenceAdapter(source)
  const targetAd = genomeSequenceAdapter(target)
  const session = {
    sessionAssemblies: [sourceAd, targetAd],
    tracks: [
      {
        type: 'SyntenyTrack',
        trackId: 'synteny',
        name: 'JCVI Synteny Anchors',
        assemblyNames: [source, target],
        adapter: {
          type: 'MCScanSimpleAnchorsAdapter',
          // 后端 synteny 文件路由：/synteny/<source_id_to_target_id>/work/<filename>
          // 文件名要求源/目标 id 中的点替换为下划线，如 G_hirsutumAD1_TM-1_ZJU_v1_1T2T.G_hirsutumAD1_N206_CRI_v1.anchors.simple
          uri: `/synteny/${source}_to_${target}/work/${source.replace(/\./g, '_')}.${target.replace(/\./g, '_')}.anchors.simple`,
        },
      },
    ],
    views: [
      {
        id: 'linearSyntenyView',
        type: 'LinearSyntenyView',
        assembly: [source, target],
        tracks: ['synteny'],
        autoDiagonalize: true,
        encoding: { color: 'query' },
      },
    ],
  }
  const query = `?config=none&session=spec-${encodeURIComponent(JSON.stringify(session))}`
  return `/assets/jbrowse/index.html${query}${loc ? `&loc=${encodeURIComponent(loc)}` : ''}`
}

/** 共线性页 JBrowse 单窗口 pairwise 共线性入口，带当前检索的 loc 定位 */
const jbrowsePairwiseLoc = computed(() => {
  if (mode.value === 'region') return region.value.trim()
  if (mode.value === 'gene') return geneModeSpans.value.source || defaultLocs[sourceGenome.value] || ''
  return jbrowseSourceLoc.value
})
const jbrowsePairwiseUrl = computed(
  () =>
    buildSyntenySession(
      sourceGenome.value,
      targetGenome.value,
      jbrowsePairwiseLoc.value,
    ),
)

/** 构建桑葚图数据。
 * ECharts 的节点高度 = max(入边和, 出边和, 节点 value)，且全图共用一个缩放系数。
 * 有了染色体实际长度（bp）后，把节点 value 设为真实长度；但 sankey 要求流量守恒，
 * 若把连线也换算成完整 bp，则目标染色体的入边之和不一定等于其自身真实长度，
 * 节点条高会被入边撑大，反而偏离真实长度。因此把连线总量压缩到源染色体长度的
 * LINK_BAND_RATIO 倍：节点 value（真实长度）始终大于入边/出边和，节点高度严格
 * 正比于染色体实际长度；连线仍按共线基因数分配带宽，等比缩小后依然可见。
 * 没有长度数据时退回原行为（节点高度由共线基因数决定），不阻断绘图。 */
const LINK_BAND_RATIO = 0.4

function buildSeries(view: SankeyView) {
  // 只有所有节点都有真实长度才启用 bp 量纲，避免个别节点缺长度时与其他节点量纲混乱
  const hasLengths = view.nodes.length > 0 && view.nodes.every((n) => !!n.lengthBp && n.lengthBp > 0)
  const outGenes = new Map<string, number>()
  if (hasLengths) {
    view.links.forEach((l) => outGenes.set(l.source, (outGenes.get(l.source) ?? 0) + l.value))
  }
  const lengthOf = new Map(view.nodes.map((n) => [n.name, n.lengthBp]))

  // 竖向布局下：source 条在上、target 条在下，标签分别朝上/朝下放置；过小的 scaffold 不显示标签。
  // 标签横排默认只写染色体 id（长度、基因数只在 tooltip 中显示）；相邻染色体间隔小于文字宽度，
  // 用两级距离交错排布，避免横向文字互相重叠。
  const showLabels = view.nodes.length <= 60
  const nodes = view.nodes.map((n, index) => ({
    name: n.name,
    value: hasLengths ? (n.lengthBp ?? 1) : undefined,
    itemStyle: { color: n.genome === 'target' ? COLORS.target : COLORS.source },
    lengthBp: n.lengthBp,
    geneCount: outGenes.get(n.name),
    label: {
      show: showLabels && (n.lengthBp ?? 0) >= 5e6,
      position: n.genome === 'target' ? 'bottom' : 'top',
      distance: index % 2 === 0 ? 5 : 18,
      fontSize: 10,
    },
  }))
  const links = view.links.map((l, index) => {
    const length = lengthOf.get(l.source)
    const genes = outGenes.get(l.source) ?? 0
    // 关键：源染色体所有连线的带宽之和 = LINK_BAND_RATIO × 真实长度 < 节点 value，
    // 保证节点高度只由真实长度决定；每条线内部仍按共线基因数占比分配。
    const bpValue = length && genes ? (l.value / genes) * length * LINK_BAND_RATIO : l.value
    const highlighted =
      !!view.highlightPair &&
      l.source === view.highlightPair.source &&
      l.target === view.highlightPair.target
    return {
      source: l.source,
      target: l.target,
      value: hasLengths ? bpValue : l.value,
      geneCount: l.value,
      sourceRegion: l.sourceRegion,
      targetRegion: l.targetRegion,
      blockId: l.blockId,
      linkIndex: index,
      // 基因模式的染色体图中，与查询基因所在区块对应的染色体对加粗、其余淡化
      lineStyle: view.highlightPair
        ? { opacity: highlighted ? 0.9 : 0.18, width: highlighted ? 2.5 : 1 }
        : undefined,
    }
  })
  return { nodes, links, hasLengths }
}

/** 从基因 id 解析所属染色体：
 * source 侧 Ghir_A01G000030 → Ghir_A01；target 侧 GhChrA01G0002 → A01。 */
function chromosomeOfGene(id: string, isSource: boolean): string {
  if (!id) return ''
  if (isSource) {
    const m = id.match(/^(.+?)G\d+/)
    return m ? m[1] : ''
  }
  const m = id.match(/([A-Za-z]\d+)G\d+/)
  return m ? m[1] : ''
}

/** blocks 按“源染色体→目标染色体”分组，供线条 hover / click 查区间与基因 */
const blockGroupCache = new Map<string, Promise<Map<string, SyntenyBlock[]>>>()

function groupBlocksByChromosome(blocks: SyntenyBlock[]): Map<string, SyntenyBlock[]> {
  const groups = new Map<string, SyntenyBlock[]>()
  for (const block of blocks) {
    const sourceChr = chromosomeOfGene(block.source_genes?.[0] ?? '', true)
    const targetChr = chromosomeOfGene(block.target_genes?.[0] ?? '', false)
    if (!sourceChr || !targetChr) continue
    const key = `${sourceChr}\u0000${targetChr}`
    const list = groups.get(key)
    if (list) list.push(block)
    else groups.set(key, [block])
  }
  return groups
}

/** 懒加载完整 blocks：默认不请求 4.3 MiB 的 blocks，只在首次悬停/点击线条时拉取并缓存 */
async function blockGroupsFor(source: string, target: string): Promise<Map<string, SyntenyBlock[]>> {
  const cacheKey = `${source}\u0000${target}`
  const cached = blockGroupCache.get(cacheKey)
  if (cached) return cached
  const task = (async () => {
    try {
      const res = await getGenomeSynteny({ source, target, includeBlocks: true })
      return res.code === 0 ? groupBlocksByChromosome(res.data.blocks ?? []) : new Map<string, SyntenyBlock[]>()
    } catch {
      return new Map<string, SyntenyBlock[]>()
    }
  })()
  blockGroupCache.set(cacheKey, task)
  return task
}

/** 批量读取基因坐标；单次最多 5000 个（实测后端 5000 个约 2.4s） */
async function loadGeneLocations(genome: string, geneIds: string[]): Promise<GeneLocationRow[]> {
  const unique = [...new Set(geneIds.filter(Boolean))]
  if (!unique.length) return []
  const rows: GeneLocationRow[] = []
  for (let i = 0; i < unique.length; i += 5000) {
    const res = await getGeneGenomicDistribution({
      genome,
      gene_ids: unique.slice(i, i + 5000).join(','),
    })
    if (res.code === 0) rows.push(...(res.data.gene_locations ?? []))
  }
  return rows
}

/** 用基因坐标算染色体区间；无坐标时退回整条染色体 */
function spanFor(chr: string, locations: GeneLocationRow[]): string {
  const hits = locations.filter((loc) => !loc.chr || loc.chr === chr)
  if (!hits.length) return ''
  const starts = hits.map((loc) => Number(loc.start)).filter(Number.isFinite)
  const ends = hits.map((loc) => Number(loc.end)).filter(Number.isFinite)
  if (!starts.length || !ends.length) return ''
  return `${chr}:${Math.min(...starts)}-${Math.max(...ends)}`
}

function fallbackSpan(view: SankeyView, name: string): string {
  const node = view.nodes.find((n) => n.name === name)
  return node?.lengthBp ? `${name}:1-${node.lengthBp}` : name
}

/** 解析 "chr:start-end"（允许千分位逗号） */
function parseRegionRange(value: string): RegionRange | null {
  const m = value.trim().match(/^([^:]+):([\d,]+)-([\d,]+)$/)
  if (!m) return null
  const chr = m[1].trim()
  const a = Number(m[2].replace(/,/g, ''))
  const b = Number(m[3].replace(/,/g, ''))
  if (!chr || !Number.isFinite(a) || !Number.isFinite(b)) return null
  return { chr, start: Math.min(a, b), end: Math.max(a, b) }
}

function rangesOverlap(a: RegionRange, b: RegionRange): boolean {
  return a.chr === b.chr && a.start <= b.end && a.end >= b.start
}

/** 由一条轨道上的基因列表计算原始坐标区间（用于 JBrowse 定位与表格展示） */
function spanOfGenes(genes: SyntenyTrackGene[], chr: string): string {
  const hits = genes.filter((g) => !chr || g.chr === chr)
  if (!hits.length) return chr
  const starts = hits.map((g) => Number(g.start)).filter(Number.isFinite)
  const ends = hits.map((g) => Number(g.end)).filter(Number.isFinite)
  if (!starts.length || !ends.length) return chr
  return `${chr}:${Math.min(...starts)}-${Math.max(...ends)}`
}

/** 只取区块首尾两个基因查询坐标，避免对整块数百个基因发请求 */
async function blockGeneSpan(genome: string, chr: string, genes: string[]): Promise<RegionRange | null> {
  if (!genes.length) return null
  const sample = genes.length > 2 ? [genes[0], genes[genes.length - 1]] : genes.slice(0, 2)
  const locations = await loadGeneLocations(genome, sample)
  return parseRegionRange(spanFor(chr, locations))
}

/** 并发受限的 map，避免一次向坐标接口发几十个请求 */
async function mapWithLimit<T, R>(
  items: T[],
  limit: number,
  worker: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length)
  let cursor = 0
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (true) {
      const index = cursor++
      if (index >= items.length) return
      results[index] = await worker(items[index], index)
    }
  })
  await Promise.all(runners)
  return results
}

/** 从染色体级响应中找到与目标染色体匹配的节点名（后端节点名可能是 GhChrA01，而基因 id 只含 A01） */
function sankeyNodeName(d: GenomeSyntenyResult, genome: 'source' | 'target', chr: string): string {
  const hit = (d.sankey?.nodes ?? []).find(
    (n) =>
      n.genome === genome &&
      (n.name === chr || n.chr === chr || n.name.endsWith(chr)),
  )
  return hit?.name || chr
}

/** 把区间命中的区块聚合成平台视图：只保留命中的 source/target 染色体与对应连线 */
function buildRegionView(
  d: GenomeSyntenyResult,
  rows: SyntenyBlockRow[],
  source: string,
  target: string,
  sourceChr: string,
  scope: string,
  srcLengths: ChromosomeLengths,
  tgtLengths: ChromosomeLengths,
): SankeyView {
  const sourceName = sankeyNodeName(d, 'source', sourceChr)
  const targetNames = new Map<string, string>()
  const linkMap = new Map<string, SankeyLink>()
  rows.forEach((row) => {
    const targetName = sankeyNodeName(d, 'target', row.targetChr)
    targetNames.set(row.targetChr, targetName)
    const existing = linkMap.get(targetName)
    const weight = Math.max(1, Math.min(row.sourceGenes.length, row.targetGenes.length))
    if (existing) {
      existing.value += weight
      existing.geneCount = (existing.geneCount ?? 0) + weight
    } else {
      linkMap.set(targetName, {
        source: sourceName,
        target: targetName,
        value: weight,
        geneCount: weight,
      })
    }
  })
  const nodes: SankeyNode[] = []
  const sourceNode = (d.sankey?.nodes ?? []).find((n) => n.name === sourceName)
  nodes.push({
    name: sourceName,
    genome: 'source',
    lengthBp: srcLengths[sourceNode?.chr || sourceChr],
  })
  linkMap.forEach((_link, targetName) => {
    const targetNode = (d.sankey?.nodes ?? []).find((n) => n.name === targetName)
    nodes.push({
      name: targetName,
      genome: 'target',
      lengthBp: tgtLengths[targetNode?.chr || targetName],
    })
  })
  const links = [...linkMap.values()]
  return {
    sourceId: d.source_id || source,
    targetId: d.target_id || target,
    scope,
    blockCount: rows.length,
    geneCount: rows.reduce(
      (sum, row) => sum + Math.min(row.sourceGenes.length, row.targetGenes.length),
      0,
    ),
    nodes,
    links,
    figures: d.figures,
    chromosome: sourceChr,
    highlightPair: links.length === 1 ? { source: sourceName, target: links[0].target } : undefined,
  }
}

/** 区间检索时按区块首尾基因坐标过滤：只保留与输入区间相交的共线性块 */
async function filterBlocksByRegion(
  blocks: SyntenyBlock[],
  source: string,
  target: string,
  regionRange: RegionRange,
): Promise<SyntenyBlockRow[]> {
  const sourceSpans = await mapWithLimit(blocks, 6, (block) =>
    blockGeneSpan(source, regionRange.chr, block.source_genes ?? []),
  )
  const candidates = blocks
    .map((block, index) => ({ block, span: sourceSpans[index] }))
    .filter(({ block, span }) => {
      if (span) return rangesOverlap(span, regionRange)
      // 坐标接口失败时，至少用基因 id 前缀确认区块属于该染色体
      return chromosomeOfGene(block.source_genes?.[0] ?? '', true) === regionRange.chr
    })

  const rows = await mapWithLimit(candidates, 4, async ({ block, span }) => {
    const sourceChr = chromosomeOfGene(block.source_genes?.[0] ?? '', true) || regionRange.chr
    const targetChr = chromosomeOfGene(block.target_genes?.[0] ?? '', false)
    const targetSpan = targetChr
      ? await blockGeneSpan(target, targetChr, block.target_genes ?? [])
      : null
    return {
      key: `${block.block_id}-${sourceChr}-${targetChr}`,
      blockId: block.block_id,
      sourceChr,
      targetChr,
      sourceRegion:
        span && span.chr === sourceChr
          ? `${sourceChr}:${span.start}-${span.end}`
          : `${sourceChr}`,
      targetRegion: targetSpan ? `${targetChr}:${targetSpan.start}-${targetSpan.end}` : targetChr,
      sourceGenes: block.source_genes ?? [],
      targetGenes: block.target_genes ?? [],
    } satisfies SyntenyBlockRow
  })
  return rows
}

/** 单条连线的区间详情缓存：hover 与 click 共用，避免重复请求 */
const linkDetailCache = new Map<string, LinkIntervalDetail>()
const linkDetailPending = new Map<string, Promise<LinkIntervalDetail>>()

function linkDetailKey(view: SankeyView, link: SankeyLink): string {
  return `${view.sourceId}\u0000${view.targetId}\u0000${link.source}\u0000${link.target}`
}

async function ensureLinkDetail(view: SankeyView, link: SankeyLink): Promise<LinkIntervalDetail> {
  // 基因级连线在 buildGeneSankey 里已带坐标，直接组装
  if (link.sourceRegion && link.targetRegion) {
    return {
      sourceRegion: link.sourceRegion,
      targetRegion: link.targetRegion,
      sourceGenes: [{ gene_id: link.source, block_id: link.blockId ?? '' }],
      targetGenes: [{ gene_id: link.target, block_id: link.blockId ?? '' }],
      blockCount: link.blockId ? 1 : 0,
    }
  }

  const key = linkDetailKey(view, link)
  const cached = linkDetailCache.get(key)
  if (cached) return cached
  const pending = linkDetailPending.get(key)
  if (pending) return pending

  const task = (async () => {
    try {
      const groups = await blockGroupsFor(view.sourceId, view.targetId)
      const blocks = groups.get(`${link.source}\u0000${link.target}`) ?? []
      const sourceGenes = [...new Set(blocks.flatMap((b) => b.source_genes ?? []))]
      const targetGenes = [...new Set(blocks.flatMap((b) => b.target_genes ?? []))]
      const [sourceLocations, targetLocations] = await Promise.all([
        loadGeneLocations(view.sourceId, sourceGenes),
        loadGeneLocations(view.targetId, targetGenes),
      ])
      const sourceBlockOf = new Map<string, string>()
      const targetBlockOf = new Map<string, string>()
      blocks.forEach((b) => {
        b.source_genes?.forEach((g) => sourceBlockOf.set(g, b.block_id))
        b.target_genes?.forEach((g) => targetBlockOf.set(g, b.block_id))
      })
      const detail: LinkIntervalDetail = {
        sourceRegion: spanFor(link.source, sourceLocations) || fallbackSpan(view, link.source),
        targetRegion: spanFor(link.target, targetLocations) || fallbackSpan(view, link.target),
        sourceGenes: sourceGenes.map((g) => ({ gene_id: g, block_id: sourceBlockOf.get(g) ?? '' })),
        targetGenes: targetGenes.map((g) => ({ gene_id: g, block_id: targetBlockOf.get(g) ?? '' })),
        blockCount: blocks.length,
      }
      linkDetailCache.set(key, detail)
      return detail
    } catch {
      const detail: LinkIntervalDetail = {
        sourceRegion: fallbackSpan(view, link.source),
        targetRegion: fallbackSpan(view, link.target),
        sourceGenes: [],
        targetGenes: [],
        blockCount: 0,
      }
      linkDetailCache.set(key, detail)
      return detail
    } finally {
      linkDetailPending.delete(key)
    }
  })()
  linkDetailPending.set(key, task)
  return task
}

function edgeTooltip(view: SankeyView, p: { dataType?: string; data?: unknown; name?: string }): string {
  const d = (p.data ?? {}) as SankeyLink & Record<string, unknown>
  if (p.dataType === 'edge') {
    const detail = linkDetailCache.get(linkDetailKey(view, d))
    const sourceRegion = detail?.sourceRegion || d.sourceRegion || fallbackSpan(view, d.source)
    const targetRegion = detail?.targetRegion || d.targetRegion || fallbackSpan(view, d.target)
    return [
      `${d.source} → ${d.target}`,
      `${t('gene_count')}: ${d.geneCount ?? d.value}`,
      `${t('synteny_reference_interval')}: ${sourceRegion}`,
      `${t('synteny_query_interval')}: ${targetRegion}`,
      `<span style="color:#909399">${t('synteny_click_interval_hint')}</span>`,
    ].join('<br/>')
  }
  const lines = [`<b>${p.name ?? d.name}</b>`]
  const length = formatLength(d.lengthBp as number | undefined)
  if (length) lines.push(`${t('synteny_chr_length')}: ${length}`)
  if (d.geneCount) lines.push(`${t('gene_count')}: ${d.geneCount}`)
  return lines.join('<br/>')
}

/** 悬停线条：后端的染色体级 link 不含区间，先异步取该染色体对的 blocks + 基因坐标并缓存 */
function prefetchLinkDetail(view: SankeyView, p: { dataType?: string; data?: unknown }): void {
  if (p.dataType !== 'edge') return
  const link = (p.data ?? {}) as SankeyLink
  if (link.sourceRegion || linkDetailCache.has(linkDetailKey(view, link))) return
  void ensureLinkDetail(view, link)
}

/** 点击共线性线条：把该连线两侧的区间与基因写入 sessionStorage，
 * 并直接跳到共线性结果页自动加载（不再进结构变异页、不要求用户手动搜索）。 */
async function navigateToSyntenyResult(args: {
  sourceId: string
  targetId: string
  sourceRegion: string
  targetRegion: string
  sourceGenes: { gene_id: string; block_id: string }[]
  targetGenes: { gene_id: string; block_id: string }[]
  sourceChr: string
  targetChr: string
}): Promise<void> {
  const payload = {
    sourceId: args.sourceId,
    targetId: args.targetId,
    intervals: [
      {
        role: 'source',
        genome: args.sourceId,
        chr: args.sourceChr,
        region: args.sourceRegion,
        genes: args.sourceGenes,
      },
      {
        role: 'target',
        genome: args.targetId,
        chr: args.targetChr,
        region: args.targetRegion,
        genes: args.targetGenes,
      },
    ],
  }
  try {
    sessionStorage.setItem(INTERVAL_STORAGE_KEY, JSON.stringify(payload))
  } catch {
    /* 隐私模式等场景写入失败时仍继续跳转，结果页会按 query 参数展示区间 */
  }
  await router.push({
    path: '/genome/synteny/results',
    query: {
      from_synteny: '1',
      source: args.sourceId,
      target: args.targetId,
      source_region: args.sourceRegion,
      target_region: args.targetRegion,
      source_chr: args.sourceChr,
      target_chr: args.targetChr,
    },
  })
}

/** 点击染色体级桑基图线条：跳转到共线性结果页 */
async function openIntervalResult(view: SankeyView, p: { dataType?: string; data?: unknown }): Promise<void> {
  if (p.dataType !== 'edge') return
  const link = (p.data ?? {}) as SankeyLink
  const detail = await ensureLinkDetail(view, link)
  await navigateToSyntenyResult({
    sourceId: view.sourceId,
    targetId: view.targetId,
    sourceRegion: detail.sourceRegion,
    targetRegion: detail.targetRegion,
    sourceGenes: detail.sourceGenes,
    targetGenes: detail.targetGenes,
    sourceChr: link.source,
    targetChr: link.target,
  })
}

/** 点击基因块：复用 geneid_summary + 全局基因检索结果页打开基因详情 */
async function openGeneDetail(box: MicroGeneBox): Promise<void> {
  const data = microData.value
  if (!data) return
  const genomeId =
    box.role === 'source'
      ? data.source_id || sourceGenome.value
      : data.target_id || targetGenome.value
  if (!genomeId) return
  const requestId = `synteny_micro_${Date.now()}`
  try {
    const response = (await httpInstance.post('/CottonOGD_api/geneid_summary/', {
      gene_id: box.gene.id,
      genome_id: genomeId,
      request_id: requestId,
    })) as any
    if (!response?.geneid_result) return
    const parseField = (value: unknown) =>
      typeof value === 'string' ? JSON.parse(value) : value
    const results = {
      geneid_result: parseField(response.geneid_result),
      gene_info_result: parseField(response.gene_info_result),
      search_map: parseField(response.search_map),
      gene_go_result: response.gene_go_result || [],
      gene_kegg_result: response.gene_kegg_result || [],
    }
    const dbIds = results.search_map
      ? Object.values(results.search_map as Record<string, { db_id?: string }>)
          .map((item) => item?.db_id)
          .filter(Boolean)
      : []
    navigationStore.setNavigationData('geneSearch', {
      results,
      dbIds,
      requestId,
    })
    router.push({ name: 'idSearchSummary' })
  } catch (e) {
    console.error('打开基因详情失败:', e)
  }
}

/** 统一的桑葚图绘制入口：主图与基因模式下的染色体图共用同一套样式与交互 */
function paintSankey(
  container: HTMLElement | null,
  instance: ReturnType<typeof echarts.init> | null,
  model: SankeyView | null,
): ReturnType<typeof echarts.init> | null {
  if (!container) {
    instance?.dispose()
    return null
  }
  // 基因/全基因组模式切换会重建 DOM；旧实例绑定在已移除的节点上，必须重新初始化
  let chartInstance = instance
  if (chartInstance && (chartInstance.isDisposed() || chartInstance.getDom() !== container)) {
    chartInstance.dispose()
    chartInstance = null
  }
  if (!chartInstance) {
    chartInstance = echarts.getInstanceByDom(container) ?? echarts.init(container)
  }
  if (!model || model.nodes.length === 0) {
    chartInstance.clear()
    return chartInstance
  }
  // 染色体级视图按基因组位置排序（source 在前、target 在后），使水平排布即基因组顺序；
  // 基因级视图保持轨道原顺序（基因 id 尾部数字无染色体位置含义）
  const orderedNodes = model.nodes.every((n) => !!n.lengthBp) ? sortNodes(model.nodes) : model.nodes
  const { nodes, links } = buildSeries({ ...model, nodes: orderedNodes })
  const showLabel = nodes.length <= 300

  chartInstance.setOption(
    {
      tooltip: {
        trigger: 'item',
        triggerOn: 'mousemove',
        formatter: (p: { dataType?: string; data?: unknown; name?: string }) => edgeTooltip(model, p),
      },
      series: [
        {
          type: 'sankey',
          // 旋转 90°：source/target 变为上下两行水平条，条块沿 x 方向排布
          orient: 'vertical',
          nodeAlign: 'left',
          nodeWidth: 16, // 固定条块厚度
          nodeGap: 2,
          layoutIterations: 0, // 保持按基因组位置排序，不让布局算法重排
          top: 96,
          bottom: 96,
          left: 12,
          right: 12,
          emphasis: { focus: 'adjacency' },
          data: nodes,
          links,
          // 标签横排，只显示染色体 / 基因原始 id；长度与基因数只在 tooltip 中显示
          label: {
            show: showLabel,
            fontSize: 10,
          },
          lineStyle: { color: 'gradient', opacity: 0.5, curveness: 0.5 },
        },
      ],
    },
    true,
  )

  chartInstance.off('mouseover')
  chartInstance.off('click')
  chartInstance.on('mouseover', (p: { dataType?: string; data?: unknown }) => prefetchLinkDetail(model, p))
  chartInstance.on('click', (p: { dataType?: string; data?: unknown }) => {
    void openIntervalResult(model, p)
  })
  chartInstance.resize()
  return chartInstance
}

function renderSankey() {
  chart = paintSankey(sankeyRef.value, chart, view.value)
}

function renderChromosomeSankey() {
  chrChart = paintSankey(chrSankeyRef.value, chrChart, chromosomeView.value)
}

watch(view, () => nextTick(renderSankey))
watch(chromosomeView, () => nextTick(renderChromosomeSankey))
watch(
  () => [mode.value, region.value, geneId.value],
  async () => {
    if (mode.value === 'all') {
      regionBlockRows.value = []
      return
    }
    regionBlockLoading.value = true
    try {
      if (mode.value === 'gene') {
        if (geneModeBlockRows.value.length === 0) return
        regionBlockRows.value = []
      }
      if (mode.value === 'region' && region.value.trim()) {
        const range = parseRegionRange(region.value)
        if (!range) {
          regionBlockRows.value = []
          return
        }
        regionBlockLoading.value = true
        try {
          const res = await getGenomeSynteny({
            source: sourceGenome.value,
            target: targetGenome.value,
            includeBlocks: true,
          })
          if (res.code !== 0) {
            regionBlockRows.value = []
            return
          }
          regionBlockRows.value = await filterBlocksByRegion(
            res.data.blocks ?? [],
            sourceGenome.value,
            targetGenome.value,
            range,
          )
        } finally {
          regionBlockLoading.value = false
        }
      }
    } finally {
      regionBlockRows.value = blockTableRows.value.filter((r) => mode.value !== 'all' && r)
      if (mode.value === 'region' && region.value.trim()) {
        regionJbrowseTarget.value = parseRegionRange(region.value)?.chr || defaultLocs[targetGenome.value] || ''
      }
    }
  },
)

function onResize() {
  chart?.resize()
  chrChart?.resize()
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  await ensureGenomesLoaded()

  // 默认优先使用 TM-1 HAU v1.1 ↔ TM-1 ZJU v1.1T2T；若后端未提供该组合再退回第一个可用组合。
  // 初始化完成后立即请求全基因组桑葚图，进入页面即展示。
  try {
    const pairs = await getSyntenyPairs()
    const allPairs = pairs.data?.pairs ?? []
    const preferred = allPairs.find(
      (p) => p.source === PREFERRED_SOURCE && p.target === PREFERRED_TARGET,
    )
    const p = preferred ?? allPairs[0]
    if (p) {
      sourceGenome.value = p.source
      targetGenome.value = p.target
    }
  } catch {
    /* 接口失败时使用前端默认值 */
  }
  if (!sourceGenome.value) {
    const def = pickDefaultGenome()
    if (def) sourceGenome.value = def
  }
  if (!targetGenome.value) targetGenome.value = PREFERRED_TARGET
  if (sourceGenome.value && targetGenome.value && !view.value) {
    await handleSubmit()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chrChart?.dispose()
  chart = null
  chrChart = null
})

const fillExample = () => {
  sourceGenome.value = 'G.hirsutumAD1_TM-1_HAU_v1.1'
  targetGenome.value = 'G.hirsutumAD1_TM-1_ZJU_v1.1T2T'
  region.value = 'Ghir_A01:1-1000000'
  geneId.value = 'Ghir_A01G000100'
}

/** 由 microsynteny 的 tracks 构建基因级桑葚图：
 * 源/目标两条轨道按 (block_id, order) 一一配对，形成跨基因组连线；节点为原始基因 id。
 * 每条连线保留两端基因的坐标与区块 id，便于 hover 显示位置和点击后展示区间基因。
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

  const regionOf = (g: SyntenyTrackGene) => `${g.chr}:${g.start}-${g.end}`
  const links: SankeyLink[] = []
  if (src.length && tgt.length) {
    const keyOf = (g: SyntenyTrackGene) => `${g.block_id}#${g.order}`
    const tMap = new Map<string, SyntenyTrackGene>()
    tgt.forEach((g) => {
      if (!tMap.has(keyOf(g))) tMap.set(keyOf(g), g)
    })
    src.forEach((s) => {
      const hit = tMap.get(keyOf(s))
      if (hit) {
        links.push({
          source: s.id,
          target: hit.id,
          value: 1,
          sourceRegion: regionOf(s),
          targetRegion: regionOf(hit),
          blockId: s.block_id,
        })
      }
    })
  }

  if (nodes.length === 0) {
    const genomeOf = (id: string) =>
      tgt.some((g) => g.id === id) ? 'target' : src.some((g) => g.id === id) ? 'source' : id.startsWith('Ghir_') ? 'source' : 'target'
    ;(data.graph?.nodes ?? []).forEach((n) => add(n.id, n.genome))
    ;(data.graph?.links ?? []).forEach((l) => {
      add(l.source, genomeOf(l.source))
      add(l.target, genomeOf(l.target))
      const sourceNode = (data.graph?.nodes ?? []).find((n) => n.id === l.source)
      const targetNode = (data.graph?.nodes ?? []).find((n) => n.id === l.target)
      links.push({
        source: l.source,
        target: l.target,
        value: 1,
        sourceRegion: sourceNode?.chr
          ? `${sourceNode.chr}:${sourceNode.start ?? 0}-${sourceNode.end ?? 0}`
          : undefined,
        targetRegion: targetNode?.chr
          ? `${targetNode.chr}:${targetNode.start ?? 0}-${targetNode.end ?? 0}`
          : undefined,
        blockId: l.block_id,
      })
    })
  }

  return { nodes, links }
}

/** 由某个基因的轨道记录确定其所在共线性区块对应的染色体对。
 * 优先取 query 标记，其次按 query_genes 匹配；目标染色体取同一 block_id 的目标轨道。 */
function chromosomePairOfQuery(data: MicrosyntenyResult): { source: string; target: string; blockId: string } | null {
  const src: SyntenyTrackGene[] = data.tracks?.source ?? []
  const tgt: SyntenyTrackGene[] = data.tracks?.target ?? []
  const queries = new Set(data.query_genes ?? [])
  const query =
    src.find((g) => g.query || queries.has(g.id)) ??
    tgt.find((g) => g.query || queries.has(g.id)) ??
    (data.graph?.nodes ?? []).find((n) => queries.has(n.id))
  if (!query || !query.chr || !query.block_id) return null
  const isSource = src.some((g) => g.id === query.id && g.block_id === query.block_id)
  const pair = isSource
    ? tgt.find((g) => g.block_id === query.block_id)
    : src.find((g) => g.block_id === query.block_id)
  if (!pair?.chr) return null
  return {
    source: isSource ? query.chr : pair.chr,
    target: isSource ? pair.chr : query.chr,
    blockId: query.block_id,
  }
}

/** 读取查询基因所在染色体对的染色体级共线性图：长度来自 .fai，目标染色体对高亮 */
async function loadChromosomeView(
  source: string,
  target: string,
  chromosome: string,
  highlightPair: { source: string; target: string },
  scope: string,
): Promise<SankeyView> {
  const res = await getGenomeSynteny({ source, target, chromosome })
  if (res.code !== 0) throw new Error(res.message || t('synteny_chromosome_level_unavailable'))
  const d = res.data
  const [srcLengths, tgtLengths] = await Promise.all([
    lengthsFor(d.source_id || source),
    lengthsFor(d.target_id || target),
  ])
  const nodes = (d.sankey?.nodes ?? []).map((n) => {
    const lengths = n.genome === 'target' ? tgtLengths : srcLengths
    return { name: n.name, genome: n.genome, lengthBp: lengths[n.chr || n.name] }
  })
  return {
    sourceId: d.source_id || source,
    targetId: d.target_id || target,
    scope,
    blockCount: d.block_count,
    geneCount: d.gene_count,
    nodes,
    links: (d.sankey?.links ?? []).map((l) => ({ source: l.source, target: l.target, value: l.value ?? 1 })),
    chromosome,
    highlightPair,
  }
}

/** 把染色体级响应归一化为视图（全基因组 / 按区域共用） */
function buildChromosomeView(
  d: GenomeSyntenyResult,
  source: string,
  target: string,
  scope: string,
  srcLengths: ChromosomeLengths,
  tgtLengths: ChromosomeLengths,
): SankeyView {
  return {
    sourceId: d.source_id || source,
    targetId: d.target_id || target,
    scope,
    blockCount: d.block_count,
    geneCount: d.gene_count,
    nodes: (d.sankey?.nodes ?? []).map((n) => {
      const lengths = n.genome === 'target' ? tgtLengths : srcLengths
      return {
        name: n.name,
        genome: n.genome,
        lengthBp: lengths[n.chr || n.name],
      }
    }),
    links: (d.sankey?.links ?? []).map((l) => ({
      source: l.source,
      target: l.target,
      value: l.value ?? 1,
    })),
    figures: d.figures,
  }
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
  chromosomeError.value = ''
  view.value = null
  chromosomeView.value = null
  microData.value = null
  try {
    if (mode.value === 'gene') {
      const res = await getMicrosynteny({
        source: sourceGenome.value,
        target: targetGenome.value,
        gene_ids: geneId.value.trim(),
      })
      if (res.code !== 0) {
        error.value = res.message
        return
      }
      const d = res.data
      microData.value = d
      const blockIds = new Set(
        [...(d.tracks?.source ?? []), ...(d.tracks?.target ?? [])]
          .map((g) => g.block_id)
          .filter(Boolean),
      )
      // 基因级视图本身由 microLayout 绘制；view 只承载顶部统计信息
      view.value = {
        sourceId: d.source_id || sourceGenome.value,
        targetId: d.target_id || targetGenome.value,
        scope: (d.query_genes ?? []).join(', ') || geneId.value.trim(),
        blockCount: blockIds.size,
        geneCount: (d.tracks?.source?.length ?? 0) + (d.tracks?.target?.length ?? 0),
        nodes: [],
        links: [],
      }

      // 同时绘制染色体级视图：只取查询基因所在共线性块涉及的染色体对
      const pair = chromosomePairOfQuery(d)
      if (pair) {
        try {
          chromosomeView.value = await loadChromosomeView(
            d.source_id || sourceGenome.value,
            d.target_id || targetGenome.value,
            pair.source,
            { source: pair.source, target: pair.target },
            pair.source,
          )
        } catch (e) {
          chromosomeError.value =
            e instanceof Error ? e.message : t('synteny_chromosome_level_unavailable')
        }
      } else {
        chromosomeError.value = t('synteny_chromosome_level_unavailable')
      }
    } else {
      // 全基因组 / 按区域：统一用 include_blocks=true 拉一次数据，
      // 既用于桑葚图（染色体级 sankey），又用于块/基因表格，避免表格单独再拉一次 4.3 MiB 全量 blocks 导致明显延迟。
      // 全基因组时后端返回全部染色体级桑葚图；按区域时从 “染色体:起-止” 中解析染色体名后过滤（后端当前按染色体聚合）
      const chromosome = mode.value === 'region' ? region.value.trim().split(':')[0].trim() : undefined
      const res = await getGenomeSynteny({
        source: sourceGenome.value,
        target: targetGenome.value,
        chromosome,
        includeBlocks: true,
      })
      if (res.code !== 0) {
        error.value = res.message
        return
      }
      const d = res.data
      // 先构建桑葚图（只依赖 sankey，不含 blocks），让图立即呈现；
      // 再并行做块/基因表格筛选（复用同一响应里的 blocks，避免二次拉取大体积数据），避免表格比图晚出现很久。
      const [srcLengths, tgtLengths] = await Promise.all([
        lengthsFor(sourceGenome.value),
        lengthsFor(targetGenome.value),
      ])
      view.value = buildChromosomeView(
        d,
        sourceGenome.value,
        targetGenome.value,
        mode.value === 'all' ? t('synteny_scope_all') : d.chromosome,
        srcLengths,
        tgtLengths,
      )
      // 按区域筛选块/基因表格：复用同一响应里的 blocks，避免二次拉取大体积数据
      if (mode.value === 'region') {
        regionBlockLoading.value = true
        try {
          const range = parseRegionRange(region.value)
          regionBlockRows.value =
            range && d.blocks
              ? await filterBlocksByRegion(d.blocks, sourceGenome.value, targetGenome.value, range)
              : []
        } finally {
          regionBlockLoading.value = false
        }
      }
    }
    await nextTick()
    renderSankey()
    renderChromosomeSankey()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.container {
  max-width: 100vw;
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

.sankey-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #495057;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-dot.source { background: #3a6ea5; }
.legend-dot.target { background: #eb6834; }

.sankey-container {
  width: 100%;
  height: 560px;
}

.figure-img {
  width: 100%;
  border: 1px solid #e9ecef;
  border-radius: 8px;
}

/* 基因级微共线性图：两条轨道 + 细连线，倒位片段用不同颜色 */
.microsynteny-wrap {
  width: 100%;
  overflow-x: auto;
  padding: 4px 0 8px;
}

.microsynteny-hint {
  margin-bottom: 8px;
  font-size: 13px;
  color: #6c757d;
}

.micro-svg {
  display: block;
  width: 100%;
  min-width: 720px;
  height: auto;
}

.track-label {
  font-size: 12px;
  font-weight: 600;
  fill: #495057;
}

.axis-tick {
  font-size: 10px;
  fill: #868e96;
}

.micro-gene {
  cursor: default;
}

.micro-link {
  cursor: pointer;
  outline: none;
}

/* 细线：与桑葚图的宽带区分；hit 路径只扩大点击热区，不显示 */
.micro-link-line {
  fill: none;
  stroke: #5c7c9f;
  stroke-width: 1;
  stroke-opacity: 0.55;
  vector-effect: non-scaling-stroke;
  transition: stroke-opacity 0.15s ease, stroke-width 0.15s ease;
}

.micro-link-hit {
  fill: none;
  stroke: transparent;
  stroke-width: 10;
  pointer-events: stroke;
}

.micro-link.query .micro-link-line {
  stroke: #3a6ea5;
  stroke-width: 1.8;
  stroke-opacity: 0.95;
}

/* 倒位/重排：红色虚线，作为颜色之外的第二重编码 */
.micro-link.inverted .micro-link-line {
  stroke: #c92a2a;
  stroke-width: 1.2;
  stroke-opacity: 0.9;
  stroke-dasharray: 5 3;
}

.micro-link:hover .micro-link-line,
.micro-link:focus-visible .micro-link-line {
  stroke-width: 2;
  stroke-opacity: 1;
}

.gene-label {
  font-size: 10px;
  fill: #1f2d3d;
  pointer-events: none;
}

.gene-label.query {
  font-weight: 600;
}

.micro-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 18px;
  margin-top: 8px;
  font-size: 13px;
  color: #495057;
}

.micro-legend > span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.micro-swatch {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.micro-swatch.source { background: #3a6ea5; }
.micro-swatch.target { background: #eb6834; }

.micro-line-swatch {
  display: inline-block;
  width: 26px;
  height: 0;
  border-top: 1.5px solid #5c7c9f;
}

.micro-line-swatch.inverted {
  border-top-color: #c92a2a;
  border-top-style: dashed;
}

.micro-table {
  margin-top: 8px;
}

/* JBrowse 区块：两侧左右分列，复用现有 JBrowse2 静态页 */
.jbrowse-col h6 {
  font-size: 13px;
  color: #6c757d;
  margin-bottom: 6px;
}

.synteny-jbrowse-frame {
  width: 100%;
  height: 420px;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  background: #fff;
}

.jbrowse-hint {
  font-size: 12px;
  color: #909399;
}

/* 共线性块与基因表格：展开行展示两侧基因明细 */
.block-gene-cell {
  padding: 6px 24px 12px;
}

.block-gene-label {
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 4px;
}

.block-gene-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.gene-tag {
  border-radius: 3px;
}

.gene-more {
  margin-left: 4px;
  font-size: 12px;
  color: #909399;
}

@media (max-width: 768px) {
  .jbrowse-col {
    margin-bottom: 16px;
  }

  .synteny-jbrowse-frame {
    height: 300px;
  }
}
</style>
