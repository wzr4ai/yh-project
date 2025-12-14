const ROLE_KEY = 'yh-role'
const TOKEN_KEY = 'yh-token'

export function setRole(role) {
  uni.setStorageSync(ROLE_KEY, role)
}

export function getRole() {
  return uni.getStorageSync(ROLE_KEY) || 'owner'
}

export function setToken(token) {
  uni.setStorageSync(TOKEN_KEY, token)
}

export function getToken() {
  return uni.getStorageSync(TOKEN_KEY)
}

export function isOwner(role) {
  return (role || getRole()) === 'owner'
}

export function isTokenValid(token) {
  if (!token) return false
  const payload = decodeJwtPayload(token)
  if (!payload || !payload.exp) return false
  const now = Date.now() / 1000
  const skew = 60 // 1min 余量
  return payload.exp > now + skew
}

function decodeJwtPayload(token) {
  const parts = token.split('.')
  if (parts.length < 2) return null
  let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
  const pad = base64.length % 4
  if (pad) {
    base64 += '='.repeat(4 - pad)
  }
  try {
    if (typeof atob === 'function') {
      return JSON.parse(decodeURIComponent(escape(atob(base64))))
    }
    if (typeof Buffer !== 'undefined') {
      return JSON.parse(Buffer.from(base64, 'base64').toString('utf8'))
    }
  } catch (e) {
    // ignore
  }
  return null
}
