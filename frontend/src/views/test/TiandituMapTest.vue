<template>
  <div class="container mt-4 mb-5">
    <h1 class="page-title">天地图组件测试</h1>
    <p class="page-subtitle mb-4">Tianditu Map Component Test — 密钥通过 Vite proxy 注入，源码中无明文</p>

    <el-card shadow="never" class="mb-4">
      <template #header>
        <span>地图控件</span>
      </template>
      <el-form :inline="true" size="small">
        <el-form-item label="经度">
          <el-input-number v-model="lng" :precision="5" :step="0.1" :min="-180" :max="180" />
        </el-form-item>
        <el-form-item label="纬度">
          <el-input-number v-model="lat" :precision="5" :step="0.1" :min="-90" :max="90" />
        </el-form-item>
        <el-form-item label="缩放">
          <el-input-number v-model="zoom" :min="1" :max="18" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleUpdate">更新位置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover">
      <TiandituMap
        ref="mapRef"
        :lng="116.40769"
        :lat="39.89945"
        :zoom="5"
        height="500px"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import TiandituMap from '@/components/data-display/TiandituMap.vue'

const mapRef = ref<InstanceType<typeof TiandituMap>>()
const lng = ref(116.40769)
const lat = ref(39.89945)
const zoom = ref(5)

function handleUpdate() {
  mapRef.value?.setCenter(lng.value, lat.value, zoom.value)
}
</script>

<style scoped>
.page-title {
  font-size: 1.8rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}
.page-subtitle {
  color: #666;
}
.mb-4 {
  margin-bottom: 1.5rem;
}
.mt-4 {
  margin-top: 1.5rem;
}
</style>
