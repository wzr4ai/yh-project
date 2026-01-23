<template>
  <view class="page">
    <view class="header card">
      <view class="title">数据分析</view>
      <view class="sub">当前范围：{{ scopeLabel }}</view>
      <view class="toggle-row">
        <view :class="['pill', scope === 'day' ? '' : 'muted']" @tap="setScope('day')">当天</view>
        <view :class="['pill', scope === 'all' ? '' : 'muted']" @tap="setScope('all')">全部</view>
      </view>
    </view>

    <view class="tab-row">
      <view :class="['tab', activeTab === 'sales' ? 'active' : '']" @tap="setTab('sales')">销售分析</view>
      <view :class="['tab', activeTab === 'inventory' ? 'active' : '']" @tap="setTab('inventory')">库存健康</view>
      <view :class="['tab', activeTab === 'pricing' ? 'active' : '']" @tap="setTab('pricing')">定价策略</view>
      <view :class="['tab', activeTab === 'ai' ? 'active' : '']" @tap="setTab('ai')">AI 洞察</view>
    </view>

    <view v-if="activeTab === 'sales'" class="grid">
      <view class="card">
        <view class="card-title">销售概览</view>
        <view class="card-value">¥{{ summary.actualSales.toFixed(2) }}</view>
        <view class="card-sub">
          毛利率 {{ summary.grossMarginLabel }} ｜ 净利率 {{ summary.netMarginLabel }}
        </view>
      </view>
      <view class="card">
        <view class="card-title">销售集中度</view>
        <view class="card-value">{{ summary.topShareLabel }}</view>
        <view class="card-sub">前五商品贡献销售占比</view>
      </view>
    </view>

    <view class="card" v-if="activeTab === 'sales'">
      <view class="card-title">销售重心（前五）</view>
      <view v-for="item in rankings.top_sales" :key="`sales-${item.product_id}`" class="row">
        <view class="row-name">{{ item.name }}</view>
        <view class="row-metric">¥{{ Number(item.sales_amount || 0).toFixed(2) }}</view>
        <view class="row-sub">利润率 {{ Number(item.profit_margin || 0).toFixed(2) }}% ｜ 库存 {{ item.stock }}</view>
      </view>
      <view v-if="!loading && !rankings.top_sales.length" class="empty">暂无销售数据</view>
    </view>

    <view class="card" v-if="activeTab === 'sales'">
      <view class="card-title">补货建议</view>
      <view v-for="item in restockList" :key="`restock-${item.product_id}`" class="row">
        <view class="row-name">{{ item.name }}</view>
        <view class="row-metric">库存 {{ item.stock }}</view>
        <view class="row-sub">销售额 ¥{{ Number(item.sales_amount || 0).toFixed(2) }}</view>
      </view>
      <view v-if="!loading && !restockList.length" class="empty">暂无需要补货的热销品</view>
    </view>

    <view class="card" v-if="activeTab === 'sales'">
      <view class="card-title">促销/定价建议</view>
      <view v-for="item in promoList" :key="`promo-${item.product_id}`" class="row">
        <view class="row-name">{{ item.name }}</view>
        <view class="row-metric">利润率 {{ Number(item.profit_margin || 0).toFixed(2) }}%</view>
        <view class="row-sub">销售额 ¥{{ Number(item.sales_amount || 0).toFixed(2) }}</view>
      </view>
      <view v-if="!loading && !promoList.length" class="empty">当前未发现明显促销需求</view>
    </view>

    <view class="card" v-if="activeTab === 'sales'">
      <view class="card-title">高毛利潜力</view>
      <view v-for="item in rankings.top_margin" :key="`margin-${item.product_id}`" class="row">
        <view class="row-name">{{ item.name }}</view>
        <view class="row-metric">利润率 {{ Number(item.profit_margin || 0).toFixed(2) }}%</view>
        <view class="row-sub">库存 {{ item.stock }}</view>
      </view>
      <view v-if="!loading && !rankings.top_margin.length" class="empty">暂无数据</view>
    </view>

    <view v-if="activeTab === 'inventory'" class="card">
      <view class="card-title">库存健康度</view>
      <view class="health-grid">
        <view>
          <view class="mini-title">畅销品</view>
          <view class="mini-value">{{ inventoryHealth.fast_moving?.count || 0 }}</view>
        </view>
        <view>
          <view class="mini-title">正常品</view>
          <view class="mini-value">{{ inventoryHealth.normal?.count || 0 }}</view>
        </view>
        <view>
          <view class="mini-title">慢销品</view>
          <view class="mini-value">{{ inventoryHealth.slow_moving?.count || 0 }}</view>
        </view>
        <view>
          <view class="mini-title">滞销品</view>
          <view class="mini-value">{{ inventoryHealth.dead_stock?.count || 0 }}</view>
        </view>
      </view>
      <view class="card-sub">平均周转天数 {{ inventoryHealth.avg_turnover_days || '—' }}</view>
    </view>

    <view v-if="activeTab === 'inventory'" class="card">
      <view class="card-title">售罄率（Top 10）</view>
      <view v-for="item in (sellThrough.by_product || []).slice(0, 10)" :key="`sell-${item.product_id}`" class="row">
        <view class="row-name">{{ item.name }}</view>
        <view class="row-metric">售罄率 {{ Number(item.sell_through_rate || 0).toFixed(1) }}%</view>
        <view class="row-sub">已售 {{ item.sold_units }} ｜ 库存 {{ item.stock_units }}</view>
      </view>
      <view v-if="!loading && !(sellThrough.by_product || []).length" class="empty">暂无售罄率数据</view>
    </view>

    <view v-if="activeTab === 'pricing'" class="card">
      <view class="card-title">定价概览</view>
      <view class="card-value">{{ Number(pricingAnalysis.avg_discount_rate || 0).toFixed(1) }}%</view>
      <view class="card-sub">平均折扣率（负数为折扣）</view>
      <view class="card-sub">潜在利润回收 ¥{{ Number(pricingAnalysis.potential_profit_recovery || 0).toFixed(2) }}</view>
    </view>

    <view v-if="activeTab === 'pricing'" class="card">
      <view class="card-title">高折扣商品</view>
      <view v-for="item in (pricingAnalysis.high_discount_products || []).slice(0, 10)" :key="`discount-${item.product_id}`" class="row">
        <view class="row-name">{{ item.name }}</view>
        <view class="row-metric">折扣率 {{ Number(item.discount_rate || 0).toFixed(1) }}%</view>
        <view class="row-sub">销售额 ¥{{ Number(item.sales_amount || 0).toFixed(2) }}</view>
      </view>
      <view v-if="!(pricingAnalysis.high_discount_products || []).length" class="empty">暂无高折扣商品</view>
    </view>

    <view v-if="activeTab === 'pricing'" class="card">
      <view class="card-title">溢价商品</view>
      <view v-for="item in (pricingAnalysis.premium_products || []).slice(0, 10)" :key="`premium-${item.product_id}`" class="row">
        <view class="row-name">{{ item.name }}</view>
        <view class="row-metric">溢价率 {{ Number(item.discount_rate || 0).toFixed(1) }}%</view>
        <view class="row-sub">销售额 ¥{{ Number(item.sales_amount || 0).toFixed(2) }}</view>
      </view>
      <view v-if="!(pricingAnalysis.premium_products || []).length" class="empty">暂无溢价商品</view>
    </view>

    <view v-if="activeTab === 'ai'" class="card">
      <view class="card-title">AI 经营分析</view>
      <view class="ai-panel">
        <view v-if="aiLoading" class="empty">加载中...</view>
        <view v-else class="ai-text">{{ aiAnalysis || '暂无分析结果' }}</view>
      </view>
      <view class="ai-actions" v-if="isOwner">
        <view class="pill" @tap="fetchAiAnalysis">重新分析</view>
      </view>
    </view>

    <view v-if="loading" class="loading">加载中...</view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'
import { getRole, isOwner } from '../../common/auth.js'

const RESTOCK_THRESHOLD = 10
const LOW_MARGIN_THRESHOLD = 20

export default {
  data() {
    return {
      role: getRole(),
      scope: 'day',
      loading: false,
      activeTab: 'sales',
      report: null,
      seasonality: {},
      inventoryHealth: {},
      sellThrough: {},
      pricingAnalysis: {},
      aiAnalysis: '',
      aiLoading: false,
      rankings: {
        top_sales: [],
        top_margin: []
      },
      summary: {
        actualSales: 0,
        grossMarginLabel: '—',
        netMarginLabel: '—',
        topShareLabel: '—'
      }
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    scopeLabel() {
      return this.scope === 'all' ? '全部' : '当天'
    },
    restockList() {
      return (this.rankings.top_sales || []).filter(item => Number(item.stock || 0) <= RESTOCK_THRESHOLD)
    },
    promoList() {
      return (this.rankings.top_sales || []).filter(item => Number(item.profit_margin || 0) <= LOW_MARGIN_THRESHOLD)
    }
  },
  onLoad(options) {
    this.role = getRole()
    if (options && options.scope) {
      const scoped = String(options.scope)
      if (scoped === 'all' || scoped === 'day') this.scope = scoped
    }
    this.fetchData()
    if (this.isOwner) {
      this.fetchReport()
      this.fetchAiAnalysis()
    }
  },
  methods: {
    setTab(tab) {
      if (!tab || tab === this.activeTab) return
      this.activeTab = tab
    },
    setScope(scope) {
      if (!scope || scope === this.scope) return
      this.scope = scope
      this.fetchData()
    },
    async fetchData() {
      this.loading = true
      try {
        const [rankings, perf, miscList] = await Promise.all([
          api.getSalesRankings(this.scope),
          api.getPerformance(),
          api.listMiscCosts({ limit: 100 })
        ])
        this.rankings = {
          top_sales: rankings?.top_sales || [],
          top_margin: rankings?.top_margin || []
        }
        const actual = Number(perf?.actual_sales) || 0
        const cost = Number(perf?.cost_total) || 0
        const miscCosts = miscList || []
        const miscTotal = miscCosts.reduce((acc, cur) => {
          const qty = Number(cur.quantity) || 1
          const amt = Number(cur.amount) || 0
          return acc + qty * amt
        }, 0)
        const netProfit = actual - cost - miscTotal
        const grossMargin = actual > 0 ? ((actual - cost) / actual) * 100 : null
        const netMargin = actual > 0 ? (netProfit / actual) * 100 : null
        const topSalesTotal = (this.rankings.top_sales || []).reduce((acc, cur) => acc + Number(cur.sales_amount || 0), 0)
        const share = actual > 0 ? (topSalesTotal / actual) * 100 : null
        this.summary = {
          actualSales: actual,
          grossMarginLabel: grossMargin === null ? '—' : `${grossMargin.toFixed(1)}%`,
          netMarginLabel: netMargin === null ? '—' : `${netMargin.toFixed(1)}%`,
          topShareLabel: share === null ? '—' : `${share.toFixed(1)}%`
        }
      } catch (err) {
        this.rankings = { top_sales: [], top_margin: [] }
        this.summary = {
          actualSales: 0,
          grossMarginLabel: '—',
          netMarginLabel: '—',
          topShareLabel: '—'
        }
        uni.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    async fetchReport() {
      try {
        const report = await api.getDashboardReport()
        const content = report?.report || {}
        this.report = content
        this.seasonality = content?.seasonality || {}
        this.inventoryHealth = content?.inventory_health || {}
        this.sellThrough = content?.sell_through || {}
        this.pricingAnalysis = content?.pricing_analysis || {}
      } catch (err) {
        this.report = null
        this.seasonality = {}
        this.inventoryHealth = {}
        this.sellThrough = {}
        this.pricingAnalysis = {}
      }
    },
    async fetchAiAnalysis() {
      if (this.aiLoading) return
      this.aiLoading = true
      try {
        const res = await api.getDashboardInsightLatest()
        this.aiAnalysis = res?.content || ''
      } catch (err) {
        this.aiAnalysis = ''
      } finally {
        this.aiLoading = false
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
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.05);
  margin-bottom: 16rpx;
}

.header .title {
  font-size: 34rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.header .sub {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #6b7280;
}

.toggle-row {
  display: flex;
  gap: 12rpx;
  margin-top: 12rpx;
}

.tab-row {
  display: flex;
  gap: 12rpx;
  flex-wrap: wrap;
  margin: 12rpx 0 16rpx;
}

.tab {
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #e5e7eb;
  color: #0b1f3a;
  font-size: 22rpx;
}

.tab.active {
  background: #0f6a7b;
  color: #f5f7fa;
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

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320rpx, 1fr));
  gap: 16rpx;
}

.card-title {
  font-size: 26rpx;
  color: #374151;
}

.card-value {
  margin-top: 8rpx;
  font-size: 36rpx;
  font-weight: 700;
  color: #0f6a7b;
}

.card-sub {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #6b7280;
}

.row {
  padding: 10rpx 0;
  border-bottom: 1rpx dashed #e5e7eb;
}

.row:last-child {
  border-bottom: none;
}

.row-name {
  font-size: 26rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.row-metric {
  margin-top: 4rpx;
  font-size: 24rpx;
  color: #0f6a7b;
  font-weight: 600;
}

.row-sub {
  margin-top: 4rpx;
  font-size: 22rpx;
  color: #6b7280;
}

.health-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
  margin-top: 10rpx;
}

.ai-panel {
  margin-top: 10rpx;
}

.ai-text {
  font-size: 24rpx;
  color: #374151;
  line-height: 1.7;
}

.ai-actions {
  margin-top: 12rpx;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 12rpx 0;
}

.loading {
  text-align: center;
  color: #9ca3af;
  padding: 20rpx 0;
}
</style>
