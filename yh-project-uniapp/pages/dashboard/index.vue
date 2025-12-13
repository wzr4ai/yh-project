<template>
  <view class="page">
    <view class="heading">
      <view class="title">运营总览</view>
      <view class="subtitle">角色：{{ roleLabel }}</view>
    </view>

    <view class="grid">
      <view class="card highlight">
        <view class="card-title">今日销售额</view>
        <view class="card-value">¥{{ metrics.actualSales.toFixed(2) }}</view>
        <view class="card-sub">订单数 {{ metrics.orders }} ｜ 客单价 ¥{{ metrics.avgTicket.toFixed(2) }}</view>
      </view>
      <view class="card" v-if="isOwner">
        <view class="card-title">今日毛利</view>
        <view class="card-value positive">¥{{ metrics.grossProfit.toFixed(2) }}</view>
        <view class="card-sub">毛利率 {{ metrics.grossMargin }}%</view>
      </view>
      <view class="card">
        <view class="card-title">销售差值 (溢价/折扣)</view>
        <view class="card-value">{{ metrics.diffSign }}¥{{ metrics.priceDiffAbs.toFixed(2) }}</view>
        <view class="card-sub" :class="{ positive: metrics.priceDiff >= 0, negative: metrics.priceDiff < 0 }">
          {{ metrics.priceDiff >= 0 ? '溢价' : '折扣' }} {{ metrics.priceDiffRate }}%
        </view>
      </view>
    </view>

    <view class="grid">
      <view class="card wide" v-if="isOwner">
        <view class="card-title">库存货值</view>
        <view class="inventory-row">
          <view>
            <view class="mini-title">库存成本</view>
            <view class="mini-value">¥{{ inventoryCost.toFixed(2) }}</view>
          </view>
          <view>
            <view class="mini-title">潜在零售价</view>
            <view class="mini-value">¥{{ inventoryRetail.toFixed(2) }}</view>
          </view>
        </view>
        <view class="card-sub">按当前价格体系计算，单仓</view>
      </view>
      <view class="card wide">
        <view class="card-title">快报</view>
        <view class="pill-row">
          <view class="pill">日</view>
          <view class="pill muted">周</view>
          <view class="pill muted">月</view>
          <view class="pill muted">自定义</view>
        </view>
        <view class="bullet">
          <view class="dot"></view>
          <view class="bullet-text">分类表现：鞭炮 {{ categoryPerf.cracker }}，组合 {{ categoryPerf.sparkler }}</view>
        </view>
        <view class="bullet">
          <view class="dot"></view>
          <view class="bullet-text">店员贡献：{{ metrics.orders }} 笔订单，客单价 ¥{{ metrics.avgTicket.toFixed(2) }}</view>
        </view>
      </view>
    </view>

    <view class="section">
      <view class="section-title">快捷入口</view>
      <view class="quick-actions">
        <view class="action" @tap="go('/pages/sales/create')">
          <view class="action-title">新增销售</view>
          <view class="action-desc">录入成交、对比标准价</view>
        </view>
        <view class="action" @tap="go('/pages/inventory/overview')">
          <view class="action-title">库存总览</view>
          <view class="action-desc">库存与潜在售价</view>
        </view>
        <view class="action" @tap="go('/pages/purchase/list')" v-if="isOwner">
          <view class="action-title">采购到货</view>
          <view class="action-desc">采购单状态、到货确认</view>
        </view>
        <view class="action" @tap="go('/pages/products/list')">
          <view class="action-title">商品目录</view>
          <view class="action-desc">价格体系与库存分布</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import {
  mockInventory,
  mockProducts,
  mockSalesToday,
  mockCategories,
  getStandardPrice
} from '../../common/mock-data.js'

export default {
  data() {
    return {
      role: getRole(),
      metrics: {
        actualSales: 0,
        grossProfit: 0,
        grossMargin: 0,
        priceDiff: 0,
        priceDiffAbs: 0,
        priceDiffRate: 0,
        diffSign: '',
        orders: 0,
        avgTicket: 0
      },
      inventoryCost: 0,
      inventoryRetail: 0,
      categoryPerf: {
        cracker: '—',
        sparkler: '—'
      }
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    roleLabel() {
      return this.role === 'owner' ? '老板' : '店员'
    }
  },
  onShow() {
    this.role = getRole()
    this.buildMetrics()
  },
  methods: {
    buildMetrics() {
      const orders = mockSalesToday.length
      const totals = mockSalesToday.reduce(
        (acc, item) => {
          const qty = item.quantity || 0
          acc.actual += (item.actualSalePrice || 0) * qty
          acc.expected += (item.snapshotStandardPrice || 0) * qty
          acc.cost += (item.snapshotCost || 0) * qty
          return acc
        },
        { actual: 0, expected: 0, cost: 0 }
      )
      const priceDiff = totals.actual - totals.expected
      const grossProfit = totals.actual - totals.cost
      const grossMargin = totals.actual ? ((grossProfit / totals.actual) * 100).toFixed(1) : '0.0'
      const avgTicket = orders ? totals.actual / orders : 0

      this.metrics = {
        actualSales: totals.actual,
        grossProfit,
        grossMargin,
        priceDiff,
        priceDiffAbs: Math.abs(priceDiff),
        priceDiffRate: totals.expected ? ((priceDiff / totals.expected) * 100).toFixed(1) : '0.0',
        diffSign: priceDiff >= 0 ? '+' : '-',
        orders,
        avgTicket
      }

      this.buildInventoryValue()
      this.buildCategoryPerf()
    },
    buildInventoryValue() {
      let costTotal = 0
      let retailTotal = 0
      mockInventory.forEach(row => {
        const product = mockProducts.find(p => p.id === row.productId)
        if (!product) return
        const qty = row.currentStock || 0
        costTotal += (product.baseCostPrice || 0) * qty
        const { price } = getStandardPrice(product)
        retailTotal += price * qty
      })
      this.inventoryCost = costTotal
      this.inventoryRetail = retailTotal
    },
    buildCategoryPerf() {
      const perf = {}
      mockCategories.forEach(c => {
        const salesForCategory = mockSalesToday
          .filter(sale => {
            const product = mockProducts.find(p => p.id === sale.productId)
            return product && product.categoryId === c.id
          })
          .reduce((acc, sale) => acc + sale.actualSalePrice * sale.quantity, 0)
        perf[c.id] = salesForCategory ? `¥${salesForCategory.toFixed(0)}` : '¥0'
      })
      this.categoryPerf = {
        cracker: perf.cracker || '¥0',
        sparkler: perf.sparkler || '¥0'
      }
    },
    go(url) {
      uni.navigateTo({ url })
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: #f7f8fa;
  box-sizing: border-box;
}

.heading {
  margin-bottom: 12rpx;
}

.title {
  font-size: 36rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.subtitle {
  color: #6b7280;
  font-size: 24rpx;
  margin-top: 6rpx;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320rpx, 1fr));
  gap: 16rpx;
  margin-top: 16rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.05);
}

.card-title {
  font-size: 26rpx;
  color: #374151;
}

.card-value {
  margin-top: 10rpx;
  font-size: 40rpx;
  font-weight: 700;
  color: #0f6a7b;
}

.card-value.positive {
  color: #0ea76a;
}

.card-sub {
  margin-top: 6rpx;
  color: #6b7280;
  font-size: 24rpx;
}

.card-sub.positive {
  color: #0ea76a;
}

.card-sub.negative {
  color: #c03428;
}

.highlight {
  background: linear-gradient(135deg, #0f6a7b, #12b5a8);
  color: #f5f7fa;
}

.highlight .card-title,
.highlight .card-sub {
  color: rgba(245, 247, 250, 0.9);
}

.highlight .card-value {
  color: #ffffff;
}

.wide {
  grid-column: span 2;
}

.inventory-row {
  display: flex;
  justify-content: space-between;
  margin-top: 12rpx;
}

.mini-title {
  color: #6b7280;
  font-size: 22rpx;
}

.mini-value {
  font-size: 32rpx;
  font-weight: 700;
  margin-top: 6rpx;
  color: #0b1f3a;
}

.pill-row {
  display: flex;
  gap: 12rpx;
  margin: 10rpx 0 6rpx;
}

.pill {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: #0f6a7b;
  color: #f5f7fa;
  font-size: 22rpx;
}

.pill.muted {
  background: #e5e7eb;
  color: #0b1f3a;
}

.bullet {
  display: flex;
  align-items: center;
  margin-top: 8rpx;
}

.dot {
  width: 10rpx;
  height: 10rpx;
  border-radius: 50%;
  background: #0f6a7b;
  margin-right: 10rpx;
}

.bullet-text {
  color: #4b5563;
  font-size: 24rpx;
}

.section {
  margin-top: 24rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320rpx, 1fr));
  gap: 14rpx;
}

.action {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 18rpx;
  border: 1rpx solid #e5e7eb;
  box-shadow: 0 8rpx 18rpx rgba(0, 0, 0, 0.04);
}

.action-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0f6a7b;
}

.action-desc {
  margin-top: 6rpx;
  color: #6b7280;
  font-size: 24rpx;
}
</style>
