<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧栏：文件导入 -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>PhyloTree iTOL Viewer</h3>

          <!-- 进化树文件 -->
          <div class="mt-4">
            <h4 class="sidebar-title"><el-icon class="play-icon"><Document /></el-icon> 进化树文件</h4>
            <div
              class="drop-zone mt-2"
              :class="{ 'is-dragover': draggingField === 'tree' }"
              @dragover.prevent="draggingField = 'tree'"
              @dragleave.prevent="draggingField = ''"
              @drop.prevent="e => onDrop(e, 'tree')"
              @click="treeInput?.click()"
            >
              <el-icon size="24"><UploadFilled /></el-icon>
              <p class="tip">拖入 Newick 文件</p>
              <p class="sub">.nwk / .tree / .txt</p>
              <input ref="treeInput" type="file" accept=".nwk,.tree,.tre,.txt,.newick" hidden @change="e => onFileChange(e, 'tree')" />
            </div>
            <el-tag v-if="treeFileName" type="success" class="mt-2 file-tag" closable @close="clearTree">
              {{ treeFileName }}
            </el-tag>
          </div>

          <!-- iTOL 配色 -->
          <div class="mt-4">
            <h4 class="sidebar-title"><el-icon class="play-icon"><Brush /></el-icon> iTOL 配色（可选）</h4>
            <div
              class="drop-zone mt-2"
              :class="{ 'is-dragover': draggingField === 'color' }"
              @dragover.prevent="draggingField = 'color'"
              @dragleave.prevent="draggingField = ''"
              @drop.prevent="e => onDrop(e, 'color')"
              @click="colorInput?.click()"
            >
              <el-icon size="24"><UploadFilled /></el-icon>
              <p class="tip">拖入 TREE_COLORS 文件</p>
              <p class="sub">iTOL 颜色模板 .txt</p>
              <input ref="colorInput" type="file" accept=".txt,.tsv,.csv" hidden @change="e => onFileChange(e, 'color')" />
            </div>
            <el-tag v-if="colorFileName" type="warning" class="mt-2 file-tag" closable @close="clearColors">
              {{ colorFileName }}
            </el-tag>

            <div v-if="colorLegend.length" class="itol-legend mt-2">
              <div v-for="g in colorLegend" :key="g.label" class="legend-item">
                <span class="legend-swatch" :style="{ background: g.color }" />
                <span>{{ g.label }} ({{ g.count }})</span>
              </div>
            </div>
          </div>

          <!-- 开关 -->
          <div class="mt-4" v-if="newickStr">
            <h4 class="sidebar-title">显示选项</h4>
            <el-checkbox v-model="showBranchLength" class="mt-2" @change="onBranchLabelToggle">显示 bootstrap</el-checkbox>
            <el-checkbox v-model="ignoreBranchLength" class="mt-2" @change="onIgnoreBranchToggle">忽略枝长</el-checkbox>
            <el-checkbox v-model="alignRight" class="mt-2" @change="onAlignToggle">叶标签对齐</el-checkbox>
          </div>
        </div>
      </div>

      <!-- 右侧：树 -->
      <div class="col-md-9">
        <div class="main-content">
          <div class="toolbar" v-if="newickStr">
            <el-radio-group v-model="layoutMode" size="small" @change="onLayoutChange">
              <el-radio-button label="rect">矩形</el-radio-button>
              <el-radio-button label="radial">环形</el-radio-button>
            </el-radio-group>
            <el-divider direction="vertical" />
            <el-button-group>
              <el-button size="small" @click="applyZoom(1.2)">+</el-button>
              <el-button size="small" @click="applyZoom(1 / 1.2)">−</el-button>
              <el-button size="small" @click="resetZoom">重置视图</el-button>
            </el-button-group>
            <el-divider direction="vertical" />
            <el-dropdown trigger="click" @command="handleExport" size="small">
              <el-button size="small">导出<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="svg">SVG</el-dropdown-item>
                  <el-dropdown-item command="png">PNG</el-dropdown-item>
                  <el-dropdown-item command="newick">Newick</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div class="tree-wrapper">
            <div ref="treeContainerRef" id="phylotree-container" class="tree-container" />
            <div v-if="!newickStr" class="empty-hint">
              <el-icon size="56"><DataBoard /></el-icon>
              <p>拖入进化树文件开始</p>
            </div>
            <div v-if="loading" class="tree-mask">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>渲染中...</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container-fluid { padding: 20px; background-color: #f5f5f5; min-height: 100vh; }
.sidebar {
  background-color: white; padding: 20px; border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,.1); height: fit-content;
}
.sidebar h3 { font-size: 1.2rem; font-weight: bold; color: #3a6ea5; }
.sidebar-title {
  font-size: 1rem; font-weight: bold; color: #333; margin-bottom: 0;
  display: flex; align-items: center; gap: 4px;
}
.play-icon { font-size: .8rem; color: #e6a23c; }
.main-content {
  background-color: white; padding: 20px; border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,.1);
}
.toolbar { display: flex; align-items: center; margin-bottom: 12px; gap: 6px; }

.drop-zone {
  border: 2px dashed #b8c7dc; border-radius: 8px;
  padding: 14px 10px; text-align: center; color: #6b7c93;
  transition: all .2s; cursor: pointer;
}
.drop-zone.is-dragover { border-color: #3a6ea5; background: #eef4fb; }
.drop-zone .tip { margin: 6px 0 2px; font-size: .85rem; }
.drop-zone .sub { font-size: .75rem; color: #9aa8b8; margin: 0; }
.file-tag { max-width: 100%; overflow: hidden; text-overflow: ellipsis; }

.itol-legend { font-size: 12px; color: #555; }
.legend-item { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
.legend-swatch {
  width: 14px; height: 14px; border-radius: 3px;
  border: 1px solid rgba(0,0,0,.15); flex: none;
}

/* phylotree 官方样式 */
.tree-selection-brush .extent { fill-opacity: .05; stroke: #fff; shape-rendering: crispEdges; }
.tree-scale-bar text { font: sans-serif; }
.tree-scale-bar line, .tree-scale-bar path { fill: none; stroke: #000; shape-rendering: crispEdges; }

.tree-wrapper {
  position: relative; width: 100%; height: 700px;
  border: 1px solid #ebeef5; border-radius: 8px;
  background: #fff; overflow: auto;
}
.tree-container { width: 100%; height: 100%; }
.tree-container :deep(.node) { font: 10px sans-serif; }
.tree-container :deep(.node circle),
.tree-container :deep(.node ellipse),
.tree-container :deep(.node rect) { fill: steelblue; stroke: black; stroke-width: .5px; }
.tree-container :deep(.internal-node circle),
.tree-container :deep(.internal-node ellipse),
.tree-container :deep(.internal-node rect) { fill: #CCC; stroke: black; stroke-width: .5px; }
.tree-container :deep(.branch) { fill: none; stroke: #999; stroke-width: 2px; }
.tree-container :deep(.node-selected) { fill: #f00 !important; }
.tree-container :deep(.branch-selected) { stroke: #f00 !important; stroke-width: 3px; }

.tree-container :deep(svg),
.tree-container :deep(svg text),
.tree-container :deep(svg g),
.tree-container :deep(svg path),
.tree-container :deep(svg circle) {
  -webkit-user-select: none; user-select: none;
}
.tree-container :deep(svg) { cursor: grab; }
.tree-container :deep(svg:active) { cursor: grabbing; }

.empty-hint {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px; color: #c0c4cc;
  pointer-events: none;
}
.tree-mask {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 10px;
  background: rgba(255,255,255,.75); z-index: 10;
}
</style>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import * as d3 from 'd3'
import {
  Document, Brush, UploadFilled, DataBoard, Loading, ArrowDown
} from '@element-plus/icons-vue'
import { phylotree } from 'phylotree'

/* ==================== 状态 ==================== */
const treeInput = ref<HTMLInputElement>()
const colorInput = ref<HTMLInputElement>()
const treeContainerRef = ref<HTMLElement>()
const draggingField = ref<'tree' | 'color' | ''>('')

const treeFileName = ref('')
const colorFileName = ref('')
const newickStr = ref('')
const loading = ref(false)

const layoutMode = ref<'rect' | 'radial'>('rect')
const alignRight = ref(true)
const showBranchLength = ref(false)
const ignoreBranchLength = ref(false)

let tree: any = null          // phylotree 实例
let display: any = null       // TreeRender 实例

/* ==================== iTOL 解析 ==================== */
interface ItolRange {
  nodeId: string
  type: 'range' | 'clade' | 'branch' | 'label' | 'label_background'
  color: string
  label?: string
}

function parseItolTreeColors(content: string): ItolRange[] {
  const lines = content.split(/\r?\n/)
  const dataStart = lines.findIndex(l => l.trim().toUpperCase() === 'DATA')
  if (dataStart === -1) return []
  const result: ItolRange[] = []
  for (const line of lines.slice(dataStart + 1)) {
    const s = line.trim()
    if (!s || s.startsWith('#')) continue
    const fields = s.includes('\t') ? s.split('\t')
      : s.includes(',') ? s.split(',')
      : s.split(/\s+/)
    if (fields.length < 3) continue
    const [nodeId, type, color, label] = fields.map(f => f.trim())
    result.push({
      nodeId,
      type: (type as ItolRange['type']) || 'range',
      color: color.startsWith('#') ? color : `#${color}`,
      label: label || undefined
    })
  }
  return result
}

function extractGeneId(raw: string): string {
  const parts = raw.split('|')
  return parts.length > 1 ? (parts[1] ?? raw) : raw
}

/* ==================== 配色状态 ==================== */
const leafColorMap = ref(new Map<string, { color: string; label: string }>())

// ★ 图例按树叶子顺序（而非 map 任意顺序）聚合
const colorLegend = computed(() => {
  if (!leafColorMap.value.size) return []
  const agg = new Map<string, { color: string; count: number }>()
  if (tree) {
    (tree.nodes as any).each?.((n: any) => {
      if (!tree.isLeafNode(n)) return
      const name = String(n.data?.name ?? '')
      const v = leafColorMap.value.get(name)
        ?? leafColorMap.value.get(extractGeneId(name))
      if (!v) return
      const key = v.label || v.color
      const cur = agg.get(key)
      if (cur) cur.count++
      else agg.set(key, { color: v.color, count: 1 })
    })
  }
  // 树未渲染时退回原逻辑
  if (!agg.size) {
    for (const { color, label } of leafColorMap.value.values()) {
      const key = label || color
      const cur = agg.get(key)
      if (cur) cur.count++
      else agg.set(key, { color, count: 1 })
    }
  }
  return [...agg.entries()].map(([label, v]) => ({ label, ...v }))
})

/* =================★ 恢复 Newick 原始叶子顺序 ==================== */
function restoreOriginalOrder() {
  if (!tree || !display) return
  // original_child_order 记录解析时的原始位置，兼容 node / node.data 两种位置
  tree.resortChildren((a: any, b: any) =>
    (a.original_child_order ?? a.data?.original_child_order ?? 0) -
    (b.original_child_order ?? b.data?.original_child_order ?? 0)
  )
}

/* ==================== 文件读取 ==================== */
async function onDrop(e: DragEvent, field: 'tree' | 'color') {
  draggingField.value = ''
  await readFile(e.dataTransfer?.files?.[0], field)
}

function onFileChange(e: Event, field: 'tree' | 'color') {
  const el = e.target as HTMLInputElement
  readFile(el.files?.[0], field)
  el.value = ''
}

async function readFile(file: File | undefined, field: 'tree' | 'color') {
  if (!file) return
  const text = await file.text()
  if (field === 'tree') {
    const trimmed = text.trim()
    if (!trimmed.includes('(') || !trimmed.includes(';')) {
      ElMessage.error('不是有效的 Newick 文件')
      return
    }
    newickStr.value = trimmed
    treeFileName.value = file.name
    ElMessage.success(`进化树已加载: ${file.name}`)
    await renderTree(trimmed)
  } else {
    const ranges = parseItolTreeColors(text)
    if (!ranges.length) {
      ElMessage.warning('未解析到有效配色数据（缺少 DATA 段）')
      return
    }
    colorFileName.value = file.name
    const m = new Map<string, { color: string; label: string }>()
    for (const r of ranges) {
      if (r.type !== 'branch' && r.type !== 'clade') {
        m.set(r.nodeId, { color: r.color, label: r.label ?? '' })
      }
    }
    leafColorMap.value = m
    ElMessage.success(`已加载 ${ranges.length} 条配色`)
    applyColorsToDom()
  }
}

function clearColors() {
  leafColorMap.value = new Map()
  colorFileName.value = ''
  applyColorsToDom(true)
}

function clearTree() {
  newickStr.value = ''
  treeFileName.value = ''
  tree = null
  display = null
  if (treeContainerRef.value) treeContainerRef.value.innerHTML = ''
}

/* ==================== 渲染 ==================== */
async function renderTree(newick: string) {
  loading.value = true
  if (treeContainerRef.value) treeContainerRef.value.innerHTML = ''
  tree = null
  display = null

  try {
    tree = new phylotree(newick)
  } catch {
    ElMessage.error('Newick 解析失败')
    loading.value = false
    return
  }

  const isRadial = layoutMode.value === 'radial'

  try {
    display = tree.render({
      container: '#phylotree-container',
      width: 1600,
      height: 700,
      // @ts-expect-error 运行时支持
      'left-right-spacing': 'fit-to-size',
      // @ts-expect-error 运行时支持
      'top-bottom-spacing': 'fit-to-size',
      'align-tips': !isRadial && alignRight.value,
      'show-scale': !isRadial,
      'is-radial': isRadial,
      'is-unrooted': false,
      // @ts-expect-error 运行时支持
      'scaling': !ignoreBranchLength.value,
      'show-labels': true,
      'font-size': 12,
      zoom: true,
      selectable: false,
      collapsible: true,
      'node-styler': (element: any, node: any) => {
        if (!tree.isLeafNode(node)) {
          const raw = node.data?.bootstrap_values
          const bs = parseFloat(raw ?? '')
          const color = isNaN(bs) || bs <= 0 ? '#BBB'
            : bs >= 95 ? '#4caf50' : bs >= 80 ? '#ff9800' : '#9e9e9e'
          element.selectAll('circle').style('fill', color)
          element.selectAll('circle').style('stroke', 'black')
          element.selectAll('circle').style('stroke-width', '0.5px')
        }
      }
    })
  } catch (err) {
    console.error(err)
    ElMessage.error('树渲染失败')
    loading.value = false
    return
  }

  // ===== prototype patch =====
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
  // cladogram 叶对齐 bug 修复
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

  if (ignoreBranchLength.value) {
    display.options['scaling'] = false
    display.update()
  }

  // ===== append 到容器 =====
  if (treeContainerRef.value) {
    treeContainerRef.value.innerHTML = ''
    treeContainerRef.value.appendChild(display.show() as unknown as Node)
  }

  // ===== zoom 重置 =====
  const d = display as any
  const svgNode = (d.svg as unknown as { node: () => SVGSVGElement }).node()
  if (svgNode && d.zoomBehavior) {
    try {
      d.currentZoomTransform = null
      d3.select(svgNode).call(d.zoomBehavior.transform, d3.zoomIdentity)
    } catch (e) {
      console.warn('zoom reset failed:', e)
    }
  }

  // nodeLabel：叶子只显示 geneId
  display.nodeLabel((node: any) =>
    tree.isLeafNode(node) ? extractGeneId(node.data?.name || '') : '')
  // branchName：bootstrap
  ;(tree as any).branchName(
    showBranchLength.value
      ? (n: any) => n.data?.bootstrap_values || ''
      : () => ''
  )
  // ★ 恢复 Newick 原始叶子顺序后再重绘
  restoreOriginalOrder()
  display.update()

  applyColorsToDom()
  loading.value = false
}

/* ==================== DOM 着色 ==================== */
let observer: MutationObserver | null = null
let applyTimer: ReturnType<typeof setTimeout> | null = null

function scheduleApply() {
  if (applyTimer) clearTimeout(applyTimer)
  applyTimer = setTimeout(() => applyColorsToDom(), 100)
}

function applyColorsToDom(reset = false) {
  const svg = treeContainerRef.value?.querySelector('svg')
  if (!svg) return

  if (reset || !leafColorMap.value.size) {
    svg.querySelectorAll<SVGGElement>('g.node').forEach(g => {
      const text = g.querySelector('text')
      if (text) { text.style.fill = ''; text.style.fontWeight = '' }
    })
    return
  }

  const byLeaf = new Map<string, string>()
  for (const [name, v] of leafColorMap.value) {
    for (const k of [name.trim().toLowerCase(), extractGeneId(name).trim().toLowerCase()]) {
      if (!byLeaf.has(k)) byLeaf.set(k, v.color)
    }
  }

  svg.querySelectorAll<SVGGElement>('g.node').forEach(g => {
    const data = (g as any).__data__
    const rawName = String(data?.name ?? data?.data?.name ?? '')
    if (!rawName) return
    const k = rawName.trim().toLowerCase()
    const color = byLeaf.get(k) ?? byLeaf.get(extractGeneId(rawName).trim().toLowerCase())
    if (!color) return
    const text = g.querySelector('text')
    if (text) { text.style.fill = color; text.style.fontWeight = 'bold' }
  })
}

function setupObserver() {
  if (!treeContainerRef.value) return
  observer?.disconnect()
  observer = new MutationObserver(scheduleApply)
  observer.observe(treeContainerRef.value, { childList: true, subtree: true })
}
setupObserver()

/* ==================== 布局 / 开关 ==================== */
function onLayoutChange() {
  if (!display) return
  const d = display as any
  d.options['is-radial'] = (layoutMode.value === 'radial')
  d.options['is-unrooted'] = false
  if (typeof d.radial === 'function') d.radial(layoutMode.value === 'radial')
  d.size = layoutMode.value === 'radial'
    ? [d.height * 3, d.width]
    : [d.height, d.width]
  restoreOriginalOrder()   // ★
  d.update()
  resetZoom()
}

function onAlignToggle() {
  if (!display) return
  display.alignTips(alignRight.value)
  restoreOriginalOrder()   // ★
  display.update()
}

function onIgnoreBranchToggle() {
  if (!display) return
  const d = display as any
  d.options['scaling'] = !ignoreBranchLength.value
  d.size = [d.height, d.width]
  restoreOriginalOrder()   // ★
  d.update()
  resetZoom()
}

function onBranchLabelToggle() {
  if (!tree || !display) return
  ;(tree as any).branchName(
    showBranchLength.value
      ? (n: any) => n.data?.bootstrap_values || ''
      : () => '')
  display.update()
}

/* ==================== 缩放 ==================== */
function applyZoom(k: number) {
  const svg = treeContainerRef.value?.querySelector('svg')
  if (!svg || !display?.zoomBehavior) return
  const cur = (svg as any).__zoom ?? { k: 1, x: 0, y: 0 }
  const newK = Math.max(0.1, Math.min(10, cur.k * k))
  d3.select(svg).call(display.zoomBehavior.transform,
    d3.zoomIdentity.translate(cur.x, cur.y).scale(newK))
}

function resetZoom() {
  const svg = treeContainerRef.value?.querySelector('svg')
  if (!svg || !display?.zoomBehavior) return
  ;(display as any).currentZoomTransform = null
  d3.select(svg).call(display.zoomBehavior.transform, d3.zoomIdentity)
}

/* ==================== 导出 ==================== */
function handleExport(cmd: string) {
  if (cmd === 'newick') {
    downloadText(newickStr.value, 'tree.nwk', 'text/plain')
    return
  }
  const svgEl = treeContainerRef.value?.querySelector('svg')
  if (!svgEl) return
  const clone = svgEl.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  const source = new XMLSerializer().serializeToString(clone)
  if (cmd === 'svg') {
    downloadText(source, 'tree.svg', 'image/svg+xml')
  } else {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = 1600; canvas.height = 700
      const ctx = canvas.getContext('2d')!
      ctx.fillStyle = '#fff'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0)
      const a = document.createElement('a')
      a.href = canvas.toDataURL('image/png')
      a.download = 'tree.png'
      a.click()
    }
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(source)
  }
}

function downloadText(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  if (applyTimer) clearTimeout(applyTimer)
  display = null
  tree = null
})
</script>
