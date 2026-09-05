<template>
  <div class="protein-structure-viewer">
    <!-- 工具栏 -->
    <div class="viewer-toolbar">
      <el-radio-group v-model="currentStyle" size="small" @change="updateStyle">
        <el-radio-button label="cartoon">Cartoon</el-radio-button>
        <el-radio-button label="stick">Stick</el-radio-button>
        <el-radio-button label="sphere">Sphere</el-radio-button>
        <el-radio-button label="line">Line</el-radio-button>
        <el-radio-button label="cross">Cross</el-radio-button>
      </el-radio-group>

      <el-radio-group v-model="currentColorScheme" size="small" @change="updateStyle" class="ml-2">
        <el-radio-button label="spectrum">Spectrum</el-radio-button>
        <el-radio-button label="element">Element</el-radio-button>
        <el-radio-button label="ss">Secondary</el-radio-button>
        <el-radio-button label="chain">Chain</el-radio-button>
      </el-radio-group>

      <el-button-group class="ml-2">
        <el-button size="small" :icon="Refresh" @click="resetView" title="Reset" />
        <el-button size="small" :type="spinning ? 'primary' : 'default'" @click="toggleSpin" title="Spin">
          <el-icon><RefreshRight /></el-icon>
        </el-button>
        <el-button size="small" @click="toggleBackground" title="Toggle Background">
          <el-icon><Moon /></el-icon>
        </el-button>
      </el-button-group>
    </div>

    <!-- 3D 渲染容器 -->
    <div class="viewer-container" v-loading="loading" element-loading-text="Loading structure...">
      <div ref="viewerEl" class="viewer-3d"></div>
      <div v-if="error" class="viewer-error">
        <el-alert :title="error" type="error" :closable="false" show-icon />
      </div>
    </div>

    <!-- PDB 信息 -->
    <div v-if="pdbInfo" class="viewer-info">
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="PDB ID">{{ pdbInfo.pdb_id }}</el-descriptions-item>
        <el-descriptions-item label="Chain">{{ pdbInfo.chain || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Description">{{ pdbInfo.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Identity">{{ pdbInfo.identity ? (pdbInfo.identity * 100).toFixed(1) + '%' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="E-value">{{ pdbInfo.evalue ? pdbInfo.evalue.toExponential(2) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="Coverage">{{ pdbInfo.cov_q ? (pdbInfo.cov_q * 100).toFixed(1) + '%' : '-' }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Refresh, RefreshRight, Moon } from '@element-plus/icons-vue'
// 获取本地 3Dmol.js 的 URL
const local3DmolUrl = new URL('../../assets/js/3Dmol.js', import.meta.url).href

interface PdbHitInfo {
  pdb_id: string
  chain?: string
  description?: string
  evalue?: number
  identity?: number
  bitscore?: number
  cov_q?: number
  cov_t?: number
  rank?: number
}

const props = defineProps<{
  pdbId: string
  chain?: string
  hitInfo?: PdbHitInfo
}>()

const viewerEl = ref<HTMLElement>()
const loading = ref(false)
const error = ref('')
const currentStyle = ref('cartoon')
const currentColorScheme = ref('chain')
const spinning = ref(false)
const darkBackground = ref(false)
const pdbInfo = ref<PdbHitInfo | null>(null)

let viewer: any = null
let $3Dmol: any = null
let scriptLoaded = false

/** 动态加载 3Dmol.js（优先本地，其次 CDN） */
async function load3DmolScript(): Promise<void> {
  if (scriptLoaded && (window as any).$3Dmol) {
    $3Dmol = (window as any).$3Dmol
    return
  }

  // 1. 优先从本地 assets 加载（用 script 标签方式，避免 UMD 兼容问题）
  try {
    await loadScript(local3DmolUrl, 'local-3dmol')
    if ((window as any).$3Dmol) {
      $3Dmol = (window as any).$3Dmol
      scriptLoaded = true
      return
    }
  } catch (e) {
    console.warn('Local 3Dmol.js load failed, trying CDN:', e)
  }

  // 2. 从 CDN 加载
  try {
    await loadScript('https://3Dmol.org/build/3Dmol-min.js', 'cdn-3dmol')
    if ((window as any).$3Dmol) {
      $3Dmol = (window as any).$3Dmol
      scriptLoaded = true
      return
    }
  } catch (e) {
    throw new Error('Failed to load 3Dmol.js from both local and CDN')
  }
}

/** 通过 script 标签加载 JS */
function loadScript(src: string, id: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.getElementById(id)) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.id = id
    script.src = src
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`))
    document.head.appendChild(script)
  })
}

/** 从 RCSB 获取 PDB 数据 */
async function fetchPdbData(pdbId: string): Promise<string> {
  const url = `https://files.rcsb.org/download/${pdbId.toUpperCase()}.pdb`
  const resp = await fetch(url)
  if (!resp.ok) {
    throw new Error(`PDB ${pdbId} not found (HTTP ${resp.status})`)
  }
  return resp.text()
}

/** 构建 3Dmol 样式对象 */
function buildStyleObject(): any {
  const style = currentStyle.value
  const scheme = currentColorScheme.value

  if (style === 'cartoon') {
    if (scheme === 'spectrum') return { cartoon: { color: 'spectrum' } }
    if (scheme === 'element') return { cartoon: { colorscheme: 'greenCarbon' } }
    if (scheme === 'ss') return { cartoon: { color: 'secondaryStructure' } }
    if (scheme === 'chain') return { cartoon: { colorscheme: 'chain' } }
  }
  if (style === 'stick') {
    if (scheme === 'spectrum') return { stick: { colorscheme: 'redCarbon' } }
    if (scheme === 'element') return { stick: {} }
    if (scheme === 'ss') return { stick: { color: 'secondaryStructure' } }
    if (scheme === 'chain') return { stick: { colorscheme: 'chain' } }
  }
  if (style === 'sphere') {
    if (scheme === 'spectrum') return { sphere: { colorscheme: 'redCarbon' } }
    if (scheme === 'element') return { sphere: {} }
    if (scheme === 'ss') return { sphere: { color: 'secondaryStructure' } }
    if (scheme === 'chain') return { sphere: { colorscheme: 'chain' } }
  }
  if (style === 'line') {
    return { line: {} }
  }
  if (style === 'cross') {
    return { cross: {} }
  }
  return { cartoon: { color: 'spectrum' } }
}

/** 应用链筛选（如果指定了 chain） */
function getSelectionObject(): any {
  if (props.chain) {
    return { chain: props.chain.toUpperCase() }
  }
  return {}
}

/** 初始化 viewer 并加载 PDB */
async function initViewer() {
  if (!viewerEl.value || !props.pdbId) return

  loading.value = true
  error.value = ''

  try {
    await load3DmolScript()

    // 清理旧 viewer
    if (viewer) {
      viewer.clear()
      viewer = null
    }
    if (viewerEl.value) {
      viewerEl.value.innerHTML = ''
    }

    // 创建 viewer
    const config = {
      backgroundColor: darkBackground.value ? '#1a1a2e' : '#f5f5f5',
      antialias: true,
    }
    viewer = $3Dmol.createViewer(viewerEl.value, config)

    // 获取 PDB 数据
    const pdbData = await fetchPdbData(props.pdbId)

    // 添加模型
    viewer.addModel(pdbData, 'pdb')

    // 应用样式到所有原子
    const styleObj = buildStyleObject()
    viewer.setStyle({}, styleObj)

    viewer.zoomTo()
    viewer.render()

    // 更新信息
    pdbInfo.value = props.hitInfo || { pdb_id: props.pdbId, chain: props.chain }
  } catch (e: any) {
    error.value = e.message || 'Failed to load structure'
    console.error('3Dmol error:', e)
  } finally {
    loading.value = false
  }
}

/** 更新样式（不重新加载 PDB 数据） */
function updateStyle() {
  console.log('updateStyle called:', currentStyle.value, currentColorScheme.value)
  if (!viewer) return
  const styleObj = buildStyleObject()
  // 清除旧样式，应用新样式到所有原子
  viewer.setStyle({}, styleObj)
  viewer.render()
}

/** 重置视图 */
function resetView() {
  if (!viewer) return
  viewer.zoomTo()
  viewer.render()
}

/** 切换旋转 */
function toggleSpin() {
  if (!viewer) return
  spinning.value = !spinning.value
  if (spinning.value) {
    viewer.spin('y', 1)
  } else {
    viewer.spin(false)
  }
}

/** 切换背景色 */
function toggleBackground() {
  darkBackground.value = !darkBackground.value
  if (viewer) {
    viewer.setBackgroundColor(darkBackground.value ? '#1a1a2e' : '#f5f5f5')
    viewer.render()
  }
}

/** 销毁 viewer */
function destroyViewer() {
  if (viewer) {
    viewer.spin(false)
    viewer.clear()
    viewer = null
  }
}

watch(() => props.pdbId, (newId) => {
  if (newId) {
    initViewer()
  }
})

watch(() => props.chain, () => {
  if (viewer && props.pdbId) {
    updateStyle()
    viewer.zoomTo()
    viewer.render()
  }
})

onMounted(() => {
  if (props.pdbId) {
    initViewer()
  }
})

onBeforeUnmount(() => {
  destroyViewer()
})
</script>

<style scoped>
.protein-structure-viewer {
  width: 100%;
}

.viewer-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
}

.ml-2 {
  margin-left: 8px;
}

.viewer-container {
  position: relative;
  width: 100%;
  height: 500px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
}

.viewer-3d {
  width: 100%;
  height: 100%;
}

.viewer-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80%;
  text-align: center;
}

.viewer-info {
  margin-top: 12px;
}
</style>
