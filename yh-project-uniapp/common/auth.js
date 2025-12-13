const ROLE_KEY = 'yh-role'

export function setRole(role) {
  uni.setStorageSync(ROLE_KEY, role)
}

export function getRole() {
  return uni.getStorageSync(ROLE_KEY) || 'owner'
}

export function isOwner(role) {
  return (role || getRole()) === 'owner'
}
