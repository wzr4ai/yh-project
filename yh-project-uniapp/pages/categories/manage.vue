<template>
  <view class="page">
    <view class="card">
      <view class="card-title">新建 / 编辑分类</view>
      <view class="form-row">
        <view class="label">名称</view>
        <input class="input" v-model="form.name" placeholder="分类名称" />
      </view>
      <view class="form-row">
        <view class="label">系数</view>
        <input class="input" type="digit" v-model.number="form.retail_multiplier" placeholder="零售价系数 (可空)" />
      </view>
      <button type="primary" class="ghost" @tap="goQuickAssign">快速分类</button>
      <button type="primary" @tap="save" :loading="saving">{{ form.id ? '更新分类' : '新增分类' }}</button>
    </view>

    <view class="list">
      <view v-for="cat in categories" :key="cat.id" class="card item">
        <view class="item-header">
          <view class="item-name">{{ cat.name }}</view>
          <view class="item-meta">
            <text>系数：{{ cat.retail_multiplier || '—' }}</text>
            <text class="flag" :class="cat.is_custom ? 'custom' : 'merchant'">{{ cat.is_custom ? '自定义' : '商家' }}</text>
          </view>
        </view>
        <view class="actions">
          <button size="mini" @tap="edit(cat)">编辑</button>
          <button size="mini" v-if="cat.is_custom" @tap="quickAdd(cat)">快速分类</button>
          <button size="mini" type="warn" @tap="remove(cat)">删除</button>
        </view>
      </view>
      <view v-if="!categories.length" class="empty">暂无分类</view>
    </view>
  </view>
</template>

<script>
import { api } from '../../common/api.js'
import { isOwner } from '../../common/auth.js'

export default {
  data() {
    return {
      categories: [],
      form: {
        id: '',
        name: '',
        retail_multiplier: null,
        is_custom: true
      },
      saving: false
    }
  },
  onShow() {
    this.loadCategories()
  },
  methods: {
    async loadCategories() {
      try {
        const data = await api.getCategories()
        const list = data || []
        this.categories = list.sort((a, b) => {
          if (a.is_custom === b.is_custom) return (a.name || '').localeCompare(b.name || '')
          return a.is_custom ? -1 : 1
        })
      } catch (err) {
        uni.showToast({ title: '加载分类失败', icon: 'none' })
      }
    },
    edit(cat) {
      this.form = { ...cat }
    },
    async save() {
      if (!this.form.name) {
        uni.showToast({ title: '请输入名称', icon: 'none' })
        return
      }
      this.saving = true
      try {
        if (this.form.id) {
          await api.updateCategory(this.form.id, {
            name: this.form.name,
            retail_multiplier: this.form.retail_multiplier,
            is_custom: this.form.is_custom
          })
        } else {
          await api.createCategory({
            name: this.form.name,
            retail_multiplier: this.form.retail_multiplier,
            is_custom: this.form.is_custom
          })
        }
        uni.showToast({ title: '已保存', icon: 'success' })
        this.form = { id: '', name: '', retail_multiplier: null, is_custom: true }
        this.loadCategories()
      } catch (err) {
        uni.showToast({ title: '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    remove(cat) {
      uni.showModal({
        title: '删除确认',
        content: '删除分类会将该分类下商品的分类清空，确认继续？',
        success: async (res) => {
          if (res.confirm) {
            try {
              await api.deleteCategory(cat.id, true)
              uni.showToast({ title: '已删除', icon: 'success' })
              this.loadCategories()
            } catch (err) {
              uni.showToast({ title: '删除失败', icon: 'none' })
            }
          }
        }
      })
    },
    quickAdd(cat) {
      uni.navigateTo({
        url: `/pages/categories/quick-add?id=${cat.id}&name=${encodeURIComponent(cat.name)}`
      })
    },
    goQuickAssign() {
      uni.navigateTo({
        url: '/pages/categories/quick-assign'
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

.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
  margin-bottom: 16rpx;
}

.ghost {
  margin-top: 10rpx;
  background: #f5f5f5;
  color: #0f6a7b;
}

.card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #0b1f3a;
  margin-bottom: 12rpx;
}

.form-row {
  display: flex;
  align-items: center;
  margin-bottom: 12rpx;
}

.label {
  width: 180rpx;
  color: #4b5563;
  font-size: 26rpx;
}

.input {
  flex: 1;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 14rpx;
  font-size: 26rpx;
}

.list .item {
  margin-bottom: 12rpx;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #0b1f3a;
}

.item-meta {
  color: #6b7280;
  font-size: 24rpx;
  display: flex;
  gap: 12rpx;
  align-items: center;
}

.actions {
  margin-top: 12rpx;
  display: flex;
  gap: 12rpx;
}

.flag {
  padding: 4rpx 8rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
}

.flag.custom {
  background: #e0f2fe;
  color: #0369a1;
}

.flag.merchant {
  background: #fef3c7;
  color: #b45309;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40rpx 0;
}
</style>
