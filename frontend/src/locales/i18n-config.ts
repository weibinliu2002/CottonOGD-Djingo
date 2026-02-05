import { createI18n } from 'vue-i18n'
import enUS from './i18n/en-US.json'
import zhCN from './i18n/zh-CN.json'

// 语言类型定义
export type Locale = 'en-US' | 'zh-CN'

// 语言配置
export const availableLanguages = [
  { value: 'en-US', label: 'English' },
  { value: 'zh-CN', label: '中文' }
]

// 默认语言
const defaultLocale: Locale = 'en-US'

// 创建 i18n 实例
export const i18n = createI18n({
  legacy: false, // 使用组合式 API
  locale: defaultLocale,
  fallbackLocale: defaultLocale,
  messages: {
    'en-US': enUS.message,
    'zh-CN': zhCN.message
  }
})

// 切换语言
export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  // 保存到本地存储
  localStorage.setItem('locale', locale)
}

// 获取当前语言
export function getLocale(): Locale {
  return i18n.global.locale.value as Locale
}

// 初始化语言
export function initLocale() {
  const savedLocale = localStorage.getItem('locale') as Locale | null
  if (savedLocale && availableLanguages.some(lang => lang.value === savedLocale)) {
    setLocale(savedLocale)
  }
}
