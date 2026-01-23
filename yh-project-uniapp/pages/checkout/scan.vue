<template>
  <view class="page">
    <view class="header">
      <view class="header-top">
        <view class="page-title">扫码结账</view>
        <view class="nav-pill" @tap="goHome">
          <text>{{ homeLabel }}</text>
        </view>
      </view>
      <view class="header-hint">支持多单挂起，点击下方标签切换订单</view>
    </view>

    <view class="section order-section">
      <view class="order-controls">
        <view class="input-wrapper">
          <text class="input-label">当前订单</text>
          <input
            class="bare-input"
            v-model="activeOrderName"
            @blur="saveOrderName"
            placeholder="输入订单备注..."
          />
        </view>
        <view class="new-order-btn" @tap="createOrder">
          <text class="plus">+</text> 新单
        </view>
      </view>
      
      <scroll-view class="order-scroll" scroll-x show-scrollbar="false">
        <view class="order-list">
          <view
            v-for="order in orders"
            :key="order.id"
            :class="['order-card', order.id === activeOrderId ? 'active' : '']"
            @tap="switchOrder(order.id)"
          >
            <view class="order-info">
              <text class="order-name">{{ order.name }}</text>
              <text class="order-meta">{{ order.count }}件 · ¥{{ order.total.toFixed(2) }}</text>
            </view>
            <view class="order-close" @tap.stop="removeOrder(order.id)">×</view>
          </view>
        </view>
      </scroll-view>
    </view>

    <view class="section scan-section">
      <view class="scan-container">
        <input
          class="scan-input"
          v-model="barcodeInput"
          placeholder="点击输入条码或扫码..."
          confirm-type="search"
          @confirm="manualAdd"
        />
        <view class="scan-actions">
          <button class="btn-action btn-add" :loading="loading" @tap="manualAdd">添加</button>
          <button class="btn-action btn-scan" :loading="scanning" @tap="scanCode">
            扫码
          </button>
        </view>
      </view>
    </view>

    <view class="section list-section" v-if="activeItems.length">
      <view class="section-header">
        <text class="section-title">结算清单</text>
        <view class="badge">{{ activeItems.length }}</view>
      </view>
      
      <view class="cart-list">
        <view class="cart-item" v-for="(item, idx) in activeItems" :key="item.id">
          <view class="item-header">
            <text class="item-name">{{ item.name }}</text>
            <view class="item-stock">
              <text class="tag">{{ item.spec || '标规' }}</text>
              <text>库存 {{ formatStock(item.stock, item) }}</text>
            </view>
          </view>
          
          <view class="item-body">
            <!-- Quantity Inputs -->
            <view class="qty-group">
              <view class="qty-field">
                <text class="field-label">箱</text>
                <input class="qty-input" type="number" v-model.number="item.box" @blur="normalizeQty(item)" />
              </view>
              <view class="qty-field" v-if="item.specQty > 1">
                <text class="field-label">个</text>
                <input class="qty-input" type="number" v-model.number="item.loose" @blur="normalizeQty(item)" />
              </view>
            </view>
            
            <!-- Price Input -->
            <view class="price-field">
              <text class="currency">¥</text>
              <input class="price-input" type="digit" v-model.number="item.actual_price" placeholder="0.00" />
            </view>
            
            <!-- Remove -->
            <view class="remove-btn" @tap="removeItem(idx)">
              <text>×</text>
            </view>
          </view>
        </view>
      </view>
    </view>
    
    <view class="empty-state" v-else>
      <text>暂无商品，请扫码添加</text>
    </view>

    <view class="footer-spacer"></view>

    <view class="footer">
      <view class="summary-panel" @tap="openDiscountDialog">
        <view class="summary-count">共 {{ activeSummary.count }} 件</view>
        <view class="summary-total">
          <text class="symbol">¥</text>
          <text class="amount">{{ activeSummary.total.toFixed(2) }}</text>
        </view>
      </view>
      <view class="footer-btns">
        <button class="btn-footer btn-secondary" @tap="clearActiveOrder" :disabled="!activeItems.length">清空</button>
        <button class="btn-footer btn-primary" :loading="submitting" @tap="submitOrder">立即结算</button>
      </view>
    </view>

    <view class="dialog-overlay" v-if="showMatchDialog">
      <view class="dialog-card">
        <view class="dialog-header">
          <text class="dialog-title">选择匹配商品</text>
          <view class="dialog-close" @tap="closeMatchDialog">×</view>
        </view>
        <scroll-view class="dialog-scroll" scroll-y>
          <view class="match-list">
            <view class="match-item" v-for="item in matchedProducts" :key="item.barcode" @tap="selectMatched(item)">
              <view class="match-name">{{ item.product?.name }}</view>
              <view class="match-detail">条码 {{ item.barcode }} · {{ item.product?.spec }}</view>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>

    <view class="dialog-overlay" v-if="showDiscountDialog">
      <view class="dialog-card">
        <view class="dialog-header">
          <text class="dialog-title">整单优惠</text>
          <view class="dialog-close" @tap="closeDiscountDialog">×</view>
        </view>
        <view class="discount-form">
          <view class="form-row">
            <text class="label">原价</text>
            <text class="value">¥{{ discountBaseTotal.toFixed(2) }}</text>
          </view>
          <view class="form-row input-row">
            <text class="label">优惠后</text>
            <input
              class="modal-input"
              type="digit"
              inputmode="decimal"
              v-model="discountInput"
              placeholder="0.00"
            />
          </view>
          <view class="form-row highlight">
            <text class="label">已优惠</text>
            <text class="value red">-¥{{ discountDelta.toFixed(2) }}</text>
          </view>
          <view class="dialog-actions">
            <button class="btn-modal btn-outline" @tap="clearDiscount">不优惠</button>
            <button class="btn-modal btn-primary" @tap="applyDiscount">确认</button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'
import { getRole, isOwner } from '../../common/auth.js'
import { piecesPerBox, formatStock } from '../../common/stock.js'

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
      matchedProducts: [],
      showDiscountDialog: false,
      discountInput: '',
      discountBaseTotal: 0
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
      const base = this.calcSummary(this.activeOrder)
      const discount = this.normalizeDiscount(this.activeOrder, base.total)
      return {
        ...base,
        baseTotal: base.total,
        total: discount === null ? base.total : discount,
        discountTotal: discount
      }
    },
    isOwner() {
      return isOwner()
    },
    homeLabel() {
      const role = getRole()
      if (role === 'owner') return '运营总览'
      if (role === 'user') return '商品展示'
      return '货物定价总览'
    },
    discountDelta() {
      const val = this.parsePrice(this.discountInput)
      const base = Number(this.discountBaseTotal) || 0
      if (val === null) return 0
      const clamped = Math.min(Math.max(val, 0), base)
      return Math.max(0, base - clamped)
    }
  },
  onShow() {
    const role = getRole()
    if (role === 'user') {
      uni.reLaunch({ url: '/pages/products/showcase' })
      return
    }
    this.loadOrders()
  },
  methods: {
    piecesPerBox,
    formatStock,
    goHome() {
      const role = getRole()
      const target =
        role === 'owner'
          ? '/pages/dashboard/index'
          : role === 'user'
            ? '/pages/products/showcase'
            : '/pages/pricing/overview'
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
      const name = this.nextOrderName()
      const order = { id, name, items: [], count: 0, total: 0, discount_total: null }
      this.orders.push(order)
      this.activeOrderId = id
      this.activeOrderName = name
      this.refreshOrderStats()
      this.persistOrders()
      if (!silent) {
        uni.showToast({ title: '已新开单', icon: 'success' })
      }
    },
    nextOrderName() {
      const names = new Set(
        this.orders
          .map(o => String(o.name || '').trim())
          .filter(Boolean)
      )
      const used = new Set()
      names.forEach((name) => {
        const match = name.match(/^结算单(\d+)$/)
        if (match) used.add(Number(match[1]))
      })
      let idx = 1
      while (used.has(idx) || names.has(`结算单${idx}`)) {
        idx += 1
      }
      return `结算单${idx}`
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
      this.orders = this.orders.map(o => {
        const base = this.calcSummary(o)
        const discount = this.normalizeDiscount(o, base.total)
        return {
          ...o,
          count: base.count,
          total: discount === null ? base.total : discount
        }
      })
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
    normalizeDiscount(order, baseTotal) {
      if (!order) return null
      if (baseTotal <= 0) {
        if (order.discount_total !== null && order.discount_total !== undefined) {
          order.discount_total = null
        }
        return null
      }
      if (order.discount_total === null || order.discount_total === undefined || order.discount_total === '') {
        return null
      }
      const raw = Number(order.discount_total)
      if (!Number.isFinite(raw)) return null
      const clamped = Math.min(Math.max(raw, 0), Math.max(0, baseTotal))
      if (clamped !== raw) {
        order.discount_total = clamped
      }
      return clamped
    },
    parsePrice(val) {
      const num = parseFloat(val)
      return Number.isFinite(num) ? num : null
    },
    openDiscountDialog() {
      const order = this.activeOrder
      if (!order) return
      const base = this.calcSummary(order)
      if (base.total <= 0) {
        uni.showToast({ title: '暂无可优惠金额', icon: 'none' })
        return
      }
      const discount = this.normalizeDiscount(order, base.total)
      this.discountBaseTotal = base.total
      const preset = discount === null ? base.total : discount
      this.discountInput = Number(preset).toFixed(2)
      this.showDiscountDialog = true
    },
    closeDiscountDialog() {
      this.showDiscountDialog = false
    },
    applyDiscount() {
      const order = this.activeOrder
      if (!order) return
      const value = this.parsePrice(this.discountInput)
      if (value === null) {
        uni.showToast({ title: '请输入有效金额', icon: 'none' })
        return
      }
      const base = this.discountBaseTotal
      const clamped = Math.min(Math.max(value, 0), Math.max(0, base))
      const ratio = base > 0 ? clamped / base : 1
      const role = getRole()
      if (role !== 'owner' && ratio < 0.8) {
        uni.showToast({ title: '店员最低可打8折', icon: 'none' })
        return
      }
      const apply = () => {
        if (Math.abs(clamped - base) <= 0.01) {
          order.discount_total = null
        } else {
          order.discount_total = clamped
        }
        this.refreshOrderStats()
        this.persistOrders()
        this.closeDiscountDialog()
      }
      let content = `原合计 ¥${base.toFixed(2)}\n优惠后 ¥${clamped.toFixed(2)}`
      let title = '确认优惠'
      if (role === 'owner' && ratio < 0.5) {
        title = '低于5折提醒'
        content = `优惠低于5折，请确认。\n${content}`
      }
      uni.showModal({
        title,
        content,
        confirmText: '确认',
        cancelText: '返回',
        success: (res) => {
          if (res.confirm) {
            apply()
          }
        }
      })
    },
    clearDiscount() {
      const order = this.activeOrder
      if (!order) return
      order.discount_total = null
      this.refreshOrderStats()
      this.persistOrders()
      this.closeDiscountDialog()
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
            this.addProduct(matches[0].product, matches[0].multiplier)
            this.barcodeInput = ''
            return
          }
          if (matches.length > 1) {
            this.openMatchDialog(matches)
            return
          }
        }
        const result = await api.getProductByBarcode(code)
        this.addProduct(result.product, result.multiplier)
        this.barcodeInput = ''
      } catch (err) {
        uni.showToast({ title: '未找到条码商品', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    addProduct(product, multiplier = 1) {
      const order = this.activeOrder
      if (!order) return
      const specQty = this.piecesPerBox(product)
      const totalAdd = Math.max(1, Math.floor(multiplier || 1))
      const addBox = Math.floor(totalAdd / specQty)
      const addLoose = totalAdd % specQty
      const addUnits = addBox * specQty + addLoose
      const existing = order.items.find(i => i.id === product.id)
      const usedUnits = existing ? this.calcUnits(existing) : 0
      const available = product.stock || 0
      if (usedUnits + addUnits > available) {
        uni.showToast({ title: '库存不足', icon: 'none' })
        return
      }
      if (existing) {
        existing.box += addBox
        existing.loose += addLoose
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
        this.addProduct(item.product, item.multiplier)
        this.barcodeInput = ''
      }
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
      order.discount_total = null
      this.refreshOrderStats()
      this.persistOrders()
    },
    async submitOrder() {
      const order = this.activeOrder
      if (!order || !order.items.length) {
        uni.showToast({ title: '请先添加商品', icon: 'none' })
        return
      }
      const base = this.calcSummary(order)
      const discount = this.normalizeDiscount(order, base.total)
      const finalTotal = discount === null ? base.total : discount
      const ratio = base.total > 0 ? finalTotal / base.total : 1
      const username = uni.getStorageSync('yh-username') || ''
      const payload = order.items
        .map(item => {
          const qty = this.calcUnits(item)
          if (qty <= 0) return null
          return {
            product_id: item.id,
            quantity: qty,
            actual_price: Number(((Number(item.actual_price) || 0) * ratio).toFixed(2))
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
$primary: #0f6a7b;
$primary-light: #e0f2f1;
$primary-dark: #094a56;
$text-main: #111827;
$text-sub: #6b7280;
$border: #e5e7eb;
$bg-page: #f3f4f6;
$bg-card: #ffffff;
$red: #ef4444;

.page {
  min-height: 100vh;
  background: $bg-page;
  padding: 24rpx;
  box-sizing: border-box;
}

.header {
  margin-bottom: 24rpx;
  
  .header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .page-title {
    font-size: 40rpx;
    font-weight: 800;
    color: $text-main;
  }
  
  .nav-pill {
    background: $primary-light;
    color: $primary;
    padding: 8rpx 20rpx;
    border-radius: 999rpx;
    font-size: 24rpx;
    font-weight: 600;
  }
  
  .header-hint {
    margin-top: 8rpx;
    font-size: 24rpx;
    color: $text-sub;
  }
}

.section {
  background: $bg-card;
  border-radius: 20rpx;
  padding: 20rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 2rpx 6rpx rgba(0,0,0,0.03);
}

.order-section {
  padding: 16rpx; // tighter
  
  .order-controls {
    display: flex;
    gap: 16rpx;
    align-items: center;
    margin-bottom: 16rpx;
    
    .input-wrapper {
      flex: 1;
      display: flex;
      align-items: center;
      background: #f9fafb;
      padding: 12rpx 16rpx;
      border-radius: 12rpx;
      border: 1rpx solid $border;
      
      .input-label {
        font-size: 24rpx;
        color: $text-sub;
        margin-right: 12rpx;
      }
      
      .bare-input {
        flex: 1;
        font-size: 28rpx;
        color: $text-main;
      }
    }
    
    .new-order-btn {
      display: flex;
      align-items: center;
      background: #fff;
      border: 1rpx solid $primary;
      color: $primary;
      padding: 12rpx 20rpx;
      border-radius: 12rpx;
      font-size: 26rpx;
      font-weight: 600;
      
      .plus {
        margin-right: 4rpx;
        font-size: 32rpx;
        line-height: 1;
      }
    }
  }
  
  .order-scroll {
    white-space: nowrap;
    width: 100%;
  }
  
  .order-list {
    display: flex;
    gap: 16rpx;
    padding-bottom: 4rpx;
  }
  
  .order-card {
    display: inline-flex;
    align-items: center;
    background: #f9fafb;
    border: 1rpx solid $border;
    border-radius: 12rpx;
    padding: 12rpx 16rpx;
    min-width: 220rpx;
    position: relative;
    transition: all 0.2s;
    
    &.active {
      background: $primary-light;
      border-color: $primary;
      .order-name { color: $primary; }
    }
    
    .order-info {
      display: flex;
      flex-direction: column;
    }
    
    .order-name {
      font-size: 26rpx;
      font-weight: 600;
      color: $text-main;
    }
    
    .order-meta {
      font-size: 20rpx;
      color: $text-sub;
      margin-top: 2rpx;
    }
    
    .order-close {
      position: absolute;
      top: 6rpx;
      right: 10rpx;
      font-size: 30rpx;
      color: #9ca3af;
      line-height: 1;
      padding: 4rpx;
    }
  }
}

.scan-section {
  padding: 24rpx;
  
  .scan-container {
    display: flex;
    flex-direction: column;
    gap: 20rpx;
  }
  
  .scan-input {
    width: 100%;
    height: 88rpx;
    background: #f9fafb;
    border: 2rpx solid $border;
    border-radius: 16rpx;
    padding: 0 24rpx;
    font-size: 32rpx;
    box-sizing: border-box;
    transition: border-color 0.2s;
    
    &:focus {
      border-color: $primary;
      background: #fff;
    }
  }
  
  .scan-actions {
    display: flex;
    gap: 16rpx;
    
    .btn-action {
      flex: 1;
      height: 80rpx;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 16rpx;
      font-size: 30rpx;
      font-weight: 600;
      border: none;
      
      &.btn-add {
        background: #f3f4f6;
        color: $text-main;
      }
      
      &.btn-scan {
        background: $primary;
        color: #fff;
        flex: 1.5;
      }
    }
  }
}

.list-section {
  padding: 0 20rpx;
  background: transparent;
  box-shadow: none;
  
  .section-header {
    display: flex;
    align-items: center;
    margin-bottom: 16rpx;
    padding-left: 8rpx;
    
    .section-title {
      font-size: 30rpx;
      font-weight: 700;
      color: $text-main;
      margin-right: 12rpx;
    }
    
    .badge {
      background: $primary;
      color: #fff;
      font-size: 20rpx;
      padding: 2rpx 10rpx;
      border-radius: 999rpx;
    }
  }
}

.cart-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.cart-item {
  background: #fff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
  
  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16rpx;
    
    .item-name {
      font-size: 30rpx;
      font-weight: 600;
      color: $text-main;
      line-height: 1.4;
      flex: 1;
      margin-right: 16rpx;
    }
    
    .item-stock {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      font-size: 20rpx;
      color: $text-sub;
      
      .tag {
        background: #f3f4f6;
        color: $text-main;
        padding: 2rpx 8rpx;
        border-radius: 6rpx;
        margin-bottom: 4rpx;
      }
    }
  }
  
  .item-body {
    display: flex;
    align-items: flex-end;
    gap: 12rpx;
    
    .qty-group {
      flex: 1.2;
      display: flex;
      gap: 12rpx;
      
      .qty-field {
        flex: 1;
        
        .field-label {
          font-size: 20rpx;
          color: $text-sub;
          display: block;
          margin-bottom: 4rpx;
          text-align: center;
        }
        
        .qty-input {
          height: 64rpx;
          background: #f3f4f6;
          border-radius: 10rpx;
          text-align: center;
          font-size: 28rpx;
          font-weight: 600;
        }
      }
    }
    
    .price-field {
      flex: 1;
      position: relative;
      
      .currency {
        position: absolute;
        left: 12rpx;
        top: 18rpx;
        font-size: 24rpx;
        color: $text-sub;
      }
      
      .price-input {
        height: 64rpx;
        background: #fff;
        border: 1rpx solid $border;
        border-radius: 10rpx;
        padding-left: 36rpx;
        font-size: 28rpx;
        font-weight: 600;
      }
    }
    
    .remove-btn {
      width: 64rpx;
      height: 64rpx;
      display: flex;
      align-items: center;
      justify-content: center;
      color: $red;
      font-size: 40rpx;
      margin-left: 8rpx;
      opacity: 0.6;
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80rpx 0;
  color: #9ca3af;
}

.footer-spacer {
  height: 160rpx;
}

.footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  padding: 20rpx 24rpx calc(20rpx + env(safe-area-inset-bottom));
  box-shadow: 0 -4rpx 16rpx rgba(0,0,0,0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 10;
  
  .summary-panel {
    display: flex;
    flex-direction: column;
    
    .summary-count {
      font-size: 24rpx;
      color: $text-sub;
    }
    
    .summary-total {
      display: flex;
      align-items: baseline;
      color: $primary;
      font-weight: 700;
      
      .symbol {
        font-size: 28rpx;
        margin-right: 4rpx;
      }
      
      .amount {
        font-size: 44rpx;
        line-height: 1;
      }
    }
  }
  
  .footer-btns {
    display: flex;
    gap: 16rpx;
    
    .btn-footer {
      margin: 0;
      font-size: 28rpx;
      font-weight: 600;
      border-radius: 12rpx;
      padding: 0 32rpx;
      height: 80rpx;
      line-height: 80rpx;
      
      &.btn-secondary {
        background: #f3f4f6;
        color: $text-sub;
        border: none;
      }
      
      &.btn-primary {
        background: $primary;
        color: #fff;
        padding: 0 48rpx;
      }
    }
  }
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  backdrop-filter: blur(2px);
}

.dialog-card {
  width: 85%;
  background: #fff;
  border-radius: 24rpx;
  overflow: hidden;
  box-shadow: 0 20rpx 40rpx rgba(0,0,0,0.2);
  
  .dialog-header {
    padding: 24rpx;
    border-bottom: 1rpx solid $border;
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .dialog-title {
      font-size: 32rpx;
      font-weight: 700;
      color: $text-main;
    }
    
    .dialog-close {
      font-size: 36rpx;
      color: $text-sub;
      padding: 8rpx;
      line-height: 0.8;
    }
  }
  
  .dialog-scroll {
    max-height: 50vh;
  }
}

.match-list {
  padding: 8rpx 0;
  
  .match-item {
    padding: 20rpx 24rpx;
    border-bottom: 1rpx solid #f3f4f6;
    
    &:active {
      background: #f9fafb;
    }
    
    .match-name {
      font-size: 28rpx;
      font-weight: 600;
      color: $text-main;
    }
    
    .match-detail {
      font-size: 22rpx;
      color: $text-sub;
      margin-top: 4rpx;
    }
  }
}

.discount-form {
  padding: 32rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  
  .form-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 28rpx;
    
    &.input-row {
      align-items: center;
    }
    
    .label {
      color: $text-sub;
    }
    
    .value {
      font-weight: 600;
      color: $text-main;
      
      &.red { color: $red; }
    }
    
    .modal-input {
      width: 200rpx;
      text-align: right;
      font-size: 32rpx;
      font-weight: 600;
      border-bottom: 2rpx solid $primary;
      padding-bottom: 8rpx;
    }
  }
  
  .dialog-actions {
    display: flex;
    gap: 16rpx;
    margin-top: 16rpx;
    
    .btn-modal {
      flex: 1;
      font-size: 28rpx;
      border-radius: 12rpx;
      
      &.btn-outline {
        background: #fff;
        border: 1rpx solid $border;
        color: $text-sub;
      }
      
      &.btn-primary {
        background: $primary;
        color: #fff;
      }
    }
  }
}
</style>
