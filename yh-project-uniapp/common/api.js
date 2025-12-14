import { getToken } from './auth.js'
import { API_BASE_URL } from './config.js'

function request(path, options = {}) {
  const token = getToken()
  const headers = options.header || {}
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE_URL}${path}`,
      method: options.method || 'GET',
      data: options.data || {},
      header: headers,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res.data || { message: '请求失败' })
        }
      },
      fail: reject
    })
  })
}

export const api = {
  getRealtime() {
    return request('/api/dashboard/realtime')
  },
  getInventoryValue() {
    return request('/api/dashboard/inventory_value')
  },
  getPerformance() {
    return request('/api/dashboard/performance')
  },
  getPurchaseOrders() {
    return request('/api/purchase-orders')
  },
  createSales(items, username) {
    const qs = username ? `?username=${encodeURIComponent(username)}` : ''
    return request(`/api/sales${qs}`, {
      method: 'POST',
      data: items
    })
  },
  calculatePrice(productId) {
    return request(`/api/price/calculate/${productId}`)
  },
  getProducts() {
    return request('/api/products')
  },
  getInventoryOverview() {
    return request('/api/inventory/overview')
  }
}
