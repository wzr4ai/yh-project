<template>
  <view class="page">
    <view class="header">
      <view class="title">AI 助手</view>
      <view class="subtitle">仅老板可用 · 写入需确认</view>
    </view>

    <view v-if="!isOwner" class="empty">仅老板可用，请使用老板账号登录。</view>

    <view v-else class="chat-wrap">
      <scroll-view class="chat" scroll-y :scroll-into-view="scrollTarget">
        <view
          v-for="(msg, idx) in messages"
          :key="msg.id"
          :id="`msg-${idx}`"
          class="message"
          :class="msg.role"
        >
          <view class="bubble">
            <text>{{ msg.content }}</text>
          </view>

          <view v-if="msg.actions && msg.actions.length" class="action-list">
            <view v-for="(action, aidx) in msg.actions" :key="`${msg.id}-${aidx}`" class="action-card">
              <view class="action-title">{{ action.title }}</view>

              <view v-if="action.preview && action.preview.items" class="action-preview">
                <view class="preview-row" v-for="item in action.preview.items" :key="item.product_id">
                  <view class="preview-name">{{ item.name }}</view>
                  <view class="preview-meta">
                    现价 ¥{{ formatMoney(item.standard_price) }} → 新价 ¥{{ formatMoney(item.new_price) }}
                  </view>
                </view>
              </view>

              <view v-if="action.result && action.result.total !== undefined" class="action-result">
                <view class="result-meta">共 {{ action.result.total }} 个商品</view>
                <view v-for="item in action.result.items.slice(0, 30)" :key="item.id" class="result-row">
                  <view class="result-name">{{ item.name }}</view>
                  <view class="result-meta">
                    单件成本 ¥{{ formatMoney(item.base_cost_price) }}
                    ｜ 箱成本 ¥{{ formatMoney(item.box_cost_price) }}
                    ｜ 每箱 {{ item.units_per_box }} 件
                    ｜ 零售价 ¥{{ formatMoney(item.standard_price) }}
                  </view>
                </view>
                <view v-if="action.result.items.length > 30" class="result-meta">仅展示前 30 条</view>
              </view>

              <view v-if="action.result && action.result.bundles" class="action-result">
                <view class="bundle-card" v-for="(bundle, bidx) in action.result.bundles" :key="`bundle-${bidx}`">
                  <view class="bundle-title">{{ bundle.title }}</view>
                  <view class="bundle-items">
                    <view v-for="item in bundle.items" :key="item.product_id" class="bundle-item">
                      {{ item.name }} x{{ item.qty }}
                    </view>
                  </view>
                  <view class="bundle-meta">
                    建议价 ¥{{ formatMoney(bundle.bundle_price) }} ｜ 成本 ¥{{ formatMoney(bundle.cost_total) }}
                    ｜ 毛利 {{ bundle.margin_pct }}%
                  </view>
                  <view class="bundle-reason" v-if="bundle.reason">{{ bundle.reason }}</view>
                </view>
              </view>

              <view class="action-footer" v-if="action.requires_confirmation">
                <button size="mini" type="primary" :loading="action.loading" @tap="confirmAction(msg, action)">
                  确认执行
                </button>
              </view>
            </view>
          </view>
        </view>
      </scroll-view>

      <view class="composer">
        <input
          class="input"
          v-model="input"
          placeholder="例如：查询所有商品及进价 / 把礼花A零售价改成98"
          confirm-type="send"
          @confirm="sendMessage"
        />
        <button size="mini" type="primary" :loading="loading" @tap="sendMessage">发送</button>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'
import { getRole, isOwner } from '../../common/auth.js'

let uid = 0

export default {
  data() {
    return {
      role: getRole(),
      messages: [
        {
          id: `msg-${uid++}`,
          role: 'assistant',
          content: '你好，我可以查询进价、调整零售价、生成智能套餐。'
        }
      ],
      input: '',
      loading: false,
      scrollTarget: ''
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    }
  },
  onShow() {
    this.role = getRole()
    if (!this.isOwner) {
      uni.showToast({ title: '仅老板可用', icon: 'none' })
    }
  },
  methods: {
    formatMoney(value) {
      const num = Number(value)
      if (!Number.isFinite(num)) return '—'
      return num.toFixed(2)
    },
    scrollToBottom() {
      this.$nextTick(() => {
        this.scrollTarget = `msg-${this.messages.length - 1}`
      })
    },
    buildChatPayload() {
      return {
        messages: this.messages.map(msg => ({
          role: msg.role,
          content: msg.content
        }))
      }
    },
    appendAssistant(res) {
      this.messages.push({
        id: `msg-${uid++}`,
        role: 'assistant',
        content: res.reply || '好的。',
        actions: (res.actions || []).map(action => ({
          ...action,
          loading: false
        }))
      })
      this.scrollToBottom()
    },
    async sendMessage() {
      if (this.loading) return
      const text = this.input.trim()
      if (!text) return
      this.messages.push({ id: `msg-${uid++}`, role: 'user', content: text })
      this.input = ''
      this.loading = true
      this.scrollToBottom()
      try {
        const res = await api.aiChat(this.buildChatPayload())
        this.appendAssistant(res)
      } catch (err) {
        const msg = err && err.detail ? err.detail : '请求失败'
        this.appendAssistant({ reply: msg, actions: [] })
      } finally {
        this.loading = false
      }
    },
    confirmAction(message, action) {
      if (!action || action.loading) return
      uni.showModal({
        title: '确认执行',
        content: '该操作会写入数据库，是否继续？',
        success: async (res) => {
          if (!res.confirm) return
          action.loading = true
          try {
            const result = await api.aiAction({
              type: action.type,
              payload: action.payload || {}
            })
            this.messages.push({
              id: `msg-${uid++}`,
              role: 'assistant',
              content: result.reply || '已完成。',
              actions: result.result
                ? [
                    {
                      type: action.type,
                      title: '执行结果',
                      result: result.result
                    }
                  ]
                : []
            })
            this.scrollToBottom()
          } catch (err) {
            const msg = err && err.detail ? err.detail : '执行失败'
            this.messages.push({ id: `msg-${uid++}`, role: 'assistant', content: msg })
            this.scrollToBottom()
          } finally {
            action.loading = false
          }
        }
      })
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
  display: flex;
  flex-direction: column;
}

.header {
  margin-bottom: 12rpx;
}

.title {
  font-size: 32rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.subtitle {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #6b7280;
}

.chat-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat {
  flex: 1;
  padding-bottom: 16rpx;
}

.message {
  margin-bottom: 16rpx;
  display: flex;
  flex-direction: column;
}

.message.user {
  align-items: flex-end;
}

.message.assistant {
  align-items: flex-start;
}

.bubble {
  max-width: 82%;
  padding: 12rpx 14rpx;
  border-radius: 12rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 18rpx rgba(0, 0, 0, 0.06);
  font-size: 24rpx;
  color: #0f172a;
}

.message.user .bubble {
  background: #0f6a7b;
  color: #ffffff;
}

.action-list {
  margin-top: 10rpx;
  width: 100%;
}

.action-card {
  background: #ffffff;
  border-radius: 14rpx;
  padding: 12rpx;
  box-shadow: 0 6rpx 18rpx rgba(0, 0, 0, 0.06);
  margin-bottom: 10rpx;
}

.action-title {
  font-weight: 600;
  font-size: 24rpx;
  color: #0b1f3a;
}

.action-preview,
.action-result {
  margin-top: 8rpx;
}

.preview-row,
.result-row {
  padding: 8rpx 0;
  border-bottom: 1rpx dashed #e5e7eb;
}

.preview-row:last-child,
.result-row:last-child {
  border-bottom: none;
}

.preview-name,
.result-name {
  font-size: 24rpx;
  color: #0b1f3a;
}

.preview-meta,
.result-meta {
  font-size: 20rpx;
  color: #6b7280;
  margin-top: 4rpx;
}

.bundle-card {
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 10rpx;
  margin-top: 8rpx;
}

.bundle-title {
  font-size: 24rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.bundle-items {
  margin-top: 6rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx 16rpx;
  font-size: 22rpx;
}

.bundle-item {
  color: #0f172a;
}

.bundle-meta {
  margin-top: 6rpx;
  font-size: 20rpx;
  color: #6b7280;
}

.bundle-reason {
  margin-top: 4rpx;
  font-size: 20rpx;
  color: #64748b;
}

.action-footer {
  margin-top: 10rpx;
  display: flex;
  justify-content: flex-end;
}

.composer {
  display: flex;
  gap: 10rpx;
  align-items: center;
  padding: 10rpx 0;
}

.input {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 10rpx 12rpx;
  font-size: 24rpx;
  background: #ffffff;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 24rpx 0;
}
</style>
