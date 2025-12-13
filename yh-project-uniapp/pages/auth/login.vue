<template>
  <view class="page">
    <view class="hero">
      <view class="brand">烟花后台</view>
      <view class="tagline">安全合规 · 价格有据 · 销售透明</view>
    </view>
    <view class="card">
      <view class="card-title">选择身份进入</view>
      <view class="role-row">
        <view
          v-for="item in roles"
          :key="item.value"
          class="role-tile"
          :class="{ active: selectedRole === item.value }"
          @tap="selectedRole = item.value"
        >
          <view class="role-name">{{ item.label }}</view>
          <view class="role-desc">{{ item.desc }}</view>
        </view>
      </view>
      <view class="input-area">
        <input
          v-model="username"
          type="text"
          placeholder="输入名字，便于记录操作人"
          placeholder-class="placeholder"
        />
      </view>
      <button class="primary-btn" @tap="handleEnter">进入系统</button>
    </view>
  </view>
</template>

<script>
import { setRole } from '../../common/auth.js'

export default {
  data() {
    return {
      selectedRole: 'owner',
      username: '',
      roles: [
        { label: '老板', value: 'owner', desc: '查看成本、毛利、报表和配置' },
        { label: '店员', value: 'clerk', desc: '仅做销售与库存扣减，隐藏成本' }
      ]
    }
  },
  methods: {
    handleEnter() {
      setRole(this.selectedRole)
      const name = this.username.trim()
      if (name) {
        uni.setStorageSync('yh-username', name)
      }
      uni.reLaunch({
        url: '/pages/dashboard/index'
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
  margin-bottom: 24rpx;
}

.role-row {
  display: flex;
  gap: 20rpx;
}

.role-tile {
  flex: 1;
  background: rgba(255, 255, 255, 0.04);
  border: 1rpx solid rgba(255, 255, 255, 0.1);
  border-radius: 14rpx;
  padding: 20rpx;
  transition: all 0.2s;
}

.role-tile.active {
  border-color: #17d9d0;
  box-shadow: 0 12rpx 24rpx rgba(23, 217, 208, 0.2);
}

.role-name {
  font-size: 30rpx;
  font-weight: 600;
}

.role-desc {
  margin-top: 8rpx;
  color: rgba(245, 247, 250, 0.7);
  font-size: 24rpx;
}

.input-area {
  margin-top: 28rpx;
  margin-bottom: 20rpx;
}

.input-area input {
  width: 100%;
  padding: 20rpx 22rpx;
  border-radius: 12rpx;
  background: rgba(255, 255, 255, 0.08);
  color: #f5f7fa;
}

.placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.primary-btn {
  margin-top: 10rpx;
  background: linear-gradient(135deg, #17d9d0, #0ab8c3);
  color: #0b1f3a;
  font-weight: 700;
  border: none;
}
</style>
