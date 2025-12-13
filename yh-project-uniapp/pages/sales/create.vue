<template>
  <view class="page">
    <view class="card">
      <view class="card-title">选择商品</view>
      <picker mode="selector" :range="products" range-key="name" @change="onProductChange">
        <view class="picker-value">
          {{ currentProduct ? currentProduct.name : '请选择商品' }}
        </view>
      </picker>
      <view v-if="currentProduct" class="meta">
        <view class="meta-item">规格：{{ currentProduct.spec }}</view>
        <view class="meta-item">分类：{{ categoryName }}</view>
        <view class="meta-item">标准零售价：¥{{ pricing.price.toFixed(2) }} ({{ pricing.basis }})</view>
        <view class="meta-item" v-if="isOwner">成本：¥{{ currentProduct.baseCostPrice }}</view>
      </view>
    </view>

    <view class="card">
      <view class="card-title">录入成交</view>
      <view class="form-row">
        <view class="label">数量</view>
        <input class="input" type="number" v-model.number="quantity" placeholder="输入数量" />
      </view>
      <view class="form-row">
        <view class="label">实际单价</view>
        <input class="input" type="digit" v-model.number="actualPrice" placeholder="¥ 输入成交单价" />
      </view>
      <view class="summary" v-if="currentProduct">
        <view class="summary-title">对比</view>
        <view class="summary-grid">
          <view>
            <view class="mini-title">标准金额</view>
            <view class="mini-value">¥{{ standardTotal.toFixed(2) }}</view>
          </view>
          <view>
            <view class="mini-title">成交金额</view>
            <view class="mini-value">¥{{ actualTotal.toFixed(2) }}</view>
          </view>
          <view>
            <view class="mini-title">差值</view>
            <view :class="['mini-value', priceDiff >= 0 ? 'positive' : 'negative']">
              {{ priceDiff >= 0 ? '+' : '-' }}¥{{ Math.abs(priceDiff).toFixed(2) }}
            </view>
          </view>
          <view v-if="isOwner">
            <view class="mini-title">毛利 (估)</view>
            <view class="mini-value">¥{{ grossProfit.toFixed(2) }}</view>
          </view>
        </view>
      </view>
      <button class="primary-btn" :disabled="!canSubmit" @tap="submitSale">保存并同步</button>
    </view>
  </view>
</template>

<script>
import { buildCategoryLookup, mockConfig, mockProducts } from '../../common/mock-data.js'
import { calculateStandardPrice } from '../../common/pricing.js'
import { getRole, isOwner } from '../../common/auth.js'

export default {
  data() {
    return {
      products: mockProducts,
      selectedProductId: '',
      quantity: 1,
      actualPrice: null,
      pricing: { price: 0, basis: '' },
      categoryLookup: buildCategoryLookup(),
      role: getRole()
    }
  },
  computed: {
    currentProduct() {
      return this.products.find(p => p.id === this.selectedProductId)
    },
    categoryName() {
      if (!this.currentProduct) return '—'
      const c = this.categoryLookup[this.currentProduct.categoryId]
      return c ? c.name : '—'
    },
    standardTotal() {
      return (this.pricing.price || 0) * (this.quantity || 0)
    },
    actualTotal() {
      return (this.actualPrice || 0) * (this.quantity || 0)
    },
    priceDiff() {
      return this.actualTotal - this.standardTotal
    },
    grossProfit() {
      if (!this.currentProduct) return 0
      const cost = this.currentProduct.baseCostPrice * (this.quantity || 0)
      return this.actualTotal - cost
    },
    canSubmit() {
      return !!(this.currentProduct && this.quantity > 0 && this.actualPrice !== null)
    },
    isOwner() {
      return isOwner(this.role)
    }
  },
  methods: {
    onProductChange(e) {
      const index = Number(e.detail.value)
      const product = this.products[index]
      this.selectedProductId = product.id
      this.pricing = calculateStandardPrice(product, this.categoryLookup, mockConfig.globalMultiplier)
    },
    submitSale() {
      uni.showToast({
        title: '已保存 (模拟)',
        icon: 'success'
      })
      console.log('sale payload', {
        productId: this.selectedProductId,
        quantity: this.quantity,
        actualPrice: this.actualPrice,
        standardPrice: this.pricing.price
      })
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
  margin-bottom: 18rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
}

.card-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.picker-value {
  padding: 20rpx;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  color: #111827;
}

.meta {
  margin-top: 12rpx;
  color: #6b7280;
  font-size: 24rpx;
  line-height: 1.6;
}

.meta-item + .meta-item {
  margin-top: 4rpx;
}

.form-row {
  display: flex;
  align-items: center;
  margin-top: 14rpx;
}

.label {
  width: 180rpx;
  color: #4b5563;
  font-size: 26rpx;
}

.input {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 18rpx;
  font-size: 26rpx;
  color: #0b1f3a;
}

.summary {
  margin-top: 18rpx;
  background: #f1f5f9;
  border-radius: 12rpx;
  padding: 16rpx;
}

.summary-title {
  color: #0b1f3a;
  font-weight: 600;
  margin-bottom: 10rpx;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12rpx;
}

.mini-title {
  color: #6b7280;
  font-size: 22rpx;
}

.mini-value {
  font-size: 30rpx;
  font-weight: 700;
  color: #0b1f3a;
  margin-top: 4rpx;
}

.mini-value.positive {
  color: #0ea76a;
}

.mini-value.negative {
  color: #c03428;
}

.primary-btn {
  margin-top: 18rpx;
  background: linear-gradient(135deg, #0f6a7b, #0ab8c3);
  color: #ffffff;
  border: none;
  font-weight: 700;
}
</style>
