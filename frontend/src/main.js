import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import { v4 as uuidv4 } from 'uuid'
import '@fortawesome/fontawesome-free/css/all.min.css'
import httpInstance from './utils/http.js'
const pinia = createPinia()
const app = createApp(App)



// 使用Vue 3的方式设置全局属性 - 挂载完整的uuid对象
app.config.globalProperties.$uuid = { v4: uuidv4 }

// 挂载axios实例到全局属性
app.config.globalProperties.$http = httpInstance

app.use(pinia).use(router).mount('#app')