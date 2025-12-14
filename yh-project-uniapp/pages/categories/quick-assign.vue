<template>
  <view class="page">
    <view class="header">
      <view class="title">快速分类</view>
      <view class="subtitle">仅显示自定义分类，点击保存一次性提交</view>
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
        <view class="categories">
          <button
            v-for="cat in customCategories"
            :key="cat.id"
            size="mini"
            :class="['cat-btn', isChecked(item.id, cat.id) ? 'active' : '']"
            @tap="toggle(item.id, cat.id)"
          >{{ cat.name.slice(0, 4) }}</button>
        </view>
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
      customCategories: [],
      products: [],
      keyword: '',
      page: 1,
      pageSize: 15,
      total: 0,
      loading: false,
      saving: false,
      selections: {} // { productId: Set(categoryId) }
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
  onShow() {
    this.loadCategories()
  },
  methods: {
    async loadCategories() {
      try {
        const data = await api.getCategories()
        this.customCategories = (data || []).filter(c => c.is_custom)
        this.loadPage()
      } catch (err) {
        uni.showToast({ title: '加载分类失败', icon: 'none' })
      }
    },
    async loadPage() {
      this.loading = true
      try {
        const data = await api.getProducts({
          offset: (this.page - 1) * this.pageSize,
          limit: this.pageSize,
          keyword: this.keyword.trim()
        })
        const items = data?.items || []
        this.products = items
        this.total = data?.total || 0
        // 初始化选中状态
        items.forEach(item => {
          if (!this.selections[item.id]) {
            this.$set(this.selections, item.id, new Set())
            ;(item.category_ids || []).forEach(cid => {
              if (this.customCategories.find(c => c.id === cid)) {
                this.selections[item.id].add(cid)
              }
            })
          }
        })
      } catch (err) {
        uni.showToast({ title: '加载商品失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    toggle(pid, cid) {
      const set = this.selections[pid] || new Set()
      if (set.has(cid)) {
        set.delete(cid)
      } else {
        set.add(cid)
      }
      this.$set(this.selections, pid, set)
    },
    isChecked(pid, cid) {
      const set = this.selections[pid]
      return set ? set.has(cid) : false
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
      this.saving = true
      try {
        // 将选择结果按分类拆分后调用后端 replaceCategoryProducts
        const categoryToProducts = {}
        Object.entries(this.selections).forEach(([pid, set]) => {
          Array.from(set).forEach(cid => {
            if (!categoryToProducts[cid]) categoryToProducts[cid] = []
            categoryToProducts[cid].push(pid)
          })
        })
        const promises = Object.entries(categoryToProducts).map(([cid, pids]) =>
          api.replaceCategoryProducts(cid, pids)
        )
        await Promise.all(promises)
        uni.showToast({ title: '已保存', icon: 'success' })
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

.categories {
  display: flex;
  flex-wrap: wrap;
  gap: 6rpx;
  max-width: 380rpx;
  justify-content: flex-end;
}

.cat-btn {
  min-width: 120rpx;
  border-radius: 10rpx;
  border: 1rpx solid #e5e7eb;
  color: #0b1f3a;
  background: #f9fafb;
}

.cat-btn.active {
  background: #0f6a7b;
  color: #fff;
  border-color: #0f6a7b;
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
  left: 0;
  right: 0;
  bottom: 100rpx;
  display: flex;
  justify-content: center;
}
</style>
