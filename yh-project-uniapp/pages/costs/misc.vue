<template>
  <view class="page">
    <view class="card">
      <view class="title">记录杂项成本</view>
      <view class="form-row">
        <view class="label">项目</view>
        <input class="input" v-model="form.item" placeholder="如：运输费、耗材" />
      </view>
      <view class="form-row">
        <view class="label">数量</view>
        <input class="input" type="digit" inputmode="decimal" v-model="form.quantity" placeholder="数量(可小数)" />
      </view>
      <view class="form-row">
        <view class="label">金额</view>
        <input class="input" type="digit" inputmode="decimal" v-model="form.amount" placeholder="金额(元)" />
      </view>
      <button class="primary-btn" :loading="saving" @tap="submit">保存</button>
    </view>

    <view class="card">
      <view class="title">最近记录</view>
      <view v-if="records.length">
        <view class="record" v-for="rec in records" :key="rec.id">
          <view class="row">
            <view class="item">{{ rec.item }}</view>
            <view class="amount">¥{{ rec.amount }}</view>
          </view>
          <view class="meta">数量：{{ rec.quantity }} ｜ 时间：{{ formatDate(rec.created_at) }}</view>
        </view>
      </view>
      <view class="empty" v-else>暂无记录</view>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      form: {
        item: '',
        quantity: '',
        amount: ''
      },
      saving: false,
      records: []
    }
  },
  onShow() {
    this.loadRecords()
  },
  methods: {
    async submit() {
      const item = (this.form.item || '').trim()
      const quantity = this.parseNumber(this.form.quantity, 1)
      const amount = this.parseNumber(this.form.amount, null)
      if (!item) {
        uni.showToast({ title: '请输入项目', icon: 'none' })
        return
      }
      if (amount === null) {
        uni.showToast({ title: '请输入金额', icon: 'none' })
        return
      }
      this.saving = true
      try {
        await api.createMiscCost({ item, quantity, amount })
        uni.showToast({ title: '已保存', icon: 'success' })
        this.form = { item: '', quantity: '', amount: '' }
        this.loadRecords()
      } catch (e) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    async loadRecords() {
      try {
        const res = await api.listMiscCosts({ limit: 50 })
        this.records = res || []
      } catch (e) {
        this.records = []
      }
    },
    parseNumber(val, fallback) {
      const num = parseFloat(val)
      if (!Number.isFinite(num)) return fallback
      return num
    },
    formatDate(val) {
      if (!val) return ''
      const d = new Date(val)
      if (Number.isNaN(d.getTime())) return ''
      const pad = (n) => (n < 10 ? `0${n}` : `${n}`)
      return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
    }
  }
}
</script>

<style lang="scss">
.page {
  padding: 12px;
}
.card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.title {
  font-weight: 600;
  margin-bottom: 10px;
}
.form-row {
  margin-bottom: 10px;
}
.label {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}
.input {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  background: #f8fafc;
}
.primary-btn {
  background: #0f6a7b;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px;
}
.record {
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}
.record:last-child {
  border-bottom: none;
}
.row {
  display: flex;
  justify-content: space-between;
  font-weight: 600;
}
.meta {
  color: #777;
  font-size: 12px;
  margin-top: 4px;
}
.amount {
  color: #e67e22;
}
.empty {
  text-align: center;
  color: #999;
}
</style>
