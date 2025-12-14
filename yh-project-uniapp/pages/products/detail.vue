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
        <view class="chips">
          <view
            v-for="cat in categories"
            :key="cat.id || 'none'"
            :class="['chip', selectedCategoryIds.includes(cat.id) ? 'active' : '']"
            @tap="isOwner ? onCategoryChange({ detail: { value: categories.indexOf(cat) } }) : null"
          >
            {{ cat.name }}
          </view>
        </view>
      </view>
      <view class="form-row">
        <view class="label">进价</view>
        <input class="input" type="digit" v-model.number="form.base_cost_price" :disabled="!isOwner" placeholder="进价" />
      </view>
      <view class="info-row">
        <view class="info-label">一件数量</view>
        <view class="info-value">{{ specQty }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">一件价格</view>
        <view class="info-value">¥{{ packPriceCalc.toFixed(2) }}</view>
      </view>
      <view class="form-row" v-if="showPackPriceRef">
        <view class="label">一件价格(参考)</view>
        <input class="input" type="digit" v-model.number="form.pack_price_ref" :disabled="!isOwner" placeholder="参考箱价" />
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

    <view class="card">
      <view class="section-title">库存</view>
      <view class="info-row">
        <view class="info-label">当前库存</view>
        <view class="info-value">{{ stock }}</view>
      </view>
      <view v-if="isOwner">
        <view class="form-row">
          <view class="label">调整数量</view>
          <input class="input" type="number" v-model.number="adjustDelta" placeholder="+/- 数量" />
        </view>
        <view class="form-row">
          <view class="label">原因</view>
          <input class="input" v-model="adjustReason" placeholder="原因(可选)" />
        </view>
        <button type="primary" size="mini" @tap="adjustInventory">调整库存</button>
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
        category_name: '',
        base_cost_price: null,
        fixed_retail_price: null,
        pack_price_ref: null,
        img_url: ''
      },
      price: {
        price: null,
        basis: ''
      },
      categories: [],
      selectedCategoryIds: [],
      stock: 0,
      adjustDelta: 0,
      adjustReason: '',
      saving: false
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    specQty() {
      const match = String(this.form.spec || '').match(/(\d+(\.\d+)?)/)
      const val = match ? parseFloat(match[1]) : 1
      return val > 0 ? val : 1
    },
    packPriceCalc() {
      const qty = this.specQty
      const single = Number(this.form.base_cost_price) || 0
      return single * qty
    },
    showPackPriceRef() {
      if (this.form.pack_price_ref === null || this.form.pack_price_ref === undefined) return false
      return Math.abs((Number(this.form.pack_price_ref) || 0) - this.packPriceCalc) > 0.01
    }
  },
  onLoad(options) {
    this.id = options.id || ''
    this.fetchCategories().then(() => {
      this.fetchDetail()
    })
    this.fetchInventory()
  },
  methods: {
    async fetchCategories() {
      try {
        const data = await api.getCategories()
        this.categories = data || []
      } catch (err) {
        this.categories = []
      }
    },
    async fetchDetail() {
      try {
        const data = await api.getProduct(this.id)
        this.form = {
          name: data.name,
          spec: data.spec,
          category_id: data.category_id,
          category_name: data.category_name || '',
          base_cost_price: data.base_cost_price,
          fixed_retail_price: data.fixed_retail_price,
          pack_price_ref: data.pack_price_ref,
          img_url: data.img_url
        }
        this.selectedCategoryIds = (data.categories || []).map(c => c.id).filter(Boolean)
        // 确保有主分类名称可显示
        if (this.selectedCategoryIds.length && !this.form.category_name) {
          const first = this.categories.find(c => c.id === this.selectedCategoryIds[0])
          this.form.category_name = first?.name || ''
        }
        this.fetchPrice()
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      }
    },
    async fetchInventory() {
      try {
        const inv = await api.getInventoryOverview()
        const row = (inv || []).find(item => item.product_id === this.id)
        this.stock = row ? row.stock : 0
      } catch (err) {
        this.stock = 0
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
        await api.updateProduct(this.id, {
          ...this.form,
          categories: this.selectedCategoryIds.map(id => ({ id })),
          category_id: this.selectedCategoryIds[0] || null,
          pack_price_ref: this.showPackPriceRef ? this.form.pack_price_ref : null
        })
        uni.showToast({ title: '已保存', icon: 'success' })
        this.fetchPrice()
      } catch (err) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    onCategoryChange(e) {
      const idx = Number(e.detail.value)
      const cat = this.categories[idx]
      if (cat) {
        const exists = this.selectedCategoryIds.includes(cat.id)
        this.selectedCategoryIds = exists
          ? this.selectedCategoryIds.filter(x => x !== cat.id)
          : this.selectedCategoryIds.concat(cat.id)
        this.form.category_id = this.selectedCategoryIds[0] || ''
        this.form.category_name = this.categories.find(c => c.id === this.form.category_id)?.name || ''
      }
    },
    async adjustInventory() {
      if (!this.adjustDelta) {
        uni.showToast({ title: '请输入调整数量', icon: 'none' })
        return
      }
      try {
        await api.adjustInventory(
          {
            product_id: this.id,
            delta: Number(this.adjustDelta),
            reason: this.adjustReason || '手动调整'
          },
          uni.getStorageSync('yh-username') || ''
        )
        uni.showToast({ title: '库存已调整', icon: 'success' })
        this.adjustDelta = 0
        this.adjustReason = ''
        this.fetchInventory()
      } catch (err) {
        uni.showToast({ title: '调整失败', icon: 'none' })
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
