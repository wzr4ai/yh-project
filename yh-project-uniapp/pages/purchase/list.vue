<template>
  <view class="page">
    <view class="hint-bar" v-if="!isOwner">
      <text class="icon">i</text> 店员模式：成本/利润相关数据已隐藏
    </view>

    <!-- Header Stats -->
    <view class="dashboard-grid">
      <view class="dash-card">
        <view class="dash-label">待到货</view>
        <view class="dash-value highlight">{{ summary.pendingCount }}</view>
      </view>
      <view class="dash-card">
        <view class="dash-label">总体进度</view>
        <view class="dash-value">{{ summary.progress }}%</view>
      </view>
      <view class="dash-card" v-if="isOwner">
        <view class="dash-label">预计成本</view>
        <view class="dash-value">¥{{ formatK(summary.totalCost) }}</view>
      </view>
      <view class="dash-action" v-if="isOwner" @tap="openCreate">
        <view class="add-icon">+</view>
        <view class="add-label">新建</view>
      </view>
    </view>

    <!-- Order List -->
    <view class="list">
      <view v-for="order in orders" :key="order.id" class="order-card" :class="statusClass(order.status)" @tap="openItems(order.id)">
        <view class="card-main">
          <view class="card-header">
            <view class="supplier-row">
              <text class="supplier-name">{{ order.supplier || '未命名供应商' }}</text>
              <view class="meta-row">
                <text class="date-tag">{{ formatDateShort(order.expected_date) }}</text>
                <text class="id-tag">#{{ order.id.slice(-6) }}</text>
              </view>
            </view>
            <view class="status-badge">
              {{ order.status }}
            </view>
          </view>
          
          <view class="card-body">
            <view class="stats-row">
              <view class="stat-item">
                <text class="stat-val">{{ order.item_count }}</text>
                <text class="stat-lbl">品类</text>
              </view>
              <view class="stat-sep"></view>
              <view class="stat-item">
                <text class="stat-val">{{ order.total_qty }}</text>
                <text class="stat-lbl">计划箱数</text>
              </view>
              <view class="stat-sep" v-if="isOwner"></view>
              <view class="stat-item" v-if="isOwner">
                <text class="stat-val">¥{{ formatPrice(order.expected_cost_total) }}</text>
                <text class="stat-lbl">预计金额</text>
              </view>
            </view>
            
            <view class="progress-section">
              <view class="progress-info">
                <text class="prog-label">入库进度</text>
                <text class="prog-val">{{ order.received_qty }}/{{ order.total_qty }} ({{ calcProgress(order) }}%)</text>
              </view>
              <view class="progress-bg">
                <view class="progress-fill" :style="{ width: calcProgress(order) + '%' }"></view>
              </view>
            </view>
          </view>
          
          <view class="card-footer">
             <view class="expand-hint">
               <text class="arrow">></text>
               查看明细
             </view>
             
             <view class="action-group">
               <view class="action-btn secondary" v-if="isOwner" @tap.stop="openEdit(order.id)">
                 编辑
               </view>
               <view class="action-btn primary" v-if="isOwner" @tap.stop="openReceive(order.id)">
                 入库
               </view>
             </view>
          </view>
        </view>
      </view>

      <view v-if="!orders.length && !loading" class="empty-state">
        <view class="empty-icon">...</view>
        <view class="empty-text">暂无采购单</view>
      </view>
      
      <view v-if="loading" class="loading-state">
        加载中...
      </view>
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
      loading: false
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
        totalQty += Number(order.total_qty) || 0
        received += Number(order.received_qty) || 0
        if (this.isOwner) totalCost += Number(order.expected_cost_total) || 0
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
  onPullDownRefresh() {
    this.fetchOrders().then(() => {
      uni.stopPullDownRefresh()
    })
  },
  methods: {
    statusClass(status) {
      if (status === '完成') return 'done'
      if (status === '部分到货') return 'partial'
      return 'pending'
    },
    formatDateShort(dateStr) {
      if (!dateStr) return '—'
      const date = new Date(dateStr)
      if (isNaN(date.getTime())) return dateStr
      return `${date.getMonth() + 1}/${date.getDate()}`
    },
    formatK(num) {
      const n = Number(num)
      if (!Number.isFinite(n)) return '0'
      if (n >= 10000) {
        return (n / 10000).toFixed(1) + 'w'
      }
      return n.toFixed(0)
    },
    formatPrice(num) {
      const n = Number(num)
      if (!Number.isFinite(n)) return '0'
      if (n >= 10000) {
        return (n / 10000).toFixed(1) + 'w'
      }
      return n.toFixed(0)
    },
    calcProgress(order) {
       const total = Number(order.total_qty) || 0
       const recv = Number(order.received_qty) || 0
       if (!total) return 0
       return Math.min(100, Math.round((recv / total) * 100))
    },
    openItems(orderId) {
      uni.navigateTo({ url: `/pages/purchase/items?id=${encodeURIComponent(orderId)}` })
    },
    openEdit(orderId) {
      uni.navigateTo({ url: `/pages/purchase/edit?id=${encodeURIComponent(orderId)}` })
    },
    openReceive(orderId) {
      uni.navigateTo({ url: `/pages/purchase/receive?id=${encodeURIComponent(orderId)}` })
    },
    openCreate() {
      uni.navigateTo({ url: '/pages/purchase/edit' })
    },
    async fetchOrders() {
      this.loading = true
      try {
        const data = await api.getPurchaseOrdersSummary()
        // Sort by date descending
        this.orders = (data || []).sort((a, b) => {
          return new Date(b.expected_date) - new Date(a.expected_date)
        })
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
        console.error(err)
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
  background: #f1f5f9;
  padding: 24rpx;
  padding-bottom: 40rpx;
  box-sizing: border-box;
}

.hint-bar {
  background: #eef2ff;
  color: #4f46e5;
  padding: 16rpx 24rpx;
  border-radius: 16rpx;
  font-size: 24rpx;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 2rpx 6rpx rgba(79, 70, 229, 0.05);
}

/* Dashboard */
.dashboard-grid {
  display: flex;
  gap: 20rpx;
  margin-bottom: 32rpx;
}

.dash-card {
  flex: 1;
  background: #ffffff;
  padding: 24rpx 16rpx;
  border-radius: 20rpx;
  box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.03);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.dash-label {
  font-size: 22rpx;
  color: #64748b;
  margin-bottom: 8rpx;
}

.dash-value {
  font-size: 36rpx;
  font-weight: 700;
  color: #0f172a;
  
  &.highlight {
    color: #0f6a7b;
  }
}

.dash-action {
  width: 100rpx;
  background: #0f6a7b;
  border-radius: 20rpx;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #fff;
  box-shadow: 0 4rpx 12rpx rgba(15, 106, 123, 0.2);
  
  &:active {
    opacity: 0.9;
    transform: scale(0.98);
  }
}

.add-icon {
  font-size: 40rpx;
  font-weight: 300;
  line-height: 1;
  margin-bottom: 4rpx;
}

.add-label {
  font-size: 20rpx;
  font-weight: 500;
}

/* List */
.list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.order-card {
  background: #ffffff;
  border-radius: 20rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.03);
  overflow: hidden;
  transition: all 0.2s ease;
  border-left: 8rpx solid transparent;
  
  &.pending { border-left-color: #cbd5e1; }
  &.partial { border-left-color: #f59e0b; }
  &.done { border-left-color: #10b981; }

  &:active {
    transform: scale(0.99);
  }
}

.card-main {
  padding: 24rpx;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20rpx;
}

.supplier-row {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.supplier-name {
  font-size: 34rpx;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
}

.meta-row {
  display: flex;
  gap: 12rpx;
  align-items: center;
}

.date-tag, .id-tag {
  font-size: 22rpx;
  color: #64748b;
  background: #f1f5f9;
  padding: 4rpx 10rpx;
  border-radius: 8rpx;
  font-family: monospace;
}

.status-badge {
  font-size: 24rpx;
  padding: 8rpx 20rpx;
  border-radius: 999rpx;
  font-weight: 600;
  background: #f8fafc;
  color: #64748b;
  
  .partial & { background: #fffbeb; color: #b45309; }
  .done & { background: #ecfdf5; color: #047857; }
}

.card-body {
  margin-bottom: 24rpx;
}

.stats-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border-radius: 12rpx;
  padding: 16rpx 24rpx;
  margin-bottom: 20rpx;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
}

.stat-val {
  font-size: 28rpx;
  font-weight: 700;
  color: #334155;
}

.stat-lbl {
  font-size: 20rpx;
  color: #94a3b8;
}

.stat-sep {
  width: 1rpx;
  height: 24rpx;
  background: #e2e8f0;
}

.progress-section {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 22rpx;
}

.prog-label { color: #94a3b8; }
.prog-val { color: #0f6a7b; font-weight: 600; }

.progress-bg {
  height: 10rpx;
  background: #f1f5f9;
  border-radius: 999rpx;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #0f6a7b, #22c1c3);
  border-radius: 999rpx;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1rpx solid #f1f5f9;
  padding-top: 20rpx;
}

.expand-hint {
  font-size: 24rpx;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 6rpx;
}

.arrow {
  font-size: 20rpx;
}

.action-group {
  display: flex;
  gap: 16rpx;
}

.action-btn {
  padding: 12rpx 28rpx;
  border-radius: 12rpx;
  font-size: 24rpx;
  font-weight: 600;
  
  &.secondary { background: #f8fafc; color: #475569; }
  &.primary { 
    background: #0f6a7b; 
    color: #ffffff;
    box-shadow: 0 4rpx 12rpx rgba(15, 106, 123, 0.2);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80rpx 0;
  opacity: 0.6;
}

.empty-icon { font-size: 64rpx; margin-bottom: 16rpx; }
.empty-text { font-size: 28rpx; color: #94a3b8; }

.loading-state {
  text-align: center;
  padding: 40rpx;
  color: #94a3b8;
  font-size: 24rpx;
}
</style>
