<template>
  <view class="page">
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
            <button v-if="isNew(item)" size="mini" type="primary" class="link" @tap="goCreateProduct">新建商品</button>
          </view>
          <view class="field">
            <view class="label">数量</view>
            <input class="input" type="number" v-model.number="item.quantity" />
          </view>
          <view class="field">
            <view class="label">成交单价</view>
            <input class="input" type="digit" v-model.number="item.actual_price" placeholder="¥" />
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
      allProducts: []
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
        const res = await api.getProducts({ offset: 0, limit: 500 })
        this.allProducts = (res?.items || []).map(p => ({
          value: p.id,
          label: `${p.name}${p.spec ? '｜' + p.spec : ''}`
        }))
        // 将列表刷新到已有项上，避免初始显示“请选择”
        this.items = this.items.map(it => ({
          ...it,
          product_id: it.product_id || it.suggested_product_id,
          product_name: it.product_name || it.suggested_product_name
        }))
      } catch (e) {
        uni.showToast({ title: '商品列表获取失败', icon: 'none' })
      }
    },
    toggleInput() {
      this.inputCollapsed = !this.inputCollapsed
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
        this.$set(this.items[idx], 'product_id', choice.value)
        this.$set(this.items[idx], 'product_name', choice.label)
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
    async analyze() {
      const text = this.rawText.trim()
      if (!text) return
      this.loading = true
      try {
        const res = await api.analyzeOrders({ raw_text: text })
        const cleaned = (res?.items || []).map(it => ({
          ...it,
          product_id: it.suggested_product_id || '',
          product_name: it.suggested_product_name || '',
          actual_price: 0,
          confidenceTag: this.confidenceTag(it)
        }))
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
.link {
  margin-top: 6px;
}
.empty {
  text-align: center;
  color: #999;
  margin-top: 40px;
}
</style>
