<template>
  <view class="page">
    <view class="hint-bar" v-if="!isOwner">
      店员仅可查看到货进度，不显示成本
    </view>

    <view class="card header-card">
      <view class="header-top">
        <view class="title">采购单列表</view>
        <button v-if="isOwner" size="mini" type="primary" @tap="openCreate">新建采购单</button>
      </view>
      <view class="sub">维护订货计划，支持编辑与调整。</view>
    </view>

    <view class="card summary" v-if="orders.length">
      <view class="summary-row">
        <view>
          <view class="mini-title">采购单数</view>
          <view class="mini-value">{{ summary.orderCount }}</view>
        </view>
        <view>
          <view class="mini-title">待到货</view>
          <view class="mini-value">{{ summary.pendingCount }}</view>
        </view>
        <view>
          <view class="mini-title">到货进度</view>
          <view class="mini-value">{{ summary.progress }}%</view>
        </view>
        <view v-if="isOwner">
          <view class="mini-title">预计总成本</view>
          <view class="mini-value">¥{{ summary.totalCost.toFixed(2) }}</view>
        </view>
      </view>
      <view class="progress-bar">
        <view class="progress" :style="{ width: summary.progress + '%' }"></view>
      </view>
    </view>

    <view class="list">
      <view v-for="order in orders" :key="order.id" class="card">
        <view class="header">
          <view>
            <view class="order-id">{{ order.id }}</view>
            <view class="meta">{{ order.supplier || '—' }} ｜ 期望到货 {{ order.expected_date || '—' }}</view>
            <view class="meta" v-if="order.remark">备注：{{ order.remark }}</view>
          </view>
          <view class="header-actions">
            <view class="status" :class="statusClass(order.status)">{{ order.status }}</view>
            <button v-if="isOwner" size="mini" class="receive-btn" @tap="openReceive(order.id)">入库</button>
            <button v-if="isOwner" size="mini" class="edit-btn" @tap="openEdit(order.id)">编辑</button>
          </view>
        </view>
        <view class="order-stats">
          <view class="stat">计划 {{ order.stats.total }} 箱</view>
          <view class="stat">已到 {{ order.stats.received }} 箱</view>
          <view class="stat">进度 {{ order.stats.progress }}%</view>
          <view class="stat" v-if="isOwner">预计成本 ¥{{ order.stats.cost.toFixed(2) }}</view>
        </view>
        <view class="progress-bar">
          <view class="progress" :style="{ width: order.stats.progress + '%' }"></view>
        </view>
        <view class="items">
          <view v-for="item in order.items" :key="item.product_id" class="item-row">
            <view class="item-name">{{ productName(item) }}</view>
            <view class="item-meta">{{ productSpec(item) }} ｜ 计划 {{ item.quantity }} 箱 ｜ 已到 {{ item.received_qty }} 箱</view>
            <view class="item-meta" v-if="isOwner">
              单价 ¥{{ formatMoney(item.expected_cost) }} ｜ 小计 ¥{{ lineCost(item).toFixed(2) }}
            </view>
          </view>
        </view>
      </view>
      <view v-if="!orders.length && !loading" class="empty">暂无采购单</view>
      <view v-if="loading" class="empty">加载中...</view>
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
      orders: [],
      loading: false,
      productMap: {}
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    summary() {
      const orders = this.orders || []
      let pendingCount = 0
      let totalQty = 0
      let received = 0
      let totalCost = 0
      orders.forEach(order => {
        if (order.status !== '完成') pendingCount += 1
        const stats = order.stats || { total: 0, received: 0, cost: 0 }
        totalQty += stats.total || 0
        received += stats.received || 0
        if (this.isOwner) totalCost += stats.cost || 0
      })
      const progress = totalQty ? Math.min(100, Math.round((received / totalQty) * 100)) : 0
      return {
        orderCount: orders.length,
        pendingCount,
        totalQty,
        received,
        progress,
        totalCost
      }
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
    openEdit(orderId) {
      if (!orderId) return
      uni.navigateTo({ url: `/pages/purchase/edit?id=${encodeURIComponent(orderId)}` })
    },
    openReceive(orderId) {
      if (!orderId) return
      uni.navigateTo({ url: `/pages/purchase/receive?id=${encodeURIComponent(orderId)}` })
    },
    openCreate() {
      uni.navigateTo({ url: '/pages/purchase/edit' })
    },
    calcOrderStats(items) {
      const list = items || []
      let total = 0
      let received = 0
      let cost = 0
      list.forEach(item => {
        const qty = Number(item.quantity) || 0
        const recv = Number(item.received_qty) || 0
        total += qty
        received += recv
        if (this.isOwner) {
          cost += (Number(item.expected_cost) || 0) * qty
        }
      })
      const progress = total ? Math.min(100, Math.round((received / total) * 100)) : 0
      return { total, received, progress, cost }
    },
    productName(item) {
      const product = this.productMap[item.product_id]
      return (product && product.name) || item.product_id
    },
    productSpec(item) {
      const product = this.productMap[item.product_id]
      return product && product.spec ? `规格 ${product.spec}` : '规格 —'
    },
    formatMoney(value) {
      const num = Number(value)
      if (!Number.isFinite(num)) return '—'
      return num.toFixed(2)
    },
    lineCost(item) {
      const qty = Number(item.quantity) || 0
      const unit = Number(item.expected_cost) || 0
      return qty * unit
    },
    async loadProductMap() {
      const ids = new Set()
      this.orders.forEach(order => {
        ;(order.items || []).forEach(item => {
          if (item.product_id && !this.productMap[item.product_id]) {
            ids.add(item.product_id)
          }
        })
      })
      if (!ids.size) return
      for (const id of ids) {
        try {
          const product = await api.getProduct(id)
          this.$set(this.productMap, id, product)
        } catch (err) {
          this.$set(this.productMap, id, { id, name: id })
        }
      }
    },
    async fetchOrders() {
      this.loading = true
      try {
        const data = await api.getPurchaseOrders()
        this.orders = (data || []).map(order => {
          const items = (order.items || []).map(item => ({
            ...item,
            quantity: Number(item.quantity) || 0,
            received_qty: Number(item.received_qty) || 0,
            expected_cost: item.expected_cost
          }))
          return {
            ...order,
            items,
            stats: this.calcOrderStats(items)
          }
        })
        await this.loadProductMap()
      } catch (err) {
        uni.showToast({ title: '加载采购单失败', icon: 'none' })
        this.orders = []
      } finally {
        this.loading = false
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

.summary {
  margin-bottom: 14rpx;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  flex-wrap: wrap;
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

.header-card {
  margin-bottom: 14rpx;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12rpx;
}

.title {
  font-size: 30rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.sub {
  margin-top: 6rpx;
  color: #6b7280;
  font-size: 22rpx;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10rpx;
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

.order-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #6b7280;
}

.stat {
  background: #f3f4f6;
  padding: 6rpx 12rpx;
  border-radius: 999rpx;
}

.progress-bar {
  height: 10rpx;
  border-radius: 999rpx;
  background: #e5e7eb;
  margin-top: 10rpx;
  overflow: hidden;
}

.progress {
  height: 100%;
  background: linear-gradient(90deg, #0f6a7b, #22c1c3);
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

.receive-btn {
  padding: 0 16rpx;
  font-size: 22rpx;
  line-height: 1.8;
  background: #0f6a7b;
  color: #ffffff;
  border: 1rpx solid #0f6a7b;
}

.edit-btn {
  padding: 0 16rpx;
  font-size: 22rpx;
  line-height: 1.8;
  background: #f1f5f9;
  color: #0f6a7b;
  border: 1rpx solid #cbd5f5;
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
