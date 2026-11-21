import { defineStore } from 'pinia'
import { apiDelete, apiGet, apiPost } from '@/utils/api'
import {
  clearAuthTokens,
  getAuthAccessToken,
  setAuthTokens
} from '@/utils/http.js'

export interface AuthUser {
  id?: number | string
  username: string
  email: string
  email_verified?: boolean
  role?: string
  is_admin?: boolean
  is_staff?: boolean
  is_superuser?: boolean
  bound_third_party_accounts?: Array<{
    provider: string
    uid: string
    connected_at: string
  }>
}

interface ApiEnvelope<T> {
  code?: number
  message?: string
  data?: T
}

interface LoginResponse {
  access: string
  refresh: string
  user: AuthUser
}

function unwrapResponse<T>(response: T | ApiEnvelope<T>): T {
  if (typeof response === 'object' && response !== null && 'data' in response) {
    const envelope = response as ApiEnvelope<T>
    if (envelope.code !== undefined && envelope.code !== 0) {
      throw new Error(envelope.message || 'The authentication request failed')
    }
    if (envelope.data === undefined) {
      throw new Error(envelope.message || 'The authentication response did not include data')
    }
    return envelope.data
  }
  return response as T
}

function isAdmin(user: AuthUser | null) {
  const role = user?.role?.toLowerCase()
  return Boolean(
    user?.is_admin ||
    user?.is_staff ||
    user?.is_superuser ||
    role === 'admin' ||
    role === 'administrator'
  )
}

const AUTH_API_BASE = '/CottonOGD_api/api/v1/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: getAuthAccessToken(),
    user: null as AuthUser | null
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken),
    isAdmin: (state) => isAdmin(state.user)
  },
  actions: {
    async login(identifier: string, password: string) {
      const trimmedIdentifier = identifier.trim()
      const credentials = trimmedIdentifier.includes('@')
        ? { email: trimmedIdentifier, password }
        : { username: trimmedIdentifier, password }

      const response = await apiPost<ApiEnvelope<LoginResponse> | LoginResponse>(
        `${AUTH_API_BASE}/login/`,
        credentials
      )
      const result = unwrapResponse(response)
      if (!result.access || !result.refresh || !result.user) {
        throw new Error('The login response is missing its access token, refresh token, or user')
      }

      setAuthTokens(result.access, result.refresh)
      this.accessToken = result.access
      this.user = result.user
      await this.loadCurrentUser()
    },

    async register(username: string, email: string, password: string, confirmPassword: string) {
      const response = await apiPost<ApiEnvelope<unknown> | unknown>(
        `${AUTH_API_BASE}/register/`,
        {
          username: username.trim(),
          email: email.trim(),
          password,
          confirm_password: confirmPassword
        }
      )
      unwrapResponse(response)
    },

    async forgotPassword(email: string) {
      const response = await apiPost<ApiEnvelope<unknown> | unknown>(
        `${AUTH_API_BASE}/forgot-password/`,
        { email: email.trim() }
      )
      unwrapResponse(response)
    },

    async resetPassword(uidb36: string, key: string, newPassword: string) {
      const response = await apiPost<ApiEnvelope<unknown> | unknown>(
        `${AUTH_API_BASE}/reset-password/`,
        { uidb36, key, new_password: newPassword }
      )
      unwrapResponse(response)
    },

    async deleteAccount() {
      const response = await apiDelete<ApiEnvelope<unknown> | unknown>(
        `${AUTH_API_BASE}/me/`
      )
      unwrapResponse(response)
      this.logout()
    },

    async loadCurrentUser() {
      const response = await apiGet<ApiEnvelope<AuthUser> | AuthUser>(
        `${AUTH_API_BASE}/me/`
      )
      const profile = unwrapResponse(response)
      if (!profile || typeof profile !== 'object' || !profile.username) {
        throw new Error('The account profile response is incomplete')
      }
      this.user = { ...this.user, ...profile }
      this.accessToken = getAuthAccessToken()
    },

    logout() {
      clearAuthTokens()
      this.accessToken = ''
      this.user = null
    }
  }
})
