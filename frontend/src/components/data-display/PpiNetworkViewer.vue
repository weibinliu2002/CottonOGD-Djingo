<template>
  <div class="ppi-network-viewer">
    <div class="ppi-network-viewer__toolbar">
      <span>{{ t('ppi_network_summary', { nodes: nodeCount, edges: edgeCount }) }}</span>
      <el-button size="small" @click="fitNetwork">{{ t('ppi_fit_network') }}</el-button>
    </div>
    <div ref="containerRef" class="ppi-network-viewer__canvas"></div>
  </div>
</template>

<script setup lang="ts">
import cytoscape, { type Core, type ElementDefinition } from 'cytoscape'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ elements: ElementDefinition[] }>()
const { t } = useI18n()
const containerRef = ref<HTMLDivElement | null>(null)

const nodeCount = computed(
  () => props.elements.filter((element) => !('source' in (element.data ?? {}))).length,
)
const edgeCount = computed(() => props.elements.length - nodeCount.value)

let cy: Core | null = null
let resizeObserver: ResizeObserver | null = null
let activeLayout: { stop: () => void } | null = null

function fitNetwork(): void {
  cy?.fit(undefined, 32)
}

function renderNetwork(elements: ElementDefinition[]): void {
  if (!cy) return
  activeLayout?.stop()
  cy.elements().remove()
  cy.add(elements)
  activeLayout = cy.layout({
    name: 'cose',
    animate: true,
    animationDuration: 400,
    fit: true,
    padding: 32,
    nodeRepulsion: 4500,
    idealEdgeLength: 90,
  }).run()
}

onMounted(() => {
  if (!containerRef.value) return
  cy = cytoscape({
    container: containerRef.value,
    elements: [],
    layout: { name: 'preset' },
    style: [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 5,
          'font-size': 11,
          color: '#243447',
          'background-color': '#3a83b9',
          width: 30,
          height: 30,
          'border-width': 2,
          'border-color': '#ffffff',
        },
      },
      {
        selector: 'edge',
        style: {
          width: 2,
          'line-color': '#a7b6c2',
          'curve-style': 'bezier',
          'target-arrow-shape': 'none',
        },
      },
      {
        selector: 'edge[score]',
        style: {
          width: 'mapData(score, 0, 1000, 1, 6)',
        },
      },
      {
        selector: ':selected',
        style: {
          'background-color': '#e58a2b',
          'line-color': '#e58a2b',
          'border-color': '#f5c27b',
        },
      },
    ],
    minZoom: 0.1,
    maxZoom: 4,
  })

  resizeObserver = new ResizeObserver(() => cy?.resize())
  resizeObserver.observe(containerRef.value)
  renderNetwork(props.elements)
})

watch(
  () => props.elements,
  (elements) => renderNetwork(elements),
)

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  activeLayout?.stop()
  activeLayout = null
  cy?.destroy()
  cy = null
})
</script>

<style scoped>
.ppi-network-viewer {
  border: 1px solid #e3e9ee;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.ppi-network-viewer__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0.9rem;
  border-bottom: 1px solid #e3e9ee;
  color: #536273;
  font-size: 0.9rem;
}

.ppi-network-viewer__canvas {
  width: 100%;
  height: min(68vh, 760px);
  min-height: 480px;
}
</style>
