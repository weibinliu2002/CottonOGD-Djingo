<template>
  <div>
    <!-- MSAViewer (BioJS msa) 在浏览器端动态加载并渲染到该容器；
         该依赖为旧版 CommonJS 包，故只在客户端 import，不参与 SSR/构建主链路 -->
    <div ref="containerRef" class="msa-viewer-host"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps<{
  /** FASTA 纯文本（需以 '>' 开头） */
  fasta: string
}>()

const containerRef = ref<HTMLElement | null>(null)
// msa 实例句柄，仅在浏览器内创建
let msaSeqs: { el: HTMLElement } | null = null

function destroyMsa(): void {
  const el = containerRef.value
  if (el) el.innerHTML = ''
  msaSeqs = null
}

async function renderMsa(): Promise<void> {
  const el = containerRef.value
  if (!el) return
  el.innerHTML = ''
  if (!props.fasta || !props.fasta.trimStart().startsWith('>')) return
  // 动态、仅浏览器端加载旧版 CommonJS 包（避免污染 SSR / 主构建链路）
  const msa = (await import('msa')).default
  const seqs = new msa.msa({
    el: el,
    seqs: msa.io.fasta.parse(props.fasta),
    // 精简显示：关闭顶部菜单与侧边栏，只渲染比对矩阵
    vis: { labels: true, conserv: false, overviewbox: false },
    conf: { dropImport: false },
  })
  seqs.render()
  msaSeqs = seqs as unknown as { el: HTMLElement }
}

onMounted(renderMsa)
onBeforeUnmount(destroyMsa)
// FASTA 变化（如切换 OG）时重新渲染
watch(() => props.fasta, renderMsa)
</script>

<style scoped>
.msa-viewer-host {
  width: 100%;
  min-height: 120px;
  overflow-x: auto;
}
</style>
