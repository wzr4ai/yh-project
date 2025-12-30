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
        <view class="card-title">利润率</view>
        <view class="card-value">{{ netMarginLabel }}</view>
        <view class="card-sub">毛利润率 {{ grossMarginLabel }}</view>
      </view>
      <view class="card">
        <view class="card-title">总成本 / 净利润</view>
        <view class="card-value">¥{{ costMetrics.totalCost.toFixed(2) }}</view>
        <view class="card-sub">净利润 ¥{{ costMetrics.netProfit.toFixed(2) }}</view>
      </view>
      <view class="card" v-if="isOwner">
        <view class="card-title">总营业额</view>
        <view class="card-value">¥{{ receiptTotal.toFixed(2) }}</view>
        <view class="card-sub">累计真实入账</view>
      </view>
    </view>

    <view class="grid">
      <view class="card wide" v-if="isOwner" @tap="go('/pages/inventory/detail')">
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
          <view>
            <view class="mini-title">有库存商品数</view>
            <view class="mini-value">{{ inventorySku }}</view>
          </view>
          <view>
            <view class="mini-title">总箱数</view>
            <view class="mini-value">{{ inventoryBoxes }}</view>
          </view>
        </view>
        <view class="card-sub">按当前价格体系计算，单仓</view>
      </view>
      <view class="card wide" @tap="openAnalysis">
        <view class="card-title">快报</view>
        <view class="toggle-row">
          <view :class="['pill', rankingScope === 'day' ? '' : 'muted']" @tap.stop="setRankingScope('day')">当天</view>
          <view :class="['pill', rankingScope === 'all' ? '' : 'muted']" @tap.stop="setRankingScope('all')">全部</view>
        </view>
        <view class="rank-section">
          <view class="rank-title">销售额前五</view>
          <view class="rank-names">{{ salesNameLabel }}</view>
        </view>
        <view class="rank-section">
          <view class="rank-title">利润率前五</view>
          <view class="rank-names">{{ marginNameLabel }}</view>
        </view>
        <view v-if="rankingLoading" class="empty">加载中...</view>
      </view>
    </view>

    <view class="section">
      <view class="section-title">快捷入口</view>
      <view class="quick-actions">
        <view class="action" @tap="go('/pages/inventory/overview')">
          <view class="action-title">库存总览</view>
          <view class="action-desc">库存与潜在售价</view>
        </view>
        <view class="action" @tap="go('/pages/purchase/list')" v-if="isOwner">
          <view class="action-title">采购到货</view>
          <view class="action-desc">采购单状态、到货确认</view>
        </view>
        <view class="action" @tap="go('/pages/purchase/replenishment')" v-if="isOwner">
          <view class="action-title">生成进货/补货单</view>
          <view class="action-desc">按库存阈值导出 CSV</view>
        </view>
        <view class="action" @tap="go('/pages/pricing/overview')" v-if="isOwner">
          <view class="action-title">店员视图（定价总览）</view>
          <view class="action-desc">查看店员可见价格页</view>
        </view>
        <view class="action" @tap="go('/pages/categories/manage')" v-if="isOwner">
          <view class="action-title">分类管理</view>
          <view class="action-desc">增删改查分类</view>
        </view>
        <view class="action" v-if="isOwner" @tap="go('/pages/costs/misc')">
          <view class="action-title">杂项成本</view>
          <view class="action-desc">记录运输、耗材等费用</view>
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
        grossProfit: 0,
        grossMargin: 0,
        orders: 0,
        avgTicket: 0
      },
      costMetrics: {
        totalCost: 0,
        netProfit: 0
      },
      salesCostTotal: 0,
      inventoryCost: 0,
      inventorySku: 0,
      inventoryBoxes: 0,
      receiptTotal: 0,
      inventoryRetail: 0,
      rankingScope: 'day',
      rankingLoading: false,
      rankings: {
        top_sales: [],
        top_margin: []
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
    grossMarginLabel() {
      const total = Number(this.receiptTotal) || 0
      if (total <= 0) return '—'
      const cost = Number(this.salesCostTotal) || 0
      const margin = ((total - cost) / total) * 100
      return `${margin.toFixed(1)}%`
    },
    netMarginLabel() {
      const total = Number(this.receiptTotal) || 0
      if (total <= 0) return '—'
      const net = Number(this.costMetrics.netProfit) || 0
      const margin = (net / total) * 100
      return `${margin.toFixed(1)}%`
    },
    salesNameLabel() {
      if (this.rankingLoading) return '加载中...'
      if (!this.rankings.top_sales.length) return '暂无数据'
      return this.rankings.top_sales.map(item => item.name).join('、')
    },
    marginNameLabel() {
      if (this.rankingLoading) return '加载中...'
      if (!this.rankings.top_margin.length) return '暂无数据'
      return this.rankings.top_margin.map(item => item.name).join('、')
    }
  },
  onShow() {
    this.role = getRole()
    this.fetchMetrics()
    this.fetchRankings()
  },
  methods: {
    async fetchRankings() {
      this.rankingLoading = true
      try {
        const data = await api.getSalesRankings(this.rankingScope)
        this.rankings = {
          top_sales: data?.top_sales || [],
          top_margin: data?.top_margin || []
        }
      } catch (err) {
        this.rankings = { top_sales: [], top_margin: [] }
      } finally {
        this.rankingLoading = false
      }
    },
    setRankingScope(scope) {
      if (!scope || scope === this.rankingScope) return
      this.rankingScope = scope
      this.fetchRankings()
    },
    openAnalysis() {
      uni.navigateTo({ url: `/pages/dashboard/analysis?scope=${encodeURIComponent(this.rankingScope)}` })
    },
    async fetchMetrics() {
      this.loading = true
      try {
        const [realtime, inv, perf, miscList] = await Promise.all([
          api.getRealtime(),
          api.getInventoryValue(),
          api.getPerformance(),
          api.listMiscCosts({ limit: 100 }),
        ])
        this.metrics = {
          actualSales: realtime.actual_sales || 0,
          expectedSales: realtime.expected_sales || 0,
          grossProfit: realtime.gross_profit || 0,
          grossMargin: realtime.gross_margin || 0,
          orders: realtime.orders || 0,
          avgTicket: realtime.avg_ticket || 0
        }
        this.inventoryCost = inv.cost_total || 0
        this.inventoryRetail = inv.retail_total || 0
        this.inventorySku = inv.sku_count || 0
        this.inventoryBoxes = inv.total_boxes || 0
        this.receiptTotal = perf?.actual_sales || 0
        this.salesCostTotal = perf?.cost_total || 0
        const miscCosts = miscList || []
        const miscTotal = miscCosts.reduce((acc, cur) => {
          const qty = Number(cur.quantity) || 1
          const amt = Number(cur.amount) || 0
          return acc + qty * amt
        }, 0)
        const totalCost = (perf?.purchase_cost_total || 0) + miscTotal
        const netProfit = (this.receiptTotal || 0) - totalCost
        this.costMetrics = {
          totalCost,
          netProfit
        }
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

.toggle-row {
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

.rank-section {
  margin-top: 10rpx;
}

.rank-title {
  font-size: 24rpx;
  color: #6b7280;
  margin-bottom: 6rpx;
}

.rank-names {
  font-size: 24rpx;
  color: #0b1f3a;
  line-height: 1.6;
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
