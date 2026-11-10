<template>
  <div class="msa-viewer">
    <!-- BioJS msa 老包以 UMD 形式放在 public/msa/，由 <script> 全局加载并挂到 window.msa，
         避免经 Vite ESM 打包老 CommonJS 包导致的兼容问题（与 PPIView 同机制）。
         加载成功则用 window.msa 渲染交互式比对；失败/未就绪则降级为原始 FASTA 文本，保证不白屏。 -->
    <div ref="hostRef" class="msa-viewer__host"></div>
    <pre v-if="fallback" class="og-fasta og-fasta--fallback">{{ fallback }}</pre>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps<{
  /** FASTA 纯文本（需以 '>' 开头） */
  fasta: string
}>()

type MsaConfig = {
  el: HTMLElement
  seqs: MsaSequence[]
  vis: { conserv: boolean; overviewbox: boolean; labels: boolean }
  zoomer: { alignmentWidth: 'auto'; alignmentHeight: number; autoResize: boolean }
  conf: { dropImport: boolean }
}

type MsaSequence = {
  name: string
  seq: string
  id: string | number
  ids: Record<string, string>
  details: Record<string, string>
}

type MsaSeqCollection = {
  pluck: (attribute: string) => unknown[]
}

type MsaLibrary = {
  (config: MsaConfig): { render: () => void }
  io: { fasta: { parse: (fasta: string) => MsaSequence[] } }
  model: { seqcol: { prototype: MsaSeqCollection } }
}

type MsaWindow = Window & { msa?: MsaLibrary }

// 使用 msa 自包含构建（已解压 dist/msa.min.gz.js 得到，内联 Backbone/underscore，
// 避免外部依赖版 dist/msa.js 缺少 _ensureElement 导致渲染失败）
const MSA_JS = '/msa/msa.standalone.js'
const MSA_CSS = '/msa/msa.css'

const hostRef = ref<HTMLElement | null>(null)
const fallback = ref('')
let msaLoadPromise: Promise<boolean> | undefined
let renderVersion = 0
const patchedSeqCollections = new WeakSet<object>()

function clearView(): void {
  if (hostRef.value) hostRef.value.innerHTML = ''
  fallback.value = ''
}

function patchStatsArrayDetection(msaLibrary: MsaLibrary): void {
  const prototype = msaLibrary.model.seqcol.prototype
  if (patchedSeqCollections.has(prototype)) return

  // stat.seqs 0.1.21 mistakes arrays with Array.prototype.at for model collections.
  const originalPluck = prototype.pluck
  prototype.pluck = function (attribute: string): unknown[] {
    const values = originalPluck.call(this, attribute)
    return new Proxy(values, {
      has(target, property) {
        return property === 'at' ? false : Reflect.has(target, property)
      },
    })
  }
  patchedSeqCollections.add(prototype)
}

// 仅加载一次 msa UMD，加载完成后 resolve(true)
function ensureLoaded(): Promise<boolean> {
  if (!document.querySelector('link[data-msa-css]')) {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = MSA_CSS
    link.dataset.msaCss = '1'
    document.head.appendChild(link)
  }
  if ((window as MsaWindow).msa) return Promise.resolve(true)
  if (msaLoadPromise) return msaLoadPromise

  msaLoadPromise = new Promise((resolve) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-msa]')
    const script = existing ?? document.createElement('script')
    let settled = false
    const timer = window.setTimeout(() => finish(false), 10000)

    function finish(loaded: boolean): void {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      const ready = loaded && Boolean((window as MsaWindow).msa)
      if (!ready) msaLoadPromise = undefined
      resolve(ready)
    }

    if (script.dataset.msaState === 'loaded' || script.dataset.msaState === 'error') {
      finish(script.dataset.msaState === 'loaded')
      return
    }

    script.addEventListener(
      'load',
      () => {
        script.dataset.msaState = 'loaded'
        finish(true)
      },
      { once: true },
    )
    script.addEventListener(
      'error',
      () => {
        script.dataset.msaState = 'error'
        finish(false)
      },
      { once: true },
    )
    if (!existing) {
      script.src = MSA_JS
      script.dataset.msa = '1'
      document.head.appendChild(script)
    }
  })

  return msaLoadPromise
}

async function renderMsa(fasta: string): Promise<void> {
  const version = ++renderVersion
  const host = hostRef.value
  if (!host) return
  clearView()
  if (!fasta.trim()) return
  if (!fasta.trimStart().startsWith('>')) {
    fallback.value = fasta
    return
  }

  const ok = await ensureLoaded()
  if (version !== renderVersion) return
  const msaLibrary = (window as MsaWindow).msa
  if (!ok || !msaLibrary) {
    fallback.value = fasta
    return
  }
  try {
    const seqs = msaLibrary.io.fasta.parse(fasta.trim().replace(/\r/g, '')).map(
      ({ name, seq, id, ids, details }) => ({ name, seq, id, ids, details }),
    )
    if (seqs.length === 0) {
      fallback.value = fasta
      return
    }
    patchStatsArrayDetection(msaLibrary)
    const inst = msaLibrary({
      el: host,
      seqs,
      vis: { conserv: true, overviewbox: true, labels: true },
      zoomer: { alignmentWidth: 'auto', alignmentHeight: 420, autoResize: true },
      conf: { dropImport: false },
    })
    inst.render()
  } catch (err) {
    console.warn('[MsaViewer] 交互式渲染失败，降级为文本展示：', err)
    clearView()
    fallback.value = fasta
  }
}

onMounted(() => {
  void renderMsa(props.fasta)
})
onBeforeUnmount(() => {
  renderVersion += 1
  clearView()
})
// FASTA 变化（如切换 OG）时重新渲染
watch(
  () => props.fasta,
  (val) => {
    void renderMsa(val)
  },
)
</script>

<style scoped>
.msa-viewer__host {
  width: 100%;
  min-height: 120px;
  max-height: 560px;
  overflow: auto;
}
.og-fasta--fallback {
  max-height: 360px;
  overflow: auto;
  white-space: pre;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
}
</style>
