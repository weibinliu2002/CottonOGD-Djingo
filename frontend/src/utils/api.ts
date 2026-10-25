/**
 * 强类型 HTTP 封装：新代码请优先使用本模块，而非直接 import http.js。
 * 内部复用 http.js 实例（token 登录、401 重放、CSRF 头均由其拦截器统一处理）。
 * 响应拦截器返回 response.data，故这里直接以业务数据类型作为泛型返回。
 */
import httpInstance from '@/utils/http.js'

/** 后端返回的统一业务包裹（success/error 约定，见各视图函数） */
export interface ApiEnvelope<T = unknown> {
  success?: boolean
  answer?: string
  tool_calls?: Array<{ name: string; arguments?: string; elapsed_ms?: number }>
  history_turns?: number
  error?: string
  data?: T
  [key: string]: unknown
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
