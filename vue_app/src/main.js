import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import { v4 as uuidv4 } from 'uuid'
import axios from 'axios'
import '@fortawesome/fontawesome-free/css/all.min.css'

const pinia = createPinia()
const app = createApp(App)

// 创建axios实例
const httpInstance = axios.create({
  baseURL: 'http://localhost:8000', // Django默认端口
  timeout: 10000,
  withCredentials: true // 启用跨域Cookie共享
})

// 请求拦截器
httpInstance.interceptors.request.use(
  config => {
    // 获取CSRF Token
    const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1]
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
httpInstance.interceptors.response.use(
  response => {
    return response
  },
  error => {
    return Promise.reject(error)
  }
)

// 使用Vue 3的方式设置全局属性 - 挂载完整的uuid对象
app.config.globalProperties.$uuid = { v4: uuidv4 }

// 挂载axios实例到全局属性
app.config.globalProperties.$http = httpInstance

app.use(pinia).use(router).mount('#app')