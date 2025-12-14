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
      <view v-for="item in rows" :key="item.product_id" class="card item">
        <view class="item-header">
          <view>
            <view class="item-name">{{ item.name }}</view>
            <view class="item-meta">{{ item.spec || '—' }} ｜ {{ item.category_name || '—' }}</view>
          </view>
          <view class="pill">库存 {{ item.stock }}</view>
        </view>
        <view class="item-grid">
          <view>
            <view class="mini-title">标准单价</view>
            <view class="mini-value">¥{{ item.standard_price.toFixed(2) }}</view>
            <view class="hint">{{ item.price_basis }}</view>
          </view>
          <view>
            <view class="mini-title">潜在总价</view>
            <view class="mini-value accent">¥{{ item.retail_total.toFixed(2) }}</view>
          </view>
          <view v-if="isOwner">
            <view class="mini-title">成本单价</view>
            <view class="mini-value">¥{{ item.base_cost_price }}</view>
          </view>
          <view v-if="isOwner">
            <view class="mini-title">成本总计</view>
            <view class="mini-value">¥{{ item.cost_total.toFixed(2) }}</view>
          </view>
        </view>
      </view>
      <view v-if="!rows.length" class="empty">暂无库存数据</view>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      role: getRole(),
      rows: [],
      totals: {
        cost: 0,
        retail: 0
      }
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    }
  },
  onShow() {
    this.role = getRole()
    this.loadData()
  },
  methods: {
    async loadData() {
      try {
        const [invValue, overview] = await Promise.all([api.getInventoryValue(), api.getInventoryOverview()])
        this.totals = {
          cost: invValue.cost_total || 0,
          retail: invValue.retail_total || 0
        }
        this.rows = overview || []
      } catch (err) {
        uni.showToast({ title: '加载库存失败', icon: 'none' })
      }
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

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40rpx 0;
}
</style>
