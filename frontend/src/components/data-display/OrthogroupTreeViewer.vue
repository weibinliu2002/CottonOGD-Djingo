<template>
  <div class="ortho-tree-viewer">
    <!-- 控制栏 -->
    <div class="tree-controls">
      <el-radio-group v-model="layoutMode" size="small" @change="renderTree(lastNewick)">
        <el-radio-button label="rect">{{ t('rectangular') }}</el-radio-button>
        <el-radio-button label="radial">{{ t('radial') }}</el-radio-button>
        <el-radio-button label="unrooted">{{ t('unrooted') }}</el-radio-button>
      </el-radio-group>
      <el-button-group>
        <el-tooltip content="+" placement="top">
          <el-button size="small" :icon="ZoomIn" @click="zoomBy(1.3)" />
        </el-tooltip>
        <el-tooltip content="−" placement="top">
          <el-button size="small" :icon="ZoomOut" @click="zoomBy(1 / 1.3)" />
        </el-tooltip>
        <el-tooltip :content="t('tree_reset')" placement="top">
          <el-button size="small" :icon="RefreshRight" @click="resetZoom" />
        </el-tooltip>
      </el-button-group>
      <el-checkbox v-model="alignRight" :disabled="layoutMode === 'unrooted'" size="small" @change="renderTree(lastNewick)">
        {{ t('tree_align_tips') }}
      </el-checkbox>
      <el-checkbox v-model="ignoreBranchLength" size="small" @change="renderTree(lastNewick)">
        {{ t('tree_ignore_branch_length') }}
      </el-checkbox>
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
    </div>

    <el-alert v-if="treeError" type="error" :title="treeError" show-icon :closable="false" class="mb-4" />

    <div ref="treeWrapperRef" class="tree-wrapper">
      <div ref="treeContainerRef" class="tree-container" />
      <div v-if="treeLoading" class="tree-mask">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ t('loading_tree') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Orthogroup 基因树查看器（复用 PhyloTreeViewer 的 phylotree 渲染管线）。
 * 输入：newick 字符串（由父组件经 getOrthogroupTree 拉取后传入）。
 * 支持矩形 / 放射 / 无根三种布局、缩放、叶对齐、忽略枝长、SVG/PNG/Newick 导出。
 */
import { ref, watch, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { phylotree } from 'phylotree'
import * as d3 from 'd3'
import {
  Loading, ZoomIn, ZoomOut, RefreshRight, Download, ArrowDown,
} from '@element-plus/icons-vue'
import type { RenderOptions } from 'phylotree'

const props = defineProps<{ newick: string }>()
const { t } = useI18n()

const treeWrapperRef = ref<HTMLElement | null>(null)
const treeContainerRef = ref<HTMLElement | null>(null)
const layoutMode = ref<'rect' | 'radial' | 'unrooted'>('rect')
const alignRight = ref(true)
const ignoreBranchLength = ref(false)
const treeLoading = ref(false)
const treeError = ref('')
const treeData = ref<InstanceType<typeof phylotree> | null>(null)
const lastNewick = ref('')
let display: any = null

function destroyTree(): void {
  if (treeContainerRef.value) treeContainerRef.value.innerHTML = ''
  treeData.value = null
  display = null
}

function renderTree(newickStr: string): void {
  if (!newickStr) return
  destroyTree()
  let tree: InstanceType<typeof phylotree>
  try {
    tree = new phylotree(newickStr)
  } catch {
    treeError.value = t('tree_parse_error')
    return
  }
  treeData.value = tree
  const isUnrooted = layoutMode.value === 'unrooted'
  const isLeafAlign = !isUnrooted && alignRight.value

  const renderOptions: RenderOptions = {
    container: '#ortho-tree-container',
    width: 1600,
    height: 700,
    // @ts-expect-error v2.6.0 运行时支持但类型未声明
    'left-right-spacing': 'fit-to-size',
    // @ts-expect-error 同上
    'top-bottom-spacing': 'fit-to-size',
    'align-tips': isLeafAlign,
    'show-scale': !isUnrooted,
    'is-radial': layoutMode.value === 'radial',
    'is-unrooted': isUnrooted,
    'scaling': !ignoreBranchLength.value,
    'show-labels': true,
    'font-size': 12,
    zoom: true,
    selectable: false,
    collapsible: true,
  }

  display = tree.render(renderOptions)

  // cladogram 叶节点对齐修复（同 PhyloTreeViewer）
  const TRProto = Object.getPrototypeOf(display) as Record<string, unknown>
  if (!(TRProto as any).__cladogramMaxDepthPatched) {
    ;(TRProto as any).__cladogramMaxDepthPatched = true
    const orig = TRProto.tree_layout as (this: any, node: any) => unknown
    TRProto.tree_layout = function (this: any, a_node: any) {
      if (a_node && !a_node.parent) {
        let md = 0
        this.phylotree.nodes.each((n: any) => {
          const isLeaf = !n.children || n.children.length === 0
          if (isLeaf && !n.hidden && !n.notshown && typeof n.depth === 'number' && n.depth > md) md = n.depth
        })
        if (md > 0) this.max_depth = md
      }
      return orig.call(this, a_node)
    }
  }
  if (ignoreBranchLength.value) {
    display.options['scaling'] = false
    display.update()
  }

  // 容器需唯一 id（与 renderOptions.container 一致）
  if (treeContainerRef.value) {
    treeContainerRef.value.id = 'ortho-tree-container'
    treeContainerRef.value.innerHTML = ''
    treeContainerRef.value.appendChild(display.show() as unknown as Node)
  }
  // 重置 d3-zoom 到 identity，避免残留 transform 截断树
  const svgNode = display.svg?.node?.()
  if (svgNode && display.zoomBehavior) {
    try {
      display.currentZoomTransform = null
      d3.select(svgNode).call(display.zoomBehavior.transform, d3.zoomIdentity)
    } catch { /* noop */ }
  }
}

function zoomBy(factor: number): void {
  const svgNode = display?.svg?.node?.()
  if (!svgNode || !display?.zoomBehavior) return
  try {
    d3.select(svgNode).transition().duration(150)
      .call(display.zoomBehavior.scaleBy, factor)
  } catch { /* noop */ }
}
function resetZoom(): void {
  const svgNode = display?.svg?.node?.()
  if (!svgNode || !display?.zoomBehavior) return
  try {
    d3.select(svgNode).call(display.zoomBehavior.transform, d3.zoomIdentity)
  } catch { /* noop */ }
}

function handleExport(cmd: string): void {
  if (!display) return
  if (cmd === 'newick') {
    downloadText(lastNewick.value || '', `${props.newick.slice(0, 0) || 'orthogroup'}.nwk`, 'text/plain')
    return
  }
  const svgNode = display.svg?.node?.() as SVGSVGElement | undefined
  if (cmd === 'svg' && svgNode) {
    const source = new XMLSerializer().serializeToString(svgNode)
    downloadText(source, 'orthogroup_tree.svg', 'image/svg+xml')
  } else if (cmd === 'png' && svgNode) {
    const source = new XMLSerializer().serializeToString(svgNode)
    const url = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(source)
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = svgNode.width.baseVal.value || 1600
      canvas.height = svgNode.height.baseVal.value || 700
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.fillStyle = '#fff'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0)
      downloadDataUrl(canvas.toDataURL('image/png'), 'orthogroup_tree.png')
    }
    img.src = url
  }
}

watch(
  () => props.newick,
  (val) => {
    lastNewick.value = val || ''
    treeError.value = ''
    if (val) renderTree(val)
    else destroyTree()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  destroyTree()
})

function downloadText(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  downloadDataUrl(url, filename)
  URL.revokeObjectURL(url)
}
function downloadDataUrl(url: string, filename: string): void {
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
</script>

<style scoped>
.ortho-tree-viewer {
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 1rem;
  background: #fff;
}
.tree-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.control-spacer {
  flex: 1;
}
.tree-wrapper {
  position: relative;
  height: 700px;
  overflow: hidden;
  background: #fff;
}
.tree-container {
  width: 100%;
  height: 100%;
}
.tree-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.7);
  color: #6c757d;
}
.mb-4 {
  margin-bottom: 1rem;
}
</style>
