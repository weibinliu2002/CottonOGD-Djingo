// 引入axios
import axios from 'axios'

// 创建统一的axios实例
const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''
const httpInstance = axios.create({
  timeout: 1000000000000,
  withCredentials: true,
  headers: {
    'X-CSRFToken': csrfToken,
    'uuid': 'test_uuid' // 默认UUID，实际应用中应该从登录状态获取
  }
})

// 响应拦截器
httpInstance.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    return Promise.reject(error)
  }
)

// 请求拦截器
httpInstance.interceptors.request.use(
  config => {
    // 获取CSRF Token
    const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1]
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }
    // 确保添加UUID头部
    if (!config.headers['uuid']) {
      config.headers['uuid'] = 'test_uuid'
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 导出axios实例
export default httpInstance