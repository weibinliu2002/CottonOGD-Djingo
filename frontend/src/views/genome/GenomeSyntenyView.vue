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

      <div v-if="ribbonLoading" class="ribbon-loading">
        <el-skeleton :rows="4" animated />
      </div>
      <SyntenyRibbonChart
        v-else-if="ribbonLayout"
        :layout="ribbonLayout"
        :selected-block="selectedBlock"
        @block-click="onRibbonBlockClick"
      />
      <el-alert
        v-else-if="ribbonError"
        :title="ribbonError"
        type="warning"
        :closable="false"
        show-icon
        class="mt-3"
      />
      <el-alert
        v-else
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

      <template v-else>
        <div v-if="ribbonLoading" class="ribbon-loading">
          <el-skeleton :rows="4" animated />
        </div>
        <SyntenyRibbonChart
          v-else-if="ribbonLayout"
          :layout="ribbonLayout"
          :selected-block="selectedBlock"
          @block-click="onRibbonBlockClick"
        />
        <el-alert
          v-else-if="ribbonError"
          :title="ribbonError"
          type="warning"
          :closable="false"
          show-icon
          class="mt-3"
        />
        <el-alert
          v-else
          :title="t('synteny_no_blocks')"
          type="info"
          :closable="false"
          show-icon
          class="mt-3"
        />
      </template>
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
        highlight-current-row
        @row-click="onBlockRowClick"
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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter, useRoute } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
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
import SyntenyRibbonChart from '@/components/genome/SyntenyRibbonChart.vue'
import {
  loadSyntenyPairData,
  toRibbonBlocks,
  buildRibbonLayout,
  compareChr,
  SYNTENY_FILE_UNAVAILABLE,
  type RibbonBlock,
  type RibbonLayout,
} from '@/components/genome/syntenyRibbon'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
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

const hasFigures = computed(
  () =>
    !!view.value?.figures &&
    (!!view.value.figures.dotplot || !!view.value.figures.depth || !!view.value.figures.karyotype),
)

/** .fai 索引按基因组缓存，避免重复检索 */
const chrLengthCache = new Map<string, ChromosomeLengths>()
async function lengthsFor(genome: string): Promise<ChromosomeLengths> {
  const hit = chrLengthCache.get(genome)
  if (hit) return hit
  const fetched = await getChromosomeLengths(genome)
  if (Object.keys(fetched).length) chrLengthCache.set(genome, fetched)
  return fetched
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

/** ---------- 染色体级 ribbon 图（真实 bp 坐标带状图） ----------
 * 替代原 ECharts sankey：sankey 的连线由流量布局决定，全部从染色体条一端堆叠，
 * 不反映共线块在染色体上的真实位置。ribbon 左右两列竖直染色体条（高度 ∝ 真实 bp），
 * 每条色带两端取该块在两侧染色体上的真实坐标（数据来自 anchors.simple + .bed）。 */
const ribbonLayout = ref<RibbonLayout | null>(null)
const ribbonLoading = ref(false)
const ribbonError = ref('')
/** 当前 ribbon 展示的块列表（供色带点击与统计使用） */
const ribbonBlocks = ref<RibbonBlock[]>([])
/** 表格选中行对应的色带；设置后图中只突出该块（区域/基因检索时使用） */
const selectedBlock = ref<RibbonBlock | null>(null)
/** 从桑葚图点进来的块端点（s1,s2,t1,t2）：
 * 一个基因可能落在多个嵌套块里（microsynteny 返回的是包含该基因的最大块），
 * 只有记住用户实际点击的块，跳转后才能只高亮那一个块。 */
const ribbonBlockHint = ref<string[] | null>(null)

/** 按当前视图构建 ribbon 布局。opts.sourceChrs 给定时只绘制这些源染色体（基因/区间模式），
 * 目标染色体取命中块实际涉及的目标染色体；
 * isHighlight 命中的色带加粗高亮；pickHighlights 可在拿到完整块列表后按块内容挑出高亮块
 * （microsynteny 的块首尾基因与 anchors 块端点对不上时，单块谓词无法判断，必须看全集）。 */
async function buildRibbonFor(
  opts: {
    sourceChrs?: string[]
    isHighlight?: (b: RibbonBlock) => boolean
    pickHighlights?: (blocks: RibbonBlock[]) => RibbonBlock[]
  } = {},
): Promise<void> {
  ribbonLayout.value = null
  ribbonError.value = ''
  const source = view.value?.sourceId || sourceGenome.value
  const target = view.value?.targetId || targetGenome.value
  if (!source || !target) return
  ribbonLoading.value = true
  try {
    const [pairData, srcLengths, tgtLengths] = await Promise.all([
      loadSyntenyPairData(source, target),
      lengthsFor(source),
      lengthsFor(target),
    ])
    let blocks = toRibbonBlocks(pairData.anchors, pairData.sourceBed, pairData.targetBed)
    if (opts.sourceChrs?.length) {
      const want = new Set(opts.sourceChrs)
      blocks = blocks.filter((b) => want.has(b.sourceChr))
    }
    ribbonBlocks.value = blocks
    // 某些检索（基因级）需要看完整块列表才能确定命中块，这里先算出高亮集合，
    // 再用对象同一性判断；集合为空时退回 isHighlight 谓词。
    const picked = opts.pickHighlights ? new Set(opts.pickHighlights(blocks)) : null
    const single = (opts.sourceChrs?.length ?? 0) === 1
    const usedSourceChrs = opts.sourceChrs?.length
      ? opts.sourceChrs
      : [...new Set(blocks.map((b) => b.sourceChr))].sort(compareChr)
    const usedTargetChrs = [...new Set(blocks.map((b) => b.targetChr))].sort(compareChr)
    if (!usedSourceChrs.length || !usedTargetChrs.length) {
      ribbonLayout.value = null
      return
    }
    ribbonLayout.value = buildRibbonLayout({
      blocks,
      sourceChrs: usedSourceChrs,
      targetChrs: usedTargetChrs,
      sourceLengths: srcLengths,
      targetLengths: tgtLengths,
      width: 1200,
      height: single ? 340 : 400,
      showTicks: single,
      clickHint: t('synteny_click_interval_hint'),
      isHighlight: picked ? (b) => picked.has(b) : opts.isHighlight,
    })
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ribbonError.value = msg.includes(SYNTENY_FILE_UNAVAILABLE)
      ? t('synteny_ribbon_source_unavailable')
      : msg
    ribbonLayout.value = null
  } finally {
    ribbonLoading.value = false
  }
}

/** 表格行与 ribbon 块匹配：优先用块首尾基因，找不到时退回双侧区间重叠最大者 */
function findRibbonBlockForRow(row: SyntenyBlockRow): RibbonBlock | null {
  const blocks = ribbonBlocks.value
  if (!blocks.length) return null
  const sGenes = new Set(row.sourceGenes)
  const tGenes = new Set(row.targetGenes)
  const byGene = blocks.find(
    (b) =>
      (sGenes.has(b.s1) || sGenes.has(b.s2)) &&
      (tGenes.has(b.t1) || tGenes.has(b.t2)),
  )
  if (byGene) return byGene
  const s = parseRegionRange(row.sourceRegion)
  const t = parseRegionRange(row.targetRegion)
  if (!s || !t) return null
  let best: RibbonBlock | null = null
  let bestScore = 0
  for (const b of blocks) {
    const so = Math.min(b.sourceEnd, s.end) - Math.max(b.sourceStart, s.start)
    const to = Math.min(b.targetEnd, t.end) - Math.max(b.targetStart, t.start)
    if (so <= 0 || to <= 0) continue
    const score = Math.min(
      so / Math.max(1, b.sourceEnd - b.sourceStart),
      to / Math.max(1, b.targetEnd - b.targetStart),
    )
    if (score > bestScore) {
      bestScore = score
      best = b
    }
  }
  return best
}

/** 表格行点击：选中对应色带并压暗其余块；再次点击同一行取消选中 */
function onBlockRowClick(row: SyntenyBlockRow): void {
  const hit = findRibbonBlockForRow(row)
  if (!hit) {
    selectedBlock.value = null
    return
  }
  selectedBlock.value = selectedBlock.value === hit ? null : hit
}

/** ribbon 色带点击：直接取该块两侧的首基因，跳回本页按基因级模式检索该共线性块 */
async function onRibbonBlockClick(block: RibbonBlock): Promise<void> {
  await navigateToSyntenyResult({
    sourceId: view.value?.sourceId || sourceGenome.value,
    targetId: view.value?.targetId || targetGenome.value,
    sourceGenes: [{ gene_id: block.s1 }],
    targetGenes: [{ gene_id: block.t1 }],
    // 记录被点击块的四端点，跳转后据此只高亮这个块（基因查询本身可能命中更大的嵌套块）
    ribbonBlock: block,
  })
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

/** 点击桑葚图连线：跳回共线性页面，以基因级模式初始化，展示该条连线的共线性块与块内基因级微共线性，
 * 满足"点击跳转展示一条共线性详细情况"的需求；基因块点击已单独跳基因详情页。 */
async function navigateToSyntenyResult(args: {
  sourceId: string
  targetId: string
  sourceGenes?: { gene_id: string }[]
  targetGenes?: { gene_id: string }[]
  /** 被点击的共线块；带上四端点，跳转后精确高亮该块 */
  ribbonBlock?: RibbonBlock
}): Promise<string | undefined> {
  const queryGene = args.sourceGenes?.[0]?.gene_id ?? args.targetGenes?.[0]?.gene_id
  const query: Record<string, string> = {
    from_synteny: '1',
    mode: 'gene',
    gene_id: queryGene ?? '',
    source: args.sourceId,
    target: args.targetId,
  }
  if (args.ribbonBlock) {
    const b = args.ribbonBlock
    query.ribbon_block = [b.s1, b.s2, b.t1, b.t2].join(',')
  }
  await router.push({ path: '/genome/synteny', query })
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

watch(
  () => [mode.value, region.value, geneId.value],
  async () => {
    // 路由 query 同步会同时改动这些字段，此时由 handleSubmit 统一请求，避免重复拉取
    if (routeQuerySyncing) return
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

/** 从路由 query 恢复检索条件：ribbon 色带点击跳回本页时会带 mode/gene_id/source/target，
 * ribbon_block 记录被点击块的四个端点（s1,s2,t1,t2），用于精确高亮该块 */
function applyRouteQuery(q: Record<string, unknown>): boolean {
  const qMode = q.mode === 'all' || q.mode === 'region' || q.mode === 'gene' ? q.mode : null
  const qGene = typeof q.gene_id === 'string' ? q.gene_id.trim() : ''
  const qRegion = typeof q.region === 'string' ? q.region.trim() : ''
  const qSource = typeof q.source === 'string' ? q.source.trim() : ''
  const qTarget = typeof q.target === 'string' ? q.target.trim() : ''
  const qBlock = typeof q.ribbon_block === 'string' ? q.ribbon_block.trim() : ''
  const hasQuery = !!(qMode || qGene || qRegion || qSource || qTarget || qBlock)
  if (!hasQuery) return false
  if (qSource) sourceGenome.value = qSource
  if (qTarget) targetGenome.value = qTarget
  if (qMode) mode.value = qMode
  if (qGene) geneId.value = qGene
  if (qRegion) region.value = qRegion
  const ends = qBlock ? qBlock.split(',').map((s) => s.trim()) : []
  ribbonBlockHint.value = ends.length === 4 && ends.every(Boolean) ? ends : null
  return true
}

let initialized = false
/** 路由 query 同步期间抑制“模式/区域输入”watch 的重复请求 */
let routeQuerySyncing = false

onMounted(async () => {
  await ensureGenomesLoaded()

  const hasRouteQuery = applyRouteQuery(route.query as Record<string, unknown>)
  if (!sourceGenome.value || !targetGenome.value) {
    // 默认优先使用 TM-1 HAU v1.1 ↔ TM-1 ZJU v1.1T2T；若后端未提供该组合再退回第一个可用组合。
    try {
      const pairs = await getSyntenyPairs()
      const allPairs = pairs.data?.pairs ?? []
      const preferred = allPairs.find(
        (p) => p.source === PREFERRED_SOURCE && p.target === PREFERRED_TARGET,
      )
      const p = preferred ?? allPairs[0]
      if (p) {
        if (!sourceGenome.value) sourceGenome.value = p.source
        if (!targetGenome.value) targetGenome.value = p.target
      }
    } catch {
      /* 接口失败时使用前端默认值 */
    }
    if (!sourceGenome.value) {
      const def = pickDefaultGenome()
      if (def) sourceGenome.value = def
    }
    if (!targetGenome.value) targetGenome.value = PREFERRED_TARGET
  }
  if (sourceGenome.value && targetGenome.value && (hasRouteQuery || !view.value)) {
    routeQuerySyncing = true
    try {
      await handleSubmit()
    } finally {
      routeQuerySyncing = false
    }
  }
  initialized = true
})

/** 从其他页面（如区块表格）跳回 /genome/synteny 时组件会复用，需要监听 query 变化重新检索 */
watch(
  () => route.query,
  async (q) => {
    if (!initialized || route.path !== '/genome/synteny') return
    routeQuerySyncing = true
    try {
      if (!applyRouteQuery(q as Record<string, unknown>)) return
      if (sourceGenome.value && targetGenome.value) await handleSubmit()
    } finally {
      routeQuerySyncing = false
    }
  },
)

const fillExample = () => {
  sourceGenome.value = 'G.hirsutumAD1_TM-1_HAU_v1.1'
  targetGenome.value = 'G.hirsutumAD1_TM-1_ZJU_v1.1T2T'
  region.value = 'Ghir_A01:1-1000000'
  geneId.value = 'Ghir_A01G000100'
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

/** microsynteny 按 block_id 归并后的块端点信息：
 * 两侧各取 order 最小/最大的基因作为首尾基因，并记录两侧坐标跨度。
 * 同一 JCVI 块在 anchors.simple 中正是以这四个首尾基因表示的，可用端点做精确匹配。 */
interface MicroRibbonSpec {
  sourceChr: string
  targetChr: string
  srcFirst: string
  srcLast: string
  tgtFirst: string
  tgtLast: string
  srcMin: number
  srcMax: number
  tgtMin: number
  tgtMax: number
}

function microRibbonSpecs(data: MicrosyntenyResult): MicroRibbonSpec[] {
  const src = data.tracks?.source ?? []
  const tgt = data.tracks?.target ?? []
  const blockIds = new Set<string>()
  for (const g of [...src, ...tgt]) if (g.block_id) blockIds.add(g.block_id)
  const specs: MicroRibbonSpec[] = []
  for (const id of blockIds) {
    const s = src.filter((g) => g.block_id === id).sort((a, b) => a.order - b.order)
    const t = tgt.filter((g) => g.block_id === id).sort((a, b) => a.order - b.order)
    if (!s.length || !t.length) continue
    const sFirst = s[0]
    const sLast = s[s.length - 1]
    const tFirst = t[0]
    const tLast = t[t.length - 1]
    if (!sFirst.chr || !tFirst.chr) continue
    specs.push({
      sourceChr: sFirst.chr,
      targetChr: tFirst.chr,
      srcFirst: sFirst.id,
      srcLast: sLast.id,
      tgtFirst: tFirst.id,
      tgtLast: tLast.id,
      srcMin: Math.min(...s.map((g) => g.start)),
      srcMax: Math.max(...s.map((g) => g.end)),
      tgtMin: Math.min(...t.map((g) => g.start)),
      tgtMax: Math.max(...t.map((g) => g.end)),
    })
  }
  return specs
}

/** 从 anchors 块中挑出 microsynteny 命中的块。
 * 不能用“端点基因是否出现在轨道里”判断：轨道包含整块的 1000+ 个基因，
 * 同一染色体上大量嵌套/相邻块的端点都在里面，会把几乎全部块误判为命中。
 * 这里按“首尾基因四端点与 anchors 块完全一致（方向不限）”精确匹配；
 * 轨道被截断导致端点对不上时，退回四端点坐标距离最小的块（距离 0 即精确块）。 */
function pickMicroRibbonBlocks(blocks: RibbonBlock[], specs: MicroRibbonSpec[]): RibbonBlock[] {
  const picked = new Set<RibbonBlock>()
  for (const spec of specs) {
    const candidates = blocks.filter(
      (b) => b.sourceChr === spec.sourceChr && b.targetChr === spec.targetChr,
    )
    if (!candidates.length) continue
    const sameSet = (a: string, b: string, x: string, y: string) =>
      (a === x && b === y) || (a === y && b === x)
    const exact = candidates.filter(
      (b) =>
        sameSet(b.s1, b.s2, spec.srcFirst, spec.srcLast) &&
        sameSet(b.t1, b.t2, spec.tgtFirst, spec.tgtLast),
    )
    if (exact.length) {
      for (const b of exact) picked.add(b)
      continue
    }
    let best: RibbonBlock | null = null
    let bestDist = Number.POSITIVE_INFINITY
    for (const b of candidates) {
      const dist =
        Math.abs(b.sourceStart - spec.srcMin) +
        Math.abs(b.sourceEnd - spec.srcMax) +
        Math.abs(b.targetStart - spec.tgtMin) +
        Math.abs(b.targetEnd - spec.tgtMax)
      if (dist < bestDist) {
        bestDist = dist
        best = b
      }
    }
    if (best) picked.add(best)
  }
  return [...picked]
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

/** 把染色体级响应归一化为视图统计信息（全基因组 / 按区域共用，图形由 ribbon 负责） */
function buildChromosomeView(
  d: GenomeSyntenyResult,
  source: string,
  target: string,
  scope: string,
): SankeyView {
  return {
    sourceId: d.source_id || source,
    targetId: d.target_id || target,
    scope,
    blockCount: d.block_count,
    geneCount: d.gene_count,
    nodes: [],
    links: [],
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
  ribbonLayout.value = null
  ribbonError.value = ''
  ribbonBlocks.value = []
  selectedBlock.value = null
  // 用户在本页手动检索时，之前从桑葚图带进来的块提示已失效；路由同步的检索要保留
  if (!routeQuerySyncing) ribbonBlockHint.value = null
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

      // 同时绘制染色体级 ribbon：只画查询基因所在共线性块涉及的那对染色体并高亮
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
        // 只高亮本次检索命中的块：基因级结果通常是一个块（少数情况含相邻块），
        // 用 microsynteny 块的四个首尾基因去精确匹配 anchors 块端点，不能按“基因是否在轨道里”判断，
        // 因为轨道含整块 1000+ 个基因，会把同染色体上大量相邻/嵌套块一起点亮（用户实测全部高亮）。
        await buildRibbonFor({
          sourceChrs: [pair.source],
          pickHighlights: (blocks) => {
            // 优先使用“从桑葚图点进来的那个块”：同一基因可能同时属于嵌套的小块和覆盖整段的大块，
            // 按基因查询只能得到大块，会和用户点的块不一致
            const hint = ribbonBlockHint.value
            if (hint) {
              const sameSet = (a: string, b: string, x: string, y: string) =>
                (a === x && b === y) || (a === y && b === x)
              const clicked = blocks.filter(
                (b) =>
                  sameSet(b.s1, b.s2, hint[0], hint[1]) &&
                  sameSet(b.t1, b.t2, hint[2], hint[3]),
              )
              if (clicked.length) return clicked
            }
            return pickMicroRibbonBlocks(blocks, microRibbonSpecs(d))
          },
        })
      } else {
        chromosomeError.value = t('synteny_chromosome_level_unavailable')
      }
    } else {
      // 全基因组 / 按区域：统一用 include_blocks=true 拉一次数据，
      // 既用于桑葚图（染色体级 sankey），又用于块/基因表格，避免表格单独再拉一次 4.3 MiB 全量 blocks 导致明显延迟。
      // 全基因组时后端返回全部染色体级桑葚图；按区域时从 “染色体:起-止” 中解析染色体名后过滤（后端当前按染色体聚合）
      const chromosome = mode.value === 'region' ? region.value.trim().split(':')[0].trim() : undefined
      const range = mode.value === 'region' ? parseRegionRange(region.value) : null
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
      view.value = buildChromosomeView(
        d,
        sourceGenome.value,
        targetGenome.value,
        mode.value === 'all' ? t('synteny_scope_all') : d.chromosome,
      )
      // 按区域筛选块/基因表格：复用同一响应里的 blocks，避免二次拉取大体积数据
      if (mode.value === 'region') {
        regionBlockLoading.value = true
        try {
          regionBlockRows.value =
            range && d.blocks
              ? await filterBlocksByRegion(d.blocks, sourceGenome.value, targetGenome.value, range)
              : []
        } finally {
          regionBlockLoading.value = false
        }
      }
      // ribbon：全基因组画全部染色体；按区域只画该源染色体并高亮落在区间内的块
      await buildRibbonFor({
        sourceChrs: chromosome ? [chromosome] : undefined,
        isHighlight: range
          ? (b) =>
              b.sourceChr === range.chr &&
              rangesOverlap({ chr: b.sourceChr, start: b.sourceStart, end: b.sourceEnd }, range)
          : undefined,
      })
    }
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

.ribbon-loading {
  padding: 8px 0;
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
