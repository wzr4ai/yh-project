<template>
  <view class="page">
    <view class="card header">
      <view class="title">商品展示</view>
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
    </view>

    <view class="list">
      <view v-for="item in items" :key="item.id" class="card item-card">
        <image v-if="item.img_url" class="thumb" :src="item.img_url" mode="aspectFill"></image>
        <view v-else class="thumb placeholder">暂无图片</view>
        <view class="info">
          <view class="name">{{ item.name }}</view>
          <view class="meta">{{ item.spec || '—' }}</view>
          <view class="actions" v-if="item.video_url || item.effect_url">
            <button size="mini" @tap="openEffect(item)">效果</button>
          </view>
        </view>
      </view>
      <view v-if="!loading && !items.length" class="empty">暂无商品</view>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      keyword: '',
      items: [],
      loading: false
    }
  },
  onShow() {
    this.reload()
  },
  methods: {
    async reload() {
      this.loading = true
      try {
        const res = await api.getProducts({
          offset: 0,
          limit: 200,
          keyword: this.keyword.trim()
        })
        this.items = res?.items || []
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
        this.items = []
      } finally {
        this.loading = false
      }
    },
    openEffect(item) {
      if (item.video_url) {
        uni.navigateTo({ url: `/pages/videos/play?id=${encodeURIComponent(item.id)}` })
        return
      }
      if (item.effect_url) {
        const url = encodeURIComponent(item.effect_url)
        uni.navigateTo({ url: `/pages/webview/view?url=${url}` })
      }
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
  padding-bottom: 80rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
  margin-bottom: 16rpx;
}

.header .title {
  font-size: 32rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.search-row {
  margin-top: 12rpx;
  display: flex;
  gap: 12rpx;
  align-items: center;
}

.search {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 12rpx 14rpx;
  font-size: 26rpx;
}

.item-card {
  display: flex;
  gap: 16rpx;
}

.thumb {
  width: 160rpx;
  height: 160rpx;
  border-radius: 12rpx;
  background: #f3f4f6;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 22rpx;
}

.info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.name {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.meta {
  font-size: 22rpx;
  color: #6b7280;
}

.actions {
  margin-top: 8rpx;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40rpx 0;
}
</style>
