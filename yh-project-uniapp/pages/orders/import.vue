<template>
  <view class="page">
    <view class="input-card">
      <view class="header">
        <view class="title">文件导入</view>
        <view class="subtitle">支持 CSV / TXT，便于批量校对</view>
      </view>
      <button class="primary-btn" :loading="uploading" :disabled="uploading" @tap="uploadCsv">
        {{ uploading ? '上传中...' : '上传文件' }}
      </button>
      <view class="upload-info" v-if="uploadFileName">已选择：{{ uploadFileName }}</view>
    </view>

    <view class="input-card" :class="{ collapsed: inputCollapsed }">
      <view class="header">
        <view class="title">原始订单文本</view>
        <button size="mini" @tap="toggleInput">{{ inputCollapsed ? '展开' : '收起' }}</button>
      </view>
      <textarea
        v-show="!inputCollapsed"
        class="textarea"
        v-model="rawText"
        placeholder="请粘贴聊天记录或订单文本..."
        maxlength="-1"
        auto-height
      />
      <button class="primary-btn" :disabled="!rawText.trim() || loading" :loading="loading" @tap="analyze">
        智能识别
      </button>
    </view>

    <view class="card" v-if="items.length">
      <view class="card-title">校对结果</view>
      <view class="legend">
        <view class="legend-item high">高置信</view>
        <view class="legend-item low">存疑</view>
        <view class="legend-item new">新商品</view>
      </view>
      <scroll-view scroll-y class="list">
        <view
          class="row"
          v-for="(item, idx) in items"
          :key="idx"
          :class="rowClass(item)"
        >
          <view class="row-header">
            <view class="raw-name">{{ item.raw_name }}</view>
            <view class="tag" v-if="item.confidenceTag">{{ item.confidenceTag }}</view>
          </view>
          <view class="field">
            <view class="label">匹配商品</view>
            <picker
              mode="selector"
              :range="pickerOptions(item)"
              range-key="label"
              :value="selectedIndex(item)"
              @change="onSelect(idx, $event.detail.value)"
            >
              <view class="picker-value">
                {{ displayName(item) }}
              </view>
            </picker>
            <button v-if="isNew(item) || isLow(item)" size="mini" type="primary" class="link" @tap="goCreateProduct">新建商品</button>
          </view>
          <view class="field">
            <view class="label">数量</view>
            <input class="input" type="number" v-model.number="item.quantity" />
          </view>
          <view class="field">
            <view class="label">成交单价</view>
            <input class="input" type="digit" v-model.number="item.actual_price" placeholder="¥" />
            <view class="price-hint" v-if="item.product_price || item.product_spec || item.product_base_cost !== null || item.detected_price != null">
              <view>
                数据库单价：{{ item.product_base_cost != null ? `¥${item.product_base_cost}` : '无' }}
              </view>
              <view>
                规格：{{ item.product_spec || '无' }} ｜
                箱价：{{ item.product_box_price != null ? `¥${item.product_box_price}` : '无' }}
              </view>
              <view v-if="item.detected_price != null">
                订单价：¥{{ item.detected_price }}
              </view>
            </view>
          </view>
        </view>
      </scroll-view>
      <button class="primary-btn" :loading="saving" :disabled="saving || !canSubmit" @tap="submitImport">确认入库</button>
    </view>

    <view v-else class="empty">
      粘贴文本后点击“智能识别”开始校对
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      rawText: '',
      inputCollapsed: false,
      items: [],
      loading: false,
      saving: false,
      allProducts: [],
      uploading: false,
      uploadFileName: ''
    }
  },
  computed: {
    canSubmit() {
      return this.items.every(i => i.product_id && i.quantity > 0 && i.actual_price !== null && i.actual_price !== undefined)
    }
  },
  onLoad() {
    this.fetchAllProducts()
  },
  methods: {
    async fetchAllProducts() {
      try {
        const res = await api.getProducts({ offset: 0, limit: 2000 })
        this.allProducts = (res?.items || []).map(p => ({
          value: p.id,
          label: `${p.name}${p.spec ? '｜' + p.spec : ''}`,
          standard_price: this.pickStandardPrice(p),
          base_cost_price: p.base_cost_price ?? null,
          name: p.name,
          spec: p.spec,
          spec_qty: this.parseSpecQty(p.spec),
          box_price: p.spec && p.base_cost_price != null && p.base_cost_price !== undefined
            ? (p.base_cost_price * this.parseSpecQty(p.spec)).toFixed(2)
            : null
        }))
        // 将列表刷新到已有项上，避免初始显示“请选择”
        this.items = this.items.map(it => this.enrichPrice(it))
      } catch (e) {
        uni.showToast({ title: '商品列表获取失败', icon: 'none' })
      }
    },
    async uploadCsv() {
      try {
        const chooseRes = await new Promise((resolve, reject) => {
          uni.chooseMessageFile({
            count: 1,
            type: 'file',
            extension: ['csv', 'txt'],
            success: resolve,
            fail: reject
          })
        })
        const file = chooseRes?.tempFiles?.[0]
        if (!file) return
        this.uploading = true
        this.uploadFileName = file.name || 'orders.csv'
        await api.uploadOrderCsv(file.path, this.uploadFileName)
        uni.showToast({ title: '上传成功', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: '上传失败', icon: 'none' })
      } finally {
        this.uploading = false
      }
    },
    toggleInput() {
      this.inputCollapsed = !this.inputCollapsed
    },
    parseSpecQty(spec) {
      const match = String(spec || '').match(/(\d+(\.\d+)?)/)
      const val = match ? parseFloat(match[1]) : 1
      return val > 0 ? val : 1
    },
    pickStandardPrice(prod) {
      // 优先使用数据库中的基础进价(base_cost_price)
      if (prod && prod.base_cost_price !== undefined && prod.base_cost_price !== null) return prod.base_cost_price
      if (prod && prod.standard_price !== undefined && prod.standard_price !== null) return prod.standard_price
      if (prod && prod.fixed_retail_price !== undefined && prod.fixed_retail_price !== null) return prod.fixed_retail_price
      return null
    },
    enrichPrice(item) {
      const pid = item.product_id || item.suggested_product_id
      let prod = this.allProducts.find(p => p.value === pid)
      if (!prod && item.product_name) {
        const nameLower = item.product_name.toLowerCase()
        prod = this.allProducts.find(p => (p.name || '').toLowerCase() === nameLower)
      }
      if (!prod && item.raw_name) {
        const rawLower = item.raw_name.toLowerCase()
        prod = this.allProducts.find(p => (p.name || '').toLowerCase() === rawLower)
      }
      const standardPrice = prod?.standard_price
      const baseCost = prod?.base_cost_price
      const spec = prod?.spec || ''
      const boxPrice = prod?.box_price ? Number(prod.box_price) : null
      const detected = item.detected_price
      let prefilled = item.actual_price || 0
      if (detected != null && standardPrice != null && Math.abs(detected - standardPrice) < 1e-6) {
        prefilled = detected
      } else if (item.actual_price == null || item.actual_price === 0) {
        prefilled = detected || standardPrice || 0
      }
      return {
        ...item,
        product_price: standardPrice ?? baseCost ?? null,
        product_base_cost: baseCost ?? null,
        prefilled_price: prefilled,
        product_spec: spec,
        product_box_price: boxPrice
      }
    },
    rowClass(item) {
      const conf = (item.confidence || '').toLowerCase()
      if (conf === 'high') return 'high'
      if (conf === 'new') return 'new'
      return 'low'
    },
    confidenceTag(item) {
      const conf = (item.confidence || '').toLowerCase()
      if (conf === 'high') return '高置信'
      if (conf === 'new') return '新商品'
      return '存疑'
    },
    pickerOptions(item) {
      const candidateOpts = (item.candidates || [])
        .filter(c => c.product_id)
        .map(c => ({ value: c.product_id, label: c.product_name || c.product_id }))
      const merged = [...candidateOpts]
      // 确保当前选中的项在列表中
      const currentId = item.product_id || item.suggested_product_id
      const currentLabel = item.product_name || item.suggested_product_name
      if (currentId && !merged.find(x => x.value === currentId)) {
        merged.push({ value: currentId, label: currentLabel || currentId })
      }
      this.allProducts.forEach(p => {
        if (!merged.find(x => x.value === p.value)) merged.push(p)
      })
      return merged
    },
    selectedIndex(item) {
      const opts = this.pickerOptions(item)
      const pid = item.product_id || item.suggested_product_id
      const idx = opts.findIndex(o => o.value === pid)
      return idx >= 0 ? idx : 0
    },
    onSelect(idx, optIndex) {
      const options = this.pickerOptions(this.items[idx])
      const choice = options[optIndex]
      if (choice) {
        const updated = {
          ...this.items[idx],
          product_id: choice.value,
          product_name: choice.label
        }
        const enriched = this.enrichPrice(updated)
        if (this.items[idx].actual_price == null || this.items[idx].actual_price === 0) {
          enriched.actual_price = enriched.prefilled_price
        }
        this.$set(this.items, idx, enriched)
      }
    },
    displayName(item) {
      const options = this.pickerOptions(item)
      const pid = item.product_id || item.suggested_product_id
      const found = options.find(o => o.value === pid)
      if (found) return found.label
      return item.product_name || item.suggested_product_name || '请选择商品'
    },
    isNew(item) {
      return (item.confidence || '').toLowerCase() === 'new'
    },
    isLow(item) {
      return (item.confidence || '').toLowerCase() === 'low'
    },
    async analyze() {
      const text = this.rawText.trim()
      if (!text) return
      this.loading = true
      try {
        const res = await api.analyzeOrders({ raw_text: text })
        const cleaned = (res?.items || []).map(it => {
          const normalized = {
            ...it,
            product_id: it.suggested_product_id || '',
            product_name: it.suggested_product_name || '',
            confidenceTag: this.confidenceTag(it),
            detected_price: it.detected_price
          }
          const enriched = this.enrichPrice(normalized)
          return {
            ...enriched,
            actual_price: enriched.prefilled_price
          }
        })
        this.items = cleaned
        this.inputCollapsed = true
        uni.showToast({ title: '识别完成', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: '识别失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    async submitImport() {
      if (!this.canSubmit) {
        uni.showToast({ title: '请完善商品与数量/价格', icon: 'none' })
        return
      }
      this.saving = true
      try {
        const payload = {
          items: this.items.map(it => ({
            product_id: it.product_id,
            quantity: Number(it.quantity) || 0,
            actual_price: Number(it.actual_price) || 0,
            raw_name: it.raw_name
          }))
        }
        await api.importOrders(payload)
        uni.showToast({ title: '已导入', icon: 'success' })
        this.items = []
        this.rawText = ''
        this.inputCollapsed = false
      } catch (e) {
        uni.showToast({ title: '导入失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    goCreateProduct() {
      uni.navigateTo({ url: '/pages/products/create' })
    }
  }
}
</script>

<style lang="scss">
.page {
  padding: 12px;
}
.input-card,
.card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.input-card.collapsed .textarea {
  display: none;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.subtitle {
  font-size: 12px;
  color: #666;
}
.title {
  font-weight: 600;
}
.textarea {
  width: 100%;
  min-height: 240px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 10px;
  box-sizing: border-box;
  background: #f8fafc;
  margin-bottom: 10px;
}
.primary-btn {
  background: #0f6a7b;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px;
}
.upload-info {
  margin-top: 8px;
  font-size: 12px;
  color: #555;
}
.card-title {
  font-weight: 600;
  margin-bottom: 8px;
}
.legend {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.legend-item {
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  color: #fff;
}
.legend-item.high {
  background: #2ecc71;
}
.legend-item.low {
  background: #f5a524;
}
.legend-item.new {
  background: #f56c6c;
}
.list {
  max-height: 60vh;
}
.row {
  border: 1px solid #e5e6eb;
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 10px;
}
.row.high {
  background: #f0fff4;
}
.row.low {
  background: #fff8e6;
}
.row.new {
  background: #fff1f0;
}
.row-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.raw-name {
  font-weight: 600;
}
.tag {
  font-size: 12px;
  color: #666;
}
.field {
  margin-bottom: 8px;
}
.label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}
.picker-value {
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
}
.input {
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
}
.price-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}
.link {
  margin-top: 6px;
}
.empty {
  text-align: center;
  color: #999;
  margin-top: 40px;
}
</style>
