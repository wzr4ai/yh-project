<template>
  <view class="page">
    <view class="card" v-if="order">
      <view class="header">
        <view>
          <view class="title">采购单入库</view>
          <view class="sub">{{ order.id }}</view>
          <view class="meta">{{ order.supplier || '—' }} ｜ 期望到货 {{ order.expected_date || '—' }}</view>
        </view>
        <view class="status" :class="statusClass(order.status)">{{ order.status }}</view>
      </view>
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
      <view class="hint">入库按条码层级计数，箱/包/个扫码会累计。</view>
    </view>

    <view class="card summary" v-if="order">
      <view class="summary-row">
        <view>
          <view class="mini-title">计划箱数</view>
          <view class="mini-value">{{ stats.total }}</view>
        </view>
        <view>
          <view class="mini-title">已入箱数</view>
          <view class="mini-value">{{ stats.received }}</view>
        </view>
        <view>
          <view class="mini-title">进度</view>
          <view class="mini-value">{{ stats.progress }}%</view>
        </view>
      </view>
      <view class="progress-bar">
        <view class="progress" :style="{ width: stats.progress + '%' }"></view>
      </view>
    </view>

    <view class="card" v-if="order">
      <view class="section-title">入库明细</view>
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
            <view class="label">已入箱数</view>
            <input class="input" type="number" v-model.number="item.received_qty" @blur="normalizeReceived(item)" />
            <view class="sub-value">合计 {{ receivedDetail(item) }}</view>
          </view>
          <view class="field">
            <view class="label">预计单价</view>
            <view class="value">¥{{ formatMoney(item.expected_cost) }}</view>
          </view>
          <view class="field">
            <view class="label">预计小计</view>
            <view class="value">¥{{ lineCost(item).toFixed(2) }}</view>
          </view>
        </view>
        <view class="row-actions">
          <button size="mini" @tap="addReceived(item, 1)">+1 箱</button>
          <button size="mini" @tap="addReceived(item, -1)">-1 箱</button>
          <button size="mini" @tap="fillRowReceived(idx)">全部入库</button>
        </view>
      </view>
      <view v-if="!formItems.length" class="empty">暂无明细</view>
    </view>

    <view v-if="!order && !loading" class="empty">未找到采购单</view>
    <view v-if="loading" class="empty">加载中...</view>

    <view class="footer" v-if="order">
      <button size="mini" @tap="goBack">返回</button>
      <button size="mini" type="primary" :loading="saving" @tap="submitReceive">保存入库</button>
    </view>

    <view class="dialog" v-if="showMatchDialog">
      <view class="dialog-content">
        <view class="dialog-header">
          <view class="dialog-title">选择匹配条码</view>
          <button size="mini" @tap="closeMatchDialog">关闭</button>
        </view>
        <scroll-view class="dialog-body" scroll-y>
          <view class="match-row" v-for="item in matchedProducts" :key="item.barcode" @tap="selectMatched(item)">
            <view class="match-name">{{ item.product?.name }}</view>
            <view class="match-meta">条码 {{ item.barcode || '—' }} ｜ 规格 {{ item.product?.spec || '—' }}</view>
          </view>
          <view v-if="!matchedProducts.length" class="empty">无匹配结果</view>
        </scroll-view>
      </view>
    </view>

    <view class="dialog" v-if="showBindDialog">
      <view class="dialog-content">
        <view class="dialog-header">
          <view class="dialog-title">绑定条码</view>
          <button size="mini" @tap="closeBindDialog">关闭</button>
        </view>
        <view class="bind-body">
          <view class="bind-row">
            <view class="label">条码</view>
            <view class="value">{{ bindBarcode }}</view>
          </view>
          <view class="bind-row">
            <view class="label">商品</view>
            <picker :range="orderProductNames" :value="bindProductIndex" @change="onBindProductChange">
              <view class="picker">{{ orderProductNames[bindProductIndex] }}</view>
            </picker>
          </view>
          <view class="bind-row">
            <view class="label">层级</view>
            <picker :range="barcodeLevels" :value="bindLevelIndex" @change="onBindLevelChange">
              <view class="picker">{{ barcodeLevels[bindLevelIndex] }}</view>
            </picker>
          </view>
          <view class="actions">
            <button size="mini" type="primary" :loading="binding" @tap="confirmBind">绑定并入库</button>
            <button size="mini" @tap="confirmBind(false)">仅绑定</button>
          </view>
          <view class="hint">若条码不在库中，可先绑定对应商品与包装层级。</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { api } from '../../common/api.js'
import { piecesPerBox, formatStock } from '../../common/stock.js'

export default {
  data() {
    return {
      role: getRole(),
      orderId: '',
      order: null,
      formItems: [],
      productMap: {},
      barcodeInput: '',
      loading: false,
      scanning: false,
      saving: false,
      skipNextFetch: false,
      showMatchDialog: false,
      matchedProducts: [],
      showBindDialog: false,
      bindBarcode: '',
      bindProductId: '',
      bindLevel: 'BOX',
      binding: false,
      barcodeLevels: ['BOX', 'UNIT', 'PIECE']
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    stats() {
      let total = 0
      let received = 0
      this.formItems.forEach(item => {
        const qty = Number(item.quantity) || 0
        const recv = Number(item.received_qty) || 0
        total += qty
        received += recv
      })
      const progress = total ? Math.min(100, Math.round((received / total) * 100)) : 0
      return { total, received, progress }
    },
    orderProductNames() {
      const names = []
      for (const item of this.formItems) {
        names.push(this.productName(item))
      }
      return names.length ? names : ['请选择']
    },
    bindProductIndex() {
      if (!this.bindProductId) return 0
      const idx = this.formItems.findIndex(item => item.product_id === this.bindProductId)
      return idx >= 0 ? idx : 0
    },
    bindLevelIndex() {
      const idx = this.barcodeLevels.indexOf(this.bindLevel)
      return idx >= 0 ? idx : 0
    }
  },
  onLoad(options) {
    this.orderId = options.id || ''
  },
  onHide() {
    this.persistDraft()
  },
  onUnload() {
    this.persistDraft()
  },
  onShow() {
    this.role = getRole()
    if (!this.isOwner) {
      uni.showToast({ title: '仅老板可入库', icon: 'none' })
      uni.navigateBack()
      return
    }
    if (this.skipNextFetch && this.order) {
      this.skipNextFetch = false
      return
    }
    this.fetchOrder()
  },
  methods: {
    draftKey() {
      return this.orderId ? `purchase-receive-draft:${this.orderId}` : ''
    },
    persistDraft() {
      const key = this.draftKey()
      if (!key || !this.formItems.length) return
      const items = this.formItems.map(item => {
        const perBox = this.itemPiecesPerBox(item)
        const receivedUnits = Number.isFinite(Number(item.received_units))
          ? Math.floor(Number(item.received_units))
          : Math.floor(Number(item.received_qty) || 0) * perBox
        const maxUnits = (Number(item.quantity) || 0) * perBox
        const safeUnits = maxUnits ? Math.min(receivedUnits, maxUnits) : receivedUnits
        return {
          product_id: item.product_id,
          received_units: safeUnits < 0 ? 0 : safeUnits,
          received_qty: Math.floor(Number(item.received_qty) || 0)
        }
      })
      try {
        uni.setStorageSync(key, { items, updated_at: Date.now() })
      } catch (e) {}
    },
    loadDraft() {
      const key = this.draftKey()
      if (!key) return
      let cached = null
      try {
        cached = uni.getStorageSync(key)
      } catch (e) {
        cached = null
      }
      if (!cached || !Array.isArray(cached.items)) return
      const draftMap = {}
      cached.items.forEach(item => {
        if (item && item.product_id) {
          draftMap[item.product_id] = item
        }
      })
      this.formItems.forEach(item => {
        const draft = draftMap[item.product_id]
        if (!draft) return
        const perBox = this.itemPiecesPerBox(item)
        const draftUnits = Number(draft.received_units)
        const units = Number.isFinite(draftUnits)
          ? Math.floor(draftUnits)
          : Math.floor(Number(draft.received_qty) || 0) * perBox
        const maxUnits = (Number(item.quantity) || 0) * perBox
        const safeUnits = maxUnits ? Math.min(units, maxUnits) : units
        item.received_units = safeUnits < 0 ? 0 : safeUnits
        item.received_qty = Math.min(Number(item.quantity) || 0, Math.floor(item.received_units / perBox))
      })
    },
    clearDraft() {
      const key = this.draftKey()
      if (!key) return
      try {
        uni.removeStorageSync(key)
      } catch (e) {}
    },
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
    itemPiecesPerBox(item, productOverride) {
      const product = productOverride || this.productMap[item.product_id] || item
      return piecesPerBox(product)
    },
    ensureReceivedUnits(item, perBox) {
      if (item.received_units === null || item.received_units === undefined) {
        item.received_units = (Number(item.received_qty) || 0) * perBox
      }
    },
    receivedDetail(item) {
      const product = this.productMap[item.product_id]
      if (!product) return '—'
      if (item.received_units === null || item.received_units === undefined) return '—'
      const units = Number(item.received_units)
      if (!Number.isFinite(units)) return '—'
      return formatStock(units, product)
    },
    barcodeLevelLabel(level) {
      const lvl = (level || '').toUpperCase()
      if (lvl === 'BOX') return '箱'
      if (lvl === 'UNIT') return '包'
      return '个'
    },
    barcodeUnitsForLevel(item, product, level) {
      const lvl = (level || '').toUpperCase()
      if (lvl === 'BOX') return this.itemPiecesPerBox(item, product)
      if (lvl === 'UNIT') return Math.max(1, Number(product?.pieces_per_unit) || 1)
      return 1
    },
    applyReceivedUnits(item, perBox, deltaUnits) {
      const qty = Number(item.quantity) || 0
      const maxUnits = qty * perBox
      const delta = Number(deltaUnits) || 0
      this.ensureReceivedUnits(item, perBox)
      let nextUnits = (Number(item.received_units) || 0) + delta
      if (nextUnits < 0) nextUnits = 0
      if (maxUnits && nextUnits > maxUnits) nextUnits = maxUnits
      const safeUnits = Math.floor(nextUnits)
      item.received_units = safeUnits
      item.received_qty = Math.min(qty, Math.floor(safeUnits / perBox))
      this.persistDraft()
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
      const perBox = this.itemPiecesPerBox(item)
      item.received_units = recv * perBox
      this.persistDraft()
    },
    addReceived(item, delta) {
      const perBox = this.itemPiecesPerBox(item)
      const deltaUnits = (Number(delta) || 0) * perBox
      if (!deltaUnits) return
      this.applyReceivedUnits(item, perBox, deltaUnits)
    },
    fillRowReceived(idx) {
      const row = this.formItems[idx]
      if (!row) return
      row.received_qty = Number(row.quantity) || 0
      const perBox = this.itemPiecesPerBox(row)
      row.received_units = row.received_qty * perBox
      this.persistDraft()
    },
    scanCode() {
      this.skipNextFetch = true
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
            this.handleMatched(matches[0])
            this.barcodeInput = ''
            return
          }
          if (matches.length > 1) {
            this.openMatchDialog(matches)
            return
          }
        }
        const result = await api.getProductByBarcode(code)
        this.handleMatched(result)
        this.barcodeInput = ''
      } catch (err) {
        this.openBindDialog(code)
      } finally {
        this.loading = false
      }
    },
    handleMatched(result) {
      const product = result.product
      if (!product || !product.id) {
        uni.showToast({ title: '条码未匹配商品', icon: 'none' })
        return
      }
      const target = this.formItems.find(item => item.product_id === product.id)
      if (!target) {
        uni.showToast({ title: '该商品不在采购单中', icon: 'none' })
        return
      }
      const perBox = this.itemPiecesPerBox(target, product)
      const level = (result.level || '').toUpperCase()
      const deltaUnits = Math.max(1, Math.floor(Number(result.multiplier) || 1))
      if (level && level !== 'BOX') {
        const levelLabel = this.barcodeLevelLabel(level)
        uni.showActionSheet({
          itemList: ['+1箱', `+1${levelLabel}`],
          success: (res) => {
            if (res.tapIndex === 0) {
              this.applyReceivedUnits(target, perBox, perBox)
              uni.showToast({ title: '已入库 +1箱', icon: 'success' })
            } else if (res.tapIndex === 1) {
              this.applyReceivedUnits(target, perBox, deltaUnits)
              uni.showToast({ title: `已入库 +1${levelLabel}`, icon: 'success' })
            }
          }
        })
      } else {
        this.applyReceivedUnits(target, perBox, deltaUnits)
        uni.showToast({ title: '已入库 +1箱', icon: 'success' })
      }
      this.barcodeInput = ''
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
        this.handleMatched(item)
        this.barcodeInput = ''
      }
    },
    openBindDialog(code) {
      this.bindBarcode = code
      const first = this.formItems[0]
      this.bindProductId = first ? first.product_id : ''
      this.bindLevel = 'BOX'
      this.showBindDialog = true
    },
    closeBindDialog() {
      this.showBindDialog = false
      this.bindBarcode = ''
      this.binding = false
    },
    onBindProductChange(e) {
      const idx = Number(e.detail.value) || 0
      const item = this.formItems[idx]
      this.bindProductId = item ? item.product_id : ''
    },
    onBindLevelChange(e) {
      const idx = Number(e.detail.value) || 0
      this.bindLevel = this.barcodeLevels[idx] || 'BOX'
    },
    async confirmBind(withReceive = true) {
      if (typeof withReceive !== 'boolean') {
        withReceive = true
      }
      if (!this.bindBarcode || !this.bindProductId) {
        uni.showToast({ title: '请选择商品', icon: 'none' })
        return
      }
      this.binding = true
      try {
        await api.addProductBarcode(this.bindProductId, {
          barcode: this.bindBarcode,
          level: this.bindLevel
        })
        if (withReceive) {
          const target = this.formItems.find(item => item.product_id === this.bindProductId)
          if (target) {
            const product = this.productMap[target.product_id]
            const perBox = this.itemPiecesPerBox(target, product)
            const deltaUnits = this.barcodeUnitsForLevel(target, product, this.bindLevel)
            this.applyReceivedUnits(target, perBox, deltaUnits)
          }
        }
        uni.showToast({ title: '已绑定', icon: 'success' })
        this.closeBindDialog()
      } catch (err) {
        const msg = err && err.detail ? err.detail : '绑定失败'
        uni.showToast({ title: msg, icon: 'none' })
      } finally {
        this.binding = false
      }
    },
    async fetchOrder() {
      if (!this.orderId) return
      this.loading = true
      try {
        const order = await api.getPurchaseOrder(this.orderId)
        this.order = order
        this.formItems = (order.items || []).map(item => ({
          ...item,
          quantity: Number(item.quantity) || 0,
          received_qty: Number(item.received_qty) || 0,
          received_units: item.received_units === null || item.received_units === undefined ? null : Number(item.received_units) || 0
        }))
        await this.loadProductMap()
        this.loadDraft()
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.loading = false
      }
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
      this.formItems.forEach(item => {
        if (item.received_units === null || item.received_units === undefined) {
          const perBox = this.itemPiecesPerBox(item)
          item.received_units = (Number(item.received_qty) || 0) * perBox
        }
      })
    },
    buildPayload() {
      return this.formItems.map(item => {
        const perBox = this.itemPiecesPerBox(item)
        const qty = Number(item.quantity) || 0
        const receivedUnits = Number.isFinite(Number(item.received_units))
          ? Math.floor(Number(item.received_units))
          : Math.floor(Number(item.received_qty) || 0) * perBox
        const maxUnits = qty * perBox
        const safeUnits = maxUnits ? Math.min(receivedUnits, maxUnits) : receivedUnits
        return {
          product_id: item.product_id,
          quantity: qty,
          expected_cost: Number(item.expected_cost) || 0,
          received_qty: Math.floor(Number(item.received_qty) || 0),
          received_units: safeUnits < 0 ? 0 : safeUnits,
          actual_cost: item.actual_cost === '' || item.actual_cost === null ? null : Number(item.actual_cost)
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
          received_units: item.received_units === null || item.received_units === undefined ? null : Number(item.received_units) || 0
        }))
        await this.loadProductMap()
        this.clearDraft()
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
  align-items: center;
}

.title {
  font-size: 30rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.sub,
.meta {
  margin-top: 6rpx;
  color: #6b7280;
  font-size: 22rpx;
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

.scan-row {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.input {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 10rpx 12rpx;
  font-size: 24rpx;
  background: #fff;
}

.hint {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #9ca3af;
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
  align-items: center;
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

.field .value {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #0b1f3a;
  font-weight: 600;
}

.field .sub-value {
  margin-top: 4rpx;
  font-size: 20rpx;
  color: #9ca3af;
}

.row-actions {
  display: flex;
  gap: 10rpx;
  margin-top: 10rpx;
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

.bind-body {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.bind-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bind-row .label {
  font-size: 22rpx;
  color: #6b7280;
}

.bind-row .value {
  font-size: 24rpx;
  color: #0b1f3a;
  font-weight: 600;
}

.picker {
  padding: 10rpx 12rpx;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  font-size: 24rpx;
  color: #0b1f3a;
  min-width: 240rpx;
  text-align: right;
}

.actions {
  display: flex;
  gap: 12rpx;
  margin-top: 6rpx;
}
</style>
