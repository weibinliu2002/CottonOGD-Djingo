<template>
  <div class="phylo-tree-viewer">
    <!-- ========== 1. 信息面板 ========== -->
    <div v-if="lastNewick" class="tree-info">
      <div v-if="!directNewickMode" class="info-chip"><span class="info-label">{{ t('family') }}:</span> {{ selectedFamily }}</div>
      <div v-if="!directNewickMode && props.category" class="info-chip"><span class="info-label">{{ t('category') }}:</span> {{ props.category }}</div>
      <div v-if="!directNewickMode && props.genome" class="info-chip"><span class="info-label">{{ t('genome') }}:</span> {{ props.genome }}</div>
      <div class="info-chip"><span class="info-label">{{ t('tree_sequences') }}:</span> {{ leafCount }}</div>
      <div class="info-chip renderer-chip">Phylocanvas.gl (WebGL)</div>
    </div>

    <!-- ========== 2. 顶部控制栏 ========== -->
    <div class="tree-controls">
      <div class="control-group" v-if="!props.family && !directNewickMode">
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
        v-if="lastNewick"
        :placeholder="t('tree_search_placeholder')"
        clearable
        size="small"
        class="search-input"
        :prefix-icon="Search"
        @input="scheduleSearch"
        @clear="clearSearch"
      />
      <div class="control-spacer" />
      <el-dropdown trigger="click" @command="handleExport" size="small" :disabled="!lastNewick">
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
        <el-button size="small" :icon="RefreshLeft" @click="resetView" :disabled="!lastNewick" />
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
    <div v-else-if="!lastNewick && !treeLoading" class="tree-status tree-empty">
      <el-icon><DataBoard /></el-icon>
      <span>{{ directNewickMode ? t('tree_empty') : t('select_family_first') }}</span>
    </div>

    <!-- ========== 4. 已加载或加载中 ========== -->
    <div v-else class="tree-loaded-area">
      <!-- 操作工具栏 -->
      <div v-if="lastNewick" class="tree-toolbar">
        <!-- 布局（Phylocanvas.gl 支持的 5 种类型） -->
        <div class="toolbar-group">
          <span class="toolbar-label">{{ t('tree_layout') }}</span>
          <el-radio-group v-model="layoutType" size="small" @change="onLayoutChange">
            <el-radio-button value="rc">{{ t('rectangular') }}</el-radio-button>
            <el-radio-button value="rd">{{ t('radial') }}</el-radio-button>
            <el-radio-button value="cr">{{ t('circular') }}</el-radio-button>
            <el-radio-button value="dg">{{ t('diagonal') }}</el-radio-button>
            <el-radio-button value="hr">{{ t('hierarchical') }}</el-radio-button>
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
              <el-button size="small" @click="fitView" :icon="FullScreen" />
            </el-tooltip>
          </el-button-group>
        </div>
        <el-divider direction="vertical" />

        <!-- 间距：映射到库的 branchZoom（枝长方向）/ stepZoom（叶子行距方向） -->
        <div class="toolbar-group">
          <span class="toolbar-label">{{ t('tree_spacing') }}</span>
          <el-tooltip :content="t('tree_spacing_h')" placement="top">
            <el-input-number
              v-model="spacingX"
              size="small"
              :min="40"
              :max="300"
              :step="10"
              :controls="false"
              class="spacing-input"
              @change="onSpacingChange"
            />
          </el-tooltip>
          <span class="spacing-unit">%</span>
          <el-tooltip :content="t('tree_spacing_v')" placement="top">
            <el-input-number
              v-model="spacingY"
              size="small"
              :min="40"
              :max="300"
              :step="10"
              :controls="false"
              class="spacing-input"
              :disabled="!stepSpacingSupported"
              @change="onSpacingChange"
            />
          </el-tooltip>
          <span class="spacing-unit">%</span>
        </div>
        <el-divider direction="vertical" />

        <!-- 排序：按子树规模重排（会重置缩放与间距） -->
        <div class="toolbar-group">
          <span class="toolbar-label">{{ t('tree_sort') }}</span>
          <el-select v-model="sortMode" size="small" class="sort-select" @change="onSortChange">
            <el-option :label="t('tree_sort_original')" value="original" />
            <el-option :label="t('tree_sort_asc')" value="asc" />
            <el-option :label="t('tree_sort_desc')" value="desc" />
          </el-select>
        </div>
        <el-divider direction="vertical" />

        <!-- 框选 -->
        <div class="toolbar-group">
          <el-button
            size="small"
            :type="selectMode ? 'primary' : 'default'"
            :icon="Crop"
            @click="toggleSelectMode"
          >
            {{ selectMode ? t('tree_select_exit') : t('tree_select_mode') }}
          </el-button>
          <el-button size="small" :disabled="!selectedGeneIds.length" @click="clearSelection">
            {{ t('tree_select_clear') }}
          </el-button>
        </div>
        <el-divider direction="vertical" />

        <!-- 显示开关 -->
        <div class="toolbar-group toolbar-switches">
          <el-checkbox size="small" v-model="showInternalLabels" @change="onToggleProp('showInternalLabels')">
            {{ t('tree_show_branch_length') }}
          </el-checkbox>
          <el-checkbox size="small" v-model="showBranchLengths" @change="onToggleProp('showBranchLengths')">
            {{ t('tree_show_branch_lengths') }}
          </el-checkbox>
          <el-checkbox size="small" v-model="alignLabels" @change="onToggleProp('alignLabels')">
            {{ t('tree_align_tips') }}
          </el-checkbox>
          <!-- 忽略枝长：按等长枝渲染（等价于 cladogram），原始枝长保留在 newick 里 -->
          <el-checkbox
            size="small"
            v-model="ignoreBranchLength"
            :disabled="!lastNewick"
            @change="onIgnoreBranchLengthChange"
          >
            {{ t('tree_ignore_branch_length') }}
          </el-checkbox>
        </div>
        <el-divider direction="vertical" />

        <!-- Reroot -->
        <div class="toolbar-group">
          <el-button size="small" @click="midpointRoot" :disabled="!lastNewick">{{ t('tree_reroot_midpoint') }}</el-button>
        </div>
      </div>

      <!-- 树容器：canvas 由 Phylocanvas.gl 创建 -->
      <div ref="treeWrapperRef" class="tree-wrapper">
        <div ref="treeContainerRef" class="tree-container" />
        <!-- bootstrap 支持度圆点：库只支持叶节点 styles，内部节点用 SVG 叠加层绘制 -->
        <svg ref="overlaySvgRef" class="bootstrap-overlay" />
        <!-- 框选层：开启框选时接管指针事件，避免与 deck.gl 的平移冲突 -->
        <div
          v-if="selectMode"
          ref="selectLayerRef"
          class="select-layer"
          @mousedown="onSelectStart"
        >
          <div v-if="selectRect" class="select-rect" :style="selectRectStyle" />
        </div>
        <div v-if="treeLoading" class="tree-mask">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>{{ t('loading_tree') }}</span>
        </div>
        <div v-if="collapsedCount > 0 || selectedNodeName || selectedGeneIds.length" class="tree-statusbar">
          <span v-if="collapsedCount > 0">{{ t('tree_collapsed_count', { n: collapsedCount }) }}</span>
          <span v-if="selectedNodeName" class="statusbar-selected">{{ t('tree_selected') }}: {{ selectedNodeName }}</span>
          <span v-if="selectedGeneIds.length" class="statusbar-selected">
            {{ t('tree_selected_count', { n: selectedGeneIds.length }) }}
          </span>
          <span class="statusbar-hint">{{ selectMode ? t('pcv_hint_select') : t('pcv_hint') }}</span>
        </div>
      </div>

      <!-- Detail panel：点击叶节点后显示 -->
      <transition name="el-fade-in-linear">
        <div v-if="detailNode" class="tree-detail-panel">
          <div class="detail-header">
            <strong>{{ t('tree_selected') }}: {{ detailNode.geneId }}</strong>
            <el-icon class="detail-close" @click="closeDetail"><Close /></el-icon>
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
  </div>
</template>

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
.renderer-chip { margin-left: auto; color: #3a6ea5; font-weight: 600; }

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

/* ============ 树容器 ============ */
.tree-wrapper {
  position: relative;
  width: 100%;
  height: 700px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.tree-container { width: 100%; height: 100%; }
.spacing-input { width: 64px; }
.spacing-unit { font-size: 12px; color: #909399; margin-left: -2px; }
.sort-select { width: 120px; }

/* bootstrap 圆点叠加层：不拦截指针事件 */
.bootstrap-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 2;
}

/* 框选层：开启后才接管指针事件 */
.select-layer {
  position: absolute;
  inset: 0;
  z-index: 3;
  cursor: crosshair;
}
.select-rect {
  position: absolute;
  border: 1px dashed #3a6ea5;
  background: rgba(58, 110, 165, 0.12);
  pointer-events: none;
}

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
  z-index: 5;
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

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
// Phylocanvas.gl 打包为 UMD：用命名空间导入再取属性，避免 cjs-lexer 识别不到命名导出。
// 注意：官方主入口 dist/phylocanvas.js 把 deck.gl 作为外部依赖，与项目已安装的
// deck.gl 8.9 存在静态属性 componentName（只读 getter）冲突，运行时会直接抛错；
// 这里改用包内自带的独立打包版本 dist/bundle.min.js（内联配套 deck.gl）。
import * as phylocanvasPkg from '@phylocanvas/phylocanvas.gl/dist/bundle.min.js'
import {
  Loading, DataBoard, Search, Download, RefreshLeft,
  ArrowDown, ZoomIn, ZoomOut, FullScreen, Close, View, Crop
} from '@element-plus/icons-vue'
import type {
  PhylocanvasGL as PhylocanvasGLInstance,
  PhylocanvasNode,
  PhylocanvasGraph
} from '@phylocanvas/phylocanvas.gl'

// ==================== 运行时取模块成员 ====================
// 默认导出即 PhylocanvasGL 类；TreeTypes 为 5 种布局常量
const PhylocanvasCtor = (phylocanvasPkg as unknown as {
  PhylocanvasGL?: typeof PhylocanvasGLInstance
  default?: typeof PhylocanvasGLInstance
}).PhylocanvasGL ?? (phylocanvasPkg as unknown as { default: typeof PhylocanvasGLInstance }).default

const TreeTypes = (phylocanvasPkg as unknown as {
  TreeTypes?: Record<string, string>
}).TreeTypes ?? {
  Circular: 'cr',
  Diagonal: 'dg',
  Hierarchical: 'hr',
  Radial: 'rd',
  Rectangular: 'rc',
}

// 布局常量 -> 中文标签的键（模板里用 rc/rd/cr/dg/hr 作为 radio 值）
const LAYOUT_KEYS: Record<string, string> = {
  rc: 'Rectangular',
  rd: 'Radial',
  cr: 'Circular',
  dg: 'Diagonal',
  hr: 'Hierarchical',
}

// ==================== 常量 ====================
const TREE_HEIGHT = 700

// ==================== Props ====================
const props = defineProps<{
  /** 基因组模式：从 tf_tree 接口按 genome/category/family 拉取（与 newick 二选一） */
  genome?: string
  category?: 'TF' | 'TR'
  families?: string[]
  /** 受控模式：外部指定家族；提供后隐藏组件内部家族选择器 */
  family?: string
  /** 需要高亮的基因 id 列表 */
  highlightGenes?: string[]
  /** 直接 newick 模式（如 Orthogroup 基因树）：提供后跳过接口拉取，参数与基因组模式一致 */
  newick?: string
}>()

// ==================== Composables ====================
const { t } = useI18n()
const router = useRouter()

// ==================== 硬编码家族（与 PhyloTreeViewer 保持一致的数据源） ====================
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
const layoutType = ref('rc')
const showInternalLabels = ref(false)
const showBranchLengths = ref(false)
const alignLabels = ref(true)
/** 忽略枝长：true 时按等长枝（cladogram）渲染 */
const ignoreBranchLength = ref(false)
const searchKeyword = ref('')
const treeLoading = ref(false)
const treeError = ref('')
const treeContainerRef = ref<HTMLElement | null>(null)
const treeWrapperRef = ref<HTMLElement | null>(null)
const overlaySvgRef = ref<SVGSVGElement | null>(null)
const selectLayerRef = ref<HTMLElement | null>(null)
const lastNewick = ref('')
const leafCount = ref(0)
const collapsedCount = ref(0)
const selectedNodeName = ref('')
const detailNode = ref<{ geneId: string } | null>(null)
/** 单击选中的叶节点基因 id（用于把标签/圆点标红） */
const clickedGeneId = ref('')

// 间距（百分比，100 = 适应容器）：水平对应枝长方向，垂直对应叶子行距方向
const spacingX = ref(100)
const spacingY = ref(100)
const sortMode = ref<'original' | 'asc' | 'desc'>('original')

// 框选
const selectMode = ref(false)
const selectedGeneIds = ref<string[]>([])
const selectRect = ref<{ x: number; y: number; w: number; h: number } | null>(null)

// 圆形/径向布局没有“叶子行距”这个轴，垂直间距禁用
const stepSpacingSupported = computed(() => layoutType.value === 'rc' || layoutType.value === 'dg')
const selectRectStyle = computed(() => {
  const r = selectRect.value
  if (!r) return {}
  return { left: `${r.x}px`, top: `${r.y}px`, width: `${r.w}px`, height: `${r.h}px` }
})

// Phylocanvas.gl 实例（不放进 Vue ref，避免深层 proxy 干扰 deck.gl）
let tree: PhylocanvasGLInstance | null = null
// 已折叠的节点 id 集合（库内部自己维护 collapsedIds，这里镜像一份用于计数）
const collapsedIds = new Set<string>()

// 竞态 / 事件监听清理
let fetchAbort: AbortController | null = null
let eventsAbort: AbortController | null = null
let searchTimer: ReturnType<typeof setTimeout> | null = null
let resizeTimer: ReturnType<typeof setTimeout> | null = null

const displayFamilies = computed(() => {
  if (props.families && props.families.length > 0) return props.families
  if (!props.category) return []
  return props.category === 'TF' ? hardcodedTFFamilies : hardcodedTRFamilies
})

/** 直接 newick 模式（Orthogroup 等）：不走 tf_tree 接口，也不显示家族选择器。
 * 用 `!== undefined` 判断，父组件传空字符串（数据尚未到达）时也应处于该模式 */
const directNewickMode = computed(() => props.newick !== undefined)

// ==================== 工具函数 ====================
function extractGeneId(rawName: string): string {
  const parts = rawName.split('|')
  return parts.length > 1 ? (parts[1] ?? rawName) : rawName
}

// ==================== 销毁 ====================
function destroyTree() {
  eventsAbort?.abort()
  eventsAbort = null
  detailNode.value = null
  selectedNodeName.value = ''
  clickedGeneId.value = ''
  collapsedIds.clear()
  collapsedCount.value = 0
  leafCount.value = 0
  if (tree) {
    try {
      tree.destroy()
    } catch {
      /* 已销毁时忽略 */
    }
    tree = null
  }
  if (treeContainerRef.value) treeContainerRef.value.innerHTML = ''
  // 叠加层由本组件维护，需要单独清理
  overlaySvgRef.value?.replaceChildren()
  selectedGeneIds.value = []
  selectRect.value = null
}

// ==================== 加载 ====================
async function loadTree() {
  // 直接 newick 模式：外部已提供树文本，不请求接口
  if (directNewickMode.value) {
    const n = (props.newick ?? '').trim()
    if (!n) {
      destroyTree()
      return
    }
    treeError.value = ''
    lastNewick.value = n
    // 容器在 lastNewick 为空时未渲染，等 DOM 更新后再建树
    await nextTick()
    renderTree(n)
    return
  }
  if (!props.genome || !selectedFamily.value) return

  fetchAbort?.abort()
  fetchAbort = new AbortController()

  destroyTree()
  treeLoading.value = true
  treeError.value = ''

  try {
    // 家族名含斜杠（如 AUX/IAA）时服务器上的文件名用下划线，直接拼路径会落到 SPA 兜底页
    const familyFile = selectedFamily.value.replace(/\//g, '_')
    const url = `/CottonOGD_api/tf_tree/tree/genome/${encodeURIComponent(props.genome)}/${props.category}/${encodeURIComponent(familyFile)}.treefile`
    const response = await fetch(url, {
      headers: { Accept: 'text/plain' },
      signal: fetchAbort.signal
    })
    if (!response.ok) {
      if (response.status === 404) throw new Error(t('tree_not_found'))
      throw new Error(`HTTP ${response.status}`)
    }
    const newick = (await response.text()).trim()
    if (!newick || newick === ';') throw new Error(t('tree_empty'))

    lastNewick.value = newick
    renderTree(newick)
  } catch (err: any) {
    if (err?.name === 'AbortError') return
    treeError.value = err.message || t('tree_parse_error')
    console.error('Phylocanvas load error:', err)
  } finally {
    treeLoading.value = false
  }
}

// ==================== 渲染 ====================
function renderTree(newickStr: string) {
  destroyTree()
  spacingX.value = 100
  spacingY.value = 100
  sortMode.value = 'original'
  const el = treeContainerRef.value
  if (!el) {
    treeError.value = t('tree_parse_error')
    return
  }

  // 注意：Phylocanvas.gl 会把容器本身写成固定像素宽高，
  // 因此必须量外层 wrapper 的宽度，否则会量到上一次渲染的尺寸
  const width = Math.max(treeWrapperRef.value?.clientWidth || el.clientWidth || 0, 600)
  try {
    tree = new PhylocanvasCtor(el, {
      source: newickStr,
      type: layoutType.value,
      size: { width, height: TREE_HEIGHT },
      showLabels: true,
      showLeafLabels: true,
      showInternalLabels: showInternalLabels.value,
      showBranchLengths: showBranchLengths.value,
      alignLabels: alignLabels.value,
      // 平移/缩放/悬停提示/路径高亮全部交给库内建交互
      interactive: { pan: true, zoom: true, tooltip: true, highlight: true },
      fontSize: 12,
      fontFamily: 'sans-serif',
      // 叶标签文字颜色跟随节点 fillColour（默认 false 时标签恒为 #333，命中高亮只变圆点不显眼）
      styleLeafLabels: true,
      nodeShape: 'circle',
      nodeSize: 12,
      showShapes: true,
      padding: 24
    }, pluginsOf())
  } catch (err) {
    console.error('Phylocanvas render error:', err)
    treeError.value = t('tree_parse_error')
    return
  }

  const graph = tree.getGraphAfterLayout()
  leafCount.value = graph?.root?.totalLeaves ?? countLeaves(graph?.root)

  // 库的平移/缩放最终都会走 setProps -> render，这里挂一层钩子，
  // 每次重绘后同步 bootstrap 叠加层的屏幕坐标
  const nativeRender = tree.render.bind(tree)
  ;(tree as unknown as { render: () => void }).render = () => {
    nativeRender()
    // 同步重画叠加层：rAF 在后台标签页会被节流，导致圆点迟迟不出现
    drawBootstrapOverlay()
  }

  applyStyles()
  bindCanvasEvents(el)
  drawBootstrapOverlay()
}

/** 内置插件：比例尺（与 phylotree 的 scale bar 对应） */
/** 生成“忽略枝长”的 newick：所有分支长度置 0，解析时库会自动走 cladogram 等长分支路径 */
function newickWithoutBranchLengths(newick: string): string {
  // 仅替换冒号后的数字（含科学计数法/负号），不碰标签文本
  return newick.replace(/:\s*-?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?/g, ':0')
}

/** 忽略枝长开关：重建树（source 变化会重置视图状态），并保留排序等状态由 renderTree 归零 */
function onIgnoreBranchLengthChange() {
  if (!lastNewick.value) return
  renderTree(ignoreBranchLength.value ? newickWithoutBranchLengths(lastNewick.value) : lastNewick.value)
}

function pluginsOf(): unknown[] {
  const p = (phylocanvasPkg as unknown as { plugins?: Record<string, unknown> }).plugins
  return p?.scalebar ? [p.scalebar] : []
}

// ==================== bootstrap 支持度着色（内部节点叠加层） ====================
const SVG_NS = 'http://www.w3.org/2000/svg'

/** 与 phylotree.js 版一致：≥95 绿、≥80 橙、其余灰 */
function bootstrapColour(value: number): string {
  if (value >= 95) return '#4caf50'
  if (value >= 80) return '#ff9800'
  return '#9e9e9e'
}

/**
 * 内部节点（含 bootstrap 标签）不属于叶节点，库的 styles 不会作用到它们，
 * 因此用一层不拦截事件的 SVG 覆盖在 WebGL 画布上，按 projectPoint 的屏幕坐标画圆点。
 */
function drawBootstrapOverlay() {
  const svg = overlaySvgRef.value
  if (!svg || !tree) return
  svg.replaceChildren()

  let graph: PhylocanvasGraph
  try {
    graph = tree.getGraphAfterLayout()
  } catch {
    return
  }
  if (!graph?.root) return

  const frag = document.createDocumentFragment()
  const walk = (node: PhylocanvasNode) => {
    if (!node.isLeaf && !node.isHidden && node.name != null) {
      const value = Number.parseFloat(String(node.name))
      if (Number.isFinite(value)) {
        const [cx, cy] = tree!.projectPoint([node.x ?? 0, node.y ?? 0])
        if (Number.isFinite(cx) && Number.isFinite(cy)) {
          const dot = document.createElementNS(SVG_NS, 'circle')
          dot.setAttribute('cx', String(cx))
          dot.setAttribute('cy', String(cy))
          dot.setAttribute('r', '5')
          dot.setAttribute('fill', bootstrapColour(value))
          dot.setAttribute('stroke', '#ffffff')
          dot.setAttribute('stroke-width', '1')
          const title = document.createElementNS(SVG_NS, 'title')
          title.textContent = `bootstrap ${value}`
          dot.appendChild(title)
          frag.appendChild(dot)
        }
      }
    }
    node.children?.forEach(walk)
  }
  walk(graph.root)
  svg.appendChild(frag)
}

function countLeaves(node?: PhylocanvasNode): number {
  if (!node) return 0
  if (!node.children || node.children.length === 0) return 1
  return node.children.reduce((s, c) => s + countLeaves(c), 0)
}

// ==================== 画布事件（点击选中 / 双击折叠） ====================
function bindCanvasEvents(el: HTMLElement) {
  eventsAbort?.abort()
  eventsAbort = new AbortController()
  const opts: AddEventListenerOptions = { signal: eventsAbort.signal }

  el.addEventListener('click', (e: MouseEvent) => {
    const node = pickNodeAt(e)
    if (!node || !node.isLeaf) return
    const geneId = extractGeneId(String(node.label ?? node.id))
    if (!geneId) return
    selectedNodeName.value = geneId
    detailNode.value = { geneId }
    // 单击选中同样标红（与框选/外部高亮共用 styles 通道）
    clickedGeneId.value = geneId
    applyStyles()
  }, opts)

  el.addEventListener('dblclick', (e: MouseEvent) => {
    const node = pickNodeAt(e)
    if (!node || node.isLeaf) return
    e.preventDefault()
    if (collapsedIds.has(node.id)) collapsedIds.delete(node.id)
    else collapsedIds.add(node.id)
    collapsedCount.value = collapsedIds.size
    tree?.collapseNode(node.id)
  }, opts)
}

function pickNodeAt(e: MouseEvent): PhylocanvasNode | null {
  const el = treeContainerRef.value
  if (!el || !tree) return null
  const rect = el.getBoundingClientRect()
  return tree.pickNodeAtCanvasPoint(e.clientX - rect.left, e.clientY - rect.top)
}

// ==================== 样式（叶标签只显示基因 id + 搜索/外部高亮着色） ====================
function applyStyles() {
  if (!tree) return
  let graph: PhylocanvasGraph
  try {
    graph = tree.getGraphAfterLayout()
  } catch {
    return
  }
  if (!graph?.root) return

  const kw = searchKeyword.value.trim().toLowerCase()
  const highlightSet = new Set((props.highlightGenes ?? []).map((g) => String(g).toLowerCase()))
  const selectedSet = new Set(selectedGeneIds.value.map((g) => g.toLowerCase()))
  const styles: Record<string, { label?: string; fillColour?: string; strokeColour?: string }> = {}

  const walk = (node: PhylocanvasNode) => {
    if (node.isLeaf) {
      const raw = String(node.label ?? node.id)
      const geneId = extractGeneId(raw)
      const matched = highlightSet.has(geneId.toLowerCase())
        || (!!kw && geneId.toLowerCase().includes(kw))
        || (!!clickedGeneId.value && geneId.toLowerCase() === clickedGeneId.value.toLowerCase())
      if (selectedSet.has(geneId.toLowerCase())) {
        // 框选结果优先级最高
        styles[node.id] = { label: geneId, fillColour: '#f56c6c', strokeColour: '#f56c6c' }
      } else if (matched) {
        styles[node.id] = { label: geneId, fillColour: '#f56c6c', strokeColour: '#f56c6c' }
      } else if (kw) {
        // 有搜索词时把未命中的叶压暗，突出命中项
        styles[node.id] = { label: geneId, fillColour: '#cccccc', strokeColour: '#cccccc' }
      } else {
        styles[node.id] = { label: geneId }
      }
    }
    node.children?.forEach(walk)
  }
  walk(graph.root)

  tree.setProps({ styles })
}

function scheduleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(applyStyles, 200)
}
function clearSearch() {
  searchKeyword.value = ''
  applyStyles()
}

// ==================== 工具栏操作 ====================
function onLayoutChange() {
  if (!tree) return
  try {
    tree.setTreeType(layoutType.value)
    // 布局切换后重新适配画布，并回到默认间距
    tree.fitInCanvas()
  } catch (e) {
    console.warn('setTreeType error:', e)
  }
  spacingX.value = 100
  spacingY.value = 100
  selectedGeneIds.value = []
  applyStyles()
  drawBootstrapOverlay()
}

function onToggleProp(key: 'showInternalLabels' | 'showBranchLengths' | 'alignLabels') {
  // 模板 v-model 已先更新 ref，这里直接把 ref 值同步给库
  const value = key === 'showInternalLabels'
    ? showInternalLabels.value
    : key === 'showBranchLengths'
      ? showBranchLengths.value
      : alignLabels.value
  tree?.setProps({ [key]: value })
}

/** 间距百分比 -> 库的独立轴缩放（zoom = log2(scale)） */
function onSpacingChange() {
  if (!tree) return
  const bx = Math.log2(spacingX.value / 100)
  const sy = Math.log2(spacingY.value / 100)
  try {
    if (layoutType.value === 'hr') {
      // 层级布局的枝长方向是纵向，屏幕水平间距对应 stepZoom
      tree.setStepZoom(bx)
      tree.setBranchZoom(sy)
    } else {
      tree.setBranchZoom(bx)
      if (stepSpacingSupported.value) tree.setStepZoom(sy)
    }
  } catch (e) {
    console.warn('spacing error:', e)
  }
}

/** 排序会重设 newick（库内部实现），因此缩放/间距/折叠都会被重置 */
function onSortChange() {
  if (!tree) return
  try {
    if (sortMode.value === 'asc') tree.ascendingNodeOrder()
    else if (sortMode.value === 'desc') tree.descendingNodeOrder()
    else tree.setSource(lastNewick.value)
  } catch (e) {
    console.warn('sort error:', e)
  }
  spacingX.value = 100
  spacingY.value = 100
  selectedGeneIds.value = []
  collapsedIds.clear()
  collapsedCount.value = 0
  detailNode.value = null
  applyStyles()
  drawBootstrapOverlay()
}

// ==================== 框选 ====================
let dragAbort: AbortController | null = null

function toggleSelectMode() {
  selectMode.value = !selectMode.value
  if (!selectMode.value) selectRect.value = null
}

function clearSelection() {
  selectedGeneIds.value = []
  applyStyles()
}

function onSelectStart(e: MouseEvent) {
  if (e.button !== 0) return
  const layer = selectLayerRef.value
  if (!layer) return
  e.preventDefault()

  dragAbort?.abort()
  dragAbort = new AbortController()
  const opts: AddEventListenerOptions = { signal: dragAbort.signal }

  const rect = layer.getBoundingClientRect()
  const startX = e.clientX - rect.left
  const startY = e.clientY - rect.top
  const additive = e.ctrlKey || e.metaKey
  const subtractive = e.altKey
  let moved = false

  const onMove = (ev: MouseEvent) => {
    const x = ev.clientX - rect.left
    const y = ev.clientY - rect.top
    if (Math.abs(x - startX) > 3 || Math.abs(y - startY) > 3) moved = true
    selectRect.value = {
      x: Math.min(startX, x),
      y: Math.min(startY, y),
      w: Math.abs(x - startX),
      h: Math.abs(y - startY)
    }
  }

  const onUp = (ev: MouseEvent) => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    const x = ev.clientX - rect.left
    const y = ev.clientY - rect.top
    selectRect.value = null
    if (!moved) return // 单击不触发框选

    const hits = collectLeavesInBox(
      Math.min(startX, x), Math.min(startY, y), Math.max(startX, x), Math.max(startY, y)
    )
    let next: string[]
    if (subtractive) {
      const hitSet = new Set(hits)
      next = selectedGeneIds.value.filter((g) => !hitSet.has(g))
    } else if (additive) {
      next = [...new Set([...selectedGeneIds.value, ...hits])]
    } else {
      next = hits
    }
    selectedGeneIds.value = next
    applyStyles()
  }

  document.addEventListener('mousemove', onMove, opts)
  document.addEventListener('mouseup', onUp, opts)
}

/** 收集矩形（画布 CSS 像素）内的叶节点基因 id */
function collectLeavesInBox(left: number, top: number, right: number, bottom: number): string[] {
  if (!tree) return []
  let graph: PhylocanvasGraph
  try {
    graph = tree.getGraphAfterLayout()
  } catch {
    return []
  }
  if (!graph?.root) return []

  const hits: string[] = []
  const walk = (node: PhylocanvasNode) => {
    if (node.isLeaf) {
      if (!node.isHidden) {
        const [cx, cy] = tree!.projectPoint([node.x ?? 0, node.y ?? 0])
        if (cx >= left && cx <= right && cy >= top && cy <= bottom) {
          const geneId = extractGeneId(String(node.label ?? node.id))
          if (geneId) hits.push(geneId)
        }
      }
      return
    }
    node.children?.forEach(walk)
  }
  walk(graph.root)
  return hits
}

function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (selectMode.value) {
    selectMode.value = false
    selectRect.value = null
  }
  clearSelection()
}

function zoomIn() {
  if (!tree) return
  tree.setZoom(tree.getZoom() + 0.35)
}
function zoomOut() {
  if (!tree) return
  tree.setZoom(tree.getZoom() - 0.35)
}
function fitView() {
  tree?.fitInCanvas()
  spacingX.value = 100
  spacingY.value = 100
  drawBootstrapOverlay()
}
function midpointRoot() {
  if (!tree) return
  try {
    // 库内置中点定根：直接用导出的工具或实例方法
    const anyTree = tree as unknown as { midpointRoot?: () => void }
    anyTree.midpointRoot?.()
    applyStyles()
  } catch (e) {
    console.warn('midpointRoot error:', e)
  }
}

// ==================== 导出 ====================
function handleExport(cmd: string) {
  // 直接 newick 模式（Orthogroup 基因树）用固定文件名
  const filename = directNewickMode.value
    ? 'orthogroup_tree'
    : `${props.category}_${selectedFamily.value}`
  if (cmd === 'newick') {
    // 导出当前排序后的树（未排序时即原始 newick）
    let newick = lastNewick.value
    try {
      newick = tree?.exportNewick() || newick
    } catch {
      /* 回退原始 newick */
    }
    downloadText(newick || '', `${filename}.nwk`, 'text/plain')
    return
  }
  if (!tree) return
  try {
    if (cmd === 'svg') {
      const out = tree.exportSVG(true)
      const blob = out instanceof Blob ? out : new Blob([String(out)], { type: 'image/svg+xml' })
      downloadBlob(blob, `${filename}.svg`)
    } else if (cmd === 'png') {
      const dataUrl = tree.exportPNG()
      if (dataUrl) downloadDataUrl(dataUrl, `${filename}.png`)
    }
  } catch (e) {
    console.warn('export error:', e)
  }
}

function downloadText(content: string, filename: string, mime: string) {
  downloadBlob(new Blob([content], { type: mime }), filename)
}
function downloadBlob(blob: Blob, filename: string) {
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

// ==================== Detail panel ====================
function goToGeneDetail(geneId: string) {
  router.push({ name: 'idSearchResults', query: { db_id: geneId } })
}

/** 关闭详情面板时同时取消单击高亮 */
function closeDetail() {
  detailNode.value = null
  selectedNodeName.value = ''
  clickedGeneId.value = ''
  applyStyles()
}

// ==================== 重置 ====================
function resetView() {
  searchKeyword.value = ''
  layoutType.value = 'rc'
  showInternalLabels.value = false
  showBranchLengths.value = false
  alignLabels.value = true
  ignoreBranchLength.value = false
  selectMode.value = false
  selectedGeneIds.value = []
  if (lastNewick.value) renderTree(lastNewick.value)
}

function onFamilyChange() {
  if (selectedFamily.value) loadTree()
}

// ==================== 自适应窗口 ====================
function onWindowResize() {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    const el = treeContainerRef.value
    if (!tree || !el) return
    try {
      tree.resize(Math.max(treeWrapperRef.value?.clientWidth || el.clientWidth || 0, 600), TREE_HEIGHT)
    } catch {
      /* 忽略 */
    }
  }, 200)
}

// ==================== watch + 家族选择 ====================
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
    if (directNewickMode.value) return
    if (!g) { destroyTree(); return }
    resolveFamily()
    loadTree()
  }
)
watch(
  () => props.category,
  () => {
    if (directNewickMode.value) return
    resolveFamily()
    if (selectedFamily.value) loadTree()
    else destroyTree()
  }
)
watch(
  () => props.highlightGenes,
  () => { applyStyles() },
  { deep: true }
)
// 直接 newick 模式：newick 变化时重新渲染（首次挂载由 onMounted 处理）
watch(
  () => props.newick,
  (n) => {
    if (n === undefined) return
    if (!n || !n.trim()) {
      lastNewick.value = ''
      destroyTree()
      return
    }
    loadTree()
  }
)

onMounted(() => {
  window.addEventListener('resize', onWindowResize)
  window.addEventListener('keydown', onKeydown)
  if (directNewickMode.value) {
    loadTree()
  } else if (props.genome) {
    resolveFamily()
    if (selectedFamily.value) loadTree()
  }
})

onBeforeUnmount(() => {
  fetchAbort?.abort()
  eventsAbort?.abort()
  if (searchTimer) clearTimeout(searchTimer)
  if (resizeTimer) clearTimeout(resizeTimer)
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('keydown', onKeydown)
  dragAbort?.abort()
  dragAbort = null
  destroyTree()
})
</script>
