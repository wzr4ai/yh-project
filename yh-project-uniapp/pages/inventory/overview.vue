<template>
  <view class="page">
    <view class="card summary">
      <view class="row">
        <view>
          <view class="mini-title">库存成本</view>
          <view class="mini-value">¥{{ totals.cost.toFixed(2) }}</view>
        </view>
        <view>
          <view class="mini-title">潜在零售价</view>
          <view class="mini-value accent">¥{{ totals.retail.toFixed(2) }}</view>
        </view>
      </view>
      <view class="mini-title">单仓模式 · 按当前价格体系计算</view>
    </view>

    <view class="list">
      <view v-for="item in rows" :key="item.product.id" class="card item">
        <view class="item-header">
          <view>
            <view class="item-name">{{ item.product.name }}</view>
            <view class="item-meta">{{ item.product.spec }} ｜ {{ item.categoryName }}</view>
          </view>
          <view class="pill">库存 {{ item.stock }}</view>
        </view>
        <view class="item-grid">
          <view>
            <view class="mini-title">标准单价</view>
            <view class="mini-value">¥{{ item.standardPrice.toFixed(2) }}</view>
            <view class="hint">{{ item.basis }}</view>
          </view>
          <view>
            <view class="mini-title">潜在总价</view>
            <view class="mini-value accent">¥{{ item.retailTotal.toFixed(2) }}</view>
          </view>
          <view v-if="isOwner">
            <view class="mini-title">成本单价</view>
            <view class="mini-value">¥{{ item.product.baseCostPrice }}</view>
          </view>
          <view v-if="isOwner">
            <view class="mini-title">成本总计</view>
            <view class="mini-value">¥{{ item.costTotal.toFixed(2) }}</view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { buildCategoryLookup, mockConfig, mockInventory, mockProducts } from '../../common/mock-data.js'
import { calculateStandardPrice } from '../../common/pricing.js'

export default {
  data() {
    return {
      role: getRole(),
      rows: [],
      totals: {
        cost: 0,
        retail: 0
      },
      categoryLookup: buildCategoryLookup()
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    }
  },
  onShow() {
    this.role = getRole()
    this.buildRows()
  },
  methods: {
    buildRows() {
      let cost = 0
      let retail = 0
      this.rows = mockInventory.map(row => {
        const product = mockProducts.find(p => p.id === row.productId)
        if (!product) return null
        const stock = row.currentStock || 0
        const { price, basis } = calculateStandardPrice(product, this.categoryLookup, mockConfig.globalMultiplier)
        const retailTotal = price * stock
        const costTotal = product.baseCostPrice * stock
        cost += costTotal
        retail += retailTotal
        return {
          product,
          stock,
          standardPrice: price,
          basis,
          retailTotal,
          costTotal,
          categoryName: (this.categoryLookup[product.categoryId] || {}).name || '—'
        }
      }).filter(Boolean)
      this.totals = { cost, retail }
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: #f7f8fa;
  padding: 20rpx;
  box-sizing: border-box;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
}

.summary .row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.mini-title {
  color: #6b7280;
  font-size: 22rpx;
}

.mini-value {
  font-size: 32rpx;
  font-weight: 700;
  color: #0b1f3a;
  margin-top: 6rpx;
}

.mini-value.accent {
  color: #0f6a7b;
}

.list {
  margin-top: 16rpx;
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}

.item {
  padding: 18rpx;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-name {
  font-size: 30rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.item-meta {
  color: #6b7280;
  margin-top: 4rpx;
  font-size: 24rpx;
}

.pill {
  padding: 10rpx 16rpx;
  background: #0f6a7b;
  color: #ffffff;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.item-grid {
  margin-top: 14rpx;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200rpx, 1fr));
  gap: 12rpx;
}

.hint {
  margin-top: 4rpx;
  color: #9ca3af;
  font-size: 22rpx;
}
</style>
