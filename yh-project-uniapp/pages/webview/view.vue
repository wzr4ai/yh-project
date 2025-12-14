<template>
  <view class="page">
    <web-view v-if="safeUrl" :src="safeUrl"></web-view>
    <view v-else class="empty">无效链接</view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      safeUrl: ''
    }
  },
  onLoad(options) {
    const url = decodeURIComponent(options.url || '')
    this.safeUrl = url
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
}
.empty {
  padding: 40rpx;
  text-align: center;
  color: #9ca3af;
}
</style>
