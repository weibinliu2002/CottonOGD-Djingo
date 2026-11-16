// 引入axios
import axios from 'axios'

// ============ 会话认证 ============
// 后端契约：
// - POST /CottonOGD_api/login/ 返回 { uuid, token }，同时种下 HttpOnly cookie auth_token（7天）
// - 旧版匿名会话 token 与账号 JWT 分开保存；优先使用账号 JWT
// - HttpOnly cookie JS 不可读（这是正常且安全的），token 只走 localStorage + Bearer header

const SESSION_TOKEN_STORAGE_KEY = 'ogd_session_token'
const AUTH_ACCESS_TOKEN_KEY = 'auth_token'
const AUTH_REFRESH_TOKEN_KEY = 'auth_refresh'
const PREVIOUS_AUTH_ACCESS_TOKEN_KEY = 'auth_access_token'
const PREVIOUS_AUTH_REFRESH_TOKEN_KEY = 'auth_refresh_token'

// 单飞控制：同一时刻只允许一个 /login/ 请求在途，其余等待复用结果（避免登录风暴）
let loginPromise = null

function getStoredToken() {
  try {
    return localStorage.getItem(SESSION_TOKEN_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

function storeToken(token) {
  try {
    if (token) {
      localStorage.setItem(SESSION_TOKEN_STORAGE_KEY, token)
    } else {
      localStorage.removeItem(SESSION_TOKEN_STORAGE_KEY)
    }
  } catch {
    /* localStorage 不可用时忽略，退化为 cookie 认证 */
  }
}

function isJwtToken(token) {
  const parts = token.split('.')
  return parts.length === 3 && parts.every(Boolean)
}

function migrateTokenStorage() {
  try {
    const storedAccess = localStorage.getItem(AUTH_ACCESS_TOKEN_KEY)
    if (storedAccess && !isJwtToken(storedAccess)) {
      if (!localStorage.getItem(SESSION_TOKEN_STORAGE_KEY)) {
        localStorage.setItem(SESSION_TOKEN_STORAGE_KEY, storedAccess)
      }
      localStorage.removeItem(AUTH_ACCESS_TOKEN_KEY)
    }

    const previousAccess = localStorage.getItem(PREVIOUS_AUTH_ACCESS_TOKEN_KEY)
    if (previousAccess && isJwtToken(previousAccess) && !localStorage.getItem(AUTH_ACCESS_TOKEN_KEY)) {
      localStorage.setItem(AUTH_ACCESS_TOKEN_KEY, previousAccess)
    }
    localStorage.removeItem(PREVIOUS_AUTH_ACCESS_TOKEN_KEY)

    const previousRefresh = localStorage.getItem(PREVIOUS_AUTH_REFRESH_TOKEN_KEY)
    if (previousRefresh && !localStorage.getItem(AUTH_REFRESH_TOKEN_KEY)) {
      localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, previousRefresh)
    }
    localStorage.removeItem(PREVIOUS_AUTH_REFRESH_TOKEN_KEY)
  } catch {
    // Storage can be unavailable in restricted browser contexts.
  }
}

migrateTokenStorage()

function getAuthenticatedAccessToken() {
  try {
    return localStorage.getItem(AUTH_ACCESS_TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

function getAuthenticatedRefreshToken() {
  try {
    return localStorage.getItem(AUTH_REFRESH_TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function getAuthAccessToken() {
  return getAuthenticatedAccessToken()
}

export function setAuthTokens(access, refresh) {
  try {
    localStorage.setItem(AUTH_ACCESS_TOKEN_KEY, access)
    localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, refresh)
  } catch (error) {
    throw new Error('Unable to persist authentication tokens', { cause: error })
  }
}

export function clearAuthTokens() {
  try {
    localStorage.removeItem(AUTH_ACCESS_TOKEN_KEY)
    localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY)
    localStorage.removeItem(PREVIOUS_AUTH_ACCESS_TOKEN_KEY)
    localStorage.removeItem(PREVIOUS_AUTH_REFRESH_TOKEN_KEY)
  } catch (error) {
    throw new Error('Unable to clear authentication tokens', { cause: error })
  }
}

function getRequestPath(url = '') {
  return url.replace(/^https?:\/\/[^/]+/i, '').split('?')[0]
}

function isAuthApiRequest(url = '') {
  return getRequestPath(url).startsWith('/CottonOGD_api/api/auth/')
}

function isPublicAuthApiRequest(url = '') {
  return /^\/CottonOGD_api\/api\/auth\/(?:register|login|refresh|verify-email|resend-verification|forgot-password|reset-password)\/?$/
    .test(getRequestPath(url))
}

/**
 * 旧版匿名会话登录：调用 /login/ 获取会话 token 并缓存，不覆盖账号 JWT。
 * 已有在途请求时直接复用（单飞），避免并发重复登录。
 */
export function login() {
  const accessToken = getAuthenticatedAccessToken()
  if (accessToken) return Promise.resolve(accessToken)
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
    const hasAuthenticatedToken = Boolean(getAuthenticatedAccessToken())

    if (isAuthApiRequest(config.url)) {
      return Promise.reject(error)
    }

    if (status === 401 && hasAuthenticatedToken && !config._authRefreshRetried) {
      const refresh = getAuthenticatedRefreshToken()
      if (!refresh) {
        return Promise.reject(error)
      }

      config._authRefreshRetried = true
      try {
        const response = await axios.post(
          '/CottonOGD_api/api/auth/refresh/',
          { refresh },
          { withCredentials: true }
        )
        const data = response?.data?.data || response?.data
        if (!data?.access) {
          throw new Error('Authentication refresh response did not include an access token')
        }
        setAuthTokens(data.access, data.refresh || refresh)
        config.headers = config.headers || {}
        config.headers.Authorization = `Bearer ${data.access}`
        return httpInstance.request(config)
      } catch (refreshError) {
        clearAuthTokens()
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          window.location.assign('/login')
        }
        return Promise.reject(refreshError)
      }
    }

    if (hasAuthenticatedToken) {
      return Promise.reject(error)
    }

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
    if (isPublicAuthApiRequest(config.url)) {
      if (typeof config.headers?.delete === 'function') {
        config.headers.delete('Authorization')
      } else if (config.headers) {
        delete config.headers.Authorization
      }
      return config
    }

    // 检查document对象是否存在
    if (typeof document !== 'undefined') {
      // 获取CSRF Token
      const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1]
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken
      }
    }
    // Bearer token 认证（cookie 认证由 withCredentials 自动生效，无需代码）
    const token = getAuthenticatedAccessToken() || getStoredToken()
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
