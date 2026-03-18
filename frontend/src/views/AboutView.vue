<template>
  <div class="container mt-4">
    <div class="page-header">
      <h1 class="page-title">{{ t('about_ogd') }}</h1>
      <p class="page-description">{{ t('ogd_is_a') }}</p>
    </div>
    <!--
    <el-card>
      <h2>{{ t('about_our_platform') }}</h2>
      <p>{{ t('about_platform_description') }}</p>
      <h3>{{ t('key_features') }}</h3>
      <ul>
        <li>{{ t('genome_browsing_and_exploration') }}</li>
        <li>{{ t('gene_expression_analysis') }}</li>
        <li>{{ t('functional_annotation_tools') }}</li>
        <li>{{ t('comparative_genomics') }}</li>
        <li>{{ t('data_download_capabilities') }}</li>
      </ul>
    </el-card>-->
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" target=".container" />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
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

ul {
  margin-left: 20px;
}
</style>