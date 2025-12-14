<template>
  <view class="page">
    <view class="card">
      <view class="card-title">新增销售</view>
      <button class="primary-btn" @tap="openDialog">添加已售货品</button>
    </view>

    <view class="card" v-if="cart.length">
      <view class="card-title">待提交列表</view>
      <view class="cart-item" v-for="(item, idx) in cart" :key="item.id">
        <view class="cart-header">
          <view class="name">{{ item.name }}</view>
          <view class="spec">规格 {{ item.spec || '—' }} ｜ 分类 {{ item.category_name || '—' }}</view>
        </view>
        <view class="cart-row">
          <view class="field">
            <view class="mini-title">箱</view>
            <input class="input" type="number" v-model.number="item.box" />
          </view>
          <view class="field" v-if="item.specQty > 1">
            <view class="mini-title">个</view>
            <input class="input" type="number" v-model.number="item.loose" />
          </view>
          <view class="field">
            <view class="mini-title">实际单价</view>
            <input class="input" type="digit" v-model.number="item.actual_price" placeholder="¥" />
          </view>
          <button size="mini" type="warn" @tap="removeFromCart(idx)">移除</button>
        </view>
      </view>
      <button class="primary-btn" :disabled="!cart.length || saving" :loading="saving" @tap="submitSale">提交销售单</button>
    </view>
    <view v-else class="empty">请先添加已售货品</view>

    <view class="dialog" v-if="showDialog">
      <view class="dialog-content">
        <view class="dialog-header">
          <view class="title">选择商品</view>
          <button size="mini" @tap="closeDialog">关闭</button>
        </view>
        <view class="search-bar">
          <input class="search" v-model="keyword" placeholder="输入关键字搜索" confirm-type="search" @confirm="searchProducts" />
          <button size="mini" @tap="searchProducts">搜索</button>
        </view>
        <scroll-view scroll-y class="dialog-body">
          <view v-for="prod in searchResults" :key="prod.id" class="row">
            <view class="info">
              <view class="name">{{ prod.name }}</view>
              <view class="meta">{{ prod.spec || '—' }} ｜ 库存 {{ prod.stock }}</view>
            </view>
            <view class="inputs">
              <view class="field">
                <view class="mini-title">箱</view>
                <input class="input mini" type="number" v-model.number="draft[prod.id].box" />
              </view>
              <view class="field" v-if="draft[prod.id].specQty > 1">
                <view class="mini-title">个</view>
                <input class="input mini" type="number" v-model.number="draft[prod.id].loose" />
              </view>
              <button size="mini" type="primary" @tap="addToCart(prod)">添加</button>
            </view>
          </view>
          <view v-if="!searchResults.length" class="empty">请输入关键字搜索商品</view>
        </scroll-view>
      </view>
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
      searchResults: [],
      keyword: '',
      draft: {},
      cart: [],
      showDialog: false,
      saving: false
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    }
  },
  methods: {
    openDialog() {
      this.showDialog = true
      this.searchResults = []
      this.keyword = ''
    },
    closeDialog() {
      this.showDialog = false
    },
    async searchProducts() {
      const kw = this.keyword.trim()
      if (!kw) {
        this.searchResults = []
        return
      }
      try {
        const list = await api.getProducts({ offset: 0, limit: 100, keyword: kw })
        const items = list?.items || []
        this.searchResults = items
          .filter(p => (p.stock || 0) > 0)
          .map(p => ({
            ...p,
            specQty: this.parseSpecQty(p.spec)
          }))
        this.searchResults.forEach(p => {
          if (!this.draft[p.id]) {
            this.$set(this.draft, p.id, { box: 0, loose: 0, specQty: p.specQty })
          } else {
            this.draft[p.id].specQty = p.specQty
          }
        })
      } catch (err) {
        uni.showToast({ title: '搜索失败', icon: 'none' })
      }
    },
    parseSpecQty(spec) {
      const match = String(spec || '').match(/(\d+(\.\d+)?)/)
      const val = match ? parseFloat(match[1]) : 1
      return val > 0 ? val : 1
    },
    addToCart(prod) {
      const draft = this.draft[prod.id] || { box: 0, loose: 0, specQty: prod.specQty }
      const box = Number(draft.box) || 0
      const loose = Number(draft.loose) || 0
      const totalUnits = box * prod.specQty + (prod.specQty > 1 ? loose : 0)
      if (totalUnits <= 0) {
        uni.showToast({ title: '请输入数量', icon: 'none' })
        return
      }
      // 校验库存：已选 + 新增 不超过可用库存
      const existing = this.cart.find(c => c.id === prod.id)
      const usedUnits = existing ? existing.box * existing.specQty + (existing.specQty > 1 ? existing.loose : 0) : 0
      const availableUnits = prod.stock || 0
      if (usedUnits + totalUnits > availableUnits) {
        uni.showToast({ title: '超出库存', icon: 'none' })
        return
      }
      if (existing) {
        existing.box += box
        existing.loose += loose
      } else {
        this.cart.push({
          id: prod.id,
          name: prod.name,
          spec: prod.spec,
          category_name: prod.category_name,
          specQty: prod.specQty,
          box,
          loose,
          actual_price: prod.standard_price || 0
        })
      }
      this.$set(this.draft, prod.id, { box: 0, loose: 0, specQty: prod.specQty })
      uni.showToast({ title: '已加入待提交', icon: 'success' })
      this.showDialog = false
    },
    removeFromCart(idx) {
      this.cart.splice(idx, 1)
    },
    async submitSale() {
      const username = uni.getStorageSync('yh-username') || ''
      const payload = this.cart
        .map(item => {
          const qty = item.box * item.specQty + (item.specQty > 1 ? item.loose : 0)
          if (qty <= 0 || item.actual_price === null || item.actual_price === undefined) return null
          return {
            product_id: item.id,
            quantity: qty,
            actual_price: item.actual_price
          }
        })
        .filter(Boolean)
      if (!payload.length) {
        uni.showToast({ title: '请先添加商品与价格', icon: 'none' })
        return
      }
      this.saving = true
      try {
        await api.createSales(payload, username)
        uni.showToast({ title: '已提交', icon: 'success' })
        this.cart = []
        this.showDialog = false
      } catch (err) {
        uni.showToast({ title: '提交失败', icon: 'none' })
      } finally {
        this.saving = false
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
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  margin-bottom: 18rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
}

.card-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.primary-btn {
  width: 100%;
  margin-top: 12rpx;
  background: #0f6a7b;
  color: #fff;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 30rpx 0;
}

.cart-item {
  border-top: 1rpx solid #e5e7eb;
  padding: 12rpx 0;
}

.cart-header .name {
  font-size: 28rpx;
  font-weight: 600;
}

.cart-header .spec {
  color: #6b7280;
  font-size: 24rpx;
}

.cart-row {
  display: flex;
  gap: 10rpx;
  align-items: center;
  margin-top: 8rpx;
}

.field {
  display: flex;
  flex-direction: column;
}

.mini-title {
  color: #6b7280;
  font-size: 22rpx;
}

.input {
  min-width: 140rpx;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 12rpx;
  font-size: 26rpx;
  color: #0b1f3a;
}

.dialog {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  top: 0;
  background: #ffffff;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20rpx;
}

.dialog-content {
  width: 92%;
  max-height: 90vh;
  background: #fff;
  border-radius: 16rpx;
  box-shadow: 0 12rpx 30rpx rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  padding: 12rpx;
}

.dialog-header .title {
  font-size: 30rpx;
  font-weight: 700;
}

.actions {
  display: flex;
  gap: 10rpx;
  align-items: center;
}

.search {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 10rpx;
  font-size: 26rpx;
}

.picker {
  padding: 10rpx 12rpx;
  border: 1rpx solid #e5e7eb;
  border-radius: 10rpx;
}

.search-bar {
  margin: 10rpx 0;
  display: flex;
  gap: 10rpx;
  align-items: center;
}

.dialog-body {
  flex: 1;
  padding: 10rpx 4rpx 20rpx 4rpx;
  }

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1rpx solid #f1f5f9;
  padding: 12rpx 0;
}

.row .info .name {
  font-size: 28rpx;
  font-weight: 600;
}

.row .meta {
  color: #6b7280;
  font-size: 24rpx;
}

.inputs {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.input.mini {
  width: 120rpx;
  padding: 10rpx;
}
</style>
