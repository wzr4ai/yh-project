import { getToken } from './auth.js'
import { API_BASE_URL } from './config.js'

const API_BASE = (API_BASE_URL || '').replace(/\/+$/, '')

function request(path, options = {}) {
  const token = getToken()
  const headers = options.header || {}
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE}${path}`,
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

const cacheStore = {
  get(key) {
    try {
      return uni.getStorageSync(key)
    } catch (e) {
      return null
    }
  },
  set(key, value) {
    try {
      uni.setStorageSync(key, value)
    } catch (e) {}
  }
}

async function cachedRequest(path, options = {}, cacheKey) {
  const token = getToken()
  const headers = options.header || {}
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  // attach ETag if cached
  const cached = cacheKey ? cacheStore.get(cacheKey) : null
  if (cached && cached.etag) {
    headers['If-None-Match'] = cached.etag
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE}${path}`,
      method: options.method || 'GET',
      data: options.data || {},
      header: headers,
      success: (res) => {
        if (res.statusCode === 304 && cached) {
          resolve(cached.data)
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          if (cacheKey && res.header && res.header.ETag) {
            cacheStore.set(cacheKey, { etag: res.header.ETag, data: res.data })
          }
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
  getReceiptTotal() {
    return request('/api/dashboard/receipt_total')
  },
  setManualReceipt(value) {
    return request('/api/dashboard/manual_receipt', { method: 'POST', data: { value } })
  },
  getInventoryValue() {
    return request('/api/dashboard/inventory_value')
  },
  getPerformance() {
    return request('/api/dashboard/performance')
  },
  analyzeOrders(payload) {
    return request('/api/orders/analyze', {
      method: 'POST',
      data: payload
    })
  },
  importOrders(payload) {
    return request('/api/orders/import', {
      method: 'POST',
      data: payload
    })
  },
  uploadOrderCsv(filePath, fileName = 'orders.csv') {
    const token = getToken()
    const headers = {}
    if (token) headers.Authorization = `Bearer ${token}`
    return new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${API_BASE}/api/orders/import-file`,
        filePath,
        name: 'file',
        formData: { filename: fileName },
        header: headers,
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try {
              resolve(JSON.parse(res.data))
            } catch (e) {
              resolve(res.data)
            }
          } else {
            reject(res.data || { message: '上传失败' })
          }
        },
        fail: reject
      })
    })
  },
  createMiscCost(payload) {
    return request('/api/misc-costs', {
      method: 'POST',
      data: payload
    })
  },
  listMiscCosts({ offset = 0, limit = 100 } = {}) {
    return request(`/api/misc-costs?offset=${offset}&limit=${limit}`)
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
    const path = `/api/products?${params.join('&')}`
    return cachedRequest(path, {}, `cache:${path}`)
  },
  getInventoryOverview() {
    const path = '/api/inventory/overview'
    return cachedRequest(path, {}, `cache:${path}`)
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
    return request(`/api/products/${id}`) // 单个商品更新频率高，暂不缓存
  },
  getCategories() {
    const path = '/api/categories'
    return cachedRequest(path, {}, `cache:${path}`)
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
