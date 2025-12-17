const ROLE_KEY = 'yh-role'
const TOKEN_KEY = 'yh-token'

export function setRole(role) {
  if (!role) {
    try {
      uni.removeStorageSync(ROLE_KEY)
    } catch (e) {}
    return
  }
  uni.setStorageSync(ROLE_KEY, role)
}

export function getRole() {
  const role = uni.getStorageSync(ROLE_KEY)
  if (role) return role
  const token = getToken()
  const payload = token ? decodeJwtPayload(token) : null
  const fromToken = payload && payload.role ? String(payload.role) : ''
  if (fromToken) {
    setRole(fromToken)
    return fromToken
  }
  return ''
}

export function setToken(token) {
  if (!token) {
    try {
      uni.removeStorageSync(TOKEN_KEY)
    } catch (e) {}
    return
  }
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
  try {
    const bytes = base64ToBytes(base64)
    const text = utf8Decode(bytes)
    return JSON.parse(text)
  } catch (e) {
    // ignore
  }
  return null
}

function base64ToBytes(base64) {
  const clean = String(base64 || '').replace(/[^A-Za-z0-9+/=]/g, '')
  const lookup = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  const rev = {}
  for (let i = 0; i < lookup.length; i++) rev[lookup[i]] = i
  const out = []
  let buffer = 0
  let bits = 0
  for (let i = 0; i < clean.length; i++) {
    const c = clean[i]
    if (c === '=') break
    const v = rev[c]
    if (v === undefined) continue
    buffer = (buffer << 6) | v
    bits += 6
    if (bits >= 8) {
      bits -= 8
      out.push((buffer >> bits) & 0xff)
    }
  }
  return new Uint8Array(out)
}

function utf8Decode(bytes) {
  const arr = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes || [])
  let out = ''
  for (let i = 0; i < arr.length; i++) {
    const b0 = arr[i]
    if (b0 < 0x80) {
      out += String.fromCharCode(b0)
      continue
    }
    if ((b0 & 0xe0) === 0xc0) {
      const b1 = arr[++i]
      out += String.fromCharCode(((b0 & 0x1f) << 6) | (b1 & 0x3f))
      continue
    }
    if ((b0 & 0xf0) === 0xe0) {
      const b1 = arr[++i]
      const b2 = arr[++i]
      out += String.fromCharCode(((b0 & 0x0f) << 12) | ((b1 & 0x3f) << 6) | (b2 & 0x3f))
      continue
    }
    if ((b0 & 0xf8) === 0xf0) {
      const b1 = arr[++i]
      const b2 = arr[++i]
      const b3 = arr[++i]
      const codePoint =
        ((b0 & 0x07) << 18) | ((b1 & 0x3f) << 12) | ((b2 & 0x3f) << 6) | (b3 & 0x3f)
      const cp = codePoint - 0x10000
      out += String.fromCharCode(0xd800 + ((cp >> 10) & 0x3ff))
      out += String.fromCharCode(0xdc00 + (cp & 0x3ff))
      continue
    }
  }
  return out
}
