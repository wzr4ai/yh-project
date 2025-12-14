<template>
  <view class="page">
    <view class="heading">
      <view class="title">运营总览</view>
      <view class="subtitle">角色：{{ roleLabel }}</view>
    </view>

    <view class="grid">
      <view class="card highlight">
        <view class="card-title">今日入账</view>
        <view class="card-value">¥{{ metrics.actualSales.toFixed(2) }}</view>
        <view class="card-sub">订单数 {{ metrics.orders }} ｜ 客单价 ¥{{ metrics.avgTicket.toFixed(2) }}</view>
      </view>
      <view class="card" v-if="isOwner">
        <view class="card-title">预期销售额</view>
        <view class="card-value">¥{{ metrics.expectedSales.toFixed(2) }}</view>
        <view class="card-sub">与入账差值 {{ diffLabel }}</view>
      </view>
      <view class="card">
        <view class="card-title">销售偏差</view>
        <view class="card-value">{{ metrics.receiptDiff >= 0 ? '+' : '-' }}¥{{ Math.abs(metrics.receiptDiff).toFixed(2) }}</view>
        <view class="card-sub" :class="{ positive: metrics.receiptDiff >= 0, negative: metrics.receiptDiff < 0 }">
          {{ metrics.receiptDiff >= 0 ? '溢价' : '折扣' }} {{ metrics.receiptDiffRate }}%
        </view>
      </view>
      <view class="card" v-if="isOwner">
        <view class="card-title">库存成本</view>
        <view class="card-value">¥{{ inventoryCost.toFixed(2) }}</view>
        <view class="card-sub">当前库存总成本</view>
      </view>
    </view>

    <view class="grid">
      <view class="card wide" v-if="isOwner">
        <view class="card-title">库存货值</view>
        <view class="inventory-row">
          <view>
            <view class="mini-title">库存成本</view>
            <view class="mini-value">¥{{ inventoryCost.toFixed(2) }}</view>
          </view>
          <view>
            <view class="mini-title">潜在零售价</view>
            <view class="mini-value">¥{{ inventoryRetail.toFixed(2) }}</view>
          </view>
        </view>
        <view class="card-sub">按当前价格体系计算，单仓</view>
      </view>
      <view class="card wide">
        <view class="card-title">快报</view>
        <view class="pill-row">
          <view class="pill">日</view>
          <view class="pill muted">周</view>
          <view class="pill muted">月</view>
          <view class="pill muted">自定义</view>
        </view>
        <view class="bullet">
          <view class="dot"></view>
          <view class="bullet-text">分类表现：鞭炮 {{ categoryPerf.cracker }}，组合 {{ categoryPerf.sparkler }}</view>
        </view>
        <view class="bullet">
          <view class="dot"></view>
          <view class="bullet-text">店员贡献：{{ metrics.orders }} 笔订单，客单价 ¥{{ metrics.avgTicket.toFixed(2) }}</view>
        </view>
      </view>
    </view>

    <view class="section">
      <view class="section-title">快捷入口</view>
      <view class="quick-actions">
        <view class="action" @tap="go('/pages/sales/create')">
          <view class="action-title">新增销售</view>
          <view class="action-desc">录入成交、对比标准价</view>
        </view>
        <view class="action" @tap="go('/pages/inventory/overview')">
          <view class="action-title">库存总览</view>
          <view class="action-desc">库存与潜在售价</view>
        </view>
        <view class="action" @tap="go('/pages/purchase/list')" v-if="isOwner">
          <view class="action-title">采购到货</view>
          <view class="action-desc">采购单状态、到货确认</view>
        </view>
        <view class="action" @tap="go('/pages/categories/manage')" v-if="isOwner">
          <view class="action-title">分类管理</view>
          <view class="action-desc">增删改查分类</view>
        </view>
        <view class="action" @tap="go('/pages/products/list')">
          <view class="action-title">商品目录</view>
          <view class="action-desc">价格体系与库存分布</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      role: getRole(),
      metrics: {
        actualSales: 0,
        expectedSales: 0,
        receiptDiff: 0,
        receiptDiffRate: 0,
        grossProfit: 0,
        grossMargin: 0,
        orders: 0,
        avgTicket: 0
      },
      inventoryCost: 0,
      inventoryRetail: 0,
      categoryPerf: {
        cracker: '—',
        sparkler: '—'
      },
      loading: false
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    roleLabel() {
      return this.role === 'owner' ? '老板' : '店员'
    },
    diffLabel() {
      const diff = this.metrics.receiptDiff || 0
      const sign = diff >= 0 ? '+' : '-'
      return `${sign}¥${Math.abs(diff).toFixed(2)}`
    }
  },
  onShow() {
    this.role = getRole()
    this.fetchMetrics()
  },
  methods: {
    async fetchMetrics() {
      this.loading = true
      try {
        const [realtime, inv, perf] = await Promise.all([
          api.getRealtime(),
          api.getInventoryValue(),
          api.getPerformance()
        ])
        this.metrics = {
          actualSales: realtime.actual_sales || 0,
          expectedSales: realtime.expected_sales || 0,
          receiptDiff: realtime.receipt_diff || 0,
          receiptDiffRate: realtime.receipt_diff_rate || 0,
          grossProfit: realtime.gross_profit || 0,
          grossMargin: realtime.gross_margin || 0,
          orders: realtime.orders || 0,
          avgTicket: realtime.avg_ticket || 0
        }
        this.inventoryCost = inv.cost_total || 0
        this.inventoryRetail = inv.retail_total || 0
      } catch (err) {
        uni.showToast({ title: '加载数据失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    go(url) {
      uni.navigateTo({ url })
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: #f7f8fa;
  box-sizing: border-box;
}

.heading {
  margin-bottom: 12rpx;
}

.title {
  font-size: 36rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.subtitle {
  color: #6b7280;
  font-size: 24rpx;
  margin-top: 6rpx;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320rpx, 1fr));
  gap: 16rpx;
  margin-top: 16rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.05);
}

.card-title {
  font-size: 26rpx;
  color: #374151;
}

.card-value {
  margin-top: 10rpx;
  font-size: 40rpx;
  font-weight: 700;
  color: #0f6a7b;
}

.card-value.positive {
  color: #0ea76a;
}

.card-sub {
  margin-top: 6rpx;
  color: #6b7280;
  font-size: 24rpx;
}

.card-sub.positive {
  color: #0ea76a;
}

.card-sub.negative {
  color: #c03428;
}

.highlight {
  background: linear-gradient(135deg, #0f6a7b, #12b5a8);
  color: #f5f7fa;
}

.highlight .card-title,
.highlight .card-sub {
  color: rgba(245, 247, 250, 0.9);
}

.highlight .card-value {
  color: #ffffff;
}

.wide {
  grid-column: span 2;
}

.inventory-row {
  display: flex;
  justify-content: space-between;
  margin-top: 12rpx;
}

.mini-title {
  color: #6b7280;
  font-size: 22rpx;
}

.mini-value {
  font-size: 32rpx;
  font-weight: 700;
  margin-top: 6rpx;
  color: #0b1f3a;
}

.pill-row {
  display: flex;
  gap: 12rpx;
  margin: 10rpx 0 6rpx;
}

.pill {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: #0f6a7b;
  color: #f5f7fa;
  font-size: 22rpx;
}

.pill.muted {
  background: #e5e7eb;
  color: #0b1f3a;
}

.bullet {
  display: flex;
  align-items: center;
  margin-top: 8rpx;
}

.dot {
  width: 10rpx;
  height: 10rpx;
  border-radius: 50%;
  background: #0f6a7b;
  margin-right: 10rpx;
}

.bullet-text {
  color: #4b5563;
  font-size: 24rpx;
}

.section {
  margin-top: 24rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320rpx, 1fr));
  gap: 14rpx;
}

.action {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 18rpx;
  border: 1rpx solid #e5e7eb;
  box-shadow: 0 8rpx 18rpx rgba(0, 0, 0, 0.04);
}

.action-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0f6a7b;
}

.action-desc {
  margin-top: 6rpx;
  color: #6b7280;
  font-size: 24rpx;
}
</style>
