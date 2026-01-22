<template>
  <view class="page">
    <view class="card">
      <view class="header">
        <view>
          <view class="title">{{ isCreate ? '新建采购单' : '采购单编辑' }}</view>
          <view class="sub" v-if="orderId">{{ orderId }}</view>
        </view>
        <view class="status-chip">{{ form.status }}</view>
      </view>
      <view class="form-grid">
        <view class="form-row">
          <view class="label">供应商</view>
          <input class="input" v-model="form.supplier" placeholder="供应商名称" />
        </view>
        <view class="form-row">
          <view class="label">期望到货</view>
          <picker mode="date" :value="form.expected_date" @change="onDateChange">
            <view class="picker">{{ form.expected_date || '选择日期' }}</view>
          </picker>
        </view>
        <view class="form-row">
          <view class="label">状态</view>
          <picker :range="statusOptions" :value="statusIndex" @change="onStatusChange">
            <view class="picker">{{ form.status }}</view>
          </picker>
        </view>
        <view class="form-row">
          <view class="label">备注</view>
          <input class="input" v-model="form.remark" placeholder="可选" />
        </view>
      </view>
    </view>

    <view class="card summary">
      <view class="summary-row">
        <view>
          <view class="mini-title">计划箱数</view>
          <view class="mini-value">{{ stats.total }}</view>
        </view>
        <view>
          <view class="mini-title">预计总成本</view>
          <view class="mini-value">¥{{ stats.cost.toFixed(2) }}</view>
        </view>
        <view>
          <view class="mini-title">商品数量</view>
          <view class="mini-value">{{ formItems.length }}</view>
        </view>
      </view>
      <view class="progress-bar">
        <view class="progress" :style="{ width: stats.progress + '%' }"></view>
      </view>
      <view class="mini-hint">进度仅用于显示，后续到货逻辑会另行处理。</view>
    </view>

    <view class="card">
      <view class="section-header">
        <view class="section-title">订货明细</view>
        <button size="mini" type="primary" @tap="openDialog">添加商品</button>
      </view>

      <view v-for="(item, idx) in formItems" :key="item.product_id" class="item-row" @tap="openEditItem(idx)">
        <view class="item-compact">
          <view class="item-main">
            <view class="item-name">{{ productName(item) }}</view>
            <view class="item-meta">{{ productSpec(item) }}</view>
          </view>
          <view class="item-stats">
            <view class="stat-pill">
              <text class="label">箱数</text>
              <text class="val">{{ item.quantity }}</text>
            </view>
            <view class="stat-pill">
              <text class="label">单价</text>
              <text class="val">¥{{ formatMoney(item.expected_cost) }}</text>
            </view>
          </view>
          <view class="item-total">
            ¥{{ lineCost(item).toFixed(2) }}
          </view>
        </view>
        <view class="item-action" @tap.stop="removeItem(idx)">
          <view class="delete-icon">×</view>
        </view>
      </view>

      <view v-if="!formItems.length" class="empty">请先添加订货商品</view>
    </view>

    <view class="dialog" v-if="showDialog">
      <view class="dialog-content">
        <view class="dialog-header">
          <view class="dialog-title">添加订货商品</view>
          <button size="mini" @tap="closeDialog">关闭</button>
        </view>
        <view class="search-bar">
          <input class="search" v-model="keyword" placeholder="输入关键字搜索" confirm-type="search" @confirm="searchProducts" />
          <button size="mini" @tap="searchProducts">搜索</button>
        </view>
        <scroll-view scroll-y class="dialog-body">
          <view v-for="prod in searchResults" :key="prod.id" class="row">
            <view class="info">
              <view class="name">{{ prod.name }}</view>
              <view class="meta">{{ prod.spec || '—' }}</view>
            </view>
            <button size="mini" type="primary" @tap="addProduct(prod)">添加</button>
          </view>
          <view v-if="!searchResults.length" class="empty">请输入关键字搜索商品</view>
        </scroll-view>
      </view>
    </view>

    <view class="footer">
      <button size="mini" @tap="goBack">返回</button>
      <button v-if="!isCreate" size="mini" type="warn" @tap="confirmDelete">删除</button>
      <button size="mini" type="primary" :loading="saving" @tap="saveOrder">保存采购单</button>
    </view>

    <!-- Edit Sheet -->
    <view class="edit-mask" v-if="showEditSheet" @tap="closeEditSheet">
      <view class="edit-sheet" @tap.stop>
        <view class="sheet-header">
          <text class="sheet-title">编辑商品</text>
          <view class="sheet-close" @tap="closeEditSheet">×</view>
        </view>
        
        <view class="sheet-body">
          <view class="sheet-info" v-if="editingIndex >= 0">
            <text class="sheet-name">{{ productName(formItems[editingIndex]) }}</text>
            <text class="sheet-spec">{{ productSpec(formItems[editingIndex]) }}</text>
          </view>
          
          <view class="sheet-form">
            <view class="sheet-field">
              <text class="sheet-label">订货箱数</text>
              <input class="sheet-input" type="number" v-model.number="editForm.quantity" :focus="true" />
            </view>
            <view class="sheet-field">
              <text class="sheet-label">预计单价 (¥)</text>
              <input class="sheet-input" type="digit" inputmode="decimal" v-model="editForm.expected_cost" />
            </view>
          </view>
          
          <view class="sheet-summary">
            <text>小计:</text>
            <text class="sheet-total">¥{{ editSheetSubtotal() }}</text>
          </view>
          
          <button class="sheet-confirm" type="primary" @tap="saveEditItem">确认修改</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { api } from '../../common/api.js'
import { piecesPerBox } from '../../common/stock.js'

export default {
  data() {
    return {
      role: getRole(),
      orderId: '',
      isCreate: true,
      form: {
        supplier: '',
        expected_date: '',
        remark: '',
        status: '待到货',
        created_by: ''
      },
      formItems: [],
      productMap: {},
      showDialog: false,
      keyword: '',
      searchResults: [],
      loading: false,
      saving: false,
      statusOptions: ['待到货', '部分到货', '完成'],
      // Item Editor State
      showEditSheet: false,
      editingIndex: -1,
      editForm: {
        quantity: 0,
        expected_cost: 0
      }
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    stats() {
      let total = 0
      let received = 0
      let cost = 0
      this.formItems.forEach(item => {
        const qty = Number(item.quantity) || 0
        const recv = Number(item.received_qty) || 0
        total += qty
        received += recv
        cost += (Number(item.expected_cost) || 0) * qty
      })
      const progress = total ? Math.min(100, Math.round((received / total) * 100)) : 0
      return { total, received, progress, cost }
    },
    statusIndex() {
      const idx = this.statusOptions.indexOf(this.form.status)
      return idx >= 0 ? idx : 0
    }
  },
  onLoad(options) {
    const id = options.id || ''
    this.orderId = id
    this.isCreate = !id
  },
  onShow() {
    this.role = getRole()
    if (!this.isOwner) {
      uni.showToast({ title: '仅老板可编辑', icon: 'none' })
      uni.navigateBack()
      return
    }
    if (this.isCreate) {
      this.initNewOrder()
    } else {
      this.fetchOrder()
    }
  },
  methods: {
    formatMoney(value) {
      const num = Number(value)
      if (!Number.isFinite(num)) return '0.00'
      return num.toFixed(2)
    },
    initNewOrder() {
      const today = new Date()
      const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(
        today.getDate()
      ).padStart(2, '0')}`
      this.form = {
        supplier: '',
        expected_date: dateStr,
        remark: '',
        status: '待到货',
        created_by: uni.getStorageSync('yh-username') || 'owner'
      }
      this.formItems = []
      this.productMap = {}
    },
    async fetchOrder() {
      if (!this.orderId) return
      this.loading = true
      try {
        const order = await api.getPurchaseOrder(this.orderId)
        this.form = {
          supplier: order.supplier || '',
          expected_date: order.expected_date || '',
          remark: order.remark || '',
          status: order.status || '待到货',
          created_by: order.created_by || uni.getStorageSync('yh-username') || 'owner'
        }
        this.formItems = (order.items || []).map(item => ({
          product_id: item.product_id,
          quantity: Number(item.quantity) || 0,
          expected_cost: item.expected_cost,
          received_qty: Number(item.received_qty) || 0,
          received_units: item.received_units === null || item.received_units === undefined ? null : Number(item.received_units) || 0,
          actual_cost: item.actual_cost
        }))
        await this.loadProductMap()
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    onDateChange(e) {
      this.form.expected_date = e.detail.value
    },
    onStatusChange(e) {
      const idx = Number(e.detail.value) || 0
      this.form.status = this.statusOptions[idx] || '待到货'
    },
    productName(item) {
      const product = this.productMap[item.product_id]
      return (product && product.name) || item.product_id
    },
    productSpec(item) {
      const product = this.productMap[item.product_id]
      return product && product.spec ? `规格 ${product.spec}` : '规格 —'
    },
    itemPiecesPerBox(item) {
      const product = this.productMap[item.product_id] || item
      return piecesPerBox(product)
    },
    lineCost(item) {
      const qty = Number(item.quantity) || 0
      const unit = Number(item.expected_cost) || 0
      return qty * unit
    },
    normalizeQuantity(item) {
      let qty = Math.floor(Number(item.quantity) || 0)
      if (qty < 0) qty = 0
      item.quantity = qty
    },
    removeItem(idx) {
      if (idx < 0) return
      this.formItems.splice(idx, 1)
    },
    openDialog() {
      this.showDialog = true
      this.keyword = ''
      this.searchResults = []
    },
    closeDialog() {
      this.showDialog = false
    },
    async searchProducts() {
      const kw = this.keyword.trim()
      if (!kw) {
        this.searchResults = []
        return
      }
      try {
        const list = await api.getProducts({ offset: 0, limit: 100, keyword: kw })
        this.searchResults = list?.items || []
      } catch (err) {
        uni.showToast({ title: '搜索失败', icon: 'none' })
      }
    },
    addProduct(product) {
      if (!product) return
      const existing = this.formItems.find(item => item.product_id === product.id)
      if (existing) {
        existing.quantity = (Number(existing.quantity) || 0) + 1
      } else {
        const expected = Number(product.box_cost_price || 0)
        this.formItems.push({
          product_id: product.id,
          quantity: 1,
          expected_cost: expected,
          received_qty: 0,
          received_units: 0,
          actual_cost: null
        })
      }
      this.$set(this.productMap, product.id, product)
      this.closeDialog()
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
    buildPayload() {
      const items = this.formItems
        .map(item => {
          const perBox = this.itemPiecesPerBox(item)
          const qty = Math.floor(Number(item.quantity) || 0)
          const receivedUnits = Number.isFinite(Number(item.received_units))
            ? Math.floor(Number(item.received_units))
            : Math.floor(Number(item.received_qty) || 0) * perBox
          const maxUnits = qty * perBox
          const safeUnits = maxUnits ? Math.min(receivedUnits, maxUnits) : receivedUnits
          return {
            product_id: item.product_id,
            quantity: qty,
            expected_cost: Number(item.expected_cost) || 0,
            received_qty: Number(item.received_qty) || 0,
            received_units: safeUnits < 0 ? 0 : safeUnits,
            actual_cost: item.actual_cost === '' || item.actual_cost === null ? null : Number(item.actual_cost)
          }
        })
        .filter(item => item.product_id && item.quantity > 0)
      return {
        id: this.isCreate ? undefined : this.orderId,
        status: this.form.status || '待到货',
        supplier: this.form.supplier,
        expected_date: this.form.expected_date,
        remark: this.form.remark,
        created_by: this.form.created_by || uni.getStorageSync('yh-username') || 'owner',
        items
      }
    },
    async saveOrder() {
      const payload = this.buildPayload()
      if (!payload.items.length) {
        uni.showToast({ title: '请至少添加一条商品', icon: 'none' })
        return
      }
      if (!payload.expected_date) {
        uni.showToast({ title: '请选择期望到货日期', icon: 'none' })
        return
      }
      this.saving = true
      try {
        if (this.isCreate) {
          const created = await api.createPurchaseOrder(payload)
          this.orderId = created.id
          this.isCreate = false
          await this.fetchOrder()
          uni.showToast({ title: '已创建', icon: 'success' })
        } else {
          await api.updatePurchaseOrder(this.orderId, payload)
          await this.fetchOrder()
          uni.showToast({ title: '已保存', icon: 'success' })
        }
      } catch (err) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    confirmDelete() {
      if (!this.orderId) return
      uni.showModal({
        title: '删除确认',
        content: '确定删除该采购单？此操作不可恢复。',
        confirmColor: '#d14343',
        success: async (res) => {
          if (res.confirm) {
            await this.deleteOrder()
          }
        }
      })
    },
    async deleteOrder() {
      if (!this.orderId) return
      try {
        await api.deletePurchaseOrder(this.orderId)
        uni.showToast({ title: '已删除', icon: 'success' })
        setTimeout(() => {
          uni.navigateBack()
        }, 400)
      } catch (err) {
        uni.showToast({ title: '删除失败', icon: 'none' })
      }
    },
    // --- Item Editor Methods ---
    openEditItem(idx) {
      if (idx < 0 || idx >= this.formItems.length) return
      const item = this.formItems[idx]
      this.editingIndex = idx
      this.editForm = {
        quantity: item.quantity,
        expected_cost: item.expected_cost
      }
      this.showEditSheet = true
    },
    closeEditSheet() {
      this.showEditSheet = false
      this.editingIndex = -1
    },
    saveEditItem() {
      if (this.editingIndex < 0) return
      const qty = Math.floor(Number(this.editForm.quantity) || 0)
      const cost = Number(this.editForm.expected_cost) || 0
      
      // Update the item in the list
      const item = this.formItems[this.editingIndex]
      item.quantity = qty < 0 ? 0 : qty
      item.expected_cost = cost < 0 ? 0 : cost
      
      this.closeEditSheet()
    },
    editSheetSubtotal() {
      const q = Number(this.editForm.quantity) || 0
      const c = Number(this.editForm.expected_cost) || 0
      return (q * c).toFixed(2)
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
  align-items: center;
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

.status-chip {
  padding: 6rpx 16rpx;
  border-radius: 999rpx;
  background: #e6f4f6;
  color: #0f6a7b;
  font-size: 22rpx;
}

.form-grid {
  margin-top: 12rpx;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220rpx, 1fr));
  gap: 12rpx;
}

.form-row .label {
  font-size: 22rpx;
  color: #6b7280;
}

.input {
  margin-top: 6rpx;
  width: 100%;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 10rpx 12rpx;
  font-size: 24rpx;
}

.picker {
  margin-top: 6rpx;
  padding: 10rpx 12rpx;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  font-size: 24rpx;
  color: #0b1f3a;
}

.summary-row {
  display: flex;
  gap: 16rpx;
  flex-wrap: wrap;
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

.mini-hint {
  margin-top: 8rpx;
  color: #9ca3af;
  font-size: 22rpx;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.item-row {
  border-top: 1rpx dashed #e5e7eb;
  padding-top: 12rpx;
  margin-top: 12rpx;
}

.item-compact {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 20rpx;
}

.item-main {
  flex: 2;
  min-width: 0;
}

.item-stats {
  flex: 2;
  display: flex;
  gap: 16rpx;
  justify-content: flex-end;
  margin-right: 16rpx;
}

.stat-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.stat-pill .label {
  font-size: 20rpx;
  color: #94a3b8;
}

.stat-pill .val {
  font-size: 26rpx;
  color: #0f172a;
  font-weight: 600;
}

.item-total {
  font-size: 28rpx;
  color: #0f6a7b;
  font-weight: 700;
  width: 140rpx;
  text-align: right;
}

.item-action {
  width: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-left: 1rpx solid #f1f5f9;
}

.delete-icon {
  color: #ef4444;
  font-size: 40rpx;
  font-weight: 300;
}

/* Edit Sheet */
.edit-mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 100;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.edit-sheet {
  background: #fff;
  border-radius: 24rpx 24rpx 0 0;
  padding: 32rpx;
  padding-bottom: env(safe-area-inset-bottom);
  animation: slideUp 0.2s ease-out;
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.sheet-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32rpx;
}

.sheet-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #0f172a;
}

.sheet-close {
  font-size: 44rpx;
  color: #94a3b8;
  padding: 0 16rpx;
}

.sheet-info {
  margin-bottom: 32rpx;
  background: #f8fafc;
  padding: 20rpx;
  border-radius: 12rpx;
}

.sheet-name {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  color: #334155;
}

.sheet-spec {
  font-size: 24rpx;
  color: #64748b;
  margin-top: 4rpx;
  display: block;
}

.sheet-form {
  display: flex;
  gap: 24rpx;
  margin-bottom: 32rpx;
}

.sheet-field {
  flex: 1;
}

.sheet-label {
  display: block;
  font-size: 24rpx;
  color: #64748b;
  margin-bottom: 12rpx;
}

.sheet-input {
  width: 100%;
  height: 80rpx;
  background: #f8fafc;
  border: 2rpx solid #e2e8f0;
  border-radius: 12rpx;
  padding: 0 20rpx;
  font-size: 32rpx;
  font-weight: 600;
  color: #0f172a;
  box-sizing: border-box;
}

.sheet-input:focus {
  border-color: #0f6a7b;
  background: #fff;
}

.sheet-summary {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 32rpx;
  font-size: 28rpx;
  color: #64748b;
}

.sheet-total {
  font-size: 40rpx;
  font-weight: 700;
  color: #0f6a7b;
}

.sheet-confirm {
  background: #0f6a7b;
  width: 100%;
  border-radius: 16rpx;
  font-size: 32rpx;
  font-weight: 600;
  padding: 10rpx 0;
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

.search-bar {
  display: flex;
  gap: 10rpx;
  align-items: center;
  margin-bottom: 12rpx;
}

.search {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 10rpx 12rpx;
  font-size: 24rpx;
}

.dialog-body {
  max-height: 50vh;
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10rpx 0;
  border-bottom: 1rpx dashed #e5e7eb;
}

.row:last-child {
  border-bottom: none;
}

.info .name {
  font-size: 26rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.info .meta {
  font-size: 22rpx;
  color: #6b7280;
  margin-top: 4rpx;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 24rpx 0;
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
