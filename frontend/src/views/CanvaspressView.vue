<template>
  <div class="container mt-4">
    <h2 class="mb-3">CanvasXpress Integration</h2>

    <el-alert
      v-if="errorMessage"
      type="error"
      :title="errorMessage"
      show-icon
      class="mb-3"
    />

    <el-card class="mb-3">
      <template #header>
        <div class="card-header">
          <span>CanvasXpress Demo</span>
          <div class="actions">
            <el-select v-model="graphType" size="small" style="width: 140px">
              <el-option label="Bar" value="Bar" />
              <el-option label="Line" value="Line" />
            </el-select>
            <el-button type="primary" size="small" :loading="isRendering" @click="renderPlot">
              Render
            </el-button>
            <el-button size="small" @click="clearPlot">
              Clear
            </el-button>
          </div>
        </div>
      </template>
      <div class="tip">
        Based on CanvasXpress integration docs: include CSS + JS, then initialize with
        <code>new CanvasXpress(targetId, data, config)</code>.
      </div>
    </el-card>

    <el-card>
      <div class="canvas-wrap">
        <canvas id="canvasxpress-root" ref="canvasRef" width="900" height="520"></canvas>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

declare global {
  interface Window {
    CanvasXpress?: any
  }
}

const canvasRef = ref<HTMLCanvasElement | null>(null)
const graphType = ref<'Bar' | 'Line'>('Bar')
const isRendering = ref(false)
const errorMessage = ref('')

const ensureCss = (id: string, href: string) => {
  if (document.getElementById(id)) return
  const link = document.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = href
  document.head.appendChild(link)
}

const ensureScript = (id: string, src: string) =>
  new Promise<void>((resolve, reject) => {
    const existing = document.getElementById(id) as HTMLScriptElement | null
    if (existing) {
      if ((existing as any).dataset.loaded === '1') {
        resolve()
        return
      }
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true })
      return
    }

    const script = document.createElement('script')
    script.id = id
    script.src = src
    script.async = true
    script.onload = () => {
      ;(script as any).dataset.loaded = '1'
      resolve()
    }
    script.onerror = () => reject(new Error(`Failed to load ${src}`))
    document.body.appendChild(script)
  })

const ensureCanvasXpress = async () => {
  if (typeof window.CanvasXpress === 'function') return
  ensureCss('canvasxpress-css', 'https://www.canvasxpress.org/dist/canvasXpress.css')
  await ensureScript('canvasxpress-js', 'https://www.canvasxpress.org/dist/canvasXpress.min.js')
  if (typeof window.CanvasXpress !== 'function') {
    throw new Error('CanvasXpress library was not loaded successfully.')
  }
}

const getDemoData = () => ({
  y: {
    vars: ['Gene1'],
    smps: ['Smp1', 'Smp2', 'Smp3', 'Smp4', 'Smp5'],
    data: [[10, 35, 88, 42, 63]]
  }
})

const getDemoConfig = () => ({
  graphType: graphType.value,
  title: `Simple ${graphType.value} graph`,
  graphOrientation: 'vertical',
  showTransition: true,
  theme: 'CanvasXpress'
})

const clearPlot = () => {
  if (!canvasRef.value) return
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
}

const renderPlot = async () => {
  isRendering.value = true
  errorMessage.value = ''
  try {
    await ensureCanvasXpress()
    if (!canvasRef.value) {
      throw new Error('Canvas element not found.')
    }
    clearPlot()
    const CanvasXpress = window.CanvasXpress as any
    new CanvasXpress('canvasxpress-root', getDemoData(), getDemoConfig())
  } catch (error: any) {
    errorMessage.value = error?.message || 'Failed to render CanvasXpress chart.'
  } finally {
    isRendering.value = false
  }
}

onMounted(async () => {
  await renderPlot()
})
</script>

<style scoped>
.container {
  max-width: 1200px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.tip {
  color: #5f6b7a;
  font-size: 13px;
}

.canvas-wrap {
  width: 100%;
  overflow-x: auto;
}
</style>
