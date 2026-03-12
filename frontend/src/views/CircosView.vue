<template>
  <div class="container mt-4">
    <h2 class="mb-3">NG-Circos Viewer</h2>
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
          <span>NG-Circos Example Layout</span>
          <div class="actions">
            <el-button type="primary" size="small" :loading="isRendering" @click="renderCircos">
              Render
            </el-button>
            <el-button size="small" @click="clearChart">
              Clear
            </el-button>
          </div>
        </div>
      </template>
      <div class="tip">
        Tracks are configured based on the NG-Circos documentation pattern:
        <code>BACKGROUND + SNP + SCATTER + LINK + Genome + config</code>.
      </div>
    </el-card>
    <el-card>
      <div id="NGCircos" ref="chartRoot" class="circos-root"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
// 使用相对路径导入，避免TypeScript类型错误
const ngCircosUrl = '/src/assets/js/NGCircos.js'

declare global {
  interface Window {
    NGCircos?: any
    jQuery?: any
  }
}

const chartRoot = ref<HTMLElement | null>(null)
const isRendering = ref(false)
const errorMessage = ref('')

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

const ensureNGCircosLib = async () => {
  if (typeof window.NGCircos === 'function') return
  await ensureScript('ngcircos-jquery', '/src/assets/js/NGCircos/jquery.js')
  await ensureScript('ngcircos-d3v3', '/src/assets/js/NGCircos/d3.js')
  await ensureScript('ngcircos-lib', '/src/assets/js/NGCircos/NGCircos.js')
  await ensureScript('ngcircos-save', '/src/assets/js/NGCircos/saveSvgAsPng.js')
  await ensureScript('ngcircos-crowbar', '/src/assets/js/NGCircos/svg-crowbar.js')
  if (typeof window.NGCircos !== 'function') {
    throw new Error('NG-Circos library is unavailable after script loading.')
  }
}

const buildDemoTracks = () => {
  const genome = [
    ['A01', 112029331],
    ['A02', 106041875],
    ['A03', 116396180],
    ['A04', 85730437],
    ['A05', 115727996],
    ['A06', 128492809]
  ]

  const snpData = [
    { chr: 'A06', pos: 80162862, value: 4.597351e-9 },
    { chr: 'A06', pos: 80382049, value: 2.512427e-18 },
    { chr: 'A06', pos: 82262582, value: 9.473178e-13 },
    { chr: 'A05', pos: 63500441, value: 6.441989e-12 }
  ]

  const scatterData = [
    { chr: 'A01', start: 268599, end: 269169, name: 'Gene_A01_001', des: 'gene' },
    { chr: 'A03', start: 834500, end: 835900, name: 'Gene_A03_009', des: 'gene' }
  ]

  const linkData = [
    {
      fusion: 'A06080162862SNV--Gene_A01_001',
      g1chr: 'A06',
      g1start: 80162862,
      g1end: 80162862,
      g1name: 'A06080162862SNV',
      g2chr: 'A01',
      g2start: 268599,
      g2end: 269169,
      g2name: 'Gene_A01_001'
    },
    {
      fusion: 'A05063500441SNV--Gene_A03_009',
      g1chr: 'A05',
      g1start: 63500441,
      g1end: 63500441,
      g1name: 'A05063500441SNV',
      g2chr: 'A03',
      g2start: 834500,
      g2end: 835900,
      g2name: 'Gene_A03_009'
    }
  ]

  const BACKGROUND01 = [
    'BACKGROUND01',
    {
      BginnerRadius: 140,
      BgouterRadius: 115,
      BgFillColor: '#F2F2F2',
      BgborderColor: '#000',
      BgborderSize: 0.3
    }
  ]

  const SNP01 = [
    'SNP01',
    {
      maxRadius: 138,
      minRadius: 117,
      SNPFillColor: '#9400D3',
      PointType: 'rect',
      circleSize: 2,
      displaySNPAxis: false
    },
    snpData
  ]

  const SCATTER01 = [
    'SCATTER01',
    {
      SCATTERRadius: 155,
      innerCircleSize: 1,
      outerCircleSize: 7,
      innerCircleColor: '#7876B1',
      outerCircleColor: '#7876B1',
      random_data: 0
    },
    scatterData
  ]

  const LINK01 = [
    'LINK01',
    {
      LinkRadius: 115,
      LinkFillColor: '#FF00CC',
      LinkWidth: 1,
      displayLinkAxis: false,
      displayLinkLabel: false
    },
    linkData
  ]

  return { genome, BACKGROUND01, SNP01, SCATTER01, LINK01 }
}

const clearChart = () => {
  if (chartRoot.value) {
    chartRoot.value.innerHTML = ''
  }
}

const renderCircos = async () => {
  isRendering.value = true
  errorMessage.value = ''
  try {
    await ensureNGCircosLib()
    clearChart()

    const { genome, BACKGROUND01, SNP01, SCATTER01, LINK01 } = buildDemoTracks()
    const NGCircos = window.NGCircos as any
    const circos = new NGCircos(
      LINK01,
      BACKGROUND01,
      SNP01,
      SCATTER01,
      [genome],
      {
        target: 'NGCircos',
        svgWidth: 760,
        svgHeight: 620,
        chrPad: 0.04,
        innerRadius: 210,
        outerRadius: 220,
        ARCMouseOnDisplay: true,
        SNPMouseOnDisplay: true,
        LINKMouseOnDisplay: true
      }
    )
    circos.draw_genome(circos.genomeLength)
  } catch (error: any) {
    errorMessage.value = error?.message || 'Failed to render NG-Circos chart.'
  } finally {
    isRendering.value = false
  }
}

onMounted(async () => {
  await renderCircos()
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
}

.tip {
  color: #5f6b7a;
  font-size: 13px;
}

.circos-root {
  min-height: 640px;
  width: 100%;
  overflow: auto;
}
</style>
