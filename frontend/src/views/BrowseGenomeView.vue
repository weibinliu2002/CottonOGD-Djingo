<template>
  <div class="container mt-4">
    <h1>{{ t('browse_genomes') }}</h1>
    <p>{{ t('page_under_development') }}</p>
    
    <!-- 回到顶部 -->
        <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script>
import { useI18n } from 'vue-i18n'

export default {
  name: 'BrowseGenomeView',
  setup() {
    const { t } = useI18n()
    return {
      t
    }
  }
}
</script>
