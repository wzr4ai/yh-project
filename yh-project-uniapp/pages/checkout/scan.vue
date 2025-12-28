<template>
  <view class="page">
    <view class="card header">
      <view class="header-row">
        <view class="title">扫码结账</view>
        <view class="nav-btn" @tap="goHome">{{ homeLabel }}</view>
      </view>
      <view class="sub">支持同时挂多单，切换订单继续扫码。</view>
    </view>

    <view class="card">
      <view class="order-row">
        <view class="order-field">
          <view class="label">当前订单</view>
          <input class="input" v-model="activeOrderName" @blur="saveOrderName" placeholder="客户名 / 订单备注" />
        </view>
        <button size="mini" type="primary" @tap="createOrder">新开单</button>
      </view>
      <scroll-view class="order-tabs" scroll-x>
        <view
          v-for="order in orders"
          :key="order.id"
          :class="['order-tab', order.id === activeOrderId ? 'active' : '']"
          @tap="switchOrder(order.id)"
        >
          <view class="order-name">{{ order.name }}</view>
          <view class="order-meta">{{ order.count }} 件 ｜ ¥{{ order.total.toFixed(2) }}</view>
          <text class="order-close" @tap.stop="removeOrder(order.id)">×</text>
        </view>
      </scroll-view>
    </view>

    <view class="card">
      <view class="scan-row">
        <input
          class="input"
          v-model="barcodeInput"
          placeholder="输入条码"
          confirm-type="search"
          @confirm="manualAdd"
        />
        <button size="mini" type="primary" :loading="loading" @tap="manualAdd">添加</button>
        <button size="mini" @tap="scanCode" :loading="scanning">扫码</button>
      </view>
      <view class="hint">每次扫码默认 +1 个，可在下方调整数量。</view>
    </view>

    <view class="card" v-if="activeItems.length">
      <view class="card-title">结算清单</view>
      <view class="cart-item" v-for="(item, idx) in activeItems" :key="item.id">
        <view class="cart-header">
          <view class="name">{{ item.name }}</view>
          <view class="spec">规格 {{ item.spec || '—' }} ｜ 库存 {{ item.stock }}</view>
        </view>
        <view class="cart-row">
          <view class="field">
            <view class="mini-title">箱</view>
            <input class="input" type="number" v-model.number="item.box" @blur="normalizeQty(item)" />
          </view>
          <view class="field" v-if="item.specQty > 1">
            <view class="mini-title">个</view>
            <input class="input" type="number" v-model.number="item.loose" @blur="normalizeQty(item)" />
          </view>
          <view class="field">
            <view class="mini-title">实际单价</view>
            <input class="input" type="digit" v-model.number="item.actual_price" placeholder="¥" />
          </view>
          <button size="mini" type="warn" @tap="removeItem(idx)">移除</button>
        </view>
      </view>
    </view>
    <view class="empty" v-else>请扫码或输入条码添加商品</view>

    <view class="footer">
      <view class="summary">
        <view>共 {{ activeSummary.count }} 件</view>
        <view>合计 ¥{{ activeSummary.total.toFixed(2) }}</view>
      </view>
      <button size="mini" @tap="clearActiveOrder" :disabled="!activeItems.length">清空</button>
      <button size="mini" type="primary" :loading="submitting" @tap="submitOrder">提交结算单</button>
    </view>

    <view class="dialog" v-if="showMatchDialog">
      <view class="dialog-content">
        <view class="dialog-header">
          <view class="dialog-title">选择匹配条码</view>
          <button size="mini" @tap="closeMatchDialog">关闭</button>
        </view>
        <scroll-view class="dialog-body" scroll-y>
          <view class="match-row" v-for="item in matchedProducts" :key="item.id" @tap="selectMatched(item)">
            <view class="match-name">{{ item.name }}</view>
            <view class="match-meta">条码 {{ item.barcode || '—' }} ｜ 规格 {{ item.spec || '—' }}</view>
          </view>
          <view v-if="!matchedProducts.length" class="empty">无匹配结果</view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'
import { isOwner } from '../../common/auth.js'

const STORAGE_KEY = 'checkout-orders'

export default {
  data() {
    return {
      orders: [],
      activeOrderId: '',
      activeOrderName: '',
      barcodeInput: '',
      loading: false,
      scanning: false,
      submitting: false,
      showMatchDialog: false,
      matchedProducts: []
    }
  },
  computed: {
    activeOrder() {
      return this.orders.find(o => o.id === this.activeOrderId) || null
    },
    activeItems() {
      return this.activeOrder?.items || []
    },
    activeSummary() {
      return this.calcSummary(this.activeOrder)
    },
    isOwner() {
      return isOwner()
    },
    homeLabel() {
      return this.isOwner ? '运营总览' : '货物定价总览'
    }
  },
  onShow() {
    this.loadOrders()
  },
  methods: {
    goHome() {
      const target = this.isOwner ? '/pages/dashboard/index' : '/pages/pricing/overview'
      uni.navigateTo({ url: target })
    },
    loadOrders() {
      try {
        const cached = uni.getStorageSync(STORAGE_KEY)
        if (cached && cached.orders && cached.orders.length) {
          this.orders = cached.orders.map(o => ({
            ...o,
            items: o.items || []
          }))
          this.activeOrderId = cached.activeOrderId || this.orders[0].id
        }
      } catch (e) {}
      if (!this.orders.length) {
        this.createOrder(true)
      } else {
        this.refreshOrderStats()
        this.syncActiveName()
      }
    },
    persistOrders() {
      try {
        uni.setStorageSync(STORAGE_KEY, {
          orders: this.orders,
          activeOrderId: this.activeOrderId
        })
      } catch (e) {}
    },
    createOrder(silent) {
      const id = `order_${Date.now()}_${Math.floor(Math.random() * 1000)}`
      const name = `结算单${this.orders.length + 1}`
      const order = { id, name, items: [], count: 0, total: 0 }
      this.orders.push(order)
      this.activeOrderId = id
      this.activeOrderName = name
      this.refreshOrderStats()
      this.persistOrders()
      if (!silent) {
        uni.showToast({ title: '已新开单', icon: 'success' })
      }
    },
    switchOrder(id) {
      if (id === this.activeOrderId) return
      this.activeOrderId = id
      this.syncActiveName()
      this.persistOrders()
    },
    removeOrder(id) {
      if (this.orders.length <= 1) {
        uni.showToast({ title: '至少保留一个订单', icon: 'none' })
        return
      }
      const idx = this.orders.findIndex(o => o.id === id)
      if (idx < 0) return
      this.orders.splice(idx, 1)
      if (this.activeOrderId === id) {
        this.activeOrderId = this.orders[0]?.id || ''
        this.syncActiveName()
      }
      this.refreshOrderStats()
      this.persistOrders()
    },
    syncActiveName() {
      const order = this.activeOrder
      this.activeOrderName = order ? order.name : ''
    },
    saveOrderName() {
      const order = this.activeOrder
      if (!order) return
      const name = this.activeOrderName.trim() || order.name
      order.name = name
      this.activeOrderName = name
      this.persistOrders()
    },
    refreshOrderStats() {
      this.orders = this.orders.map(o => ({
        ...o,
        ...this.calcSummary(o)
      }))
    },
    calcSummary(order) {
      if (!order) return { count: 0, total: 0 }
      const items = order.items || []
      let count = 0
      let total = 0
      items.forEach(item => {
        const qty = this.calcUnits(item)
        count += qty
        total += qty * (Number(item.actual_price) || 0)
      })
      return { count, total }
    },
    scanCode() {
      this.scanning = true
      uni.scanCode({
        onlyFromCamera: true,
        scanType: ['barCode', 'qrCode'],
        success: (res) => {
          this.barcodeInput = res.result || ''
          this.scanAdd()
        },
        fail: () => {
          uni.showToast({ title: '扫码失败', icon: 'none' })
        },
        complete: () => {
          this.scanning = false
        }
      })
    },
    manualAdd() {
      this.addByBarcode(true)
    },
    scanAdd() {
      this.addByBarcode(false)
    },
    async addByBarcode(useSuffixMatch) {
      const code = this.barcodeInput.trim()
      if (!code) return
      this.loading = true
      try {
        if (useSuffixMatch) {
          const matches = await api.getProductsByBarcodeSuffix(code, 20)
          if (matches.length === 1) {
            this.addProduct(matches[0])
            this.barcodeInput = ''
            return
          }
          if (matches.length > 1) {
            this.openMatchDialog(matches)
            return
          }
        }
        const product = await api.getProductByBarcode(code)
        this.addProduct(product)
        this.barcodeInput = ''
      } catch (err) {
        uni.showToast({ title: '未找到条码商品', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    addProduct(product) {
      const order = this.activeOrder
      if (!order) return
      const specQty = this.parseSpecQty(product.spec)
      const addBox = specQty > 1 ? 0 : 1
      const addLoose = specQty > 1 ? 1 : 0
      const addUnits = addBox * specQty + (specQty > 1 ? addLoose : 0)
      const existing = order.items.find(i => i.id === product.id)
      const usedUnits = existing ? this.calcUnits(existing) : 0
      const available = product.stock || 0
      if (usedUnits + addUnits > available) {
        uni.showToast({ title: '库存不足', icon: 'none' })
        return
      }
      if (existing) {
        existing.box += addBox
      } else {
        order.items.push({
          id: product.id,
          name: product.name,
          spec: product.spec,
          specQty,
          category_name: product.category_name,
          stock: product.stock || 0,
          box: addBox,
          loose: addLoose,
          actual_price: product.standard_price || product.price_min || 0
        })
      }
      this.refreshOrderStats()
      this.persistOrders()
      uni.showToast({ title: '已加入', icon: 'success' })
    },
    openMatchDialog(matches) {
      this.matchedProducts = matches || []
      this.showMatchDialog = true
    },
    closeMatchDialog() {
      this.showMatchDialog = false
      this.matchedProducts = []
    },
    selectMatched(item) {
      this.closeMatchDialog()
      if (item) {
        this.addProduct(item)
        this.barcodeInput = ''
      }
    },
    parseSpecQty(spec) {
      const match = String(spec || '').match(/(\d+(\.\d+)?)/)
      const val = match ? parseFloat(match[1]) : 1
      return val > 0 ? val : 1
    },
    calcUnits(item) {
      const specQty = item.specQty || 1
      const box = Number(item.box) || 0
      const loose = specQty > 1 ? Number(item.loose) || 0 : 0
      return Math.max(0, Math.floor(box * specQty + loose))
    },
    normalizeQty(item) {
      const specQty = item.specQty || 1
      const stock = item.stock || 0
      let box = Math.max(0, Math.floor(item.box || 0))
      let loose = specQty > 1 ? Math.max(0, Math.floor(item.loose || 0)) : 0
      let total = box * specQty + loose
      if (total > stock) {
        const maxBox = Math.floor(stock / specQty)
        const maxLoose = stock - maxBox * specQty
        box = maxBox
        loose = specQty > 1 ? maxLoose : 0
      }
      item.box = box
      item.loose = loose
      this.refreshOrderStats()
      this.persistOrders()
    },
    removeItem(idx) {
      const order = this.activeOrder
      if (!order) return
      order.items.splice(idx, 1)
      this.refreshOrderStats()
      this.persistOrders()
    },
    clearActiveOrder() {
      const order = this.activeOrder
      if (!order) return
      order.items = []
      this.refreshOrderStats()
      this.persistOrders()
    },
    async submitOrder() {
      const order = this.activeOrder
      if (!order || !order.items.length) {
        uni.showToast({ title: '请先添加商品', icon: 'none' })
        return
      }
      const username = uni.getStorageSync('yh-username') || ''
      const payload = order.items
        .map(item => {
          const qty = this.calcUnits(item)
          if (qty <= 0) return null
          return {
            product_id: item.id,
            quantity: qty,
            actual_price: Number(item.actual_price) || 0
          }
        })
        .filter(Boolean)
      if (!payload.length) {
        uni.showToast({ title: '数量无效', icon: 'none' })
        return
      }
      this.submitting = true
      try {
        await api.createSales(payload, username)
        uni.showToast({ title: '结算完成', icon: 'success' })
        if (this.orders.length > 1) {
          this.removeOrder(order.id)
        } else {
          order.items = []
          this.refreshOrderStats()
          this.persistOrders()
        }
      } catch (err) {
        uni.showToast({ title: '提交失败', icon: 'none' })
      } finally {
        this.submitting = false
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
  padding-bottom: 140rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
  margin-bottom: 16rpx;
}

.header .title {
  font-size: 32rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}

.nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6rpx 18rpx;
  border-radius: 999rpx;
  font-size: 24rpx;
  background: #0f6a7b;
  color: #ffffff;
}

.header .sub {
  margin-top: 6rpx;
  color: #6b7280;
  font-size: 24rpx;
}

.order-row {
  display: flex;
  align-items: flex-end;
  gap: 12rpx;
}

.order-field {
  flex: 1;
}

.label {
  font-size: 24rpx;
  color: #6b7280;
  margin-bottom: 6rpx;
}

.input {
  width: 100%;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 14rpx;
  font-size: 26rpx;
  background: #fff;
}

.order-tabs {
  display: flex;
  gap: 12rpx;
  margin-top: 14rpx;
  white-space: nowrap;
}

.order-tab {
  position: relative;
  min-width: 200rpx;
  padding: 12rpx 16rpx;
  border-radius: 12rpx;
  border: 1rpx solid #e5e7eb;
  background: #f9fafb;
  display: inline-flex;
  flex-direction: column;
  gap: 6rpx;
}

.order-tab.active {
  border-color: #0f6a7b;
  background: #e6f4f6;
}

.order-name {
  font-size: 26rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.order-meta {
  font-size: 22rpx;
  color: #6b7280;
}

.order-close {
  position: absolute;
  top: 6rpx;
  right: 10rpx;
  font-size: 26rpx;
  color: #9ca3af;
}

.scan-row {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.hint {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #9ca3af;
}

.card-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.cart-item {
  padding: 16rpx 0;
  border-top: 1rpx dashed #e5e7eb;
}

.cart-item:first-child {
  border-top: none;
}

.cart-header {
  margin-bottom: 10rpx;
}

.name {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.spec {
  font-size: 22rpx;
  color: #6b7280;
  margin-top: 4rpx;
}

.cart-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  align-items: flex-end;
}

.field {
  min-width: 160rpx;
  flex: 1;
}

.mini-title {
  font-size: 22rpx;
  color: #6b7280;
  margin-bottom: 4rpx;
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
  box-shadow: 0 -6rpx 12rpx rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.summary {
  flex: 1;
  font-size: 24rpx;
  color: #0b1f3a;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.dialog {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}

.dialog-content {
  width: 86%;
  max-height: 70vh;
  background: #ffffff;
  border-radius: 16rpx;
  padding: 16rpx;
  box-shadow: 0 12rpx 30rpx rgba(15, 23, 42, 0.2);
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.dialog-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.dialog-body {
  max-height: 50vh;
}

.match-row {
  padding: 12rpx 0;
  border-bottom: 1rpx dashed #e5e7eb;
}

.match-row:last-child {
  border-bottom: none;
}

.match-name {
  font-size: 26rpx;
  color: #0b1f3a;
  font-weight: 600;
}

.match-meta {
  font-size: 22rpx;
  color: #6b7280;
  margin-top: 4rpx;
}
</style>
