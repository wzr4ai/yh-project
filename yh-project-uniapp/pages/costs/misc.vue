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
      <view class="form-row">
        <view class="label">成本支出方</view>
        <picker mode="selector" :range="payerOptions" range-key="label" :value="form.payer_index" @change="onCreatePayerChange">
          <view class="input">{{ currentCreatePayerLabel }}</view>
        </picker>
      </view>
      <button class="primary-btn" :loading="savingCreate" @tap="submit">保存</button>
    </view>

    <view class="card">
      <view class="title">最近记录</view>
      <view class="summary">总杂项成本：¥{{ totalAmount().toFixed(2) }}</view>
      <view v-if="records.length">
        <view class="record" v-for="rec in records" :key="rec.id">
          <view class="row">
            <view class="item">{{ rec.item }}</view>
            <view class="amount">¥{{ (Number(rec.amount || 0) * (Number(rec.quantity) || 1)).toFixed(2) }}</view>
          </view>
          <view class="meta">数量：{{ rec.quantity }} ｜ 支出方：{{ payerLabel(rec) }}</view>
          <view class="meta">时间：{{ formatDate(rec.created_at) }}</view>
          <view class="actions">
            <button size="mini" :disabled="deletingId === rec.id" @tap="startEdit(rec)">编辑</button>
            <button size="mini" type="warn" :loading="deletingId === rec.id" :disabled="deletingId === rec.id" @tap="confirmDelete(rec)">删除</button>
          </view>
        </view>
      </view>
      <view class="empty" v-else>暂无记录</view>
    </view>

    <view class="card" v-if="editId">
      <view class="title">编辑杂项成本</view>
      <view class="form-row">
        <view class="label">项目</view>
        <input class="input" v-model="editForm.item" />
      </view>
      <view class="form-row">
        <view class="label">数量</view>
        <input class="input" type="digit" inputmode="decimal" v-model="editForm.quantity" />
      </view>
      <view class="form-row">
        <view class="label">金额</view>
        <input class="input" type="digit" inputmode="decimal" v-model="editForm.amount" />
      </view>
      <view class="form-row">
        <view class="label">成本支出方</view>
        <picker mode="selector" :range="payerOptions" range-key="label" :value="editForm.payer_index" @change="onEditPayerChange">
          <view class="input">{{ currentEditPayerLabel }}</view>
        </picker>
      </view>
      <view class="edit-actions">
        <button size="mini" @tap="cancelEdit">取消</button>
        <button size="mini" type="primary" :loading="savingEdit" @tap="saveEdit">保存</button>
      </view>
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
        amount: '',
        payer_index: 0
      },
      editId: '',
      editForm: {
        item: '',
        quantity: '',
        amount: '',
        payer_index: 0
      },
      savingCreate: false,
      savingEdit: false,
      deletingId: '',
      records: [],
      shareholders: []
    }
  },
  computed: {
    payerOptions() {
      const options = [{ label: '公账', cost_payer_type: 'public', cost_payer_shareholder_id: null }]
      for (const item of this.shareholders) {
        options.push({
          label: item.name || '未命名股东',
          cost_payer_type: 'shareholder',
          cost_payer_shareholder_id: item.id
        })
      }
      return options
    },
    currentCreatePayerLabel() {
      const idx = this.normalizePayerIndex(this.form.payer_index)
      return this.payerOptions[idx]?.label || '公账'
    },
    currentEditPayerLabel() {
      const idx = this.normalizePayerIndex(this.editForm.payer_index)
      return this.payerOptions[idx]?.label || '公账'
    }
  },
  onShow() {
    this.loadData()
  },
  methods: {
    normalizePayerIndex(index) {
      const idx = Number(index)
      if (!Number.isInteger(idx) || idx < 0 || idx >= this.payerOptions.length) return 0
      return idx
    },
    findPayerIndex(costPayerType, costPayerShareholderId) {
      const type = costPayerType || 'public'
      const holderId = costPayerShareholderId || null
      const idx = this.payerOptions.findIndex((item) => {
        return item.cost_payer_type === type && (item.cost_payer_shareholder_id || null) === holderId
      })
      return idx >= 0 ? idx : 0
    },
    selectedPayer(index) {
      const idx = this.normalizePayerIndex(index)
      return this.payerOptions[idx] || this.payerOptions[0]
    },
    onCreatePayerChange(e) {
      this.form.payer_index = Number(e?.detail?.value || 0)
    },
    onEditPayerChange(e) {
      this.editForm.payer_index = Number(e?.detail?.value || 0)
    },
    resetCreateForm() {
      this.form = {
        item: '',
        quantity: '',
        amount: '',
        payer_index: 0
      }
    },
    resetEditForm() {
      this.editId = ''
      this.editForm = {
        item: '',
        quantity: '',
        amount: '',
        payer_index: 0
      }
    },
    payerLabel(rec) {
      const type = rec?.cost_payer_type || 'public'
      if (type !== 'shareholder') return '公账'
      const holderId = rec?.cost_payer_shareholder_id
      if (!holderId) return '股东'
      const holder = this.shareholders.find((item) => item.id === holderId)
      return holder?.name || '股东'
    },
    totalAmount() {
      return this.records.reduce((acc, cur) => {
        const qty = Number(cur.quantity) || 1
        const amt = Number(cur.amount) || 0
        return acc + qty * amt
      }, 0)
    },
    async submit() {
      if (this.savingCreate) return
      const item = (this.form.item || '').trim()
      const quantity = this.parseNumber(this.form.quantity, 1)
      const amount = this.parseNumber(this.form.amount, null)
      const payer = this.selectedPayer(this.form.payer_index)
      if (!item) {
        uni.showToast({ title: '请输入项目', icon: 'none' })
        return
      }
      if (!Number.isFinite(quantity) || quantity <= 0) {
        uni.showToast({ title: '请输入正确数量', icon: 'none' })
        return
      }
      if (amount === null) {
        uni.showToast({ title: '请输入金额', icon: 'none' })
        return
      }
      this.savingCreate = true
      try {
        const created = await api.createMiscCost({
          item,
          quantity,
          amount,
          cost_payer_type: payer.cost_payer_type,
          cost_payer_shareholder_id: payer.cost_payer_shareholder_id
        })
        uni.showToast({ title: '已保存', icon: 'success' })
        if (created && created.id) {
          this.records = [created, ...this.records]
        } else {
          await this.loadRecords()
        }
        this.resetCreateForm()
      } catch (e) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.savingCreate = false
      }
    },
    startEdit(rec) {
      this.editId = rec.id
      this.editForm = {
        item: rec.item,
        quantity: String(rec.quantity ?? ''),
        amount: String(rec.amount ?? ''),
        payer_index: this.findPayerIndex(rec.cost_payer_type, rec.cost_payer_shareholder_id)
      }
    },
    cancelEdit() {
      this.resetEditForm()
    },
    async saveEdit() {
      if (!this.editId || this.savingEdit) return
      const item = (this.editForm.item || '').trim()
      const quantity = this.parseNumber(this.editForm.quantity, 1)
      const amount = this.parseNumber(this.editForm.amount, null)
      const payer = this.selectedPayer(this.editForm.payer_index)
      if (!item) {
        uni.showToast({ title: '请输入项目', icon: 'none' })
        return
      }
      if (!Number.isFinite(quantity) || quantity <= 0) {
        uni.showToast({ title: '请输入正确数量', icon: 'none' })
        return
      }
      if (amount === null) {
        uni.showToast({ title: '请输入金额', icon: 'none' })
        return
      }
      this.savingEdit = true
      try {
        const updated = await api.updateMiscCost(this.editId, {
          item,
          quantity,
          amount,
          cost_payer_type: payer.cost_payer_type,
          cost_payer_shareholder_id: payer.cost_payer_shareholder_id
        })
        uni.showToast({ title: '已更新', icon: 'success' })
        if (updated && updated.id) {
          this.records = this.records.map((item) => (item.id === updated.id ? updated : item))
        } else {
          await this.loadRecords()
        }
        this.resetEditForm()
      } catch (e) {
        uni.showToast({ title: '更新失败', icon: 'none' })
      } finally {
        this.savingEdit = false
      }
    },
    confirmDelete(rec) {
      if (!rec?.id || this.deletingId) return
      uni.showModal({
        title: '删除确认',
        content: `确认删除“${rec.item || '该记录'}”吗？`,
        success: async (modalRes) => {
          if (!modalRes.confirm) return
          this.deletingId = rec.id
          try {
            await api.deleteMiscCost(rec.id)
            this.records = this.records.filter((item) => item.id !== rec.id)
            if (this.editId === rec.id) this.resetEditForm()
            uni.showToast({ title: '已删除', icon: 'success' })
          } catch (e) {
            uni.showToast({ title: '删除失败', icon: 'none' })
          } finally {
            this.deletingId = ''
          }
        }
      })
    },
    async loadData() {
      await Promise.all([this.loadRecords(), this.loadShareholders()])
      if (this.editId) {
        this.editForm.payer_index = this.normalizePayerIndex(this.editForm.payer_index)
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
    async loadShareholders() {
      try {
        const res = await api.listShareholders({ activeOnly: false })
        this.shareholders = Array.isArray(res) ? res : []
      } catch (e) {
        this.shareholders = []
      }
      this.form.payer_index = this.normalizePayerIndex(this.form.payer_index)
      this.editForm.payer_index = this.normalizePayerIndex(this.editForm.payer_index)
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
.summary {
  font-weight: 600;
  margin-bottom: 8px;
  color: #0f6a7b;
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
.actions {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.empty {
  text-align: center;
  color: #999;
}
</style>
