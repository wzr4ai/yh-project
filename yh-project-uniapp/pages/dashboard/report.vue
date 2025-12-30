<template>
  <view class="page">
    <view class="card header">
      <view class="title">销售与库存分析报告（临时）</view>
      <view class="sub">用于后续调用 LLM 进行深度分析</view>
      <view class="meta">生成时间：{{ generatedLabel }}</view>
      <view class="actions">
        <button size="mini" type="primary" :loading="loading" @tap="fetchReport">生成/刷新</button>
        <button size="mini" @tap="copyJson" :disabled="!reportJson">复制 JSON</button>
      </view>
    </view>

    <view class="card">
      <view class="card-title">LLM 分析建议</view>
      <view v-if="analysisError" class="error">分析失败：{{ analysisError }}</view>
      <scroll-view scroll-y class="report-box analysis-box">
        <text selectable class="report-text">{{ analysisText || '暂无分析内容' }}</text>
      </scroll-view>
      <view v-if="analysisMetaLabel" class="meta">模型：{{ analysisMetaLabel }}</view>
    </view>

    <view class="card">
      <view class="card-title">报告输出</view>
      <scroll-view scroll-y class="report-box">
        <text selectable class="report-text">{{ reportJson || '暂无数据' }}</text>
      </scroll-view>
    </view>

    <view v-if="loading" class="loading">生成中...</view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'
import { getRole, isOwner } from '../../common/auth.js'

export default {
  data() {
    return {
      role: getRole(),
      loading: false,
      report: null,
      reportJson: '',
      generatedAt: '',
      analysisText: '',
      analysisError: '',
      analysisMeta: {
        model: '',
        protocol: '',
        finishReason: ''
      }
    }
  },
  computed: {
    generatedLabel() {
      if (!this.generatedAt) return '—'
      return String(this.generatedAt)
    },
    analysisMetaLabel() {
      const parts = []
      if (this.analysisMeta.model) parts.push(this.analysisMeta.model)
      if (this.analysisMeta.protocol) parts.push(this.analysisMeta.protocol)
      if (this.analysisMeta.finishReason) parts.push(this.analysisMeta.finishReason)
      return parts.join(' / ')
    }
  },
  onShow() {
    this.role = getRole()
    if (!isOwner(this.role)) {
      uni.showToast({ title: '仅老板可查看', icon: 'none' })
      uni.navigateBack()
      return
    }
    this.fetchReport()
  },
  methods: {
    async fetchReport() {
      if (this.loading) return
      this.loading = true
      try {
        const data = await api.getDashboardReportAnalysis()
        this.report = data?.report || null
        this.reportJson = this.report ? JSON.stringify(this.report, null, 2) : ''
        this.generatedAt = data?.generated_at || ''
        this.analysisText = data?.analysis || ''
        this.analysisError = data?.analysis_error || ''
        this.analysisMeta = {
          model: data?.model || '',
          protocol: data?.protocol || '',
          finishReason: data?.finish_reason || ''
        }
      } catch (err) {
        this.report = null
        this.reportJson = ''
        this.generatedAt = ''
        this.analysisText = ''
        this.analysisError = ''
        this.analysisMeta = { model: '', protocol: '', finishReason: '' }
        uni.showToast({ title: '生成失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    copyJson() {
      if (!this.reportJson) {
        uni.showToast({ title: '暂无内容', icon: 'none' })
        return
      }
      uni.setClipboardData({ data: this.reportJson })
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
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
  margin-bottom: 16rpx;
}

.header .title {
  font-size: 32rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.header .sub {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #6b7280;
}

.meta {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #9ca3af;
}

.actions {
  margin-top: 12rpx;
  display: flex;
  gap: 12rpx;
}

.card-title {
  font-size: 26rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.report-box {
  max-height: 60vh;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 16rpx;
  background: #f9fafb;
}

.analysis-box {
  max-height: 40vh;
}

.report-text {
  font-size: 22rpx;
  color: #374151;
  line-height: 1.6;
  white-space: pre-wrap;
}

.error {
  color: #c03428;
  font-size: 22rpx;
  margin: 8rpx 0;
}

.loading {
  text-align: center;
  color: #6b7280;
  font-size: 24rpx;
  margin-top: 10rpx;
}
</style>
