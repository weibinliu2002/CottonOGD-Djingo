<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

defineProps<{
  title?: string
}>()
</script>

<template>
  <div class="placeholder-container">
    <div class="placeholder-content">
      <el-icon class="placeholder-icon" :size="64"><Tools /></el-icon>
      <h2>{{ title || t('under_construction') }}</h2>
      <p>{{ t('this_feature_is_under_development') }}</p>
      <el-button type="primary" @click="$router.back()">
        {{ t('go_back') }}
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.placeholder-container {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.placeholder-content {
  text-align: center;
  max-width: 500px;
}

.placeholder-icon {
  color: #3a6ea5;
  margin-bottom: 24px;
}

.placeholder-content h2 {
  color: #333;
  margin-bottom: 16px;
  font-size: 28px;
}

.placeholder-content p {
  color: #666;
  margin-bottom: 24px;
  font-size: 16px;
}
</style>
