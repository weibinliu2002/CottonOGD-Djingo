<template>
  <el-dropdown trigger="click" @command="handleLanguageChange">
    <span class="language-selector">
      <el-avatar :size="32" class="language-avatar">
        {{ currentLanguageLabel }}
      </el-avatar>
      <el-icon class="ml-1"><arrow-down /></el-icon>
    </span>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="lang in availableLanguages"
          :key="lang.value"
          :command="lang.value"
          :disabled="lang.value === currentLocale"
        >
          {{ lang.label }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { i18n, availableLanguages, setLocale, getLocale, type Locale } from '../locales/i18n-config'

// 当前语言
const currentLocale = computed(() => getLocale())

// 当前语言标签
const currentLanguageLabel = computed(() => {
  const lang = availableLanguages.find(l => l.value === currentLocale.value)
  return lang ? lang.label.substring(0, 2) : 'EN'
})

// 处理语言切换
const handleLanguageChange = (lang: string) => {
  setLocale(lang as Locale)
}
</script>

<style scoped>
.language-selector {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.language-avatar {
  font-size: 12px;
  font-weight: bold;
}
</style>