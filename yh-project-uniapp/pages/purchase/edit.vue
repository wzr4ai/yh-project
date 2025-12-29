<template>
  <view class="page">
    <view class="card" v-if="order">
      <view class="header">
        <view>
          <view class="title">采购单编辑</view>
          <view class="sub">{{ order.id }}</view>
        </view>
        <view class="status" :class="statusClass(order.status)">{{ order.status }}</view>
      </view>
      <view class="info-grid">
        <view class="info-item">
          <view class="label">供应商</view>
          <view class="value">{{ order.supplier || '—' }}</view>
        </view>
        <view class="info-item">
          <view class="label">期望到货</view>
          <view class="value">{{ order.expected_date || '—' }}</view>
        </view>
        <view class="info-item" v-if="order.remark">
          <view class="label">备注</view>
          <view class="value">{{ order.remark }}</view>
        </view>
      </view>
    </view>

    <view class="card summary" v-if="order">
      <view class="summary-row">
        <view>
          <view class="mini-title">计划箱数</view>
          <view class="mini-value">{{ stats.total }}</view>
        </view>
        <view>
          <view class="mini-title">已到箱数</view>
          <view class="mini-value">{{ stats.received }}</view>
        </view>
        <view>
          <view class="mini-title">到货进度</view>
          <view class="mini-value">{{ stats.progress }}%</view>
        </view>
        <view v-if="isOwner">
          <view class="mini-title">预计总成本</view>
          <view class="mini-value">¥{{ stats.cost.toFixed(2) }}</view>
        </view>
      </view>
      <view class="progress-bar">
        <view class="progress" :style="{ width: stats.progress + '%' }"></view>
      </view>
      <view class="actions">
        <button size="mini" @tap="fillAllReceived">全部到货</button>
        <button size="mini" @tap="clearReceived">清空到货</button>
      </view>
    </view>

    <view class="card" v-if="order">
      <view class="section-title">到货明细</view>
      <view v-for="(item, idx) in formItems" :key="item.product_id" class="item-row">
        <view class="item-header">
          <view>
            <view class="item-name">{{ productName(item) }}</view>
            <view class="item-meta">{{ productSpec(item) }}</view>
          </view>
          <view class="tag">计划 {{ item.quantity }} 箱</view>
        </view>
        <view class="item-grid">
          <view class="field">
            <view class="label">已到箱数</view>
            <input class="input" type="number" v-model.number="item.received_qty" @blur="normalizeReceived(item)" />
          </view>
          <view class="field">
            <view class="label">预计单价</view>
            <view class="value">¥{{ formatMoney(item.expected_cost) }}</view>
          </view>
          <view class="field">
            <view class="label">实际单价</view>
            <input
              class="input"
              type="digit"
              inputmode="decimal"
              v-model="item.actual_cost"
              placeholder="可为空"
            />
          </view>
          <view class="field">
            <view class="label">预计小计</view>
            <view class="value">¥{{ lineCost(item).toFixed(2) }}</view>
          </view>
        </view>
        <view class="row-actions">
          <button size="mini" @tap="fillRowReceived(idx)">本行到货</button>
          <button size="mini" @tap="clearRowReceived(idx)">本行清空</button>
        </view>
      </view>
    </view>

    <view v-if="!order && !loading" class="empty">未找到采购单</view>
    <view v-if="loading" class="empty">加载中...</view>

    <view class="footer" v-if="order">
      <button size="mini" @tap="goBack">返回</button>
      <button size="mini" type="primary" :loading="saving" @tap="submitReceive">保存到货</button>
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
      orderId: '',
      order: null,
      formItems: [],
      productMap: {},
      loading: false,
      saving: false
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    stats() {
      const items = this.formItems || []
      let total = 0
      let received = 0
      let cost = 0
      items.forEach(item => {
        const qty = Number(item.quantity) || 0
        const recv = Number(item.received_qty) || 0
        total += qty
        received += recv
        if (this.isOwner) cost += (Number(item.expected_cost) || 0) * qty
      })
      const progress = total ? Math.min(100, Math.round((received / total) * 100)) : 0
      return { total, received, progress, cost }
    }
  },
  onLoad(options) {
    this.orderId = options.id || ''
  },
  onShow() {
    this.role = getRole()
    if (!this.isOwner) {
      uni.showToast({ title: '仅老板可编辑', icon: 'none' })
      uni.navigateBack()
      return
    }
    this.fetchOrder()
  },
  methods: {
    statusClass(status) {
      if (status === '完成') return 'done'
      if (status === '部分到货') return 'partial'
      return 'pending'
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
    normalizeReceived(item) {
      const max = Number(item.quantity) || 0
      let recv = Math.floor(Number(item.received_qty) || 0)
      if (recv < 0) recv = 0
      if (recv > max) recv = max
      item.received_qty = recv
    },
    fillRowReceived(idx) {
      const row = this.formItems[idx]
      if (!row) return
      row.received_qty = Number(row.quantity) || 0
    },
    clearRowReceived(idx) {
      const row = this.formItems[idx]
      if (!row) return
      row.received_qty = 0
    },
    fillAllReceived() {
      this.formItems.forEach(item => {
        item.received_qty = Number(item.quantity) || 0
      })
    },
    clearReceived() {
      this.formItems.forEach(item => {
        item.received_qty = 0
      })
    },
    async loadProductMap() {
      const ids = new Set()
      this.formItems.forEach(item => {
        if (item.product_id && !this.productMap[item.product_id]) {
          ids.add(item.product_id)
        }
      })
      for (const id of ids) {
        try {
          const product = await api.getProduct(id)
          this.$set(this.productMap, id, product)
        } catch (err) {
          this.$set(this.productMap, id, { id, name: id })
        }
      }
    },
    async fetchOrder() {
      if (!this.orderId) return
      this.loading = true
      try {
        const orders = await api.getPurchaseOrders()
        const order = (orders || []).find(o => o.id === this.orderId)
        if (!order) {
          this.order = null
          return
        }
        this.order = order
        this.formItems = (order.items || []).map(item => ({
          ...item,
          quantity: Number(item.quantity) || 0,
          received_qty: Number(item.received_qty) || 0,
          expected_cost: item.expected_cost
        }))
        await this.loadProductMap()
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    buildPayload() {
      return this.formItems.map(item => {
        const actual = item.actual_cost === '' || item.actual_cost === null ? null : Number(item.actual_cost)
        return {
          product_id: item.product_id,
          quantity: Number(item.quantity) || 0,
          expected_cost: Number(item.expected_cost) || 0,
          received_qty: Math.floor(Number(item.received_qty) || 0),
          actual_cost: Number.isFinite(actual) ? actual : null
        }
      })
    },
    async submitReceive() {
      if (!this.orderId) return
      this.saving = true
      try {
        const payload = this.buildPayload()
        const updated = await api.receivePurchaseOrder(this.orderId, payload)
        this.order = updated
        this.formItems = (updated.items || []).map(item => ({
          ...item,
          quantity: Number(item.quantity) || 0,
          received_qty: Number(item.received_qty) || 0,
          expected_cost: item.expected_cost
        }))
        await this.loadProductMap()
        uni.showToast({ title: '已保存', icon: 'success' })
      } catch (err) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    goBack() {
      uni.navigateBack()
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
  padding-bottom: 140rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
  margin-bottom: 14rpx;
}

.header {
  display: flex;
  justify-content: space-between;
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

.status {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  color: #ffffff;
  height: fit-content;
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

.info-grid {
  margin-top: 12rpx;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220rpx, 1fr));
  gap: 12rpx;
}

.info-item {
  background: #f9fafb;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 12rpx;
}

.label {
  color: #6b7280;
  font-size: 22rpx;
}

.value {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #0b1f3a;
  font-weight: 600;
}

.summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.mini-title {
  color: #6b7280;
  font-size: 22rpx;
}

.mini-value {
  margin-top: 4rpx;
  font-size: 30rpx;
  font-weight: 700;
  color: #0b1f3a;
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

.actions {
  display: flex;
  gap: 12rpx;
  margin-top: 12rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.item-row {
  border-top: 1rpx dashed #e5e7eb;
  padding-top: 12rpx;
  margin-top: 12rpx;
}

.item-row:first-of-type {
  border-top: none;
  padding-top: 0;
  margin-top: 0;
}

.item-header {
  display: flex;
  justify-content: space-between;
  gap: 12rpx;
}

.item-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.item-meta {
  font-size: 22rpx;
  color: #6b7280;
  margin-top: 4rpx;
}

.tag {
  padding: 6rpx 12rpx;
  background: #e6f4f6;
  color: #0f6a7b;
  border-radius: 999rpx;
  font-size: 22rpx;
  height: fit-content;
}

.item-grid {
  margin-top: 12rpx;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200rpx, 1fr));
  gap: 12rpx;
}

.field .input {
  width: 100%;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 10rpx 12rpx;
  font-size: 24rpx;
  margin-top: 6rpx;
}

.row-actions {
  display: flex;
  gap: 10rpx;
  margin-top: 10rpx;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40rpx 0;
}

.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: #ffffff;
  padding: 12rpx 20rpx env(safe-area-inset-bottom);
  display: flex;
  gap: 12rpx;
  box-shadow: 0 -6rpx 12rpx rgba(0, 0, 0, 0.05);
}
</style>
