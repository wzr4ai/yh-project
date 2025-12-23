<template>
  <view class="page">
    <view class="card">
      <view class="title">视频预览</view>
      <view class="sub">若无法播放，请稍后重试或重新获取链接。</view>
    </view>

    <view class="card video-card">
      <video
        v-if="videoUrl"
        :src="videoUrl"
        controls
        autoplay
        object-fit="contain"
        @error="onError"
      ></video>
      <view v-else class="empty">正在获取视频链接...</view>
    </view>

    <view class="footer">
      <button size="mini" @tap="refresh" :loading="loading">重新获取</button>
      <button size="mini" @tap="copyUrl" :disabled="!videoUrl">复制链接</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'

const CACHE_PREFIX = 'video-url:'
const SKEW_SECONDS = 60

export default {
  data() {
    return {
      productId: '',
      videoUrl: '',
      loading: false
    }
  },
  onLoad(options) {
    this.productId = options.id || options.product_id || ''
  },
  onShow() {
    this.loadVideoUrl()
  },
  methods: {
    cacheKey() {
      return `${CACHE_PREFIX}${this.productId}`
    },
    loadFromCache() {
      try {
        const cached = uni.getStorageSync(this.cacheKey())
        if (!cached || !cached.url || !cached.expires_at) return ''
        const now = Math.floor(Date.now() / 1000)
        if (cached.expires_at - SKEW_SECONDS > now) {
          return cached.url
        }
      } catch (e) {}
      return ''
    },
    saveCache(url, expiresAt) {
      try {
        uni.setStorageSync(this.cacheKey(), { url, expires_at: expiresAt })
      } catch (e) {}
    },
    async loadVideoUrl(force = false) {
      if (!this.productId) {
        uni.showToast({ title: '缺少商品ID', icon: 'none' })
        return
      }
      if (!force) {
        const cached = this.loadFromCache()
        if (cached) {
          this.videoUrl = cached
          return
        }
      }
      this.loading = true
      try {
        const res = await api.getProductVideoUrl(this.productId)
        this.videoUrl = res?.url || ''
        if (res?.url && res?.expires_at) {
          this.saveCache(res.url, res.expires_at)
        }
      } catch (err) {
        uni.showToast({ title: '获取视频失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    refresh() {
      this.loadVideoUrl(true)
    },
    copyUrl() {
      if (!this.videoUrl) return
      uni.setClipboardData({
        data: this.videoUrl,
        success: () => uni.showToast({ title: '已复制', icon: 'success' })
      })
    },
    onError() {
      uni.showToast({ title: '播放失败', icon: 'none' })
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
  margin-bottom: 16rpx;
}

.video-card {
  padding: 0;
  overflow: hidden;
}

video {
  width: 100%;
  height: 500rpx;
  background: #000;
}

.title {
  font-size: 30rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.sub {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #6b7280;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40rpx 0;
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
</style>
