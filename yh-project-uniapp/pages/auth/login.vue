<template>
  <view class="page">
    <view class="hero">
      <view class="brand">烟花后台</view>
      <view class="tagline">微信小程序一键登录 · JWT 自动鉴权</view>
    </view>
    <view class="card">
      <view class="card-title">正在登录</view>
      <view class="loading">请稍候，自动获取微信登录态…</view>
      <view class="hint">若为首次登录将自动注册为店员</view>
      <view class="divider"></view>
      <view class="manual">
        <view class="manual-title">登录异常？点击重试</view>
        <button class="primary-btn" :loading="loading" @tap="autoWeappLogin">重试登录</button>
      </view>
    </view>
  </view>
</template>

<script>
import { setRole, setToken, getToken, getRole, isTokenValid } from '../../common/auth.js'
import { API_BASE_URL } from '../../common/config.js'

export default {
  data() {
    return {
      loading: false
    }
  },
  onShow() {
    const token = getToken()
    if (token && isTokenValid(token)) {
      // 已登录且 token 未过期，直接跳转
      if (!getRole()) {
        setRole('clerk')
      }
      uni.reLaunch({ url: '/pages/dashboard/index' })
      return
    }
    this.autoWeappLogin()
  },
  methods: {
    autoWeappLogin() {
      this.loading = true
      // 在微信小程序内会返回真实 code，H5/非微信环境用 mock code
      uni.login({
        provider: 'weixin',
        success: (res) => {
          const code = res.code || 'mock-code'
          this.exchangeCode(code)
        },
        fail: () => {
          this.exchangeCode('mock-code')
        }
      })
    },
    exchangeCode(code) {
      uni.request({
        url: `${API_BASE_URL}/api/auth/weapp`,
        method: 'POST',
        data: { code },
        success: (resp) => {
          const data = resp.data
          if (data && data.token) {
            setToken(data.token)
            setRole(data.role)
            uni.setStorageSync('yh-username', data.username)
            uni.reLaunch({ url: '/pages/dashboard/index' })
          } else {
            this.failToast()
          }
        },
        fail: () => this.failToast(),
        complete: () => {
          this.loading = false
        }
      })
    },
    failToast() {
      uni.showToast({
        title: '登录失败',
        icon: 'none'
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0b1f3a, #0f6a7b);
  padding: 48rpx 32rpx 80rpx;
  box-sizing: border-box;
  color: #f5f7fa;
}

.hero {
  margin-top: 40rpx;
  margin-bottom: 32rpx;
}

.brand {
  font-size: 44rpx;
  font-weight: 700;
  letter-spacing: 2rpx;
}

.tagline {
  margin-top: 12rpx;
  color: rgba(245, 247, 250, 0.8);
  font-size: 26rpx;
}

.card {
  background: #0f1320;
  border-radius: 18rpx;
  padding: 32rpx;
  box-shadow: 0 16rpx 32rpx rgba(0, 0, 0, 0.35);
}

.card-title {
  font-size: 32rpx;
  font-weight: 600;
  margin-bottom: 12rpx;
}

.loading {
  color: #c7d2fe;
  font-size: 26rpx;
}

.hint {
  margin-top: 8rpx;
  color: rgba(245, 247, 250, 0.65);
  font-size: 24rpx;
}

.divider {
  margin: 20rpx 0;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.08);
}

.manual-title {
  color: rgba(245, 247, 250, 0.85);
  font-size: 26rpx;
  margin-bottom: 10rpx;
}

.primary-btn {
  background: linear-gradient(135deg, #17d9d0, #0ab8c3);
  color: #0b1f3a;
  font-weight: 700;
  border: none;
}
</style>
