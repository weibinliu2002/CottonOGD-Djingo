﻿<template>
  <div class="sequence-full-wrapper">
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
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

// Sequence Server 代理路径
const iframeSrc = ref('/blast/')
const loading = ref(true)
const error = ref('')

const handleIframeLoad = () => {
  loading.value = false
  error.value = ''
}

const handleIframeError = () => {
  loading.value = false
  error.value = 'Sequence Server 加载失败，请确认服务可访问。'
  ElMessage.error('Sequence Server load failed')
}

const retryLoad = () => {
  loading.value = true
  error.value = ''
  iframeSrc.value = '/blast/'
}
</script>

<style scoped>
.sequence-full-wrapper {
  width: 100vw;
  position: relative;
  left: 50%;
  right: 50%;
  margin-left: -50vw;
  margin-right: -50vw;
  max-width: 100vw;
  padding: 0;
}

.sequence-shell {
  position: relative;
  width: 100%;
  min-height: calc(100vh - 160px);
  height: calc(100vh - 160px);
  background: #ffffff;
  overflow: hidden;
}

.sequence-frame {
  display: block;
  width: 100%;
  min-height: calc(100vh - 160px);
  height: calc(100vh - 160px);
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

@media (max-width: 992px) {
  .sequence-shell,
  .sequence-frame {
    min-height: calc(100vh - 140px);
    height: calc(100vh - 140px);
  }
}

@media (max-width: 768px) {
  .sequence-shell,
  .sequence-frame {
    min-height: calc(100vh - 120px);
    height: calc(100vh - 120px);
  }
}
</style>
