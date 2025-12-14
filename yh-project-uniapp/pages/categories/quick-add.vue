<template>
  <view class="page">
    <view class="header">
      <view class="title">将商品加入：{{ categoryName }}</view>
      <view class="subtitle">选中商品后点击保存一次性提交</view>
    </view>

    <view class="search-bar">
      <input
        class="search-input"
        v-model="keyword"
        type="text"
        placeholder="搜索商品名称"
        confirm-type="search"
        @confirm="doSearch"
      />
      <button size="mini" @tap="doSearch">搜索</button>
    </view>

    <view class="list">
      <view v-for="item in products" :key="item.id" class="row">
        <view class="info">
          <view class="name">{{ item.name }}</view>
          <view class="meta">{{ item.spec || '—' }} ｜ 库存 {{ item.stock }}</view>
        </view>
        <view
          class="add-btn"
          :class="{ active: selectedIds.includes(item.id) }"
          @tap="toggle(item.id)"
        >{{ selectedIds.includes(item.id) ? '✔' : '+' }}</view>
      </view>
      <view class="loadmore" v-if="loading">加载中...</view>
      <view class="loadmore" v-else-if="finished">没有更多了</view>
    </view>

    <view class="pager">
      <button size="mini" :disabled="page <= 1 || loading" @tap="goPage(page - 1)">上一页</button>
      <view class="page-info">第 {{ page }} / {{ totalPages }} 页</view>
      <button size="mini" :disabled="page >= totalPages || loading" @tap="goPage(page + 1)">下一页</button>
    </view>

    <view class="actions">
      <button type="primary" :loading="saving" @tap="save">保存</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'

export default {
  data() {
    return {
      categoryId: '',
      categoryName: '',
      products: [],
      selectedIds: [],
      seen: [],
      page: 1,
      pageSize: 20,
      total: 0,
      loading: false,
      saving: false,
      keyword: ''
    }
  },
  computed: {
    totalPages() {
      if (!this.total) return 1
      return Math.max(1, Math.ceil(this.total / this.pageSize))
    },
    finished() {
      return this.page >= this.totalPages
    }
  },
  onLoad(options) {
    this.categoryId = options.id || ''
    this.categoryName = options.name || ''
    this.loadPage()
  },
  methods: {
    async loadPage() {
      this.loading = true
      try {
        const data = await api.getProducts({
          offset: (this.page - 1) * this.pageSize,
          limit: this.pageSize,
          keyword: this.keyword.trim()
        })
        const items = data?.items || []
        // 初始化选中状态：首次看到的商品，如果已在分类则默认选中
        items.forEach(item => {
          if (!this.seen.includes(item.id)) {
            this.seen.push(item.id)
            if ((item.category_ids || []).includes(this.categoryId) && !this.selectedIds.includes(item.id)) {
              this.selectedIds.push(item.id)
            }
          }
        })
        this.products = items
        this.total = data?.total || 0
      } catch (err) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    toggle(id) {
      const exists = this.selectedIds.includes(id)
      this.selectedIds = exists ? this.selectedIds.filter(x => x !== id) : this.selectedIds.concat(id)
    },
    goPage(target) {
      if (target < 1 || target > this.totalPages || target === this.page) return
      this.page = target
      this.loadPage()
    },
    onSearchInput(e) {
      this.keyword = e.detail.value
    },
    doSearch() {
      this.page = 1
      this.loadPage()
    },
    async save() {
      if (!this.categoryId) {
        uni.showToast({ title: '缺少分类', icon: 'none' })
        return
      }
      if (!this.selectedIds.length) {
        uni.showToast({ title: '未选择商品', icon: 'none' })
        return
      }
      this.saving = true
      try {
        await api.replaceCategoryProducts(this.categoryId, this.selectedIds)
        uni.showToast({ title: '已保存分类', icon: 'success' })
        this.selectedIds = []
        this.seen = []
        this.page = 1
        this.loadPage()
      } catch (err) {
        uni.showToast({ title: '保存失败', icon: 'none' })
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
  padding-bottom: 120rpx;
}

.header {
  margin-bottom: 12rpx;
}

.title {
  font-size: 32rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.subtitle {
  color: #6b7280;
  font-size: 24rpx;
  margin-top: 4rpx;
}

.search-bar {
  margin: 10rpx 0;
  display: flex;
  gap: 10rpx;
}

.search-input {
  flex: 1;
  background: #fff;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 12rpx;
  font-size: 26rpx;
}

.list {
  margin-top: 10rpx;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.row {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 12rpx;
  padding: 14rpx;
  border: 1rpx solid #e5e7eb;
}

.info {
  flex: 1;
}

.name {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.meta {
  font-size: 24rpx;
  color: #6b7280;
  margin-top: 4rpx;
}

.add-btn {
  width: 48rpx;
  height: 48rpx;
  border-radius: 12rpx;
  border: 1rpx solid #0f6a7b;
  color: #0f6a7b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30rpx;
  font-weight: 700;
}

.add-btn.active {
  background: #0f6a7b;
  color: #fff;
}

.loadmore {
  text-align: center;
  color: #6b7280;
  padding: 12rpx 0;
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

.actions {
  position: fixed;
  right: 20rpx;
  bottom: 80rpx;
}
</style>
