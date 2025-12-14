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
            <view class="meta">{{ order.supplier || '—' }} ｜ 期望到货 {{ order.expected_date || '—' }}</view>
          </view>
          <view class="status" :class="statusClass(order.status)">{{ order.status }}</view>
        </view>
        <view class="items">
          <view v-for="item in order.items" :key="item.product_id" class="item-row">
            <view class="item-name">{{ item.product_id }}</view>
            <view class="item-meta">需求 {{ item.quantity }} ｜ 已到 {{ item.received_qty }}</view>
            <view class="item-meta" v-if="isOwner">预计成本 ¥{{ item.expected_cost }}</view>
          </view>
        </view>
      </view>
      <view v-if="!orders.length" class="empty">暂无采购单</view>
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
      orders: []
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    }
  },
  onShow() {
    this.role = getRole()
    this.fetchOrders()
  },
  methods: {
    statusClass(status) {
      if (status === '完成') return 'done'
      if (status === '部分到货') return 'partial'
      return 'pending'
    },
    async fetchOrders() {
      try {
        const data = await api.getPurchaseOrders()
        this.orders = data || []
      } catch (err) {
        uni.showToast({ title: '加载采购单失败', icon: 'none' })
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

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40rpx 0;
}
</style>
