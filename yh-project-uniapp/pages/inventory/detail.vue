<template>
  <view class="page">
    <view class="card">
      <view class="title">库存货值</view>
      <view class="grid">
        <view class="block">
          <view class="label">库存成本</view>
          <view class="value">¥{{ overview.cost_total.toFixed(2) }}</view>
        </view>
        <view class="block">
          <view class="label">潜在零售价</view>
          <view class="value">¥{{ overview.retail_total.toFixed(2) }}</view>
        </view>
        <view class="block">
          <view class="label">有库存商品数</view>
          <view class="value">{{ overview.sku_count }}</view>
        </view>
        <view class="block">
          <view class="label">总箱数</view>
          <view class="value">{{ overview.total_boxes }}</view>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="title">分类分布</view>
      <view v-if="categories.length">
        <view class="row" v-for="cat in categories" :key="cat.id">
          <view class="row-main">
            <view class="cat-name">{{ cat.name }}</view>
            <view class="cat-meta">SKU {{ cat.sku }} ｜ 箱数 {{ cat.boxes }}</view>
          </view>
          <view class="row-values">
            <view class="cost">成本 ¥{{ cat.cost }}</view>
            <view class="retail">潜在 ¥{{ cat.retail }}</view>
          </view>
        </view>
      </view>
      <view v-else class="empty">暂无数据</view>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      overview: {
        cost_total: 0,
        retail_total: 0,
        sku_count: 0,
        total_boxes: 0
      },
      categories: [],
      loading: false
    }
  },
  onShow() {
    this.fetchData()
  },
  methods: {
    async fetchData() {
      this.loading = true
      try {
        const res = await api.getInventoryBreakdown()
        this.overview = {
          cost_total: res?.cost_total || 0,
          retail_total: res?.retail_total || 0,
          sku_count: res?.sku_count || 0,
          total_boxes: res?.total_boxes || 0
        }
        this.categories = res?.categories || []
      } catch (e) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.loading = false
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
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.block {
  background: #f7f8fb;
  border-radius: 8px;
  padding: 10px;
}
.label {
  font-size: 12px;
  color: #666;
}
.value {
  font-size: 18px;
  font-weight: 700;
  margin-top: 4px;
  color: #0f6a7b;
}
.row {
  border-bottom: 1px solid #f0f0f0;
  padding: 10px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.row:last-child {
  border-bottom: none;
}
.cat-name {
  font-weight: 600;
}
.cat-meta {
  font-size: 12px;
  color: #777;
  margin-top: 2px;
}
.row-values {
  text-align: right;
  font-size: 12px;
}
.cost {
  color: #e67e22;
}
.retail {
  color: #0f6a7b;
  margin-top: 2px;
}
.empty {
  text-align: center;
  color: #999;
  padding: 12px 0;
}
</style>
