// 引入axios
import axios from 'axios'
// 创建axios实例
const httpInstance = axios.create({
  // 不设置固定baseURL，使用相对路径，这样可以自动适应不同端口
  // 当在8000端口运行时，请求会发送到8000端口
  // 当在5173端口运行时，请求会通过Vite代理发送到8000端口
  timeout: 1000000000000,
  withCredentials: true // 启用跨域Cookie共享
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
    return config
  },
  error => {
    return Promise.reject(error)
  }
)
export default httpInstance