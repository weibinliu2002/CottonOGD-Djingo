<template>
  <div class="sequence-shell">
    <iframe
      ref="iframeRef"
      class="sequence-frame"
      :src="iframeSrc"
      frameborder="0"
      @load="handleIframeLoad"
      @error="handleIframeError"
    />

    <div v-if="loading" class="state-layer loading-layer">
      <div class="spinner" />
      <p>Loading Sequence Server...</p>
    </div>

    <div v-if="error" class="state-layer error-layer">
      <p>{{ error }}</p>
      <el-button type="primary" @click="retryLoad">Retry</el-button>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

const LAST_URL_KEY = 'sequence_server_last_url_v2'
const BASE_URL = '/sequence-server/'
const BASE_ORIGIN = window.location.origin

const iframeRef = ref(null)
const iframeSrc = ref(BASE_URL)
const loading = ref(true)
const error = ref('')

let trackTimer = null

const getStoredUrl = () => {
  const url = window.sessionStorage.getItem(LAST_URL_KEY)
  if (!url) return BASE_URL
  if (url.startsWith('/sequence-server/')) return url
  if (url.startsWith(`${BASE_ORIGIN}/sequence-server/`)) return url
  return BASE_URL
}

const storeUrl = (url) => {
  if (!url || typeof url !== 'string') return
  window.sessionStorage.setItem(LAST_URL_KEY, url)
}

const syncUrlFromIframe = () => {
  if (!iframeRef.value?.contentWindow) return

  try {
    const href = iframeRef.value.contentWindow.location.href
    if (href) {
      storeUrl(href)
    }
  } catch {
    // Cross-origin pages cannot expose location to parent.
    // We still keep seamless embed and rely on postMessage if available.
  }
}

const handleIframeLoad = () => {
  loading.value = false
  error.value = ''
  syncUrlFromIframe()
}

const handleIframeError = () => {
  loading.value = false
  error.value = 'Sequence Server 加载失败，请确认服务可访问。'
  ElMessage.error('Sequence Server load failed')
}

const retryLoad = () => {
  loading.value = true
  error.value = ''
  iframeSrc.value = getStoredUrl()
}

const handleMessage = (event) => {
  if (event.origin !== BASE_ORIGIN) return

  const data = event.data
  if (!data || typeof data !== 'object') return

  const nextUrl = data.url || data.href || data.currentUrl
  if (typeof nextUrl === 'string' && nextUrl.startsWith(BASE_ORIGIN)) {
    storeUrl(nextUrl)
  }
}

onMounted(() => {
  iframeSrc.value = getStoredUrl()
  trackTimer = window.setInterval(syncUrlFromIframe, 1000)
  window.addEventListener('message', handleMessage)
})

onBeforeUnmount(() => {
  if (trackTimer) {
    window.clearInterval(trackTimer)
    trackTimer = null
  }
  window.removeEventListener('message', handleMessage)
})
</script>

<style scoped>
.sequence-shell {
  position: relative;
  width: 100%;
  min-height: calc(100vh - 110px);
  background: #ffffff;
  overflow: hidden;
}

.sequence-frame {
  display: block;
  width: 100%;
  height: calc(100vh - 110px);
  border: 0;
  background: #ffffff;
}

.state-layer {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.loading-layer {
  background: rgba(255, 255, 255, 0.9);
  color: #334155;
}

.error-layer {
  background: rgba(255, 255, 255, 0.95);
  color: #991b1b;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 4px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .sequence-shell,
  .sequence-frame {
    min-height: calc(100vh - 90px);
    height: calc(100vh - 90px);
  }
}
</style>

