<template>
  <view class="page">
    <view class="hint-bar" v-if="!isOwner">
      店员仅可查看到货进度，不显示成本
    </view>
    <view class="list">
      <view v-for="order in orders" :key="order.id" class="card">
        <view class="header">
          <view>
            <view class="order-id">{{ order.id }}</view>
            <view class="meta">{{ order.supplier }} ｜ 期望到货 {{ order.expectedDate }}</view>
          </view>
          <view class="status" :class="statusClass(order.status)">{{ order.status }}</view>
        </view>
        <view class="items">
          <view v-for="item in order.items" :key="item.productId" class="item-row">
            <view class="item-name">{{ getProductName(item.productId) }}</view>
            <view class="item-meta">需求 {{ item.quantity }} ｜ 已到 {{ item.receivedQty }}</view>
            <view class="item-meta" v-if="isOwner">预计成本 ¥{{ item.expectedCost }}</view>
          </view>
        </view>
        <view class="actions">
          <button size="mini" type="primary" @tap="confirmReceive(order)" :disabled="order.status === '完成'">
            到货确认 (模拟)
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { mockProducts, mockPurchaseOrders } from '../../common/mock-data.js'

export default {
  data() {
    return {
      role: getRole(),
      orders: mockPurchaseOrders
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    }
  },
  onShow() {
    this.role = getRole()
  },
  methods: {
    getProductName(id) {
      const p = mockProducts.find(item => item.id === id)
      return p ? p.name : '未知商品'
    },
    statusClass(status) {
      if (status === '完成') return 'done'
      if (status === '部分到货') return 'partial'
      return 'pending'
    },
    confirmReceive(order) {
      uni.showToast({
        title: '已确认 (模拟)',
        icon: 'success'
      })
      console.log('confirm receive', order.id)
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

.hint-bar {
  background: #fef3c7;
  color: #92400e;
  padding: 12rpx 16rpx;
  border-radius: 12rpx;
  font-size: 24rpx;
  margin-bottom: 12rpx;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 18rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-id {
  font-size: 30rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.meta {
  color: #6b7280;
  margin-top: 6rpx;
  font-size: 24rpx;
}

.status {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  color: #ffffff;
}

.status.done {
  background: #0ea76a;
}

.status.partial {
  background: #f59e0b;
}

.status.pending {
  background: #6b7280;
}

.items {
  margin-top: 14rpx;
  border-top: 1rpx solid #e5e7eb;
  padding-top: 12rpx;
}

.item-row + .item-row {
  margin-top: 10rpx;
}

.item-name {
  font-size: 26rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.item-meta {
  color: #6b7280;
  font-size: 24rpx;
  margin-top: 2rpx;
}

.actions {
  margin-top: 12rpx;
  display: flex;
  justify-content: flex-end;
}
</style>
