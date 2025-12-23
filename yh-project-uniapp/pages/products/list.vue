<template>
  <view class="page">
    <view class="toolbar">
      <view class="filter-bar" @tap="toggleFilter">
        <view class="filter-label">分类</view>
        <view class="filter-value">{{ currentCategoryLabel }}</view>
        <view :class="['arrow', showFilter ? 'up' : 'down']"></view>
      </view>
      <view class="search-bar">
        <input
          class="search-input"
          type="text"
          v-model="keyword"
          placeholder="搜索商品"
          confirm-type="search"
          @confirm="doSearch"
        />
        <button size="mini" @tap="doSearch">搜</button>
      </view>
      <view class="action-bar" v-if="isOwner">
        <button type="primary" size="mini" @tap="openCreate">新增</button>
      </view>
    </view>
    <view class="filter-panel" v-if="showFilter">
      <view class="panel-title">自定义类别（多选，OR）</view>
      <scroll-view scroll-y style="max-height: 240rpx;">
        <view v-for="cat in customCategories" :key="cat.id || 'all'" class="panel-row" @tap="toggleTempCustom(cat)">
          <view class="checkbox" :class="{ checked: tempCustomIds.includes(cat.id) }"></view>
          <view class="panel-name">{{ cat.name }}</view>
        </view>
      </scroll-view>
      <view class="panel-title">商家类别（单类别 OR，自身可多选，整体与左侧为 AND）</view>
      <scroll-view scroll-y style="max-height: 240rpx;">
        <view v-for="cat in merchantCategories" :key="cat.id || 'all-m'" class="panel-row" @tap="toggleTempMerchant(cat)">
          <view class="checkbox" :class="{ checked: tempMerchantIds.includes(cat.id) }"></view>
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
            <view
              class="name"
              :class="{
                'is-problem': item.category_name && item.category_name.includes('问题'),
                'is-zero': item.stock === 0
              }"
            >
              {{ item.name }}
            </view>
            <view class="meta">{{ item.spec || '—' }} ｜ {{ item.category_name || '—' }}</view>
          </view>
          <view class="price-area">
            <view class="price">
              <text>¥{{ item.price_min.toFixed(2) }}</text>
              <text v-if="item.price_max > item.price_min"> ~ ¥{{ item.price_max.toFixed(2) }}</text>
            </view>
            <button
              v-if="item.video_url || item.effect_url"
              size="mini"
              type="primary"
              class="effect-btn"
              @tap.stop="openVideo(item.id)"
            >效果</button>
          </view>
        </view>
        <view class="footer">
          <view class="footer-item" v-if="isOwner">成本 ¥{{ item.base_cost_price }}</view>
          <view class="footer-item">库存 {{ item.stock }}</view>
          <view class="footer-item tag">{{ item.price_basis }}</view>
          <view class="footer-item">潜在总价 ¥{{ item.retail_total.toFixed(2) }}</view>
        </view>
      </view>
      <view class="loadmore" v-if="loading">加载中...</view>
      <view class="loadmore" v-else-if="finished">没有更多了</view>
      <view v-if="!products.length && !loading" class="empty">暂无商品</view>
    </view>

    <view class="pager">
      <button size="mini" :disabled="page <= 1 || loading" @tap="goPage(page - 1)">上一页</button>
      <view class="page-info" @tap="openJumpInput">第 {{ page }} / {{ totalPages }} 页</view>
      <view class="jump" v-if="showJumpInput">
        <input class="jump-input" type="number" v-model.number="jumpPageInput" placeholder="页码" />
        <button size="mini" @tap="jumpToPage">跳转</button>
      </view>
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
      customCategories: [{ id: '', name: '全部' }],
      merchantCategories: [
        { id: '', name: '全部' },
        { id: '__uncategorized__', name: '未分类' }
      ],
      selectedCustomIds: [],
      selectedMerchantIds: [],
      tempCustomIds: [],
      tempMerchantIds: [],
      showFilter: false,
      keyword: '',
      showJumpInput: false,
      jumpPageInput: ''
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
      const customNames = this.customCategories.filter(c => this.selectedCustomIds.includes(c.id)).map(c => c.name)
      const merchantNames = this.merchantCategories.filter(c => this.selectedMerchantIds.includes(c.id)).map(c => c.name)
      const parts = []
      if (customNames.length) parts.push(`自定义:${customNames.join('、')}`)
      if (merchantNames.length) parts.push(`商家:${merchantNames.join('、')}`)
      return parts.length ? parts.join(' | ') : '全部'
    },
    totalPages() {
      if (!this.total) return 1
      return Math.max(1, Math.ceil(this.total / this.pageSize))
    },
    cacheKey() {
      const params = []
      params.push(`offset=${(this.page - 1) * this.pageSize}`)
      params.push(`limit=${this.pageSize}`)
      if (this.selectedMerchantIds.length) params.push(`merchant_category_ids=${this.selectedMerchantIds.join(',')}`)
      if (this.selectedCustomIds.length) params.push(`custom_category_ids=${this.selectedCustomIds.join(',')}`)
      if (this.keyword.trim()) params.push(`keyword=${encodeURIComponent(this.keyword.trim())}`)
      return `cache:/api/products?${params.join('&')}`
    }
  },
  onLoad() {
    const saved = uni.getStorageSync('products-page')
    if (saved) {
      const num = Number(saved)
      if (num > 0) this.page = num
    }
  },
  onShow() {
    this.role = getRole()
    this.fetchCategories().then(() => {
      this.loadPage()
    })
  },
  onHide() {
    uni.setStorageSync('products-page', this.page)
  },
  onUnload() {
    uni.setStorageSync('products-page', this.page)
  },
  methods: {
    tryLoadCache() {
      try {
        const cached = uni.getStorageSync(this.cacheKey)
        if (cached && cached.data) {
          this.products = cached.data.items || []
          this.total = cached.data.total || 0
        }
      } catch (e) {
        // ignore cache errors
      }
    },
    resetAndLoad() {
      this.page = 1
      this.products = []
      this.total = 0
      this.loadPage()
    },
    async loadPage() {
      this.loading = true
      this.tryLoadCache()
      try {
        const data = await api.getProducts({
          offset: (this.page - 1) * this.pageSize,
          limit: this.pageSize,
          customCategoryIds: this.selectedCustomIds,
          merchantCategoryIds: this.selectedMerchantIds,
          keyword: this.keyword.trim()
        })
        const items = (data && data.items) || []
        this.total = data?.total || 0
        this.products = items
        // 写入缓存
        try {
          uni.setStorageSync(this.cacheKey, { etag: null, data })
        } catch (e) {
          // ignore cache write errors
        }
      } catch (err) {
        uni.showToast({ title: '加载商品失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    onSearchInput(e) {
      this.keyword = e.detail.value
    },
    doSearch() {
      this.resetAndLoad()
    },
    toggleFilter() {
      this.tempCustomIds = [...this.selectedCustomIds]
      this.tempMerchantIds = [...this.selectedMerchantIds]
      this.showFilter = !this.showFilter
    },
    toggleTempCustom(cat) {
      if (!cat) return
      if (!cat.id) {
        this.tempCustomIds = []
        return
      }
      const exists = this.tempCustomIds.includes(cat.id)
      this.tempCustomIds = exists ? this.tempCustomIds.filter(x => x !== cat.id) : this.tempCustomIds.concat(cat.id)
    },
    toggleTempMerchant(cat) {
      if (!cat) return
      if (!cat.id) {
        this.tempMerchantIds = []
        return
      }
      if (cat.id === '__uncategorized__') {
        this.tempMerchantIds = ['__uncategorized__']
        return
      }
      const exists = this.tempMerchantIds.includes(cat.id)
      this.tempMerchantIds = exists
        ? this.tempMerchantIds.filter(x => x !== cat.id)
        : this.tempMerchantIds.concat(cat.id).filter(id => id !== '__uncategorized__')
    },
    cancelFilter() {
      this.showFilter = false
    },
    applyFilter() {
      this.selectedCustomIds = [...this.tempCustomIds]
      this.selectedMerchantIds = [...this.tempMerchantIds]
      this.showFilter = false
      this.resetAndLoad()
    },
    async fetchCategories() {
      try {
        const data = await api.getCategories()
        const list = data || []
        this.customCategories = [{ id: '', name: '全部' }].concat(list.filter(c => c.is_custom))
        this.merchantCategories = [
          { id: '', name: '全部' },
          { id: '__uncategorized__', name: '未分类' }
        ].concat(list.filter(c => !c.is_custom))
      } catch (err) {
        this.customCategories = [{ id: '', name: '全部' }]
        this.merchantCategories = [
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
    openJumpInput() {
      this.showJumpInput = true
      this.jumpPageInput = String(this.page)
    },
    jumpToPage() {
      const p = parseInt(this.jumpPageInput, 10)
      if (!p || p < 1 || p > this.totalPages) {
        uni.showToast({ title: '页码无效', icon: 'none' })
        return
      }
      this.showJumpInput = false
      this.goPage(p)
    },
    openCreate() {
      uni.navigateTo({
        url: '/pages/products/create'
      })
    },
    openDetail(id) {
      uni.navigateTo({
        url: `/pages/products/detail?id=${id}`
      })
    },
    openVideo(id) {
      if (!id) return
      uni.navigateTo({
        url: `/pages/videos/play?id=${encodeURIComponent(id)}`
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

.toolbar {
  display: flex;
  gap: 10rpx;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12rpx;
}

.filter-bar {
  flex: 1;
  min-width: 220rpx;
  display: flex;
  align-items: center;
  padding: 12rpx 14rpx;
  background: #fff;
  border-radius: 12rpx;
  border: 1rpx solid #e5e7eb;
  box-shadow: 0 6rpx 12rpx rgba(0, 0, 0, 0.03);
}

.search-bar {
  flex: 2;
  min-width: 280rpx;
  display: flex;
  gap: 8rpx;
  align-items: center;
}

.search-input {
  flex: 1;
  background: #fff;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 14rpx;
  font-size: 26rpx;
}

.filter-label {
  color: #6b7280;
  font-size: 24rpx;
}

.action-bar {
  flex-shrink: 0;
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
  margin: 6rpx 0;
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
.name.is-problem {
  color: #e54d42;
}
.name.is-zero {
  color: rgba(11, 31, 58, 0.5);
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

.price-area {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8rpx;
}

.effect-btn {
  min-width: 120rpx;
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

.jump {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.jump-input {
  width: 120rpx;
  border: 1rpx solid #e5e7eb;
  border-radius: 10rpx;
  padding: 6rpx 10rpx;
  font-size: 24rpx;
}
</style>
