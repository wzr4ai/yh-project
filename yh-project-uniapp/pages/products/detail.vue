<template>
  <view class="page">
    <view class="card">
      <view class="section-title">商品信息</view>
      <view class="form-row">
        <view class="label">名称</view>
        <input class="input" v-model="form.name" :disabled="!isOwner" placeholder="商品名称" />
      </view>
      <view class="form-row">
        <view class="label">规格</view>
        <input class="input" v-model="form.spec" :disabled="!isOwner" placeholder="规格" />
      </view>
      <view class="form-row">
        <view class="label">分类</view>
        <input class="input" v-model="form.category_id" :disabled="!isOwner" placeholder="分类ID或名称" />
      </view>
      <view class="form-row">
        <view class="label">进价</view>
        <input class="input" type="digit" v-model.number="form.base_cost_price" :disabled="!isOwner" placeholder="进价" />
      </view>
      <view class="form-row">
        <view class="label">固定零售价</view>
        <input class="input" type="digit" v-model.number="form.fixed_retail_price" :disabled="!isOwner" placeholder="为空则按分类/全局系数计算" />
      </view>
      <view class="form-row">
        <view class="label">图片</view>
        <input class="input" v-model="form.img_url" :disabled="!isOwner" placeholder="图片 URL (可选)" />
      </view>
    </view>

    <view class="card">
      <view class="section-title">价格信息</view>
      <view class="info-row">
        <view class="info-label">标准价</view>
        <view class="info-value">¥{{ price.price?.toFixed(2) || '-' }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">依据</view>
        <view class="info-value">{{ price.basis || '-' }}</view>
      </view>
    </view>

    <view class="actions" v-if="isOwner">
      <button type="primary" :loading="saving" @tap="save">保存</button>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      id: '',
      role: getRole(),
      form: {
        name: '',
        spec: '',
        category_id: '',
        base_cost_price: null,
        fixed_retail_price: null,
        img_url: ''
      },
      price: {
        price: null,
        basis: ''
      },
      saving: false
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    }
  },
  onLoad(options) {
    this.id = options.id || ''
    this.fetchDetail()
  },
  methods: {
    async fetchDetail() {
      try {
        const data = await api.getProduct(this.id)
        this.form = {
          name: data.name,
          spec: data.spec,
          category_id: data.category_id,
          base_cost_price: data.base_cost_price,
          fixed_retail_price: data.fixed_retail_price,
          img_url: data.img_url
        }
        this.fetchPrice()
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      }
    },
    async fetchPrice() {
      try {
        const price = await api.calculatePrice(this.id)
        this.price = price
      } catch (err) {
        this.price = { price: null, basis: '' }
      }
    },
    async save() {
      this.saving = true
      try {
        await api.updateProduct(this.id, this.form)
        uni.showToast({ title: '已保存', icon: 'success' })
        this.fetchPrice()
      } catch (err) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  padding: 20rpx;
  background: #f7f8fa;
  box-sizing: border-box;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
  margin-bottom: 16rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.form-row {
  display: flex;
  align-items: center;
  margin-bottom: 12rpx;
}

.label {
  width: 180rpx;
  color: #4b5563;
  font-size: 26rpx;
}

.input {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 14rpx;
  font-size: 26rpx;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10rpx;
}

.info-label {
  color: #6b7280;
  font-size: 24rpx;
}

.info-value {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.actions {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: #ffffff;
  padding: 12rpx 20rpx env(safe-area-inset-bottom);
  box-shadow: 0 -6rpx 12rpx rgba(0, 0, 0, 0.05);
}
</style>
