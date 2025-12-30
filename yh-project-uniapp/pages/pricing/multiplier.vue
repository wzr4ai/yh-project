<template>
  <view class="page">
    <view class="card">
      <view class="title">售价系数调整</view>
      <view class="sub">标准售价 = 成本 × 系数区间（默认取区间上限）</view>
      <view class="form-row">
        <view class="label">最低系数</view>
        <input class="input" type="digit" v-model="form.min" placeholder="如：1.5" />
      </view>
      <view class="form-row">
        <view class="label">最高系数</view>
        <input class="input" type="digit" v-model="form.max" placeholder="如：1.8" />
      </view>
      <view class="hint">若最高低于最低，将自动按最低系数保存。</view>
      <view class="actions">
        <button size="mini" @tap="resetForm" :disabled="loading">重置</button>
        <button size="mini" type="primary" @tap="save" :loading="loading">保存</button>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'
import { getRole, isOwner } from '../../common/auth.js'

export default {
  data() {
    return {
      role: getRole(),
      loading: false,
      form: {
        min: '',
        max: ''
      },
      original: {
        min: '',
        max: ''
      }
    }
  },
  onShow() {
    this.role = getRole()
    if (!isOwner(this.role)) {
      uni.showToast({ title: '仅老板可调整', icon: 'none' })
      uni.navigateBack()
      return
    }
    this.fetchConfig()
  },
  methods: {
    async fetchConfig() {
      this.loading = true
      try {
        const data = await api.getPricingMultiplier()
        const min = Number(data?.min_multiplier) || 0
        const max = Number(data?.max_multiplier) || 0
        this.form.min = min ? String(min) : ''
        this.form.max = max ? String(max) : ''
        this.original = { ...this.form }
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    resetForm() {
      this.form = { ...this.original }
    },
    async save() {
      const minVal = parseFloat(this.form.min)
      const maxVal = parseFloat(this.form.max)
      if (!Number.isFinite(minVal) || !Number.isFinite(maxVal)) {
        uni.showToast({ title: '请输入有效系数', icon: 'none' })
        return
      }
      this.loading = true
      try {
        const data = await api.updatePricingMultiplier({
          min_multiplier: minVal,
          max_multiplier: maxVal
        })
        const min = Number(data?.min_multiplier) || minVal
        const max = Number(data?.max_multiplier) || maxVal
        this.form.min = String(min)
        this.form.max = String(max)
        this.original = { ...this.form }
        uni.showToast({ title: '已保存', icon: 'success' })
      } catch (err) {
        uni.showToast({ title: '保存失败', icon: 'none' })
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

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
}

.title {
  font-size: 32rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.sub {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #6b7280;
}

.form-row {
  display: flex;
  align-items: center;
  margin-top: 14rpx;
}

.label {
  width: 160rpx;
  font-size: 26rpx;
  color: #4b5563;
}

.input {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 12rpx;
  font-size: 26rpx;
  background: #fff;
}

.hint {
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #9ca3af;
}

.actions {
  margin-top: 16rpx;
  display: flex;
  justify-content: flex-end;
  gap: 10rpx;
}
</style>
