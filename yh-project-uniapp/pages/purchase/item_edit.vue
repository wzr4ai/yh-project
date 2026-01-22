<template>
  <view class="page">
    <view class="card">
      <view class="field">
        <text class="label">商品</text>
        <view class="value">{{ item.product_name || item.product_id }}</view>
      </view>
      <view class="field">
        <text class="label">规格</text>
        <view class="value">{{ item.product_spec || '—' }}</view>
      </view>
    </view>

    <view class="card form">
      <view class="form-item">
        <text class="form-label">计划数量 (箱)</text>
        <input class="form-input" type="number" v-model="form.quantity" />
      </view>
      
      <view class="form-item">
        <text class="form-label">预计成本 (单价)</text>
        <input class="form-input" type="digit" v-model="form.expected_cost" />
      </view>
    </view>

    <view class="actions">
      <button class="btn-save" @tap="save" :disabled="submitting" :loading="submitting">保存修改</button>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      orderId: '',
      itemId: '',
      item: {},
      form: {
        quantity: '',
        expected_cost: ''
      },
      submitting: false
    }
  },
  onLoad(options) {
    this.orderId = options.order_id
    this.itemId = options.item_id
    
    if (!isOwner(getRole())) {
      uni.showToast({ title: '无权操作', icon: 'none' })
      setTimeout(() => uni.navigateBack(), 1500)
      return
    }
    
    this.loadItem()
  },
  methods: {
    async loadItem() {
      try {
        const data = await api.getPurchaseOrderItem(this.orderId, this.itemId)
        this.item = data
        this.form.quantity = data.quantity
        this.form.expected_cost = data.expected_cost
      } catch (e) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      }
    },
    async save() {
      if (this.submitting) return
      this.submitting = true

      const qty = Math.floor(Number(this.form.quantity))
      if (!Number.isFinite(qty) || qty < 0) {
        uni.showToast({ title: '数量需为非负整数', icon: 'none' })
        this.submitting = false
        return
      }
      const cost = Number(this.form.expected_cost)
      if (!Number.isFinite(cost) || cost < 0) {
        uni.showToast({ title: '成本需为非负数字', icon: 'none' })
        this.submitting = false
        return
      }

      const payload = {
        quantity: qty,
        expected_cost: cost
      }
      
      try {
        await api.updatePurchaseOrderItem(this.orderId, this.itemId, payload)
        
        // Set dirty flag
        uni.setStorageSync(`purchase:items_dirty:${this.orderId}`, true)
        
        uni.showToast({ title: '保存成功', icon: 'success' })
        setTimeout(() => uni.navigateBack(), 1000)
      } catch (e) {
        uni.showToast({ title: '保存失败', icon: 'none' })
        this.submitting = false
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
}
.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.03);
}

.field {
  display: flex;
  justify-content: space-between;
  padding: 12rpx 0;
  border-bottom: 1rpx solid #f1f5f9;
  font-size: 28rpx;
  
  &:last-child { border-bottom: none; }
}
.label { color: #64748b; }
.value { font-weight: 500; color: #1e293b; }

.form { padding: 0 24rpx; }
.form-item {
  padding: 24rpx 0;
  border-bottom: 1rpx solid #f1f5f9;
  
  &:last-child { border-bottom: none; }
}
.form-label {
  display: block;
  font-size: 24rpx;
  color: #64748b;
  margin-bottom: 12rpx;
}
.form-input {
  font-size: 32rpx;
  font-weight: 600;
  color: #0f172a;
  height: 60rpx;
}

.actions { margin-top: 48rpx; }
.btn-save {
  background: #0f6a7b;
  color: #fff;
  border-radius: 16rpx;
  font-size: 30rpx;
  font-weight: 600;
  box-shadow: 0 4rpx 12rpx rgba(15, 106, 123, 0.3);
  
  &:active { transform: scale(0.98); opacity: 0.9; }
  &[disabled] { background: #cbd5e1; box-shadow: none; }
}
</style>
