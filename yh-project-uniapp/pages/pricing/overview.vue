<template>
  <view class="page">
    <view class="header card">
      <view class="title">货物定价总览</view>

      <view class="search-row">
        <input
          class="search"
          v-model="keyword"
          placeholder="搜索商品名称"
          confirm-type="search"
          @confirm="reload"
        />
        <button size="mini" type="primary" @tap="reload">搜索</button>
      </view>

      <view class="filter-row">
        <view class="filter-label">自定义分类</view>
        <picker :range="customCategoryNames" :value="customCategoryIndex" @change="onCategoryChange">
          <view class="picker">{{ customCategoryNames[customCategoryIndex] }}</view>
        </picker>
      </view>
    </view>

    <view class="list">
      <view v-for="item in items" :key="item.id" class="card row">
        <view class="left">
          <view class="name">{{ item.name }}</view>
          <view class="meta">
            <text>{{ item.spec || '—' }}</text>
            <text class="sep">｜</text>
            <text>{{ item.category_name || '—' }}</text>
            <text class="sep">｜</text>
            <text>库存 {{ item.stock }}</text>
          </view>
        </view>
        <view class="right">
          <view class="price">¥{{ Number(item.displayPrice || 0).toFixed(2) }}</view>
          <view v-if="item.effect_url" class="preview">
            <button size="mini" @tap="openEffect(item.effect_url)">效果</button>
          </view>
        </view>
      </view>
      <view v-if="!loading && !items.length" class="empty">暂无数据</view>
    </view>

    <view class="footer">
      <button size="mini" @tap="forceRelogin">重新登录</button>
      <button size="mini" @tap="reload" :loading="loading">刷新</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'
import { setToken, setRole } from '../../common/auth.js'

export default {
  data() {
    return {
      keyword: '',
      items: [],
      loading: false,
      customCategories: [],
      customCategoryIndex: 0
    }
  },
  computed: {
    customCategoryNames() {
      const names = ['全部自定义分类']
      for (const c of this.customCategories) {
        if (c && c.name) names.push(c.name)
      }
      return names
    }
  },
  onShow() {
    this.loadCategories()
    this.reload()
  },
  methods: {
    async loadCategories() {
      try {
        const list = await api.getCategories()
        this.customCategories = (list || []).filter(c => c.is_custom)
      } catch (err) {
        this.customCategories = []
      }
    },
    onCategoryChange(e) {
      this.customCategoryIndex = Number(e.detail.value) || 0
      this.reload()
    },
    selectedCustomCategoryId() {
      if (this.customCategoryIndex <= 0) return ''
      const cat = this.customCategories[this.customCategoryIndex - 1]
      return cat && cat.id ? cat.id : ''
    },
    async reload() {
      this.loading = true
      try {
        const res = await api.getPricingOverview({
          limit: 500,
          keyword: this.keyword.trim(),
          onlyInStock: true,
          customCategoryId: this.selectedCustomCategoryId()
        })
        this.items = (res?.items || []).map((it) => {
          const priceMin = it.price_min ?? it.standard_price ?? 0
          const priceMax = it.price_max ?? it.standard_price ?? priceMin
          const display = it.standard_price ?? priceMin ?? priceMax ?? 0
          return { ...it, price_min: priceMin, price_max: priceMax, displayPrice: display }
        })
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
        this.items = []
      } finally {
        this.loading = false
      }
    },
    openEffect(url) {
      if (!url) return
      const safe = encodeURIComponent(url)
      uni.navigateTo({ url: `/pages/webview/view?url=${safe}` })
    },
    forceRelogin() {
      setToken('')
      setRole('')
      try {
        uni.removeStorageSync('yh-role')
        uni.removeStorageSync('yh-token')
        uni.removeStorageSync('yh-username')
      } catch (e) {}
      uni.reLaunch({ url: '/pages/auth/login' })
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
  padding-bottom: 120rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
}

.header {
  margin-bottom: 14rpx;
}

.title {
  font-size: 32rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.sub {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #6b7280;
}

.search-row {
  margin-top: 14rpx;
  display: flex;
  gap: 10rpx;
  align-items: center;
}

.search {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 14rpx 16rpx;
  font-size: 26rpx;
  background: #fff;
}

.filter-row {
  margin-top: 12rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.filter-label {
  font-size: 24rpx;
  color: #374151;
  width: 180rpx;
}

.picker {
  flex: 1;
  padding: 12rpx 16rpx;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  font-size: 26rpx;
  color: #0b1f3a;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.meta {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #6b7280;
}

.sep {
  margin: 0 8rpx;
}

.right {
  text-align: right;
  min-width: 170rpx;
}

.price {
  font-size: 30rpx;
  font-weight: 800;
  color: #0f6a7b;
}

.basis {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #9ca3af;
}

.preview {
  margin-top: 8rpx;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 30rpx 0;
}

.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: #ffffff;
  padding: 12rpx 20rpx env(safe-area-inset-bottom);
  box-shadow: 0 -6rpx 12rpx rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: flex-end;
  gap: 12rpx;
}

.picker {
  background: #fff;
}
</style>
