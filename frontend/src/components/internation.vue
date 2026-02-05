<template>
  <el-config-provider :locale="elementLocale">
    <app />
  </el-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElConfigProvider } from 'element-plus'
import en from 'element-plus/es/locale/lang/en'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { i18n, initLocale, getLocale } from '../locales/i18n-config'

// 导入 Element Plus 语言包
const elementLocales = {
  'en-US': en,
  'zh-CN': zhCn
}

// 计算当前使用的 Element Plus 语言包
const elementLocale = computed(() => {
  const currentLocale = getLocale()
  return elementLocales[currentLocale] || en
})

// 初始化语言
onMounted(() => {
  initLocale()
})
</script>