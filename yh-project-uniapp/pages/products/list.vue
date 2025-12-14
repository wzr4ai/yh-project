<template>
  <view class="page">
    <view class="filter">
      <picker mode="selector" :range="categoryOptions" range-key="label" @change="onCategoryChange">
        <view class="picker-value">
          {{ currentCategoryLabel }}
        </view>
      </picker>
    </view>

    <view class="list">
      <view v-for="item in products" :key="item.id" class="card">
        <view class="header">
          <view>
            <view class="name">{{ item.name }}</view>
            <view class="meta">{{ item.spec || '—' }} ｜ {{ item.category_name || '—' }}</view>
          </view>
          <view class="price">¥{{ item.standard_price.toFixed(2) }}</view>
        </view>
        <view class="tags">
          <view class="tag">{{ item.price_basis }}</view>
        </view>
        <view class="footer">
          <view class="footer-item" v-if="isOwner">成本 ¥{{ item.base_cost_price }}</view>
          <view class="footer-item">库存 {{ item.stock }}</view>
          <view class="footer-item">潜在总价 ¥{{ item.retail_total.toFixed(2) }}</view>
        </view>
      </view>
      <view class="loadmore" v-if="loading">加载中...</view>
      <view class="loadmore" v-else-if="finished">没有更多了</view>
      <view v-if="!products.length && !loading" class="empty">暂无商品</view>
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
      products: [],
      page: 1,
      pageSize: 20,
      total: 0,
      loading: false,
      categoryOptions: [
        { label: '全部', value: '' },
        { label: '鞭炮', value: '鞭炮' },
        { label: '烟花组合', value: '烟花组合' },
        { label: '玩具烟花', value: '玩具烟花' }
      ],
      currentCategory: ''
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    finished() {
      return this.products.length >= this.total && this.total > 0
    },
    currentCategoryLabel() {
      const found = this.categoryOptions.find(c => c.value === this.currentCategory)
      return found ? found.label : '全部'
    }
  },
  onShow() {
    this.role = getRole()
    this.resetAndLoad()
  },
  onReachBottom() {
    if (!this.finished && !this.loading) {
      this.loadMore()
    }
  },
  methods: {
    resetAndLoad() {
      this.page = 1
      this.products = []
      this.total = 0
      this.loadMore()
    },
    async loadMore() {
      this.loading = true
      try {
        const data = await api.getProducts({
          offset: (this.page - 1) * this.pageSize,
          limit: this.pageSize,
          category: this.currentCategory
        })
        const items = (data && data.items) || []
        this.total = data?.total || 0
        this.products = this.products.concat(items)
        this.page += 1
      } catch (err) {
        uni.showToast({ title: '加载商品失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    onCategoryChange(e) {
      const idx = Number(e.detail.value)
      this.currentCategory = this.categoryOptions[idx]?.value || ''
      this.resetAndLoad()
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

.filter {
  margin-bottom: 16rpx;
}

.picker-value {
  padding: 16rpx;
  background: #fff;
  border-radius: 12rpx;
  border: 1rpx solid #e5e7eb;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 18rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-size: 30rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.meta {
  color: #6b7280;
  margin-top: 6rpx;
  font-size: 24rpx;
}

.price {
  font-size: 32rpx;
  font-weight: 700;
  color: #0f6a7b;
}

.tags {
  display: flex;
  gap: 8rpx;
  margin-top: 10rpx;
}

.tag {
  padding: 6rpx 12rpx;
  background: #f1f5f9;
  color: #0b1f3a;
  border-radius: 10rpx;
  font-size: 22rpx;
}

.footer {
  margin-top: 12rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  color: #4b5563;
  font-size: 24rpx;
}

.footer-item {
  background: #f9fafb;
  padding: 10rpx 12rpx;
  border-radius: 10rpx;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40rpx 0;
}

.loadmore {
  text-align: center;
  color: #6b7280;
  padding: 16rpx 0;
}
</style>
