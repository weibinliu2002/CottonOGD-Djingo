import assert from 'node:assert/strict'
import { test } from 'node:test'
import axios from 'axios'

test('public auth requests omit legacy tokens while protected requests use JWT', async () => {
  const values = new Map([['auth_token', 'legacy-uuid-session']])
  const originalLocalStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  const originalDocument = Object.getOwnPropertyDescriptor(globalThis, 'document')
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, String(value)),
      removeItem: (key) => values.delete(key)
    }
  })
  globalThis.document = { cookie: '' }

  try {
    const { default: http, setAuthTokens, clearAuthTokens } = await import('../utils/http.js')
    const requests = []
    let loginRequestCount = 0
    http.defaults.adapter = async (config) => {
      requests.push(config)
      if (config.url === '/CottonOGD_api/api/auth/login/' && ++loginRequestCount === 2) {
        const response = {
          data: { error: { code: 'auth_error', message: 'invalid credentials' } },
          status: 401,
          statusText: 'Unauthorized',
          headers: {},
          config
        }
        throw new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, response)
      }
      return { data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config }
    }
    axios.defaults.adapter = http.defaults.adapter

    await http.post('/CottonOGD_api/api/auth/login/', {})
    assert.equal(requests[0].headers.get('Authorization'), undefined)
    assert.equal(values.get('ogd_session_token'), 'legacy-uuid-session')
    assert.equal(values.has('auth_token'), false)

    await http.post('/CottonOGD_api/api/auth/forgot-password/', { email: 'user@example.com' })
    await http.post('/CottonOGD_api/api/auth/reset-password/', {
      uidb36: '1',
      key: 'reset-key',
      new_password: 'password123'
    })
    assert.equal(requests[1].headers.get('Authorization'), undefined)
    assert.equal(requests[2].headers.get('Authorization'), undefined)

    setAuthTokens('jwt.header.signature', 'refresh-token')
    await http.get('/CottonOGD_api/api/auth/me/')
    assert.equal(requests[3].headers.get('Authorization'), 'Bearer jwt.header.signature')

    clearAuthTokens()
    await http.get('/CottonOGD_api/legacy-data/')
    assert.equal(requests[4].headers.get('Authorization'), 'Bearer legacy-uuid-session')

    await assert.rejects(http.post('/CottonOGD_api/api/auth/login/', {}))
    assert.equal(requests.length, 6)
  } finally {
    if (originalLocalStorage) Object.defineProperty(globalThis, 'localStorage', originalLocalStorage)
    else delete globalThis.localStorage
    if (originalDocument) Object.defineProperty(globalThis, 'document', originalDocument)
    else delete globalThis.document
  }
})
