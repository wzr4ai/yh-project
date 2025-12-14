<template>
  <view class="page">
    <view class="filter-bar" @tap="toggleFilter">
      <view class="filter-label">分类</view>
      <view class="filter-value">{{ currentCategoryLabel }}</view>
      <view :class="['arrow', showFilter ? 'up' : 'down']"></view>
    </view>
    <view class="filter-panel" v-if="showFilter">
      <view class="panel-title">选择分类（多选）</view>
      <scroll-view scroll-y style="max-height: 400rpx;">
        <view v-for="cat in categories" :key="cat.id || 'all'" class="panel-row" @tap="toggleTemp(cat)">
          <view class="checkbox" :class="{ checked: tempCategoryIds.includes(cat.id) }"></view>
          <view class="panel-name">{{ cat.name }}</view>
        </view>
      </scroll-view>
      <view class="panel-actions">
        <button size="mini" @tap.stop="cancelFilter">取消</button>
        <button size="mini" type="primary" @tap.stop="applyFilter">应用</button>
      </view>
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
      categories: [
        { id: '', name: '全部' },
        { id: '__uncategorized__', name: '未分类' }
      ],
      currentCategoryIds: [],
      tempCategoryIds: [],
      showFilter: false
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
    toggleFilter() {
      this.tempCategoryIds = [...this.currentCategoryIds]
      this.showFilter = !this.showFilter
    },
    toggleTemp(cat) {
      if (!cat) return
      if (!cat.id) {
        this.tempCategoryIds = []
      } else if (cat.id === '__uncategorized__') {
        this.tempCategoryIds = ['__uncategorized__']
      } else {
        const exists = this.tempCategoryIds.includes(cat.id)
        this.tempCategoryIds = exists
          ? this.tempCategoryIds.filter(x => x !== cat.id)
          : this.tempCategoryIds.concat(cat.id)
        this.tempCategoryIds = this.tempCategoryIds.filter(id => id !== '__uncategorized__')
      }
    },
    cancelFilter() {
      this.showFilter = false
    },
    applyFilter() {
      this.currentCategoryIds = [...this.tempCategoryIds]
      this.showFilter = false
      this.resetAndLoad()
    },
    async fetchCategories() {
      try {
        const data = await api.getCategories()
        this.categories = [
          { id: '', name: '全部' },
          { id: '__uncategorized__', name: '未分类' }
        ].concat(data || [])
      } catch (err) {
        this.categories = [
          { id: '', name: '全部' },
          { id: '__uncategorized__', name: '未分类' }
        ]
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

.filter-bar {
  display: flex;
  align-items: center;
  padding: 14rpx 16rpx;
  background: #fff;
  border-radius: 12rpx;
  border: 1rpx solid #e5e7eb;
  box-shadow: 0 6rpx 12rpx rgba(0, 0, 0, 0.03);
}

.filter-label {
  color: #6b7280;
  font-size: 24rpx;
}

.filter-value {
  flex: 1;
  text-align: right;
  color: #0b1f3a;
  font-size: 26rpx;
  padding: 0 10rpx;
}

.arrow {
  width: 0;
  height: 0;
  border-left: 10rpx solid transparent;
  border-right: 10rpx solid transparent;
}

.arrow.down {
  border-top: 12rpx solid #6b7280;
}

.arrow.up {
  border-bottom: 12rpx solid #6b7280;
}

.filter-panel {
  margin-top: 10rpx;
  background: #fff;
  border-radius: 12rpx;
  border: 1rpx solid #e5e7eb;
  padding: 14rpx;
  box-shadow: 0 10rpx 20rpx rgba(0, 0, 0, 0.05);
}

.panel-title {
  font-size: 26rpx;
  color: #0b1f3a;
  margin-bottom: 10rpx;
}

.panel-row {
  display: flex;
  align-items: center;
  padding: 10rpx 0;
}

.checkbox {
  width: 28rpx;
  height: 28rpx;
  border-radius: 6rpx;
  border: 2rpx solid #cbd5e1;
  margin-right: 12rpx;
}

.checkbox.checked {
  background: #0f6a7b;
  border-color: #0f6a7b;
}

.panel-name {
  color: #0b1f3a;
  font-size: 26rpx;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12rpx;
  margin-top: 10rpx;
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
