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
