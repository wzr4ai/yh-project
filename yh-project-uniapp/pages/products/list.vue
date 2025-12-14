<template>
  <view class="page">
    <view class="banner">
      <view class="banner-title">商品目录</view>
      <view class="banner-desc">支持 CSV/Excel 批量导入，校验错误可下载错误行</view>
      <button size="mini" type="primary" class="import-btn" @tap="showImportHint">导入指引</button>
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
      <view v-if="!products.length" class="empty">暂无商品</view>
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
      offset: 0,
      pageSize: 20,
      total: 0,
      loading: false
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    finished() {
      return this.products.length >= this.total && this.total > 0
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
      this.offset = 0
      this.products = []
      this.total = 0
      this.loadMore()
    },
    async loadMore() {
      this.loading = true
      try {
        const data = await api.getProducts({ offset: this.offset, limit: this.pageSize })
        const items = (data && data.items) || []
        this.total = data?.total || 0
        this.products = this.products.concat(items)
        this.offset += this.pageSize
      } catch (err) {
        uni.showToast({ title: '加载商品失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    async fetchProducts() {
      // deprecated, kept for compatibility
      return this.resetAndLoad()
    },
    showImportHint() {
      uni.showModal({
        title: '导入指引',
        content: '使用 CSV/Excel 按模板列：名称、分类、规格、进价、固定零售价、别名。导入后可下载错误行。',
        showCancel: false
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
}

.banner {
  background: linear-gradient(135deg, #0f6a7b, #0ab8c3);
  border-radius: 16rpx;
  padding: 20rpx;
  color: #f5f7fa;
  position: relative;
  margin-bottom: 16rpx;
}

.banner-title {
  font-size: 32rpx;
  font-weight: 700;
}

.banner-desc {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: rgba(245, 247, 250, 0.85);
}

.import-btn {
  position: absolute;
  right: 20rpx;
  top: 20rpx;
  background: #ffffff;
  color: #0f6a7b;
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
</style>
