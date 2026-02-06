<template>
  <div class="container mt-4">
    <div class="page-header">
      <h1 class="page-title">{{ t('contact_us') }}</h1>
      <p class="page-description">{{ t('get_in_touch') }}</p>
    </div>
    <el-card>
      <p>This page is under development...</p>
    </el-card>
  </div>
</template>

<script>
import { useI18n } from 'vue-i18n'

export default {
  name: 'Contact_usView',
  setup() {
    const { t } = useI18n()
    return {
      t
    }
  }
}
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: left;
  margin-bottom: 30px;
}

.page-title {
  font-size: 36px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 16px;
}

.page-description {
  font-size: 16px;
  color: #666;
  line-height: 1.6;
  max-width: 800px;
  margin: 0;
}
</style>