/**
 * 强类型 HTTP 封装：新代码请优先使用本模块，而非直接 import http.js。
 * 内部复用 http.js 实例（token 登录、401 重放、CSRF 头均由其拦截器统一处理）。
 * v1 后端统一返回信封 { code, message, data }，http.js 响应拦截器已解包，
 * 故这里直接以业务数据类型作为泛型返回；错误由 axios reject 携带 code/message。
 */
import httpInstance from '@/utils/http.js'

/** v1 后端统一响应信封（拦截器解包前形态） */
export interface ApiEnvelope<T = unknown> {
  code: number
  message: string
  data: T | null
  [key: string]: unknown
}

/** v1 业务错误码（见 backend/docs/api/errors.md；HTTP 状态 = code // 100） */
export interface V1ErrorBody {
  code: number
  message: string
  data?: unknown
}

export function apiGet<T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> {
  return httpInstance.get(url, { params }) as Promise<T>
}

export function apiPost<T = unknown>(
  url: string,
  data?: unknown,
  config?: { timeout?: number; signal?: AbortSignal },
): Promise<T> {
  return httpInstance.post(url, data, config) as Promise<T>
}

export function apiPut<T = unknown>(url: string, data?: unknown): Promise<T> {
  return httpInstance.put(url, data) as Promise<T>
}

export function apiDelete<T = unknown>(url: string): Promise<T> {
  return httpInstance.delete(url) as Promise<T>
}
