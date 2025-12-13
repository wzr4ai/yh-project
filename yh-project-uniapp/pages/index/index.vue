<template>
  <view class="page">
    <view class="message">正在跳转...</view>
  </view>
</template>

<script>
export default {
  onLoad() {
    uni.reLaunch({
      url: '/pages/auth/login'
    })
  }
}
</script>

<style>
.page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0b1f3a;
}

.message {
  font-size: 28rpx;
}
</style>
