interface ApiErrorResponse {
  response?: {
    data?: {
      error?: { message?: string }
      message?: string
      detail?: string
    }
  }
  message?: string
}

export function getAuthErrorMessage(error: unknown, fallback: string) {
  if (typeof error !== 'object' || error === null) return fallback
  const apiError = error as ApiErrorResponse
  return apiError.response?.data?.error?.message
    || apiError.response?.data?.message
    || apiError.response?.data?.detail
    || apiError.message
    || fallback
}
