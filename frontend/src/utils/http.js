// 引入axios
import axios from 'axios'

// ============ 会话认证 ============
// 后端契约：
// - POST /CottonOGD_api/login/ 返回 { uuid, token }，同时种下 HttpOnly cookie auth_token（7天）
// - 业务接口认证：Authorization: Bearer <token>（推荐）或同站自动携带 auth_token cookie
// - HttpOnly cookie JS 不可读（这是正常且安全的），token 只走 localStorage + Bearer header

const TOKEN_STORAGE_KEY = 'auth_token'

// 单飞控制：同一时刻只允许一个 /login/ 请求在途，其余等待复用结果（避免登录风暴）
let loginPromise = null

function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

function storeToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
  } catch {
    /* localStorage 不可用时忽略，退化为 cookie 认证 */
  }
}

/**
 * 登录：调用 /login/ 获取新 token 并缓存。
 * 已有在途请求时直接复用（单飞），避免并发重复登录。
 */
export function login() {
  if (loginPromise) return loginPromise
  // 用原始 axios 调用（不走下方拦截器，避免递归重试）
  loginPromise = axios
    .post('/CottonOGD_api/login/', null, { withCredentials: true })
    .then((res) => {
      const token = res?.data?.token || ''
      storeToken(token)
      return token
    })
    .finally(() => {
      loginPromise = null
    })
  return loginPromise
}

/**
 * 登出：调用 /logout/ 吊销 token/cookie/会话，并清除本地缓存 token
 */
export async function logout() {
  try {
    await axios.post('/CottonOGD_api/logout/', null, { withCredentials: true })
  } finally {
    storeToken('')
  }
}

// 创建统一的axios实例
const httpInstance = axios.create({
  timeout: 30000, // 30秒超时
  withCredentials: true // 同站自动携带 auth_token cookie
})

// 响应拦截器
httpInstance.interceptors.response.use(
  response => {
    return response.data
  },
  async error => {
    const config = error.config || {}
    const status = error.response?.status
    // 400/401（token 过期或失效）：重新登录后重放一次原请求；重放仍失败才报错
    if ((status === 400 || status === 401) && !config._retried) {
      config._retried = true
      try {
        await login()
      } catch {
        return Promise.reject(error)
      }
      // 重放原请求（请求拦截器会附加新 token）
      return httpInstance.request(config)
    }
    return Promise.reject(error)
  }
)

// 请求拦截器
httpInstance.interceptors.request.use(
  config => {
    // 检查document对象是否存在
    if (typeof document !== 'undefined') {
      // 获取CSRF Token
      const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1]
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken
      }
    }
    // Bearer token 认证（cookie 认证由 withCredentials 自动生效，无需代码）
    const token = getStoredToken()
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 导出axios实例
export default httpInstance
