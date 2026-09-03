import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { phylotree } from 'phylotree'
import * as d3 from 'd3'
import { Loading, DataBoard, Refresh } from '@element-plus/icons-vue'
import type { PhylotreeNode, PhylotreeLink, RenderOptions } from 'phylotree'<template>
  <div class="phylo-tree-viewer">
    <!-- 控制面板 -->
    <div class="tree-controls">
      <div class="control-group">
        <label class="control-label">{{ t('family') }}</label>
        <el-select
          v-model="selectedFamily"
          filterable
          :placeholder="t('family')"
          @change="onFamilyChange"
          class="family-select"
        >
          <el-option
            v-for="f in displayFamilies"
            :key="f"
            :label="f"
            :value="f"
          />
        </el-select>
      </div>
      <el-button
        v-if="treeData"
        @click="toggleLayout"
        size="small"
        :icon="Refresh"
      >
        {{ isRadial ? t('rectangular') : t('radial') }}
      </el-button>
    </div>

    <!-- 加载状态 -->
    <div v-if="treeLoading" class="tree-status">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>{{ t('loading_tree') }}</span>
    </div>

    <!-- 错误提示 -->
    <el-alert
      v-else-if="treeError"
      type="error"
      :title="treeError"
      show-icon
      :closable="false"
      class="tree-error"
    />

    <!-- 空状态提示 -->
    <div v-else-if="!treeData && !treeLoading" class="tree-status tree-empty">
      <el-icon><DataBoard /></el-icon>
      <span>{{ t('select_family_first') }}</span>
    </div>

    <!-- 树容器 -->
    <div
      ref="treeContainerRef"
      class="tree-container"
      v-show="!treeLoading && !treeError && treeData"
    />

    <!-- 自定义 Tooltip -->
    <div
      ref="tooltipRef"
      class="tree-tooltip"
      v-show="tooltipVisible"
      :style="{ left: tooltipX + 'px', top: tooltipY + 'px' }"
    >
      {{ tooltipText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { phylotree } from 'phylotree'
import * as d3 from 'd3'
import { Loading, DataBoard, Refresh } from '@element-plus/icons-vue'
import type { PhylotreeNode, PhylotreeLink, RenderOptions } from 'phylotree'

// ==================== Props ====================
const props = defineProps<{
  genome: string
  category: 'TF' | 'TR'
  families?: string[]
}>()

// ==================== Composables ====================
const { t } = useI18n()
const router = useRouter()

// ==================== 硬编码家族列表（fallback） ====================
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
const isRadial = ref(false)
const treeLoading = ref(false)
const treeError = ref('')
const treeData = ref<InstanceType<typeof phylotree> | null>(null)
const treeDisplay = ref<any>(null)
const treeContainerRef = ref<HTMLElement | null>(null)

// Tooltip 状态
const tooltipRef = ref<HTMLElement | null>(null)
const tooltipVisible = ref(false)
const tooltipX = ref(0)
const tooltipY = ref(0)
const tooltipText = ref('')

// ==================== 计算属性 ====================
const displayFamilies = computed(() => {
  if (props.families && props.families.length > 0) {
    return props.families
  }
  return props.category === 'TF' ? hardcodedTFFamilies : hardcodedTRFamilies
})

// ==================== 核心方法 ====================

/** 销毁已有树 */
function destroyTree() {
  if (treeContainerRef.value) {
    treeContainerRef.value.innerHTML = ''
  }
  treeData.value = null
  treeDisplay.value = null
}

/** 加载并渲染系统发生树 */
async function loadTree() {
  if (!props.genome || !selectedFamily.value) return

  destroyTree()
  treeLoading.value = true
  treeError.value = ''

  try {
    // 1. 获取 Newick 数据
    const url = `/CottonOGD_api/tf_tree/tree/genome/${props.genome}/${props.category}/${selectedFamily.value}.treefile`
    const response = await fetch(url, { headers: { Accept: 'text/plain' } })

    if (!response.ok) {
      throw new Error(response.status === 404 ? t('tree_not_found') : `HTTP ${response.status}`)
    }

    const newick = await response.text()
    if (!newick || !newick.trim()) {
      throw new Error(t('tree_empty'))
    }

    // 2. 解析 Newick 为树对象
    let tree: InstanceType<typeof phylotree>
    try {
      tree = new phylotree(newick.trim(), { bootstrap_values: true })
    } catch {
      throw new Error(t('tree_parse_error'))
    }

    treeData.value = tree

    // 3. 等待 DOM 更新
    await nextTick()

    if (!treeContainerRef.value) {
      throw new Error('Container not found')
    }

    // 4. 渲染树
    const renderOptions: RenderOptions = {
      container: treeContainerRef.value,
      'left-right-spacing': 'fixed-step',
      'top-bottom-spacing': 'fixed-step',
      'align-tips': true,
      'show-scale': true,
      'is-radial': isRadial.value,
      'show-labels': true,
      'font-size': 12
    }

    const display = tree.render(renderOptions)
    treeDisplay.value = display

    // 5. 叶子节点标签：去掉 genome| 前缀，只显示 geneid
    display.nodeLabel((node: PhylotreeNode) => {
      if (tree.isLeafNode(node)) {
        const rawName = node.data.name || ''
        const parts = rawName.split('|')
        return parts.length > 1 ? parts[1] : rawName
      }
      return ''
    })

    // 6. Bootstrap 值着色
    display.edgeStyler((element: any, link: PhylotreeLink) => {
      const bootstrap = parseFloat(link.target?.data?.attribute || '')
      if (!isNaN(bootstrap) && bootstrap > 0) {
        const color = bootstrap >= 95 ? '#4caf50' : bootstrap >= 80 ? '#ff9800' : '#9e9e9e'
        element.selectAll('circle').style('fill', color)
      }
    })

    // 7. 叶子节点交互：hover tooltip + click 跳转
    setupLeafInteractions(tree, display)

  } catch (err: any) {
    treeError.value = err.message || t('tree_parse_error')
    console.error('PhyloTree load error:', err)
  } finally {
    treeLoading.value = false
  }
}

/** 设置叶子节点交互（hover tooltip + click 跳转） */
function setupLeafInteractions(
  tree: InstanceType<typeof phylotree>,
  display: any
) {
  // 使用 setTimeout 确保 SVG 已挂载到 DOM
  setTimeout(() => {
    try {
      const svg = display.svg
      if (!svg) return

      // 选择所有叶子节点
      svg.selectAll('.phylotree-node').each(function (this: any, node: PhylotreeNode) {
        if (!tree.isLeafNode(node)) return

        const el = d3.select(this)
        const rawName = node.data.name || ''
        const parts = rawName.split('|')
        const geneId = parts.length > 1 ? parts[1] : rawName
        const genomeName = parts.length > 1 ? parts[0] : ''

        // 点击事件 → 跳转到基因详情
        el.on('click', (event: MouseEvent) => {
          event.stopPropagation()
          if (geneId) {
            router.push({
              name: 'idSearchResults',
              query: { db_id: geneId }
            })
          }
        })

        // 鼠标悬停 → tooltip 显示完整标签
        el.on('mouseenter', (event: MouseEvent) => {
          tooltipText.value = genomeName ? `${genomeName} | ${geneId}` : geneId
          tooltipVisible.value = true
          updateTooltipPosition(event)
        })

        el.on('mousemove', (event: MouseEvent) => {
          updateTooltipPosition(event)
        })

        el.on('mouseleave', () => {
          tooltipVisible.value = false
        })

        // 指针样式
        el.style('cursor', 'pointer')
      })
    } catch (err) {
      console.warn('PhyloTree leaf interaction setup error:', err)
    }
  }, 100)
}

/** 更新 tooltip 位置 */
function updateTooltipPosition(event: MouseEvent) {
  tooltipX.value = event.clientX + 12
  tooltipY.value = event.clientY - 12
}

// ==================== 事件处理 ====================

function onFamilyChange() {
  if (selectedFamily.value) {
    loadTree()
  }
}

function toggleLayout() {
  isRadial.value = !isRadial.value
  if (treeDisplay.value) {
    treeDisplay.value.radial(isRadial.value)
    treeDisplay.value.update()
  }
}

// ==================== 监听 genome 变化 ====================
watch(
  () => props.genome,
  (newGenome) => {
    if (newGenome && selectedFamily.value) {
      loadTree()
    } else {
      destroyTree()
    }
    // 重置家族选择
    if (!selectedFamily.value) {
      destroyTree()
    }
  }
)

// ==================== 生命周期 ====================
onBeforeUnmount(() => {
  destroyTree()
})
</script>

<style scoped>
.phylo-tree-viewer {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.tree-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.family-select {
  width: 240px;
}

.tree-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px 20px;
  color: #909399;
  font-size: 15px;
}

.tree-empty {
  flex-direction: column;
  gap: 12px;
  color: #c0c4cc;
}

.tree-empty .el-icon {
  font-size: 48px;
}

.tree-error {
  margin: 12px 0;
}

.tree-container {
  flex: 1;
  width: 100%;
  min-height: 500px;
  overflow: auto;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  position: relative;
}

.tree-container :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}

.tree-container :deep(.phylotree-node text) {
  font-size: 12px;
  fill: #333;
}

.tree-container :deep(.phylotree-branch) {
  stroke: #555;
  stroke-width: 1.2;
}

/* Tooltip 样式 */
.tree-tooltip {
  position: fixed;
  pointer-events: none;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Courier New', monospace;
  white-space: nowrap;
  z-index: 9999;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: opacity 0.15s ease;
}

/* 响应式 */
@media (max-width: 768px) {
  .tree-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .family-select {
    width: 100%;
  }
}
</style>
