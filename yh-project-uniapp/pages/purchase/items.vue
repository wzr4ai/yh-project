<template>
  <view class="page">
    <view class="header-card" v-if="order">
      <view class="h-row">
         <text class="h-supplier">{{ order.supplier || '未命名供应商' }}</text>
         <text class="h-status" :class="statusClass(order.status)">{{ order.status }}</text>
      </view>
      <view class="h-meta">
        <text>单号: #{{ order.id.slice(-6) }}</text>
        <text>预计: {{ order.expected_date }}</text>
      </view>
    </view>

    <view class="list">
       <view class="list-header">
          <text class="col col-main">商品信息</text>
          <text class="col col-qty">数量</text>
          <text class="col col-cost" v-if="isOwner">单价/小计</text>
       </view>

       <view v-for="item in items" :key="item.id" class="item-card" @tap="openItemEdit(item)">
          <view class="col col-main">
             <text class="p-name">{{ item.product_name || item.product_id }}</text>
             <text class="p-spec">{{ item.product_spec || '—' }}</text>
          </view>
          <view class="col col-qty">
             <view class="qty-row">
               <text class="q-curr">{{ item.received_qty }}</text>
               <text class="q-sep">/</text>
               <text class="q-total">{{ item.quantity }}</text>
             </view>
          </view>
          <view class="col col-cost" v-if="isOwner">
             <view class="cost-row">
               <text class="c-unit">@{{ formatNum(item.expected_cost) }}</text>
               <text class="c-total">¥{{ formatNum(item.expected_cost * item.quantity) }}</text>
             </view>
          </view>
          <view class="arrow">></view>
       </view>
    </view>

    <view class="loading-more" v-if="loading">加载中...</view>
    <view class="no-more" v-if="!hasMore && items.length > 0">没有更多了</view>
    <view class="empty" v-if="!loading && items.length === 0">暂无明细</view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      orderId: '',
      order: null,
      items: [],
      offset: 0,
      limit: 50,
      total: 0,
      hasMore: true,
      loading: false,
      role: getRole()
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    }
  },
  onLoad(options) {
    this.orderId = options.id
    this.loadOrder()
    this.loadItems(true)
  },
  onShow() {
    this.role = getRole()
    const dirtyKey = `purchase:items_dirty:${this.orderId}`
    if (uni.getStorageSync(dirtyKey)) {
      uni.removeStorageSync(dirtyKey)
      this.loadItems(true)
    }
  },
  onPullDownRefresh() {
    Promise.all([this.loadOrder(), this.loadItems(true)]).then(() => {
      uni.stopPullDownRefresh()
    })
  },
  onReachBottom() {
    if (this.hasMore && !this.loading) {
      this.loadItems(false)
    }
  },
  methods: {
    statusClass(status) {
      if (status === '完成') return 'done'
      if (status === '部分到货') return 'partial'
      return 'pending'
    },
    formatNum(n) {
      return Number(n).toFixed(2).replace(/\.00$/, '')
    },
    async loadOrder() {
      try {
        this.order = await api.getPurchaseOrder(this.orderId)
      } catch (e) {
        console.error(e)
      }
    },
    async loadItems(reset = false) {
      if (this.loading) return
      this.loading = true
      if (reset) {
        this.offset = 0
        this.items = []
        this.total = 0
        this.hasMore = true
      }
      
      try {
        const data = await api.getPurchaseOrderItems(this.orderId, { offset: this.offset, limit: this.limit })
        const list = (data && data.items) || []
        this.total = Number(data && data.total) || 0
        if (reset) {
          this.items = list
        } else {
          this.items = [...this.items, ...list]
        }
        this.offset += list.length
        this.hasMore = this.total ? this.items.length < this.total : list.length === this.limit
      } catch (e) {
        uni.showToast({ title: '加载明细失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    openItemEdit(item) {
      if (!this.isOwner) return
      uni.navigateTo({
        url: `/pages/purchase/item_edit?order_id=${encodeURIComponent(this.orderId)}&item_id=${encodeURIComponent(item.id)}`
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: #f1f5f9;
  padding: 24rpx;
}
.header-card {
  background: #fff;
  padding: 24rpx;
  border-radius: 20rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.03);
}
.h-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12rpx; }
.h-supplier { font-size: 32rpx; font-weight: 700; color: #1e293b; }
.h-status { font-size: 24rpx; padding: 4rpx 12rpx; border-radius: 8rpx; background: #f1f5f9; color: #64748b; }
.h-status.done { background: #ecfdf5; color: #047857; }
.h-status.partial { background: #fffbeb; color: #b45309; }
.h-meta { font-size: 24rpx; color: #94a3b8; display: flex; gap: 24rpx; }

.list-header {
  display: flex; padding: 0 24rpx 12rpx; 
  font-size: 24rpx; color: #94a3b8;
}
.col { overflow: hidden; }
.col-main { flex: 1; }
.col-qty { width: 140rpx; text-align: center; }
.col-cost { width: 180rpx; text-align: right; }

.item-card {
  background: #fff;
  padding: 24rpx;
  border-radius: 16rpx;
  margin-bottom: 16rpx;
  display: flex;
  align-items: center;
  position: relative;
  
  &:active { opacity: 0.8; }
}
.p-name { font-size: 28rpx; font-weight: 600; color: #334155; display: block; margin-bottom: 4rpx; }
.p-spec { font-size: 22rpx; color: #94a3b8; }

.qty-row { display: flex; align-items: baseline; justify-content: center; }
.q-curr { color: #0f6a7b; font-weight: 700; font-size: 28rpx; }
.q-sep { margin: 0 4rpx; color: #cbd5e1; font-size: 20rpx; }
.q-total { color: #64748b; font-size: 24rpx; }

.cost-row { display: flex; flex-direction: column; align-items: flex-end; }
.c-unit { font-size: 20rpx; color: #94a3b8; }
.c-total { font-size: 26rpx; font-weight: 600; color: #334155; }

.arrow { position: absolute; right: 12rpx; top: 50%; transform: translateY(-50%); font-size: 20rpx; color: #cbd5e1; opacity: 0; }
.item-card:active .arrow { opacity: 1; }

.loading-more, .no-more, .empty {
  text-align: center; color: #94a3b8; font-size: 24rpx; padding: 24rpx;
}
</style>
