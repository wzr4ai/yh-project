<template>
  <view class="page">
    <view class="card">
      <view class="section-title">新建商品</view>
      <view class="form-row">
        <view class="label">名称</view>
        <input class="input" v-model="form.name" placeholder="商品名称" />
      </view>
      <view class="form-row">
        <view class="label">条码</view>
        <input class="input" v-model="form.barcode" placeholder="商品条码 (可选)" />
      </view>
      <view class="form-row">
        <view class="label">规格说明</view>
        <input class="input" v-model="form.spec" placeholder="规格描述（如：1x10x6）" />
      </view>
      <view class="form-row">
        <view class="label">每箱中包数</view>
        <input class="input" type="number" v-model.number="form.units_per_box" placeholder="如：10" />
      </view>
      <view class="form-row">
        <view class="label">每包件数</view>
        <input class="input" type="number" v-model.number="form.pieces_per_unit" placeholder="如：6" />
      </view>
      <view class="form-row">
        <view class="label">分类</view>
        <view class="chips">
          <view
            v-for="cat in categories"
            :key="cat.id"
            :class="['chip', selectedCategoryIds.includes(cat.id) ? 'active' : '']"
            @tap="toggleCategory(cat.id)"
          >
            {{ cat.name }}
          </view>
        </view>
      </view>
      <view class="form-row">
        <view class="label">整箱进价</view>
        <input class="input" type="digit" inputmode="decimal" v-model="form.box_cost_price" placeholder="整箱进价（可小数）" />
      </view>
      <view class="form-row">
        <view class="label">固定零售价</view>
        <input class="input" type="digit" inputmode="decimal" v-model="form.fixed_retail_price" placeholder="为空则按系数，可小数" />
      </view>
      <view class="form-row">
        <view class="label">图片</view>
        <input class="input" v-model="form.img_url" placeholder="图片 URL (可选)" />
      </view>
    </view>

    <view class="actions">
      <button type="primary" :loading="saving" @tap="save">保存</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      form: {
        name: '',
        barcode: '',
        spec: '',
        units_per_box: 1,
        pieces_per_unit: 1,
        box_cost_price: null,
        base_cost_price: null,
        fixed_retail_price: null,
        img_url: ''
      },
      categories: [],
      selectedCategoryIds: [],
      saving: false
    }
  },
  onShow() {
    this.loadCategories()
  },
  methods: {
    async loadCategories() {
      try {
        const data = await api.getCategories()
        this.categories = data || []
      } catch (err) {
        this.categories = []
      }
    },
    toggleCategory(id) {
      const exists = this.selectedCategoryIds.includes(id)
      this.selectedCategoryIds = exists ? this.selectedCategoryIds.filter(x => x !== id) : this.selectedCategoryIds.concat(id)
    },
    async save() {
      if (!this.form.name) {
        uni.showToast({ title: '请输入名称', icon: 'none' })
        return
      }
      const units = this.parseInt(this.form.units_per_box, 1)
      const pieces = this.parseInt(this.form.pieces_per_unit, 1)
      const boxCost = this.parsePrice(this.form.box_cost_price)
      const baseCost = boxCost && units > 0 && pieces > 0 ? boxCost / (units * pieces) : 0
      const fixedRetail = this.parsePrice(this.form.fixed_retail_price)
      this.saving = true
      try {
        await api.createProduct({
          ...this.form,
          units_per_box: units,
          pieces_per_unit: pieces,
          box_cost_price: boxCost,
          base_cost_price: baseCost,
          fixed_retail_price: fixedRetail,
          categories: this.selectedCategoryIds.map(id => ({ id })),
          category_id: this.selectedCategoryIds[0] || null
        })
        uni.showToast({ title: '已创建', icon: 'success' })
        uni.navigateBack()
      } catch (err) {
        uni.showToast({ title: '创建失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    parsePrice(val) {
      const num = parseFloat(val)
      return Number.isFinite(num) ? num : null
    },
    parseInt(val, fallback) {
      const num = parseInt(val, 10)
      return Number.isFinite(num) && num > 0 ? num : fallback
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

.section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.form-row {
  margin-bottom: 12rpx;
}

.label {
  color: #4b5563;
  font-size: 26rpx;
  margin-bottom: 6rpx;
}

.input {
  width: 100%;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 14rpx;
  font-size: 26rpx;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.chip {
  padding: 10rpx 16rpx;
  border-radius: 12rpx;
  border: 1rpx solid #e5e7eb;
  background: #f9fafb;
  color: #0b1f3a;
  font-size: 24rpx;
}

.chip.active {
  background: #0f6a7b;
  color: #fff;
  border-color: #0f6a7b;
}

.actions {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: #fff;
  padding: 12rpx 20rpx env(safe-area-inset-bottom);
  box-shadow: 0 -6rpx 12rpx rgba(0, 0, 0, 0.05);
}
</style>
