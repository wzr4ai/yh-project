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
      <view class="label">商家分类</view>
      <picker :range="merchantCategories" range-key="name" :value="merchantIndex" @change="onMerchantChange" :disabled="!isOwner">
        <view class="picker-value">{{ merchantLabel }}</view>
      </picker>
    </view>
    <view class="form-row">
      <view class="label">自定义分类</view>
      <view class="chips">
        <view
          v-for="cat in customCategories"
          :key="cat.id || 'none'"
          :class="['chip', selectedCustomIds.includes(cat.id) ? 'active' : '']"
          @tap="isOwner ? onCustomCategoryChange(cat.id) : null"
        >
          {{ cat.name }}
        </view>
      </view>
    </view>
      <view class="form-row">
        <view class="label">进价</view>
        <input class="input" type="digit" inputmode="decimal" v-model="form.base_cost_price" :disabled="!isOwner" placeholder="进价（可小数）" />
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
        <input class="input" type="digit" inputmode="decimal" v-model="form.fixed_retail_price" :disabled="!isOwner" placeholder="为空则按分类/全局系数计算，可小数" />
      </view>
      <view class="form-row">
        <view class="label">图片</view>
        <input class="input" v-model="form.img_url" :disabled="!isOwner" placeholder="图片 URL (可选)" />
      </view>
      <view class="form-row">
        <view class="label">效果链接</view>
        <input class="input" v-model="form.effect_url" :disabled="!isOwner" placeholder="烟花效果展示链接 (可选)" />
      </view>
    </view>

    <view class="card">
      <view class="section-title">库存</view>
      <view class="info-row">
        <view class="info-label">当前库存</view>
        <view class="info-value">{{ stockDisplay }}</view>
      </view>
      <view v-if="isOwner">
        <view class="quick-actions">
          <view class="quick-row" v-if="specUnits > 1">
            <button size="mini" class="quick-btn danger" @tap="quickAdjustBox(-1)">-1箱</button>
            <button size="mini" class="quick-btn" @tap="quickAdjustBox(1)">+1箱</button>
          </view>
          <view class="quick-row">
            <button size="mini" class="quick-btn danger" @tap="quickAdjustUnit(-1)">-1个</button>
            <button size="mini" class="quick-btn" @tap="quickAdjustUnit(1)">+1个</button>
          </view>
          <view class="quick-hint" v-if="specUnits > 1">说明：箱按 {{ specUnits }} 个/箱 折算</view>
        </view>

        <view class="form-row">
          <view class="label">调整箱数</view>
          <input class="input" type="number" v-model.number="adjustBoxDelta" placeholder="+/- 箱" />
        </view>
        <view class="form-row" v-if="specUnits > 1">
          <view class="label">调整散件</view>
          <input class="input" type="number" v-model.number="adjustLooseDelta" placeholder="+/- 个" />
        </view>
        <view class="form-row">
          <view class="label">原因</view>
          <input class="input" v-model="adjustReason" placeholder="原因(可选)" />
        </view>
        <view class="adjust-actions">
          <button type="primary" size="mini" @tap="adjustInventory">调整库存</button>
          <button size="mini" @tap="resetAdjust">清空</button>
        </view>
      </view>
    </view>

    <view class="actions" v-if="isOwner">
      <button type="primary" :loading="saving" @tap="save">保存</button>
      <button class="delete-btn" size="mini" @tap="confirmDelete">删除商品</button>
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
        img_url: '',
        effect_url: ''
      },
      price: {
        price: null,
        basis: ''
      },
      customCategories: [],
      merchantCategories: [],
      selectedCustomIds: [],
      selectedMerchantId: '',
      stockBox: 0,
      stockLoose: 0,
      adjustBoxDelta: 0,
      adjustLooseDelta: 0,
      adjustReason: '',
      saving: false
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    merchantIndex() {
      const idx = this.merchantCategories.findIndex(c => c.id === this.selectedMerchantId)
      return idx >= 0 ? idx : 0
    },
    merchantLabel() {
      const cat = this.merchantCategories[this.merchantIndex]
      return cat ? cat.name : '未选择'
    },
    specQty() {
      const match = String(this.form.spec || '').match(/(\d+(\.\d+)?)/)
      const val = match ? parseFloat(match[1]) : 1
      return val > 0 ? val : 1
    },
    specUnits() {
      const val = Number(this.specQty) || 1
      const rounded = Math.round(val)
      if (Math.abs(val - rounded) < 1e-6) return Math.max(1, rounded)
      return Math.max(1, Math.floor(val))
    },
    packPriceCalc() {
      const qty = this.specQty
      const single = Number(this.form.base_cost_price) || 0
      return single * qty
    },
    stockDisplay() {
      if (this.specUnits <= 1) return `${this.stockBox}`
      return `${this.stockBox}箱 ${this.stockLoose}个`
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
        const list = data || []
        this.customCategories = list.filter(c => c.is_custom)
        this.merchantCategories = [{ id: '', name: '未选择' }].concat(list.filter(c => !c.is_custom))
      } catch (err) {
        this.customCategories = []
        this.merchantCategories = [{ id: '', name: '未选择' }]
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
          img_url: data.img_url,
          effect_url: data.effect_url
        }
        const custom = (data.categories || []).filter(c => c.is_custom).map(c => c.id).filter(Boolean)
        this.selectedCustomIds = custom
        this.selectedMerchantId = data.category_id || ''
        this.form.category_name =
          this.merchantCategories.find(c => c.id === this.selectedMerchantId)?.name || this.form.category_name || ''
        this.fetchPrice()
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      }
    },
    async fetchInventory() {
      try {
        const inv = await api.getInventory(this.id)
        this.stockBox = inv?.current_stock || 0
        this.stockLoose = inv?.loose_units || 0
      } catch (err) {
        this.stockBox = 0
        this.stockLoose = 0
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
        const baseCost = this.parsePrice(this.form.base_cost_price)
        const fixedRetail = this.parsePrice(this.form.fixed_retail_price)
        const packRef = this.parsePrice(this.form.pack_price_ref)
        await api.updateProduct(this.id, {
          ...this.form,
          base_cost_price: baseCost,
          fixed_retail_price: fixedRetail,
          pack_price_ref: this.showPackPriceRef ? packRef : null,
          categories: this.selectedCustomIds.map(id => ({ id })),
          category_id: this.selectedMerchantId || null,
          // 上面已填充 pack_price_ref
        })
        if (this.hasAdjustDelta()) {
          await this.adjustInventory(true)
        }
        uni.showToast({ title: '已保存', icon: 'success' })
        this.fetchPrice()
      } catch (err) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    onCustomCategoryChange(id) {
      const exists = this.selectedCustomIds.includes(id)
      this.selectedCustomIds = exists ? this.selectedCustomIds.filter(x => x !== id) : this.selectedCustomIds.concat(id)
    },
    onMerchantChange(e) {
      const idx = Number(e.detail.value)
      const cat = this.merchantCategories[idx]
      if (cat) {
        this.selectedMerchantId = cat.id || ''
        this.form.category_id = this.selectedMerchantId
        this.form.category_name = cat.name || ''
      }
    },
    parsePrice(val) {
      const num = parseFloat(val)
      return Number.isFinite(num) ? num : null
    },
    resetAdjust() {
      this.adjustBoxDelta = 0
      this.adjustLooseDelta = 0
      this.adjustReason = ''
    },
    hasAdjustDelta() {
      const box = Number(this.adjustBoxDelta) || 0
      const loose = Number(this.adjustLooseDelta) || 0
      return !!(box || loose)
    },
    async adjustInventoryWithUnits(deltaUnits, reason, skipToast = false) {
      const units = Number(deltaUnits) || 0
      const delta = units > 0 ? Math.floor(units) : Math.ceil(units)
      if (!delta) {
        uni.showToast({ title: '请输入调整数量', icon: 'none' })
        return
      }
      try {
        await api.adjustInventory(
          {
            product_id: this.id,
            delta,
            reason: reason || '手动调整'
          },
          uni.getStorageSync('yh-username') || ''
        )
        if (!skipToast) {
          uni.showToast({ title: '库存已调整', icon: 'success' })
        }
        this.resetAdjust()
        this.fetchInventory()
      } catch (err) {
        uni.showToast({ title: '调整失败', icon: 'none' })
      }
    },
    async adjustInventory(skipToast = false) {
      const box = Number(this.adjustBoxDelta) || 0
      const loose = Number(this.adjustLooseDelta) || 0
      const totalUnits = box * this.specUnits + (this.specUnits > 1 ? loose : 0)
      return this.adjustInventoryWithUnits(totalUnits, this.adjustReason || '手动调整', skipToast)
    },
    async quickAdjustBox(deltaBoxes) {
      const boxes = Number(deltaBoxes) || 0
      if (!boxes) return
      const deltaUnits = boxes * this.specUnits
      return this.adjustInventoryWithUnits(deltaUnits, `快速调整 ${boxes > 0 ? '+' : ''}${boxes} 箱`)
    },
    async quickAdjustUnit(deltaUnits) {
      const delta = Number(deltaUnits) || 0
      if (!delta) return
      return this.adjustInventoryWithUnits(delta, `快速调整 ${delta > 0 ? '+' : ''}${delta} 个`)
    },
    confirmDelete() {
      uni.showModal({
        title: '删除确认',
        content: '确定删除该商品？相关库存与分类关联将一并清理。',
        confirmText: '删除',
        confirmColor: '#d14343',
        success: async (res) => {
          if (res.confirm) {
            await this.deleteProduct()
          }
        }
      })
    },
    async deleteProduct() {
      try {
        await api.deleteProduct(this.id)
        uni.showToast({ title: '已删除', icon: 'success' })
        setTimeout(() => {
          uni.navigateBack()
        }, 400)
      } catch (err) {
        uni.showToast({ title: '删除失败', icon: 'none' })
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
  padding-bottom: 140rpx; /* 留给固定按钮 */
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
  display: flex;
  gap: 12rpx;
}

.delete-btn {
  background: #fff;
  color: #d14343;
  border: 1rpx solid #f3b6b6;
}

.quick-actions {
  margin: 10rpx 0 14rpx;
  padding: 14rpx;
  border-radius: 14rpx;
  background: #f9fafb;
  border: 1rpx solid #e5e7eb;
}

.quick-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10rpx;
}

.quick-row + .quick-row {
  margin-top: 10rpx;
}

.quick-btn {
  border: 1rpx solid #e5e7eb;
  background: #ffffff;
  color: #0f6a7b;
  font-weight: 600;
}

.quick-btn.danger {
  color: #b91c1c;
  border-color: #f3b6b6;
}

.quick-hint {
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #6b7280;
}

.adjust-actions {
  display: flex;
  gap: 12rpx;
  margin-top: 6rpx;
}
</style>
