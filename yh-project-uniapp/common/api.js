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
  getProducts({
    offset = 0,
    limit = 20,
    categoryId = '',
    categoryIds = [],
    customCategoryIds = [],
    merchantCategoryIds = [],
    keyword = ''
  } = {}) {
    const params = []
    params.push(`offset=${offset}`)
    params.push(`limit=${limit}`)
    if (categoryId) params.push(`category_id=${encodeURIComponent(categoryId)}`)
    if (categoryIds.length) params.push(`category_ids=${categoryIds.map(encodeURIComponent).join(',')}`)
    if (customCategoryIds.length) params.push(`custom_category_ids=${customCategoryIds.map(encodeURIComponent).join(',')}`)
    if (merchantCategoryIds.length) params.push(`merchant_category_ids=${merchantCategoryIds.map(encodeURIComponent).join(',')}`)
    if (keyword) params.push(`keyword=${encodeURIComponent(keyword)}`)
    return request(`/api/products?${params.join('&')}`)
  },
  getInventoryOverview() {
    return request('/api/inventory/overview')
  },
  adjustInventory(data, username) {
    const qs = username ? `?username=${encodeURIComponent(username)}` : ''
    return request(`/api/inventory/adjust${qs}`, {
      method: 'POST',
      data
    })
  },
  getInventory(productId) {
    return request(`/api/inventory/${productId}`)
  },
  getProduct(id) {
    return request(`/api/products/${id}`)
  },
  getCategories() {
    return request('/api/categories')
  },
  createCategory(data) {
    return request('/api/categories', { method: 'POST', data })
  },
  updateCategory(id, data) {
    return request(`/api/categories/${id}`, { method: 'PUT', data })
  },
  deleteCategory(id, force = false) {
    const qs = force ? '?force=true' : ''
    return request(`/api/categories/${id}${qs}`, { method: 'DELETE' })
  },
  replaceCategoryProducts(categoryId, productIds) {
    return request(`/api/categories/${categoryId}/products`, {
      method: 'PUT',
      data: { product_ids: productIds }
    })
  },
  createProduct(payload) {
    return request('/api/products', {
      method: 'POST',
      data: payload
    })
  },
  deleteProduct(id) {
    return request(`/api/products/${id}`, { method: 'DELETE' })
  },
  updateProduct(id, payload) {
    return request(`/api/products/${id}`, {
      method: 'PUT',
      data: payload
    })
  }
}
