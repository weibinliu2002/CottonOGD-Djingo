<template>
  <div class="tianditu-map-container">
    <div ref="mapContainerRef" class="map-container"></div>
    <div v-if="loadError" class="map-error">
      <el-empty :description="loadError" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

// 天地图 JS API 通过 Vite proxy 加载，密钥由 proxy 注入，源码中无明文
const SCRIPT_SRC = '/tianditu-api?v=4.0'

const props = withDefaults(defineProps<{
  /** 中心经度 */
  lng?: number
  /** 中心纬度 */
  lat?: number
  /** 缩放级别 1-18 */
  zoom?: number
  /** 容器高度 */
  height?: string
}>(), {
  lng: 116.40769,
  lat: 39.89945,
  zoom: 12,
  height: '400px',
})

const mapContainerRef = ref<HTMLElement>()
const loadError = ref('')
let map: any = null
let scriptEl: HTMLScriptElement | null = null

/** 动态加载天地图 API 脚本 */
function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    // 已加载过则直接返回
    const existing = document.querySelector('script[data-tianditu]') as HTMLScriptElement | null
    if (existing) {
      if ((window as any).T) {
        resolve()
      } else {
        existing.addEventListener('load', () => resolve())
        existing.addEventListener('error', () => reject(new Error('Failed to load Tianditu API')))
      }
      return
    }

    scriptEl = document.createElement('script')
    scriptEl.src = SCRIPT_SRC
    scriptEl.type = 'text/javascript'
    scriptEl.setAttribute('data-tianditu', 'true')
    scriptEl.onload = () => resolve()
    scriptEl.onerror = () => reject(new Error('Failed to load Tianditu API script'))
    document.head.appendChild(scriptEl)
  })
}

/** 初始化地图 */
async function initMap() {
  if (!mapContainerRef.value) return

  try {
    await loadScript()
    const T = (window as any).T
    if (!T || !T.Map) {
      throw new Error('Tianditu API not available')
    }

    await nextTick()
    map = new T.Map(mapContainerRef.value)
    map.centerAndZoom(new T.LngLat(props.lng, props.lat), props.zoom)
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : 'Unknown error'
    console.error('Tianditu map init failed:', e)
  }
}

onMounted(() => {
  initMap()
})

onBeforeUnmount(() => {
  if (map && typeof map.destroy === 'function') {
    map.destroy()
    map = null
  }
})

defineExpose({
  /** 获取地图实例（用于外部扩展操作） */
  getMap: () => map,
  /** 重新设置中心点和缩放 */
  setCenter: (lng: number, lat: number, zoom?: number) => {
    if (map && (window as any).T) {
      map.centerAndZoom(new (window as any).T.LngLat(lng, lat), zoom || props.zoom)
    }
  },
})
</script>

<style scoped>
.tianditu-map-container {
  position: relative;
  width: 100%;
}

.map-container {
  width: 100%;
  height: v-bind('props.height');
  border-radius: 8px;
  overflow: hidden;
}

.map-error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}
</style>
