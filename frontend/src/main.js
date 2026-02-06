import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import { v4 as uuidv4 } from 'uuid'
import '@fortawesome/fontawesome-free/css/all.min.css'
import httpInstance from './utils/http.js'
import { useGenomeStore } from './stores/genome_info.ts'
import { useFamilyStore } from './stores/familyInfo.ts'
import ElementPlus from 'element-plus'
import { i18n, initLocale } from './locales/i18n-config'

const pinia = createPinia()
const app = createApp(App)

app.use(ElementPlus)

// 使用Vue 3的方式设置全局属性 - 挂载完整的uuid对象
app.config.globalProperties.$uuid = { v4: uuidv4 }

// 挂载axios实例到全局属性
app.config.globalProperties.$http = httpInstance

// 注册i18n
app.use(i18n)

// 初始化语言设置
initLocale()

app.use(pinia).use(router).mount('#app')

// 初始化基因组store，在应用启动时获取数据
const genomeStore = useGenomeStore()
genomeStore.initialize()

// 初始化家族store，在应用启动时获取数据
const familyStore = useFamilyStore()
familyStore.initialize()