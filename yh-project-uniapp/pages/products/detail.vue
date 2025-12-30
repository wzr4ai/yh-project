<template>
  <view class="page">
    <view class="card">
      <view class="section-title">商品信息</view>
      <view class="form-row">
        <view class="label">名称</view>
        <input class="input" v-model="form.name" :disabled="!isOwner" placeholder="商品名称" />
      </view>
      <view class="form-row">
        <view class="label">条码</view>
        <input class="input" v-model="form.barcode" :disabled="!isOwner" placeholder="商品条码 (可选)" />
        <button v-if="isOwner" size="mini" class="scan-btn" @tap="scanMainBarcode">扫码</button>
      </view>
      <view class="form-row" v-if="isOwner">
        <view class="label">条码列表</view>
        <view class="barcode-list">
          <view class="barcode-row" v-for="(item, idx) in form.barcodes" :key="idx">
            <input class="input barcode-input" v-model="item.barcode" placeholder="条码" />
            <picker :range="barcodeLevels" :value="barcodeLevelIndex(item.level)" @change="onBarcodeLevelChange(idx, $event)">
              <view class="picker-value">{{ item.level || 'PIECE' }}</view>
            </picker>
            <button size="mini" class="scan-btn" @tap="scanBarcode(idx)">扫码</button>
            <button size="mini" type="warn" @tap="removeBarcode(idx)">删除</button>
          </view>
          <view class="barcode-actions">
            <button size="mini" @tap="addBarcode">添加条码</button>
            <button size="mini" @tap="scanNewBarcode">扫码新增</button>
          </view>
        </view>
      </view>
    <view class="form-row">
      <view class="label">规格说明</view>
      <input class="input" v-model="form.spec" :disabled="!isOwner" placeholder="规格描述（如：1x10x6）" />
    </view>
    <view class="form-row">
      <view class="label">每箱中包数</view>
      <input class="input" type="number" v-model.number="form.units_per_box" :disabled="!isOwner" placeholder="如：10" />
    </view>
    <view class="form-row">
      <view class="label">每包件数</view>
      <input class="input" type="number" v-model.number="form.pieces_per_unit" :disabled="!isOwner" placeholder="如：6" />
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
        <view class="label">整箱进价</view>
        <input class="input" type="digit" inputmode="decimal" v-model="form.box_cost_price" :disabled="!isOwner" placeholder="整箱进价（可小数）" />
      </view>
      <view class="info-row">
        <view class="info-label">每箱件数</view>
        <view class="info-value">{{ piecesPerBox }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">箱价</view>
        <view class="info-value">¥{{ boxPriceCalc.toFixed(2) }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">箱成本</view>
        <view class="info-value">¥{{ boxCostLevel.toFixed(2) }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">包成本</view>
        <view class="info-value">¥{{ unitCostLevel.toFixed(2) }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">件成本</view>
        <view class="info-value">¥{{ pieceCostLevel.toFixed(2) }}</view>
      </view>
      <view class="form-row" v-if="showPackPriceRef">
        <view class="label">箱价(参考)</view>
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
import { formatStock } from '../../common/stock.js'

export default {
  data() {
    return {
      id: '',
      role: getRole(),
      form: {
        name: '',
        barcode: '',
        spec: '',
        units_per_box: 1,
        pieces_per_unit: 1,
        category_id: '',
        category_name: '',
        box_cost_price: null,
        base_cost_price: null,
        fixed_retail_price: null,
        pack_price_ref: null,
        img_url: '',
        effect_url: '',
        barcodes: []
      },
      price: {
        price: null,
        basis: ''
      },
      customCategories: [],
      merchantCategories: [],
      selectedCustomIds: [],
      selectedMerchantId: '',
      stockPieces: 0,
      saving: false,
      barcodeLevels: ['BOX', 'UNIT', 'PIECE']
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
    unitsPerBox() {
      return this.parseInt(this.form.units_per_box, 1)
    },
    piecesPerUnit() {
      return this.parseInt(this.form.pieces_per_unit, 1)
    },
    piecesPerBox() {
      return this.unitsPerBox * this.piecesPerUnit
    },
    boxPriceCalc() {
      const boxCost = Number(this.form.box_cost_price) || 0
      if (boxCost > 0) return boxCost
      const pieceCost = Number(this.form.base_cost_price) || 0
      return pieceCost * this.piecesPerBox
    },
    boxCostLevel() {
      return this.boxPriceCalc
    },
    unitCostLevel() {
      return this.unitsPerBox ? this.boxPriceCalc / this.unitsPerBox : 0
    },
    pieceCostLevel() {
      return this.piecesPerBox ? this.boxPriceCalc / this.piecesPerBox : 0
    },
    stockDisplay() {
      return formatStock(this.stockPieces, {
        units_per_box: this.unitsPerBox,
        pieces_per_unit: this.piecesPerUnit
      })
    },
    showPackPriceRef() {
      if (this.form.pack_price_ref === null || this.form.pack_price_ref === undefined) return false
      return Math.abs((Number(this.form.pack_price_ref) || 0) - this.boxPriceCalc) > 0.01
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
          barcode: data.barcode || '',
          spec: data.spec,
          units_per_box: data.units_per_box || 1,
          pieces_per_unit: data.pieces_per_unit || 1,
          category_id: data.category_id,
          category_name: data.category_name || '',
          box_cost_price: data.box_cost_price || null,
          base_cost_price: data.base_cost_price,
          fixed_retail_price: data.fixed_retail_price,
          pack_price_ref: data.pack_price_ref,
          img_url: data.img_url,
          effect_url: data.effect_url,
          barcodes: (data.barcodes || []).map(b => ({ barcode: b.barcode, level: b.level || 'PIECE' }))
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
        this.stockPieces = inv?.current_stock || 0
      } catch (err) {
        this.stockPieces = 0
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
        const units = this.parseInt(this.form.units_per_box, 1)
        const pieces = this.parseInt(this.form.pieces_per_unit, 1)
        const boxCost = this.parsePrice(this.form.box_cost_price)
        const baseCost = boxCost && units > 0 && pieces > 0 ? boxCost / (units * pieces) : 0
        const fixedRetail = this.parsePrice(this.form.fixed_retail_price)
        const packRef = this.parsePrice(this.form.pack_price_ref)
        await api.updateProduct(this.id, {
          ...this.form,
          units_per_box: units,
          pieces_per_unit: pieces,
          box_cost_price: boxCost,
          base_cost_price: baseCost,
          fixed_retail_price: fixedRetail,
          pack_price_ref: this.showPackPriceRef ? packRef : null,
          barcodes: (this.form.barcodes || []).filter(b => b && b.barcode),
          categories: this.selectedCustomIds.map(id => ({ id })),
          category_id: this.selectedMerchantId || null,
          // 上面已填充 pack_price_ref
        })
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
    parseInt(val, fallback) {
      const num = parseInt(val, 10)
      return Number.isFinite(num) && num > 0 ? num : fallback
    },
    addBarcode() {
      this.form.barcodes.push({ barcode: '', level: 'PIECE' })
    },
    removeBarcode(idx) {
      if (idx < 0) return
      this.form.barcodes.splice(idx, 1)
    },
    barcodeLevelIndex(level) {
      const idx = this.barcodeLevels.indexOf(level)
      return idx >= 0 ? idx : 2
    },
    onBarcodeLevelChange(idx, e) {
      const val = Number(e.detail.value)
      const level = this.barcodeLevels[val] || 'PIECE'
      if (this.form.barcodes[idx]) {
        this.form.barcodes[idx].level = level
      }
    },
    scanBarcode(idx) {
      uni.scanCode({
        onlyFromCamera: true,
        scanType: ['barCode', 'qrCode'],
        success: (res) => {
          const code = (res.result || '').trim()
          if (!code) return
          if (this.form.barcodes[idx]) {
            this.form.barcodes[idx].barcode = code
          }
        },
        fail: () => {
          uni.showToast({ title: '扫码失败', icon: 'none' })
        }
      })
    },
    scanMainBarcode() {
      uni.scanCode({
        onlyFromCamera: true,
        scanType: ['barCode', 'qrCode'],
        success: (res) => {
          const code = (res.result || '').trim()
          if (!code) return
          this.form.barcode = code
        },
        fail: () => {
          uni.showToast({ title: '扫码失败', icon: 'none' })
        }
      })
    },
    scanNewBarcode() {
      uni.scanCode({
        onlyFromCamera: true,
        scanType: ['barCode', 'qrCode'],
        success: (res) => {
          const code = (res.result || '').trim()
          if (!code) return
          this.form.barcodes.push({ barcode: code, level: 'PIECE' })
        },
        fail: () => {
          uni.showToast({ title: '扫码失败', icon: 'none' })
        }
      })
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

.barcode-list {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.barcode-row {
  display: flex;
  gap: 10rpx;
  align-items: center;
  flex-wrap: wrap;
}

.barcode-input {
  flex: 1;
}

.picker-value {
  padding: 10rpx 12rpx;
  border: 1rpx solid #e5e7eb;
  border-radius: 10rpx;
  background: #f9fafb;
  color: #0b1f3a;
  font-size: 24rpx;
}

.barcode-actions {
  display: flex;
  gap: 10rpx;
}

.scan-btn {
  margin-left: 8rpx;
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

</style>
