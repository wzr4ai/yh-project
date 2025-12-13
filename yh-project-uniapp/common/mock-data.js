import { calculateStandardPrice } from './pricing.js'

export const mockConfig = {
  globalMultiplier: 1.5
}

export const mockCategories = [
  { id: 'sparkler', name: '烟花组合', retailMultiplier: 1.8 },
  { id: 'cracker', name: '鞭炮', retailMultiplier: 1.6 },
  { id: 'toy', name: '玩具烟花', retailMultiplier: null }
]

export const mockProducts = [
  {
    id: 'p1',
    name: '吉祥如意组合',
    categoryId: 'sparkler',
    spec: '16 发 / 箱',
    baseCostPrice: 68,
    fixedRetailPrice: null,
    imgUrl: '/static/fireworks-1.png'
  },
  {
    id: 'p2',
    name: '喜庆连环炮',
    categoryId: 'cracker',
    spec: '1000 响',
    baseCostPrice: 42,
    fixedRetailPrice: 96,
    imgUrl: '/static/fireworks-2.png'
  },
  {
    id: 'p3',
    name: '星河梦幻棒',
    categoryId: 'toy',
    spec: '10 支 / 袋',
    baseCostPrice: 12,
    fixedRetailPrice: null,
    imgUrl: '/static/fireworks-3.png'
  }
]

export const mockInventory = [
  { productId: 'p1', warehouseId: 'default', currentStock: 120 },
  { productId: 'p2', warehouseId: 'default', currentStock: 80 },
  { productId: 'p3', warehouseId: 'default', currentStock: 260 }
]

export const mockSalesToday = [
  {
    id: 's1',
    productId: 'p2',
    quantity: 4,
    actualSalePrice: 105,
    snapshotCost: 42,
    snapshotStandardPrice: 96
  },
  {
    id: 's2',
    productId: 'p1',
    quantity: 2,
    actualSalePrice: 130,
    snapshotCost: 68,
    snapshotStandardPrice: 122.4
  }
]

export const mockPurchaseOrders = [
  {
    id: 'po-20240201',
    status: '部分到货',
    supplier: 'A 供应商',
    expectedDate: '2024-02-03',
    remark: '春节补货',
    items: [
      { productId: 'p1', quantity: 50, expectedCost: 68, receivedQty: 20, actualCost: 68 },
      { productId: 'p2', quantity: 30, expectedCost: 42, receivedQty: 0, actualCost: null }
    ]
  },
  {
    id: 'po-20240120',
    status: '完成',
    supplier: 'B 供应商',
    expectedDate: '2024-01-22',
    remark: '常规补货',
    items: [
      { productId: 'p3', quantity: 120, expectedCost: 12, receivedQty: 120, actualCost: 12 }
    ]
  }
]

export function buildCategoryLookup() {
  const map = {}
  mockCategories.forEach(c => {
    map[c.id] = c
  })
  return map
}

export function getStandardPrice(product) {
  return calculateStandardPrice(product, buildCategoryLookup(), mockConfig.globalMultiplier)
}
