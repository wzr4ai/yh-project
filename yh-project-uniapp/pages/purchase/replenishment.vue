<template>
  <view class="page">
    <view class="card">
      <view class="title">生成进货/补货单</view>
      <view class="sub">按当前库存与目标库存（箱）生成 CSV，可直接转发给供应商。</view>

      <view class="form-row">
        <view class="label">单据类型</view>
        <picker :range="needModeOptions" :value="needModeIndex" @change="onNeedModeChange">
          <view class="picker">{{ needModeOptions[needModeIndex] }}</view>
        </picker>
      </view>

      <view class="form-row">
        <view class="label">分类（可选）</view>
        <picker :range="categoryNames" :value="categoryIndex" @change="onCategoryChange">
          <view class="picker">{{ categoryNames[categoryIndex] }}</view>
        </picker>
      </view>

      <view class="form-row">
        <view class="label">目标库存（箱）</view>
        <input class="input" type="number" v-model="targetBoxes" placeholder="例如 2" />
      </view>

      <view class="form-row">
        <view class="label">仅导出需要补货</view>
        <switch :checked="onlyNeed" @change="onOnlyNeedChange" />
      </view>

      <view class="form-row">
        <view class="label">单价口径</view>
        <radio-group class="radio-row" @change="onPriceModeChange">
          <label class="radio">
            <radio value="cost" :checked="priceMode === 'cost'" />
            <text>进价</text>
          </label>
          <label class="radio">
            <radio value="standard" :checked="priceMode === 'standard'" />
            <text>标准零售价</text>
          </label>
        </radio-group>
      </view>

      <view class="actions">
        <button type="primary" @tap="generate">生成并下载 CSV</button>
        <button @tap="copyLink" v-if="lastDownloadUrl">复制下载链接</button>
      </view>
    </view>

    <view class="card" v-if="lastSavedPath">
      <view class="title small">最近生成</view>
      <view class="path">{{ lastSavedPath }}</view>
      <view class="actions">
        <button size="mini" @tap="openLast">打开</button>
      </view>
    </view>
  </view>
</template>

<script>
import { getRole, isOwner } from '../../common/auth.js'
import { api, buildApiUrl, buildAuthHeaders } from '../../common/api.js'

export default {
  data() {
    return {
      role: getRole(),
      needModeOptions: ['补货单（低于目标）', '进货单（仅缺货）'],
      needModeIndex: 0,
      categories: [],
      categoryIndex: 0,
      targetBoxes: '2',
      onlyNeed: true,
      priceMode: 'cost',
      lastSavedPath: '',
      lastDownloadUrl: ''
    }
  },
  computed: {
    isOwner() {
      return isOwner(this.role)
    },
    categoryNames() {
      const names = ['全部']
      for (const c of this.categories) {
        if (c && c.name) names.push(c.name)
      }
      return names
    },
    selectedCategoryId() {
      if (this.categoryIndex <= 0) return ''
      const c = this.categories[this.categoryIndex - 1]
      return c && c.id ? c.id : ''
    }
  },
  onShow() {
    this.role = getRole()
    if (!this.isOwner) {
      uni.showToast({ title: '仅老板可用', icon: 'none' })
      uni.navigateBack()
      return
    }
    this.loadCategories()
  },
  methods: {
    onNeedModeChange(e) {
      this.needModeIndex = Number(e.detail.value) || 0
    },
    onCategoryChange(e) {
      this.categoryIndex = Number(e.detail.value) || 0
    },
    onOnlyNeedChange(e) {
      this.onlyNeed = !!(e && e.detail && e.detail.value)
    },
    onPriceModeChange(e) {
      const val = e && e.detail ? e.detail.value : ''
      if (val === 'cost' || val === 'standard') {
        this.priceMode = val
      }
    },
    async loadCategories() {
      try {
        const list = await api.getCategories()
        this.categories = list || []
      } catch (err) {
        uni.showToast({ title: '加载分类失败', icon: 'none' })
      }
    },
    buildDownloadUrl() {
      const target = Number(this.targetBoxes)
      if (!target || target <= 0) {
        throw new Error('请输入目标库存（箱）')
      }
      const needMode = this.needModeIndex === 1 ? 'out_of_stock' : 'below_target'
      const params = []
      params.push(`target_boxes=${encodeURIComponent(String(target))}`)
      params.push(`need_mode=${encodeURIComponent(needMode)}`)
      params.push(`only_need=${encodeURIComponent(String(!!this.onlyNeed))}`)
      params.push(`price_mode=${encodeURIComponent(this.priceMode)}`)
      if (this.selectedCategoryId) {
        params.push(`category_id=${encodeURIComponent(this.selectedCategoryId)}`)
      }
      return buildApiUrl(`/api/exports/replenishment.csv?${params.join('&')}`)
    },
    async generate() {
      let url = ''
      try {
        url = this.buildDownloadUrl()
      } catch (e) {
        uni.showToast({ title: e.message || '参数错误', icon: 'none' })
        return
      }

      this.lastDownloadUrl = url
      uni.showLoading({ title: '生成中...' })

      const tokenHeaders = buildAuthHeaders()
      uni.downloadFile({
        url,
        header: tokenHeaders,
        success: (res) => {
          if (res.statusCode !== 200) {
            uni.hideLoading()
            uni.showToast({ title: '下载失败', icon: 'none' })
            return
          }
          const tempFilePath = res.tempFilePath
          uni.saveFile({
            tempFilePath,
            success: (saveRes) => {
              uni.hideLoading()
              this.lastSavedPath = saveRes.savedFilePath
              uni.showToast({ title: '已生成', icon: 'success' })
              this.openSavedFile(saveRes.savedFilePath)
            },
            fail: () => {
              uni.hideLoading()
              uni.showToast({ title: '保存失败', icon: 'none' })
            }
          })
        },
        fail: () => {
          uni.hideLoading()
          uni.showToast({ title: '下载失败', icon: 'none' })
        }
      })
    },
    openSavedFile(filePath) {
      if (!filePath) return
      uni.openDocument({
        filePath,
        showMenu: true,
        success: () => {},
        fail: () => {
          uni.showModal({
            title: '已生成 CSV',
            content: '当前环境不支持直接打开 CSV，可在文件管理中查看/转发。',
            showCancel: false
          })
        }
      })
    },
    openLast() {
      this.openSavedFile(this.lastSavedPath)
    },
    copyLink() {
      if (!this.lastDownloadUrl) return
      uni.setClipboardData({
        data: this.lastDownloadUrl,
        success: () => {
          uni.showToast({ title: '已复制', icon: 'success' })
        }
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
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.04);
}

.card + .card {
  margin-top: 14rpx;
}

.title {
  font-size: 30rpx;
  font-weight: 700;
  color: #0b1f3a;
}

.title.small {
  font-size: 28rpx;
}

.sub {
  margin-top: 8rpx;
  color: #6b7280;
  font-size: 24rpx;
}

.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #e5e7eb;
}

.form-row:last-of-type {
  border-bottom: none;
}

.label {
  color: #374151;
  font-size: 26rpx;
}

.picker {
  padding: 10rpx 16rpx;
  border-radius: 12rpx;
  border: 1rpx solid #e5e7eb;
  color: #0b1f3a;
  font-size: 24rpx;
  min-width: 280rpx;
  text-align: right;
}

.input {
  width: 280rpx;
  border: 1rpx solid #e5e7eb;
  border-radius: 12rpx;
  padding: 10rpx 16rpx;
  font-size: 24rpx;
  text-align: right;
}

.radio-row {
  display: flex;
  gap: 18rpx;
  align-items: center;
}

.radio {
  display: flex;
  align-items: center;
  gap: 10rpx;
  font-size: 24rpx;
  color: #0b1f3a;
}

.actions {
  display: flex;
  gap: 12rpx;
  margin-top: 18rpx;
}

.path {
  margin-top: 10rpx;
  color: #6b7280;
  font-size: 22rpx;
  word-break: break-all;
}
</style>
