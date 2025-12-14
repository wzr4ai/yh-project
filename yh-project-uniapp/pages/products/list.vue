<template>
  <view class="page">
    <view class="filter">
      <view class="filter-title">分类筛选（多选）</view>
      <view class="chips">
        <view
          v-for="cat in categories"
          :key="cat.id || 'all'"
          :class="['chip', currentCategoryIds.includes(cat.id) ? 'active' : '']"
          @tap="toggleCategory(cat)"
        >
          {{ cat.name }}
        </view>
      </view>
      <view class="filter-hint">再次点击可取消；不选等于全部</view>
    </view>

    <view class="list">
      <view v-for="item in products" :key="item.id" class="card" @tap="openDetail(item.id)">
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

    <view class="pager">
      <button size="mini" :disabled="page <= 1 || loading" @tap="goPage(page - 1)">上一页</button>
      <view class="page-info">第 {{ page }} / {{ totalPages }} 页</view>
      <button size="mini" :disabled="page >= totalPages || loading" @tap="goPage(page + 1)">下一页</button>
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
      categories: [{ id: '', name: '全部' }],
      currentCategoryIds: []
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    finished() {
      return this.page >= this.totalPages && this.total > 0
    },
    currentCategoryLabel() {
      if (!this.currentCategoryIds.length) return '全部'
      const names = this.categories.filter(c => this.currentCategoryIds.includes(c.id)).map(c => c.name)
      return names.length ? names.join('、') : '全部'
    },
    totalPages() {
      if (!this.total) return 1
      return Math.max(1, Math.ceil(this.total / this.pageSize))
    }
  },
  onShow() {
    this.role = getRole()
    this.fetchCategories().then(() => {
      this.resetAndLoad()
    })
  },
  methods: {
    resetAndLoad() {
      this.page = 1
      this.products = []
      this.total = 0
      this.loadPage()
    },
    async loadPage() {
      this.loading = true
      try {
        const data = await api.getProducts({
          offset: (this.page - 1) * this.pageSize,
          limit: this.pageSize,
          categoryIds: this.currentCategoryIds
        })
        const items = (data && data.items) || []
        this.total = data?.total || 0
        this.products = items
      } catch (err) {
        uni.showToast({ title: '加载商品失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    toggleCategory(cat) {
      if (!cat || !cat.id) {
        this.currentCategoryIds = []
      } else {
        const exists = this.currentCategoryIds.includes(cat.id)
        this.currentCategoryIds = exists
          ? this.currentCategoryIds.filter(x => x !== cat.id)
          : this.currentCategoryIds.concat(cat.id)
      }
      this.resetAndLoad()
    },
    async fetchCategories() {
      try {
        const data = await api.getCategories()
        this.categories = [{ id: '', name: '全部' }].concat(data || [])
      } catch (err) {
        this.categories = [{ id: '', name: '全部' }]
      }
    },
    goPage(target) {
      if (target < 1 || target > this.totalPages || target === this.page) return
      this.page = target
      this.loadPage()
    },
    openDetail(id) {
      uni.navigateTo({
        url: `/pages/products/detail?id=${id}`
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
  padding-bottom: 120rpx; /* 给底部分页栏留空间 */
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

.pager {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: #ffffff;
  border-top: 1rpx solid #e5e7eb;
  padding: 12rpx 20rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 -6rpx 12rpx rgba(0, 0, 0, 0.05);
}

.page-info {
  color: #0b1f3a;
  font-size: 26rpx;
}
</style>
