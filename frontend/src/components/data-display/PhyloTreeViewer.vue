<template>
  <div class="phylo-tree-viewer">
    <!-- ========== 1. 信息面板 ========== -->
    <div v-if="treeData" class="tree-info">
      <div class="info-chip"><span class="info-label">{{ t('family') }}:</span> {{ selectedFamily }}</div>
      <div class="info-chip"><span class="info-label">{{ t('category') }}:</span> {{ props.category }}</div>
      <div class="info-chip"><span class="info-label">{{ t('genome') }}:</span> {{ props.genome }}</div>
      <div class="info-chip" v-if="leafCount > 0"><span class="info-label">{{ t('tree_sequences') }}:</span> {{ leafCount }}</div>
    </div>

    <!-- ========== 2. 顶部控制栏（任何状态都显示） ========== -->
    <div class="tree-controls">
      <div class="control-group" v-if="!props.family">
        <label class="control-label">{{ t('family') }}</label>
        <el-select
          v-model="selectedFamily"
          filterable
          :placeholder="t('family')"
          @change="onFamilyChange"
          class="family-select"
          size="small"
        >
          <el-option v-for="f in displayFamilies" :key="f" :label="f" :value="f" />
        </el-select>
      </div>
      <el-input
        v-model="searchKeyword"
        v-if="treeData"
        :placeholder="t('tree_search_placeholder')"
        clearable
        size="small"
        class="search-input"
        :prefix-icon="Search"
        @input="scheduleSearch"
        @clear="clearSearch"
      />
      <div class="control-spacer" />
      <el-dropdown trigger="click" @command="handleExport" size="small" :disabled="!treeData">
        <el-button size="small" :icon="Download">{{ t('export') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="svg">SVG</el-dropdown-item>
            <el-dropdown-item command="png">PNG</el-dropdown-item>
            <el-dropdown-item command="newick">Newick</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-tooltip :content="t('tree_reset')" placement="top">
        <el-button size="small" :icon="RefreshLeft" @click="resetView" :disabled="!treeData" />
      </el-tooltip>
    </div>

    <!-- ========== 3. 错误 / 空状态 ========== -->
    <el-alert
      v-if="treeError"
      type="error"
      :title="treeError"
      show-icon
      :closable="false"
      class="tree-error"
    />
    <div v-else-if="!treeData && !treeLoading" class="tree-status tree-empty">
      <el-icon><DataBoard /></el-icon>
      <span>{{ t('select_family_first') }}</span>
    </div>

    <!-- ========== 4. 已加载或加载中 ========== -->
    <div v-else class="tree-loaded-area">

      <!-- 操作工具栏 -->
      <div v-if="treeData" class="tree-toolbar">
        <!-- 布局 -->
        <div class="toolbar-group">
          <span class="toolbar-label">{{ t('tree_layout') }}</span>
          <el-radio-group v-model="layoutMode" size="small" @change="onLayoutChange">
            <el-radio-button label="rect">{{ t('rectangular') }}</el-radio-button>
            <el-radio-button label="radial">{{ t('radial') }}</el-radio-button>
            <el-radio-button label="unrooted">{{ t('unrooted') }}</el-radio-button>
          </el-radio-group>
        </div>
        <el-divider direction="vertical" />

        <!-- Zoom -->
        <div class="toolbar-group">
          <span class="toolbar-label">{{ t('tree_zoom') }}</span>
          <el-button-group>
            <el-tooltip content="+" placement="top">
              <el-button size="small" @click="zoomIn" :icon="ZoomIn" />
            </el-tooltip>
            <el-tooltip content="−" placement="top">
              <el-button size="small" @click="zoomOut" :icon="ZoomOut" />
            </el-tooltip>
            <el-tooltip :content="t('tree_fit')" placement="top">
              <el-button size="small" @click="fitZoom" :icon="FullScreen" />
            </el-tooltip>
            <el-tooltip :content="t('tree_reset')" placement="top">
              <el-button size="small" @click="resetZoom" :icon="RefreshRight" />
            </el-tooltip>
          </el-button-group>
        </div>
        <el-divider direction="vertical" />

        <!-- 间距（数值输入，用户要求不用按钮） -->
        <div class="toolbar-group">
          <span class="toolbar-label">{{ t('tree_spacing') }}</span>
          <span class="spacing-sub">垂直</span>
          <el-input-number
            v-model="spacingY" :min="2" :max="100" :step="2" size="small"
            controls-position="right" @change="onSpacingYChange"
            style="width: 90px"
          />
          <span class="spacing-sub">水平</span>
          <el-input-number
            v-model="spacingX" :min="14" :max="100" :step="2" size="small"
            controls-position="right" @change="onSpacingXChange"
            style="width: 90px"
          />
        </div>
        <el-divider direction="vertical" />

        <!-- 排序 -->
        <div class="toolbar-group">
          <el-dropdown trigger="click" @command="sortNodes" size="small">
            <el-button size="small" :icon="Sort">{{ t('tree_sort') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="asc">{{ t('tree_sort_asc') }}</el-dropdown-item>
                <el-dropdown-item command="desc">{{ t('tree_sort_desc') }}</el-dropdown-item>
                <el-dropdown-item command="original">{{ t('tree_sort_original') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <el-divider direction="vertical" />

        <!-- Reroot -->
        <div class="toolbar-group">
          <el-dropdown trigger="click" @command="handleReroot" size="small">
            <el-button size="small">{{ t('tree_reroot') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="midpoint">{{ t('tree_reroot_midpoint') }}</el-dropdown-item>
                <el-dropdown-item command="reset">{{ t('tree_reroot_reset') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <el-divider direction="vertical" />

        <!-- 开关 checkbox -->
        <div class="toolbar-group toolbar-switches">
          <el-checkbox size="small" v-model="showBranchLength" @change="onBranchLabelToggle">
            {{ t('tree_show_branch_length') }}
          </el-checkbox>
          <el-checkbox size="small" v-model="alignRight" :disabled="layoutMode === 'unrooted'" @change="onAlignToggle">
            {{ t('tree_align_tips') }}
          </el-checkbox>
          <el-checkbox size="small" v-model="ignoreBranchLength" @change="onIgnoreBranchToggle">
            {{ t('tree_ignore_branch_length') }}
          </el-checkbox>
        </div>
      </div>

      <!-- 树容器（固定高度 700px，overflow hidden + d3-zoom 内部平移） -->
      <div class="tree-wrapper">
        <div ref="treeContainerRef" id="phylotree-container" class="tree-container" />
        <div v-if="treeLoading" class="tree-mask">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>{{ t('loading_tree') }}</span>
        </div>
        <div v-if="collapsedCount > 0 || selectedNodeName" class="tree-statusbar">
          <span v-if="collapsedCount > 0">{{ t('tree_collapsed_count', { n: collapsedCount }) }}</span>
          <span v-if="selectedNodeName" class="statusbar-selected">{{ t('tree_selected') }}: {{ selectedNodeName }}</span>
          <span class="statusbar-hint">{{ t('tree_hint') }}</span>
        </div>
      </div>

      <!-- Detail panel：点击 tip 后显示 -->
      <transition name="el-fade-in-linear">
        <div v-if="detailNode" class="tree-detail-panel">
          <div class="detail-header">
            <strong>{{ t('tree_selected') }}: {{ detailNode.geneId }}</strong>
            <el-icon class="detail-close" @click="detailNode = null"><Close /></el-icon>
          </div>
          <div class="detail-row"><span>{{ t('tree_detail_genome') }}:</span> {{ props.genome }}</div>
          <div class="detail-row"><span>{{ t('tree_detail_category') }}:</span> {{ props.category }}</div>
          <div class="detail-row"><span>{{ t('tree_detail_family') }}:</span> {{ selectedFamily }}</div>
          <el-button size="small" type="primary" :icon="View" @click="goToGeneDetail(detailNode.geneId)">
            {{ t('tree_view_gene_detail') }}
          </el-button>
        </div>
      </transition>
    </div>

    <!-- Tooltip -->
    <div
      class="tree-tooltip"
      v-show="tooltipVisible"
      :style="{ left: tooltipX + 'px', top: tooltipY + 'px' }"
    >
      <div class="tt-row"><strong>{{ tooltipText }}</strong></div>
      <div class="tt-row"><span>{{ t('genome') }}:</span> {{ props.genome }}</div>
      <div class="tt-row"><span>{{ t('category') }}:</span> {{ props.category }}</div>
      <div class="tt-row"><span>{{ t('family') }}:</span> {{ selectedFamily }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { phylotree } from 'phylotree'
import * as d3 from 'd3'
import {
  Loading, DataBoard, Search, Download, RefreshLeft, RefreshRight,
  Sort, ArrowDown,
  ZoomIn, ZoomOut, FullScreen, Close, View
} from '@element-plus/icons-vue'
import type { PhylotreeNode, RenderOptions } from 'phylotree'

// ==================== 类型 ====================
interface D3StylerElement {
  selectAll: (selector: string) => D3StylerElement
  style: (k: string, v: string | number | null) => D3StylerElement
  attr: (k: string, v: string | null) => D3StylerElement
}

interface PhyloEdge {
  target: PhylotreeNode
  tag?: boolean
  __data__?: PhylotreeNode
}

interface DetailNodeInfo {
  geneId: string
}

// 带可选 tag 的树节点（搜索命中 / 外部表格选中高亮标记）
interface TaggedNode extends PhylotreeNode {
  tag?: boolean
}

// phylotree.nodes 集合的运行时形态（.each 遍历）
interface NodeCollection {
  each: (fn: (n: TaggedNode) => void) => void
}

// TreeRender.links 数组的运行时形态
interface LinkArray extends Array<PhyloEdge> {}

// ==================== Props ====================
const props = defineProps<{
  genome: string
  category: 'TF' | 'TR'
  families?: string[]
  /** 受控模式：由外部（TF/TR 页面的家族单选）指定家族；提供后隐藏组件内部家族选择器 */
  family?: string
  /** 需要在树中高亮的基因 id 列表（来自外部表格多选） */
  highlightGenes?: string[]
}>()

// ==================== Composables ====================
const { t } = useI18n()
const router = useRouter()

// ==================== 硬编码家族 ====================
const hardcodedTFFamilies: string[] = [
  'Alfin-like', 'AP2', 'ARF', 'ARR-B', 'B3', 'BBR-BPC', 'BES1', 'bHLH', 'bZIP',
  'C2H2', 'C3H', 'CAMTA', 'CO-like', 'CPP', 'DBB', 'Dof', 'E2F_DP', 'EIL', 'ERF',
  'FAR1', 'G2-like', 'GATA', 'GeBP', 'GRAS', 'GRF', 'HB-other', 'HB-PHD', 'HD-ZIP',
  'HRT-like', 'HSF', 'LBD', 'LFY', 'LSD', 'MIKC_MADS', 'M-type_MADS', 'MYB',
  'MYB_related', 'NAC', 'NF-X1', 'NF-YA', 'NF-YB', 'NF-YC', 'Nin-like', 'NZZ_SPL',
  'RAV', 'S1Fa-like', 'SAP', 'SBP', 'SRS', 'STAT', 'TALE', 'TCP', 'Trihelix', 'VOZ',
  'Whirly', 'WOX', 'WRKY', 'YABBY', 'ZF-HD',
  'BSD', 'CSD', 'DBP', 'DDT', 'FHA', 'HB-BELL', 'LIM', 'OFP', 'PLATZ',
  'Sigma70-like', 'Tify', 'TUB', 'ULT', 'VARL', 'WD40-like', 'zn-clus'
]
const hardcodedTRFamilies: string[] = [
  'ARID', 'AUX/IAA', 'Coactivator p15', 'GNAT', 'HMG', 'IWS1', 'Jumonji',
  'MBF1', 'MED6', 'MED7', 'mTERF', 'PHD', 'Pseudo ARR-B', 'RB', 'Rcd1-like',
  'SET', 'SNF2', 'SOH1', 'SWI/SNF-BAF60b', 'SWI/SNF-SWI3', 'TAZ', 'TRAF'
]

// ==================== 状态 ====================
const selectedFamily = ref('')
const layoutMode = ref<'rect' | 'radial' | 'unrooted'>('rect')
const alignRight = ref(true)
const showBranchLength = ref(false)
const ignoreBranchLength = ref(false)
const searchKeyword = ref('')
const treeLoading = ref(false)
const treeError = ref('')
const treeData = ref<InstanceType<typeof phylotree> | null>(null)
const treeDisplay = ref<any>(null)
const treeContainerRef = ref<HTMLElement | null>(null)
const lastNewick = ref('')
const leafCount = ref(0)
const collapsedCount = ref(0)
const selectedNodeName = ref('')
const detailNode = ref<DetailNodeInfo | null>(null)

// 间距（数值输入，初始化后由 render 写入默认值）
const spacingX = ref(0)
const spacingY = ref(0)

// Tooltip
const tooltipVisible = ref(false)
const tooltipX = ref(0)
const tooltipY = ref(0)
const tooltipText = ref('')

// 竞态 / 监听清理
let fetchAbort: AbortController | null = null
let leafEventsAbort: AbortController | null = null
let searchTimer: ReturnType<typeof setTimeout> | null = null

const displayFamilies = computed(() => {
  if (props.families && props.families.length > 0) return props.families
  return props.category === 'TF' ? hardcodedTFFamilies : hardcodedTRFamilies
})

// ==================== 工具函数 ====================
function extractGeneId(rawName: string): string {
  const parts = rawName.split('|')
  return parts.length > 1 ? (parts[1] ?? rawName) : rawName
}
function bootstrapColor(node: PhylotreeNode): string | null {
  const raw = (node.data as { bootstrap_values?: string }).bootstrap_values
  const bs = parseFloat(raw ?? '')
  if (isNaN(bs) || bs <= 0) return null
  if (bs >= 95) return '#4caf50'
  if (bs >= 80) return '#ff9800'
  return '#9e9e9e'
}
function countLeaves(node: PhylotreeNode): number {
  const children = (node as PhylotreeNode & { children?: PhylotreeNode[] }).children
  if (!children || children.length === 0) return 1
  return children.reduce((s, c) => s + countLeaves(c), 0)
}

// ==================== 销毁 ====================
function destroyTree() {
  leafEventsAbort?.abort()
  leafEventsAbort = null
  tooltipVisible.value = false
  detailNode.value = null
  selectedNodeName.value = ''
  collapsedCount.value = 0
  if (treeContainerRef.value) treeContainerRef.value.innerHTML = ''
  treeData.value = null
  treeDisplay.value = null
}

// ==================== 加载 ====================
async function loadTree() {
  if (!props.genome || !selectedFamily.value) return

  // 中止上一个请求（竞态处理）
  fetchAbort?.abort()
  fetchAbort = new AbortController()

  destroyTree()
  treeLoading.value = true
  treeError.value = ''

  try {
    const url = `/CottonOGD_api/tf_tree/tree/genome/${props.genome}/${props.category}/${selectedFamily.value}.treefile`
    const response = await fetch(url, {
      headers: { Accept: 'text/plain' },
      signal: fetchAbort.signal
    })

    if (!response.ok) {
      if (response.status === 404) throw new Error(t('tree_not_found'))
      throw new Error(`HTTP ${response.status}`)
    }
    const newick = await response.text()
    const trimmed = newick.trim()
    if (!trimmed || trimmed === ';') throw new Error(t('tree_empty'))

    lastNewick.value = trimmed
    await renderTree(trimmed)
  } catch (err: any) {
    if (err?.name === 'AbortError') return
    treeError.value = err.message || t('tree_parse_error')
    console.error('PhyloTree load error:', err)
  } finally {
    treeLoading.value = false
  }
}

// ==================== 渲染 ====================
async function renderTree(newickStr: string) {
  destroyTree()
  let tree: InstanceType<typeof phylotree>
  try {
    tree = new phylotree(newickStr)
  } catch {
    throw new Error(t('tree_parse_error'))
  }
  treeData.value = tree

  await nextTick()
  if (!treeContainerRef.value) throw new Error('Container not found')

  const isRadial = layoutMode.value === 'radial'
  const isUnrooted = layoutMode.value === 'unrooted'
  const isLeafAlign = !isUnrooted && alignRight.value
  leafCount.value = countLeaves(tree.nodes as unknown as PhylotreeNode)

  const renderOptions: RenderOptions = {
    container: '#phylotree-container',
    // 显式大画布：fit-to-size 会把超长叶标签（~450px）算进宽度，
    // 默认 800px 宽会导致分枝被压缩得很短，加大画布给分枝留足空间
    width: 1600,
    height: 700,
    // @ts-expect-error v2.6.0 支持，但类型声明未更新
    'left-right-spacing': 'fit-to-size',
    // @ts-expect-error v2.6.0 支持，但类型声明未更新
    'top-bottom-spacing': 'fit-to-size',
    'align-tips': isLeafAlign,
    'show-scale': !isUnrooted,
    'is-radial': isRadial,
    'is-unrooted': isUnrooted,
    // scaling=false 时为 cladogram（忽略枝长），叶节点按层数对齐到最右/最外圈。
    // 运行时支持该选项（phylotree v2.6.0），RenderOptions 类型声明未列出 scaling，
    // 与 node-styler/edge-styler 一样作为额外选项传入（对象字面量不触发 excess 检查）。
    'scaling': !ignoreBranchLength.value,
    'show-labels': true,
    'font-size': 12,
    zoom: true,
    selectable: false,
    collapsible: true,
    // 官方 demo 没有 node-styler / edge-styler，但我们需要 bootstrap 着色 + 搜索高亮
    'node-styler': (element: D3StylerElement, node: PhylotreeNode & { tag?: boolean }) => {
      if (tree.isLeafNode(node)) {
        const hasQuery = searchKeyword.value.trim().length > 0
        const tagged = node.tag === true
        // tagged 可能来自搜索命中或外部表格选中高亮；均红色加粗
        element.style('opacity', hasQuery && !tagged ? '0.15' : '1')
        element.selectAll('text')
          .style('fill', tagged ? '#f56c6c' : '#222')
          .style('font-weight', tagged ? 'bold' : 'normal')
      } else {
        const color = bootstrapColor(node)
        const circles = element.selectAll('circle')
        circles.style('fill', color ?? '#BBB')
        circles.style('stroke', 'black')
        circles.style('stroke-width', '0.5px')
      }
    },
    'edge-styler': (element: D3StylerElement, edge: PhyloEdge) => {
      const hasQuery = searchKeyword.value.trim().length > 0
      const tagged = edge.tag === true
      element.style('opacity', hasQuery && !tagged ? '0.15' : '1')
      element.style('stroke', tagged ? '#f56c6c' : '#999')
      element.style('stroke-width', tagged ? '3px' : '2px')
    }
  }

  const display = tree.render(renderOptions)

  // 关键：在存进 Vue ref 之前，先用原始 display 对象 patch TreeRender.prototype
  // （Vue ref 会 proxy 对象，但 draw.js 内部持有的是原始 TreeRender 实例）
  const TRProto = Object.getPrototypeOf(display) as Record<string, unknown>
  if (typeof TRProto.unrooted !== 'function') {
    TRProto.unrooted = function (attr?: boolean) {
      if (arguments.length === 0) return (this as any).options['is-unrooted']
      ;(this as any).options['is-unrooted'] = attr
      return this
    }
  }
  if (typeof TRProto.alignTips !== 'function') {
    TRProto.alignTips = function (attr?: boolean) {
      if (arguments.length === 0) return (this as any).options['align-tips']
      ;(this as any).options['align-tips'] = attr
      return this
    }
  }
  if (typeof TRProto.nodeLabel !== 'function') {
    TRProto.nodeLabel = function (attr?: any) {
      if (arguments.length === 0) return (this as any)._nodeLabel
      ;(this as any)._nodeLabel = attr
      return this
    }
  }

  // 修复 phylotree「忽略枝长」(options.scaling=false, cladogram) 时的叶节点对齐 bug。
  // 源码 tree_layout 中：scaling=false 时叶节点 y = this.max_depth（意图让所有叶对齐
  // 到最深位置，即短枝伸长到最右/最外圈），内部节点 y = depth。但 placenodes 在递归
  // 开始前把 this.max_depth 重置为 1，真正的 max_depth 要等整个递归结束后才计算，
  // 导致叶节点递归时误用旧值 1 —— 短枝无法伸长。rect 与 radial 布局均受影响。
  // 包装 tree_layout：根节点进入递归前，预先按可见叶节点算好 max_depth 注入，
  // 这样 _extents / scales / rect 坐标 / radial 半径全部按正确深度计算。
  if (!(TRProto as any).__cladogramMaxDepthPatched) {
    ;(TRProto as any).__cladogramMaxDepthPatched = true
    const origTreeLayout = TRProto.tree_layout as (this: any, node: any) => unknown
    TRProto.tree_layout = function (this: any, a_node: any) {
      if (a_node && !a_node.parent) {
        let md = 0
        this.phylotree.nodes.each((n: any) => {
          const isLeaf = !n.children || n.children.length === 0
          if (isLeaf && !n.hidden && !n.notshown && typeof n.depth === 'number') {
            if (n.depth > md) md = n.depth
          }
        })
        if (md > 0) this.max_depth = md
      }
      return origTreeLayout.call(this, a_node)
    }
  }

  // 首次 render() 在上面的 patch 安装前已完成一次布局；若当前为「忽略枝长」模式，
  // 需用打过补丁的 tree_layout 重新布局，叶节点才能正确对齐到最右/最外圈。
  if (ignoreBranchLength.value) {
    ;(display as any).options['scaling'] = false
    display.update()
  }

  // 现在再存进 Vue ref（prototype 已经 patch 好了）
  treeDisplay.value = display

  // 验证 patch 成功（用原始 display，不经过 ref proxy）
  const d = display as any
  console.log('[Phylo] prototype unrooted:', typeof Object.getPrototypeOf(d).unrooted)
  console.log('[Phylo] display.unrooted (proto lookup):', typeof d.unrooted)

  // 官方 demo 模式: append 游离 SVG
  if (treeContainerRef.value) {
    treeContainerRef.value.innerHTML = ''
    treeContainerRef.value.appendChild(display.show() as unknown as Node)
  }

  // 关键修复：phylotree render() 内部：
  //   1. 给 .phylotree-container 加 baseTransform（居中树）
  //   2. this.svg.call(this.zoomBehavior) 绑定 d3-zoom
  // 但 render 完后 zoom 内部可能有残留 transform → 叠加 baseTransform 后树被截断
  // 用真 d3.zoom 的 programmatic transform 重置到 identity：
  const svgNode = (display.svg as unknown as { node: () => SVGSVGElement }).node()
  console.log('[Phylo] render post:', { hasSvgNode: !!svgNode, hasZoom: !!d.zoomBehavior, hasTransform: !!d.zoomBehavior?.transform })
  if (svgNode && d.zoomBehavior) {
    try {
      d.currentZoomTransform = null
      d3.select(svgNode).call(d.zoomBehavior.transform, d3.zoomIdentity)
      console.log('[Phylo] zoom reset OK')
    } catch (e) {
      console.warn('[Phylo] zoom reset FAILED:', e)
    }
  }

  // 设置默认 nodeLabel（只显示 geneid）和 branchName
  display.nodeLabel((node: PhylotreeNode) => {
    if (tree.isLeafNode(node)) return extractGeneId(node.data.name || '')
    return ''
  })
  ;(tree as unknown as { branchName: (fn: (n: PhylotreeNode) => string) => void }).branchName(
    showBranchLength.value
      ? (node: PhylotreeNode) => (node.data as { bootstrap_values?: string }).bootstrap_values || ''
      : () => ''
  )

  // 把 phylotree 默认间距同步到我们的 state（让数值输入框显示当前值）
  // spacing_x/y 为 getter/setter 方法，无参调用返回当前值；运行时存在但 .d.ts 未声明，用 any 访问
  spacingX.value = Number(d.spacing_x?.call(d) ?? 14)
  spacingY.value = Number(d.spacing_y?.call(d) ?? 30)

  setupLeafInteractions(tree, display)
  setupInternalNodeInteractions(tree, display)
  // 渲染完成后应用一次高亮（搜索关键字 + 外部表格选中基因）
  applyHighlighting()
}

// ==================== 事件委托 ====================
function resolveLeafNode(
  tree: InstanceType<typeof phylotree>,
  target: EventTarget | null
): { el: SVGGElement; node: PhylotreeNode } | null {
  if (!target || !(target instanceof Element)) return null
  const g = target.closest('g.node') as SVGGElement | null
  if (!g) return null
  const node = (g as unknown as { __data__?: PhylotreeNode }).__data__
  if (!node || !tree.isLeafNode(node)) return null
  return { el: g, node }
}

function resolveInternalNode(
  tree: InstanceType<typeof phylotree>,
  target: EventTarget | null
): { el: SVGGElement; node: PhylotreeNode } | null {
  if (!target || !(target instanceof Element)) return null
  const g = target.closest('g.internal-node') as SVGGElement | null
  if (!g) return null
  const node = (g as unknown as { __data__?: PhylotreeNode }).__data__
  if (!node || tree.isLeafNode(node)) return null
  return { el: g, node }
}

function setupLeafInteractions(tree: InstanceType<typeof phylotree>, _display: any) {
  const container = treeContainerRef.value
  if (!container) return
  leafEventsAbort?.abort()
  leafEventsAbort = new AbortController()
  const opts: AddEventListenerOptions = { signal: leafEventsAbort.signal }

  container.addEventListener('click', (e: MouseEvent) => {
    const target: EventTarget | null = e.target
    const r = resolveLeafNode(tree, target)
    if (!r) return
    e.stopPropagation()
    const geneId = extractGeneId(r.node.data.name || r.el.getAttribute('data-node-name') || '')
    if (!geneId) return
    selectedNodeName.value = geneId
    detailNode.value = { geneId }
  }, opts)

  container.addEventListener('mouseover', (e: MouseEvent) => {
    const target: EventTarget | null = e.target
    const r = resolveLeafNode(tree, target)
    if (!r) return
    const raw = r.node.data.name || r.el.getAttribute('data-node-name') || ''
    tooltipText.value = extractGeneId(raw)
    tooltipVisible.value = true
    updateTooltip(e)
  }, opts)

  container.addEventListener('mousemove', (e: MouseEvent) => {
    if (tooltipVisible.value) updateTooltip(e)
  }, opts)

  container.addEventListener('mouseout', (e: MouseEvent) => {
    const r = resolveLeafNode(tree, e.target)
    if (!r) return
    const rel = e.relatedTarget as Element | null
    if (!rel || !r.el.contains(rel)) tooltipVisible.value = false
  }, opts)
}

function setupInternalNodeInteractions(tree: InstanceType<typeof phylotree>, _display: any) {
  const container = treeContainerRef.value
  if (!container) return
  const opts: AddEventListenerOptions = { signal: leafEventsAbort?.signal }

  container.addEventListener('dblclick', (e: MouseEvent) => {
    const target: EventTarget | null = e.target
    const r = resolveInternalNode(tree, target)
    if (!r) return
    e.stopPropagation()
    treeToggleCollapse(tree, r.node)
    collapsedCount.value = countCollapsed(tree)
    treeDisplay.value?.update()
  }, opts)

  container.addEventListener('contextmenu', (e: MouseEvent) => {
    const target: EventTarget | null = e.target
    const r = resolveInternalNode(tree, target)
    if (!r) return
    e.preventDefault()
    tree.reroot(r.node)
    treeDisplay.value?.update()
  }, opts)
}

function countCollapsed(tree: InstanceType<typeof phylotree>): number {
  const root = tree.nodes as unknown as PhylotreeNode & { children?: PhylotreeNode[]; collapsed?: boolean }
  if (!root) return 0
  let n = 0
  const walk = (node: PhylotreeNode & { children?: PhylotreeNode[]; collapsed?: boolean }) => {
    if (node.collapsed) n++
    node.children?.forEach(walk)
  }
  walk(root)
  return n
}

function updateTooltip(event: MouseEvent) {
  tooltipX.value = event.clientX + 12
  tooltipY.value = event.clientY - 12
}

// ==================== 树操作 ====================
function resetAndRender() {
  if (!lastNewick.value) return
  treeLoading.value = true
  treeError.value = ''
  try {
    renderTree(lastNewick.value)
  } catch (err: any) {
    treeError.value = err.message || t('tree_parse_error')
    console.error(err)
  } finally {
    treeLoading.value = false
  }
}

function onLayoutChange() {
  const d = treeDisplay.value
  if (!d) return
  const dAny = d as any
  const mode = layoutMode.value

  // 官方写法：设置 options 后 update()，placenodes 内部根据
  // this.unrooted() / this.radial() 选择布局分支
  dAny.options['is-radial'] = (mode === 'radial')
  dAny.options['is-unrooted'] = (mode === 'unrooted')
  if (typeof dAny.radial === 'function') dAny.radial(mode === 'radial')
  if (typeof dAny.unrooted === 'function') dAny.unrooted(mode === 'unrooted')

  // 关键：radial 分支的 placenodes 会把 this.size 改写成 ≈ 直径的值并残留，
  // 导致下次切换后 fit-to-size 在缩小后的 size 里布局（树变小）。
  // 每次切换前重置 size 为初始画布尺寸。
  if (mode === 'radial') {
    // 径向半径 ≈ 角度跨度/2π，跨度由 fit-to-size 的 size[0] 决定；
    // 放大 size[0] 让半径 ≈ 画布高的一半，径向树撑满容器
    dAny.size = [dAny.height * 3, dAny.width]
  } else {
    dAny.size = [dAny.height, dAny.width]
  }

  d.update()

  // 布局切换后坐标全变，zoom 归零让树重新居中
  const svgNode = (d.svg as unknown as { node: () => SVGSVGElement }).node()
  if (svgNode && d.zoomBehavior) {
    d.currentZoomTransform = null
    d3.select(svgNode).call(d.zoomBehavior.transform, d3.zoomIdentity)
  }
  if (mode === 'unrooted') {
    alignRight.value = false
  }
}

function onAlignToggle() {
  const d = treeDisplay.value
  if (!d) return
  d.alignTips(alignRight.value)
  d.update()
}

// 忽略枝长：官方 options["scaling"] 开关
// false 时 tree_layout 用 y = depth（层数）布局，即等长分支的 cladogram
// 比例尺也会自动隐藏（draw_scale_bar = show-scale && do_scaling）
function onIgnoreBranchToggle() {
  const d = treeDisplay.value
  if (!d) return
  const dAny = d as any
  dAny.options['scaling'] = !ignoreBranchLength.value
  // size 重置，避免残留污染（同布局切换逻辑）
  dAny.size = [dAny.height, dAny.width]
  d.update()
  const svgNode = (d.svg as unknown as { node: () => SVGSVGElement }).node()
  if (svgNode && d.zoomBehavior) {
    d.currentZoomTransform = null
    d3.select(svgNode).call(d.zoomBehavior.transform, d3.zoomIdentity)
  }
}

function onBranchLabelToggle() {
  const d = treeDisplay.value
  const tree = treeData.value
  if (!d || !tree) return
  tree.branchName(showBranchLength.value
    ? (node: PhylotreeNode) => (node.data as { bootstrap_values?: string }).bootstrap_values || ''
    : () => '')
  d.update()
}

function onSpacingXChange() {
  const d = treeDisplay.value
  if (!d) return
  const v = Math.max(14, Math.min(100, spacingX.value))
  d.spacing_x?.call(d, v)
  d.update()
}

function onSpacingYChange() {
  const d = treeDisplay.value
  if (!d) return
  const v = Math.max(2, Math.min(100, spacingY.value))
  d.spacing_y?.call(d, v)
  d.update()
}

function treeToggleCollapse(tree: unknown, node: PhylotreeNode) {
  ;(tree as unknown as { toggleCollapse: (n: PhylotreeNode) => void }).toggleCollapse(node)
}

function sortNodes(order: string) {
  const tree = treeData.value
  const d = treeDisplay.value
  if (!tree || !d) return
  console.log('[Phylo] sortNodes called:', order)
  if (order === 'original') {
    tree.resortChildren((a: any, b: any) =>
      // original_child_order 可能在 node 自身也可能在 node.data 上
      (a.original_child_order ?? a.data?.original_child_order ?? 0) -
      (b.original_child_order ?? b.data?.original_child_order ?? 0)
    )
  } else {
    tree.resortChildren((a: any, b: any) => {
      // height/value 是 d3-hierarchy 计算的，直接在 node 上（不是 data 里）
      const v = (b.height - a.height || b.value - a.value)
      return order === 'asc' ? v : -v
    })
  }
  d.update()
  console.log('[Phylo] sortNodes done')
}

function handleReroot(cmd: string) {
  const tree = treeData.value
  const d = treeDisplay.value
  if (!tree || !d) return
  try {
    if (cmd === 'midpoint') {
      const mid = (phylotree as unknown as { computeMidpoint(tree: unknown): { location: PhylotreeNode } })
        .computeMidpoint(tree)
      tree.reroot(mid.location)
    } else if (cmd === 'reset') {
      // reset = 用原始 Newick 重新渲染
      resetAndRender()
      return
    }
    d.update()
  } catch (e: unknown) {
    console.warn('reroot error:', e)
  }
}

// ==================== Zoom（真 d3 API） ====================
function applyZoom(k: number) {
  const svg = getSvgNode()
  const d = treeDisplay.value
  if (!svg || !d?.zoomBehavior) return
  const cur = (svg as unknown as { __zoom?: { k: number; x: number; y: number } }).__zoom
    ?? d3.zoomIdentity
  const newK = Math.max(0.1, Math.min(10, cur.k * k))
  d3.select(svg).call(d.zoomBehavior.transform,
    d3.zoomIdentity.translate(cur.x, cur.y).scale(newK))
}

function zoomIn() { applyZoom(1.2) }
function zoomOut() { applyZoom(1 / 1.2) }

function resetZoom() {
  const svg = getSvgNode()
  const d = treeDisplay.value
  if (!svg || !d?.zoomBehavior) return
  d3.select(svg).call(d.zoomBehavior.transform, d3.zoomIdentity)
}

function fitZoom() {
  resetZoom()
  const d = treeDisplay.value
  if (!d) return
  d.placenodes?.()
  d.update()
}

function getSvgNode(): SVGSVGElement | null {
  return treeContainerRef.value?.querySelector('svg') ?? null
}

// ==================== 搜索 / 高亮 ====================
// 说明：render 选项中 selectable=false（避免与 d3-zoom 拖拽冲突），此时 phylotree 的
// modifySelection() 不会真正写 tag（源码要求 selectable/binary-selectable 才进入打标分支）。
// 因此这里直接遍历节点/连线写入 tag，再 update() 触发 node-styler/edge-styler 重绘。
// tag=true 的叶节点 = 搜索命中 或 外部表格选中高亮；styler 据此着红色加粗。
function applyHighlighting() {
  const tree = treeData.value
  const d = treeDisplay.value
  if (!tree || !d) return
  const kw = searchKeyword.value.trim().toLowerCase()
  const highlightSet = new Set((props.highlightGenes ?? []).map((g) => String(g).toLowerCase()))

  const leafTagged = (node: TaggedNode): boolean => {
    if (!tree.isLeafNode(node)) return false
    const gid = extractGeneId(node.data?.name || '').toLowerCase()
    if (!gid) return false
    if (highlightSet.has(gid)) return true
    if (kw && gid.includes(kw)) return true
    return false
  }

  // 叶节点打 tag
  const nodes = tree.nodes as unknown as NodeCollection
  nodes.each((n: TaggedNode) => { n.tag = leafTagged(n) })
  // 连线 tag 跟随其目标节点（叶边连到叶节点）
  const links = (d as { links?: LinkArray }).links
  if (links && Array.isArray(links)) {
    links.forEach((link) => { link.tag = link.target?.tag === true })
  }

  d.update()
}

function scheduleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(applyHighlighting, 200)
}
function clearSearch() {
  searchKeyword.value = ''
  applyHighlighting()
}

// ==================== Export ====================
function handleExport(cmd: string) {
  if (cmd === 'newick') {
    downloadText(lastNewick.value || '', `${props.category}_${selectedFamily.value}.nwk`, 'text/plain')
    return
  }
  const svgEl = treeContainerRef.value?.querySelector('svg')
  if (!svgEl) return

  const clone = svgEl.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
  const source = new XMLSerializer().serializeToString(clone)

  if (cmd === 'svg') {
    downloadText(source, `${props.category}_${selectedFamily.value}.svg`, 'image/svg+xml')
  } else if (cmd === 'png') {
    svgToPng(source, svgEl.getAttribute('width'), svgEl.getAttribute('height'),
      (url: string) => downloadDataUrl(url, `${props.category}_${selectedFamily.value}.png`))
  }
}

function downloadText(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  downloadDataUrl(url, filename)
  URL.revokeObjectURL(url)
}
function downloadDataUrl(url: string, filename: string) {
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
function svgToPng(svgSource: string, width: string | null, height: string | null, callback: (url: string) => void) {
  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas')
    canvas.width = parseInt(width || '1200', 10)
    canvas.height = parseInt(height || '800', 10)
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0)
    callback(canvas.toDataURL('image/png'))
  }
  img.onerror = () => callback('')
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgSource)
}

// ==================== Detail panel ====================
function goToGeneDetail(geneId: string) {
  router.push({ name: 'idSearchResults', query: { db_id: geneId } })
}

// ==================== 重置 ====================
function resetView() {
  searchKeyword.value = ''
  layoutMode.value = 'rect'
  alignRight.value = true
  showBranchLength.value = false
  resetAndRender()
}

function onFamilyChange() {
  if (selectedFamily.value) loadTree()
}

// ==================== watch + 家族选择 ====================
// 受控模式：外部通过 props.family 指定家族（与页面家族单选同步）；
// 非受控模式：自动选中第一个家族让树能自动加载。
function resolveFamily(): boolean {
  if (props.family) {
    selectedFamily.value = props.family
    return true
  }
  if (displayFamilies.value.length === 0) return false
  const first = displayFamilies.value[0] ?? ''
  if (!selectedFamily.value || !displayFamilies.value.includes(selectedFamily.value)) {
    selectedFamily.value = first
  }
  return !!selectedFamily.value
}

watch(
  () => props.family,
  (f) => {
    if (!f) return
    if (selectedFamily.value !== f) {
      selectedFamily.value = f
      loadTree()
    }
  }
)
watch(
  () => props.genome,
  (g) => {
    if (!g) { destroyTree(); return }
    resolveFamily()
    loadTree()
  }
)
watch(
  () => props.category,
  () => {
    resolveFamily()
    if (selectedFamily.value) loadTree()
    else destroyTree()
  }
)
// 外部表格选中的高亮基因变化时，重新打 tag
watch(
  () => props.highlightGenes,
  () => { applyHighlighting() },
  { deep: true }
)

onMounted(() => {
  if (props.genome) {
    resolveFamily()
    if (selectedFamily.value) loadTree()
  }
})

onBeforeUnmount(() => {
  fetchAbort?.abort()
  leafEventsAbort?.abort()
  if (searchTimer) clearTimeout(searchTimer)
  destroyTree()
})
</script>

<style scoped>
.phylo-tree-viewer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

/* ============ 信息面板 ============ */
.tree-info {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #eef1f5 100%);
  border: 1px solid #ebeef5;
  border-radius: 8px;
  font-size: 13px;
  color: #303133;
}
.info-chip .info-label { color: #909399; margin-right: 4px; }

/* ============ 第一行：家族 + 搜索 + 导出 ============ */
.tree-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  flex-wrap: wrap;
}
.control-group { display: flex; align-items: center; gap: 8px; }
.control-label { font-size: 13px; color: #606266; white-space: nowrap; }
.family-select { width: 220px; }
.search-input { width: 240px; }
.control-spacer { flex: 1; }

/* ============ 工具栏 ============ */
.tree-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #fafbfc;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  flex-wrap: wrap;
}
.toolbar-group { display: flex; align-items: center; gap: 6px; }
.toolbar-label { font-size: 12px; color: #909399; white-space: nowrap; margin-right: 2px; }
.toolbar-switches { gap: 12px; }
.spacing-sub { font-size: 12px; color: #909399; margin: 0 4px; white-space: nowrap; }

/* ============ 引入 phylotree 官方样式 ============ */
/* 从 d:\Users\21023\Downloads\phylotree.js-master\phylotree.js-master\phylotree.css 复制 */
.tree-selection-brush .extent { fill-opacity: .05; stroke: #fff; shape-rendering: crispEdges; }
.tree-scale-bar text { font: sans-serif; }
.tree-scale-bar line, .tree-scale-bar path { fill: none; stroke: #000; shape-rendering: crispEdges; }

.phylo-tree-viewer :deep(.node) { font: 10px sans-serif; }
.phylo-tree-viewer :deep(.node circle),
.phylo-tree-viewer :deep(.node ellipse),
.phylo-tree-viewer :deep(.node rect) { fill: steelblue; stroke: black; stroke-width: 0.5px; }
.phylo-tree-viewer :deep(.internal-node circle),
.phylo-tree-viewer :deep(.internal-node ellipse),
.phylo-tree-viewer :deep(.internal-node rect) { fill: #CCC; stroke: black; stroke-width: 0.5px; }
.phylo-tree-viewer :deep(.node-selected) { fill: #f00 !important; }
.phylo-tree-viewer :deep(.node-collapsed circle),
.phylo-tree-viewer :deep(.node-collapsed ellipse),
.phylo-tree-viewer :deep(.node-collapsed rect) { fill: black !important; }
.phylo-tree-viewer :deep(.node-tagged) { fill: #00f; }
.phylo-tree-viewer :deep(.branch) { fill: none; stroke: #999; stroke-width: 2px; }
.phylo-tree-viewer :deep(.clade) { fill: lightgrey; stroke: #222; stroke-width: 2px; opacity: 0.5; }
.phylo-tree-viewer :deep(.branch-selected) { stroke: #f00 !important; stroke-width: 3px; }
.phylo-tree-viewer :deep(.branch-tagged) { stroke: #00f; stroke-dasharray: 10,5; stroke-width: 2px; }
.phylo-tree-viewer :deep(.branch-tracer) { stroke: #bbb; stroke-dasharray: 3,4; stroke-width: 1px; }
.phylo-tree-viewer :deep(.branch:hover) { stroke-width: 10px; }
.phylo-tree-viewer :deep(.internal-node circle:hover),
.phylo-tree-viewer :deep(.internal-node ellipse:hover),
.phylo-tree-viewer :deep(.internal-node rect:hover) { fill: black; stroke: #CCC; }

/* ============ 树容器 ============ */
.tree-wrapper {
  position: relative;
  width: 100%;
  height: 700px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  overflow: auto;
}
.tree-container { width: 100%; height: 100%; }

/* 树的平移由 d3-zoom 处理：按住鼠标(mousedown)拖动平移、松开(mouseup)即停。
   必须禁止浏览器对 SVG <text> 的原生文本选中——否则按住拖动会选中基因名（蓝色高亮），
   单击也会残留选中焦点态，表现为"点一下就选中"而非"按住才拖动"。 */
.tree-container :deep(svg),
.tree-container :deep(svg text),
.tree-container :deep(svg g),
.tree-container :deep(svg path),
.tree-container :deep(svg circle) {
  -webkit-user-select: none;
  -moz-user-select: none;
  user-select: none;
  -webkit-user-drag: none;
  -webkit-touch-callout: none;
}
/* 按住可拖动的光标反馈：默认抓手，按下时为抓取态 */
.tree-container :deep(svg) { cursor: grab; }
.tree-container :deep(svg:active) { cursor: grabbing; }

/* ============ 状态栏 ============ */
.tree-statusbar {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 8px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 12px;
  color: #909399;
  pointer-events: none;
  background: rgba(255, 255, 255, 0.88);
  padding: 2px 10px;
  border-radius: 4px;
}
.statusbar-selected { color: #f56c6c; font-weight: 600; }
.statusbar-hint { margin-left: auto; }

/* ============ 加载遮罩 ============ */
.tree-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.75);
  color: #606266;
  font-size: 15px;
  z-index: 10;
}

/* ============ Detail panel ============ */
.tree-detail-panel {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 280px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px 14px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.1);
  z-index: 20;
  font-size: 13px;
}
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 8px;
  margin-bottom: 8px;
}
.detail-close { cursor: pointer; color: #909399; }
.detail-row { color: #606266; margin-bottom: 4px; }
.detail-row span { color: #909399; margin-right: 4px; }

/* ============ Tooltip ============ */
.tree-tooltip {
  position: fixed;
  pointer-events: none;
  background: rgba(30, 30, 30, 0.92);
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  white-space: nowrap;
  z-index: 9999;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
}
.tt-row { margin: 2px 0; }
.tt-row span { color: #b5b5b5; margin-right: 4px; }

/* ============ 空状态 ============ */
.tree-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px 20px;
  color: #909399;
  font-size: 15px;
}
.tree-empty { flex-direction: column; gap: 12px; color: #c0c4cc; }
.tree-empty .el-icon { font-size: 48px; }
.tree-error { margin: 4px 0; }

/* ============ 响应式 ============ */
@media (max-width: 768px) {
  .tree-wrapper { height: 560px; }
  .tree-toolbar, .tree-controls { gap: 6px; }
  .family-select, .search-input { width: 100%; }
}
</style>
