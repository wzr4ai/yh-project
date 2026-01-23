<template>
  <view class="page">
    <view class="card">
      <view class="title">股东资金概览</view>
      <view class="summary">
        净利润 ¥{{ formatNum(summary.net_profit) }} ｜
        毛利润 ¥{{ formatNum(summary.gross_profit) }} ｜
        可分配 ¥{{ formatNum(summary.distributable_total) }}
      </view>
    </view>

    <view class="card">
      <view class="title">股东管理</view>
      <button class="primary-btn" @tap="startAdd">新增股东</button>

      <view v-if="actionMode === 'add' || actionMode === 'edit'" class="form-block">
        <view class="form-title">{{ actionMode === 'edit' ? '编辑股东' : '新增股东' }}</view>
        <view class="form-row">
          <view class="label">姓名</view>
          <input class="input" v-model="form.name" placeholder="股东姓名" />
        </view>
        <view class="form-row">
          <view class="label">持股比例 (%)</view>
          <input class="input" type="digit" v-model="form.share_ratio" placeholder="如 50" />
        </view>
        <view class="form-row">
          <view class="label">角色</view>
          <input class="input" v-model="form.role" placeholder="如 投资人" />
        </view>
        <view class="form-row">
          <view class="label">备注</view>
          <input class="input" v-model="form.note" placeholder="可选" />
        </view>
        <view class="form-row row-between">
          <view class="label">状态：{{ form.is_active ? '启用' : '停用' }}</view>
          <switch
            :checked="form.is_active"
            @change="e => form.is_active = e.detail.value"
            color="#0f6a7b"
            style="transform:scale(0.8)"
          />
        </view>
        <view class="edit-actions">
          <button size="mini" @tap="cancelAction">取消</button>
          <button size="mini" type="primary" :loading="saving" @tap="saveShareholder">保存</button>
        </view>
      </view>
    </view>

    <view class="card" v-if="actionMode === 'capital' || actionMode === 'distribution'">
      <view class="title">{{ actionMode === 'capital' ? '记录入资' : '记录分红' }}</view>
      <view class="summary">股东：{{ targetName }}</view>
      <view class="form-row">
        <view class="label">金额</view>
        <input class="input" type="digit" v-model="form.amount" placeholder="金额(元)" />
      </view>
      <view class="form-row">
        <view class="label">日期</view>
        <picker mode="date" :value="form.biz_date" @change="e => form.biz_date = e.detail.value">
          <view class="input">{{ form.biz_date || '请选择日期' }}</view>
        </picker>
      </view>
      <view class="form-row">
        <view class="label">备注</view>
        <input class="input" v-model="form.memo" placeholder="可选" />
      </view>
      <view class="edit-actions">
        <button size="mini" @tap="cancelAction">取消</button>
        <button size="mini" type="primary" :loading="saving" @tap="saveLedger">保存</button>
      </view>
    </view>

    <view class="card">
      <view class="title">股东列表</view>
      <view v-if="summary.items && summary.items.length">
        <view class="record" v-for="item in summary.items" :key="item.shareholder_id">
          <view class="row">
            <view class="item">
              {{ item.name }}
              <text class="tag" v-if="item.role">{{ item.role }}</text>
              <text class="tag tag-off" v-if="!item.is_active">停用</text>
            </view>
            <view class="amount">{{ formatRatio(item.share_ratio) }}%</view>
          </view>
          <view class="meta">
            实际比例 {{ formatRatio(item.effective_ratio * 100) }}% ｜
            已入资 ¥{{ formatNum(item.contributed) }} ｜
            已分红 ¥{{ formatNum(item.distributed) }}
          </view>
          <view class="meta">
            余额 ¥{{ formatNum(item.balance) }} ｜
            需补资 ¥{{ formatNum(item.need_topup) }} ｜
            可分红 ¥{{ formatNum(item.can_distribute) }}
          </view>
          <view class="meta" v-if="item.note">备注：{{ item.note }}</view>
          <view class="actions">
            <button size="mini" @tap="startEdit(item)">编辑</button>
            <button size="mini" @tap="startCapital(item)">入资</button>
            <button size="mini" @tap="startDistribution(item)">分红</button>
          </view>
        </view>
      </view>
      <view class="empty" v-else>暂无股东数据</view>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'
import { isOwner, getRole } from '../../common/auth.js'

export default {
  data() {
    return {
      summary: {
        items: [],
        net_profit: 0,
        gross_profit: 0,
        distributable_total: 0
      },
      actionMode: '',
      targetId: '',
      saving: false,
      form: {
        name: '',
        share_ratio: '',
        role: '',
        note: '',
        is_active: true,
        amount: '',
        biz_date: '',
        memo: ''
      }
    }
  },
  computed: {
    targetName() {
      const item = (this.summary.items || []).find((val) => val.shareholder_id === this.targetId)
      return item ? item.name : ''
    }
  },
  onShow() {
    if (!isOwner(getRole())) {
      uni.showToast({ title: '无权访问', icon: 'none' })
      setTimeout(() => uni.navigateBack(), 800)
      return
    }
    this.resetForm()
    this.loadData()
  },
  methods: {
    formatNum(val) {
      return Number(val || 0).toFixed(2)
    },
    formatRatio(val) {
      const num = Number(val || 0)
      return Number.isFinite(num) ? num.toFixed(2) : '0.00'
    },
    today() {
      const d = new Date()
      const pad = (n) => (n < 10 ? `0${n}` : `${n}`)
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    },
    resetForm() {
      this.form = {
        name: '',
        share_ratio: '',
        role: '',
        note: '',
        is_active: true,
        amount: '',
        biz_date: this.today(),
        memo: ''
      }
    },
    async loadData() {
      try {
        const res = await api.getShareholderSummary()
        this.summary = res || { items: [] }
      } catch (e) {
        this.summary = { items: [], net_profit: 0, gross_profit: 0, distributable_total: 0 }
        uni.showToast({ title: '加载失败', icon: 'none' })
      }
    },
    startAdd() {
      this.actionMode = 'add'
      this.targetId = ''
      this.resetForm()
    },
    startEdit(item) {
      this.actionMode = 'edit'
      this.targetId = item.shareholder_id
      this.form = {
        name: item.name || '',
        share_ratio: String(item.share_ratio ?? ''),
        role: item.role || '',
        note: item.note || '',
        is_active: item.is_active !== false,
        amount: '',
        biz_date: this.today(),
        memo: ''
      }
    },
    startCapital(item) {
      this.actionMode = 'capital'
      this.targetId = item.shareholder_id
      this.resetForm()
    },
    startDistribution(item) {
      this.actionMode = 'distribution'
      this.targetId = item.shareholder_id
      this.resetForm()
    },
    cancelAction() {
      this.actionMode = ''
      this.targetId = ''
      this.resetForm()
    },
    async saveShareholder() {
      const name = (this.form.name || '').trim()
      if (!name) {
        uni.showToast({ title: '请输入姓名', icon: 'none' })
        return
      }
      const ratio = Number(this.form.share_ratio)
      if (!Number.isFinite(ratio) || ratio < 0) {
        uni.showToast({ title: '请输入正确比例', icon: 'none' })
        return
      }
      this.saving = true
      try {
        const payload = {
          name,
          share_ratio: ratio,
          role: this.form.role || null,
          note: this.form.note || null,
          is_active: this.form.is_active
        }
        if (this.actionMode === 'edit' && this.targetId) {
          await api.updateShareholder(this.targetId, payload)
        } else {
          await api.createShareholder(payload)
        }
        uni.showToast({ title: '已保存', icon: 'success' })
        this.cancelAction()
        this.loadData()
      } catch (e) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    async saveLedger() {
      if (!this.targetId) {
        uni.showToast({ title: '请选择股东', icon: 'none' })
        return
      }
      const amount = Number(this.form.amount)
      if (!Number.isFinite(amount) || amount <= 0) {
        uni.showToast({ title: '请输入金额', icon: 'none' })
        return
      }
      this.saving = true
      try {
        const payload = {
          shareholder_id: this.targetId,
          amount,
          biz_date: this.form.biz_date || this.today(),
          memo: this.form.memo || null
        }
        if (this.actionMode === 'capital') {
          await api.createShareholderCapital(payload)
        } else {
          await api.createShareholderDistribution(payload)
        }
        uni.showToast({ title: '已保存', icon: 'success' })
        this.cancelAction()
        this.loadData()
      } catch (e) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
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
.form-block {
  margin-top: 12px;
}
.form-title {
  font-weight: 600;
  margin-bottom: 10px;
}
.form-row {
  margin-bottom: 10px;
}
.row-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  margin-bottom: 8px;
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
.item {
  font-weight: 600;
}
.amount {
  color: #0f6a7b;
}
.meta {
  color: #777;
  font-size: 12px;
  margin-top: 4px;
}
.tag {
  margin-left: 6px;
  font-size: 10px;
  color: #666;
  background: #f0f0f0;
  border-radius: 6px;
  padding: 0 4px;
}
.tag-off {
  color: #a00;
  background: #ffe5e5;
}
.actions {
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
