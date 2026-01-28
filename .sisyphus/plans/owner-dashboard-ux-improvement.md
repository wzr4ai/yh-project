# Owner Dashboard UX Improvement Plan

## Context

### Original Request
分析当前项目的用户体验,尤其是针对老板的数据分析部分.提出改进意见。

### Interview Summary
**Key Discussions**:
- 用户希望基于分析报告生成可执行的工作计划
- 重点改进P0（紧急）和P1（高优先级）的UX问题
- 保持向后兼容，不破坏现有功能
- 移动端优先设计（微信小程序）

**Research Findings**:
- 现有功能已覆盖销售、库存、定价、季节性分析等核心指标
- 后端API实现完善（`backend/app/services/logic_dashboard.py`, `backend/app/api/routes/dashboard.py`）
- 前端页面：`yh-project-uniapp/pages/dashboard/index.vue`（运营总览）和 `analysis.vue`（数据分析）
- **测试基础设施不存在**：项目中没有测试文件，pyproject.toml未包含测试框架依赖
- 技术栈：UniApp (Vue 2) + FastAPI + PostgreSQL

### Metis Review
Metis consultation failed due to provider error. Self-review performed instead.

---

## Work Objectives

### Core Objective
改进老板数据分析仪表板的用户体验，让老板能够在5-10秒内快速了解核心经营状况，并通过可视化和结构化洞察提高决策效率。

### Concrete Deliverables
- 重构的运营总览页面（信息层级优化）
- 异常提示横幅组件
- 完整的销售排行列表（带分页）
- 集成的数据可视化组件（趋势图、饼图等）
- 扩展的时间范围选择器（日/周/月/自定义）
- 结构化的AI洞察卡片（带行动按钮）
- 数据导出功能（PDF/Excel）

### Definition of Done
- [ ] P0改进完成并验证通过（信息层级、异常提示、销售排行）
- [ ] P1改进完成并验证通过（可视化、时间范围、AI结构化、导出）
- [ ] 所有原有功能保持正常工作（向后兼容）
- [ ] 移动端体验在iPhone/Android微信中验证通过
- [ ] 老板角色权限控制依然有效

### Must Have
- **P0-1**: 运营总览信息层级优化（顶部3个核心指标，次要信息折叠）
- **P0-2**: 异常检测与提示机制（折扣率异常、销售骤降）
- **P0-3**: 销售排行完整化（点击展开完整列表，带分页和趋势标识）
- **P1-1**: 数据可视化集成（7日销售趋势图、库存周转曲线、销售集中度饼图）
- **P1-2**: 时间范围扩展（支持日/周/月/自定义区间查询）
- **P1-3**: AI洞察结构化（卡片式展示，每条建议带行动按钮）
- **P1-4**: 数据导出功能（支持PDF/Excel格式）

### Must NOT Have (Guardrails)
- **不改变后端核心业务逻辑**：仅优化数据呈现方式
- **不破坏角色权限控制**：所有owner-only功能必须保持权限保护
- **不修改数据库表结构**：纯UX改进，不涉及数据模型变更
- **不引入新的外部依赖**：使用UniApp生态内成熟的图表库（如uCharts）
- **不删除现有API端点**：保持向后兼容

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO
- **User wants tests**: TBD (需要在任务1中确认)
- **Framework**: TBD
- **QA approach**: TDD (if tests enabled) / Manual verification (if no tests)

### If Manual QA Only (RECOMMENDED for this UX task)

**CRITICAL**: 这是一个以UI/UX改进为主的前端任务，手动验证是更合适的选择。每个任务包含详细的手动验证步骤：

**By Deliverable Type:**

| Type | Verification Tool | Procedure |
|------|------------------|-----------|
| **Frontend/UI changes** | Playwright browser (WeChat DevTools) | 在微信开发者工具中加载页面，交互验证UI变化 |
| **API changes (if any)** | curl / httpie | 测试新增的API端点 |
| **Data export** | 文件打开器 | 下载并打开导出的PDF/Excel文件验证内容 |

**Evidence Required:**
- 微信开发者工具截图（每个UI改动）
- API请求/响应日志（如果涉及后端改动）
- 导出文件内容截图

---

## Task Flow

```
Task 1: Test Strategy Decision
  ↓
Task 2: P0-1 Information Hierarchy (Frontend)
  ↓
Task 3: P0-2 Exception Alerts (Frontend + Backend)
  ↓
Task 4: P0-3 Complete Sales Rankings (Frontend)
  ↓
Task 5: P1-1 Data Visualization (Frontend)
  ↓
Task 6: P1-2 Time Range Extension (Frontend + Backend)
  ↓
Task 7: P1-3 Structured AI Insights (Frontend + Backend)
  ↓
Task 8: P1-4 Data Export (Frontend + Backend)
```

## Parallelization

| Group | Tasks | Reason |
|-------|-------|--------|
| A | 2, 3, 4 | Independent frontend changes, can be done in parallel |
| B | 5, 6, 7, 8 | Each may require backend changes, can be partially parallel |

| Task | Depends On | Reason |
|------|------------|--------|
| 3 | None | Can be implemented independently |
| 6 | None | Can be implemented independently |
| 7 | None | Can be implemented independently |

---

## TODOs

- [ ] 1. 确定测试策略

  **What to do**:
  - 询问用户是否需要设置测试基础设施
  - 说明这是以UI/UX改进为主的前端任务
  - 推荐：手动QA + 微信开发者工具验证（更适合UI任务）
  - 可选：设置前端测试框架（如vue-test-utils + jest），但工作量较大

  **Must NOT do**:
  - 未经用户同意擅自决定测试策略
  - 忽略移动端验证（必须在微信开发者工具中验证）

  **Parallelizable**: NO (blocks all other tasks)

  **References**:

  **Pattern References** (existing code to follow):
  - `yh-project-uniapp/pages/dashboard/index.vue:1-730` - 当前运营总览页面实现
  - `yh-project-uniapp/pages/dashboard/analysis.vue:1-470` - 当前数据分析页面实现

  **Documentation References**:
  - `.sisyphus/drafts/ux-analysis-owner-dashboard.md` - 完整的UX分析报告

  **Acceptance Criteria**:

  **Manual Execution Verification**:

  *Decision Point: Ask user question*

  - [ ] User confirms test strategy preference (TDD vs Manual QA)
  - [ ] If Manual QA: Document detailed verification steps for each task
  - If TDD:
    - [ ] Frontend test framework installed (vue-test-utils + jest)
    - [ ] Example test created to verify setup
    - [ ] Each subsequent task includes test case writing

  **Commit**: NO (decision point, not a code change)
  - Message: N/A

---

- [ ] 2. P0-1: 运营总览信息层级优化

  **What to do**:
  - 重新设计 `yh-project-uniapp/pages/dashboard/index.vue` 的布局
  - **顶部横幅**（仅3个核心指标）：
    - 今日入账（实际销售额）
    - 净利润率（毛利润率作为辅助）
    - 库存健康度（综合评分）
  - **关键提醒区**（异常提示）：
    - 如果有异常，显示红色/黄色横幅
    - 暂无异常时显示绿色提示"经营状况正常"
  - **折叠区域**（次要信息）：
    - 库存货值（成本、潜在售价、SKU数、总箱数） - 点击展开
    - 春节节奏（天数倒计时、当前阶段、进度条） - 点击展开
    - AI洞察 - 保持当前的一行摘要 + 展开全文设计
  - **快捷入口**：
    - 保持当前的7个功能入口卡片

  **Must NOT do**:
  - 删除现有的任何指标数据
  - 改变后端API调用逻辑
  - 破坏角色权限控制（isOwner判断）

  **Parallelizable**: YES (with 3, 4)

  **References**:

  **Pattern References**:
  - `yh-project-uniapp/pages/dashboard/index.vue:31-88` - 当前卡片布局实现
  - `yh-project-uniapp/pages/dashboard/index.vue:560-630` - 当前grid布局样式

  **API/Type References**:
  - `backend/app/api/routes/dashboard.py:15-38` - `/dashboard/realtime` 端点
  - `backend/app/models/schemas.py:211-218` - DashboardRealtime schema

  **Documentation References**:
  - `.sisyphus/drafts/ux-analysis-owner-dashboard.md` - P0-1改进建议详细说明

  **Acceptance Criteria**:

  **Manual Execution Verification**:

  *For Frontend/UI changes:*
  - [ ] Using 微信开发者工具:
    - Navigate to: `运营总览` page
    - Verify: 顶部横幅显示3个核心指标（今日入账、净利润率、库存健康度）
    - Verify: 如果有异常，显示警告横幅（红色/黄色）；无异常显示绿色提示
    - Action: 点击"库存货值"展开区域
    - Verify: 库存货值详情展开显示（成本、潜在售价、SKU数、总箱数）
    - Action: 点击"春节节奏"展开区域
    - Verify: 春节节奏详情展开显示（天数、阶段、进度条）
    - Action: 点击"AI洞察"展开区域
    - Verify: AI洞察全文展开显示
    - Screenshot: Save evidence to `.sisyphus/evidence/task2-top-banners.png`
    - Screenshot: Save evidence to `.sisyphus/evidence/task2-collapsed-state.png`
    - Screenshot: Save evidence to `.sisyphus/evidence/task2-expanded-state.png`

  *For Functionality:*
  - [ ] 所有原有数据正常显示（通过对比改版前后的数值）
  - [ ] Owner角色能看到所有展开区域
  - [ ] Clerk角色只能看到基础指标，折叠区域隐藏或显示受限信息
  - [ ] 页面加载速度无明显下降（<2秒）

  **Evidence Required:**
  - [ ] Screenshot of redesigned top banners (3 core metrics)
  - [ ] Screenshot of collapsed state (showing exception alert if exists)
  - [ ] Screenshot of expanded states (inventory, seasonality, AI)
  - [ ] Manual verification checklist completed

  **Commit**: YES (after verification)
  - Message: `feat(dashboard): optimize information hierarchy on owner overview page`
  - Files: `yh-project-uniapp/pages/dashboard/index.vue`
  - Pre-commit: None (manual QA)

---

- [ ] 3. P0-2: 异常检测与提示机制

  **What to do**:

  **Backend Changes**:
  - 在 `backend/app/services/logic_dashboard.py` 中新增异常检测逻辑：
    ```python
    def detect_exceptions(session: AsyncSession, today: date) -> dict:
        # 检测折扣率异常（>20%或<-10%）
        # 检测销售骤降（同比<-30%，如果有历史数据）
        # 检测库存积压（滞销品占比>30%）
        return {
            "discount_rate_high": bool,  # 今日折扣率>20%
            "discount_rate_low": bool,   # 今日折扣率<-10%（溢价过多）
            "sales_drop": bool,         # 销售额同比<-30%
            "inventory_overstock": bool,  # 滞销品占比>30%
            "exceptions": list[dict]    # 详细异常列表
        }
    ```
  - 修改 `backend/app/api/routes/dashboard.py` 中的 `/dashboard/realtime` 端点，返回异常信息

  **Frontend Changes**:
  - 在 `yh-project-uniapp/pages/dashboard/index.vue` 中添加异常提示横幅组件
  - 根据异常类型显示不同颜色：
    - 红色：严重异常（销售骤降、库存积压）
    - 黄色：警告异常（折扣率过高/过低）
    - 绿色：无异常

  **Must NOT do**:
  - 修改数据库表结构
  - 删除现有的任何指标
  - 改变异常检测的业务逻辑（除非用户明确要求）

  **Parallelizable**: YES (with 2, 4)

  **References**:

  **Pattern References**:
  - `backend/app/services/logic_dashboard.py:29-52` - dashboard_realtime 函数
  - `backend/app/services/logic_dashboard.py:89-107` - dashboard_performance 函数
  - `backend/app/api/routes/dashboard.py:15-38` - /dashboard/realtime 端点

  **External References**:
  - UniApp notification component: https://uniapp.dcloud.net.cn/component/notice.html

  **Verified Paths**:
  - `yh-project-uniapp/pages/products/detail.vue` - 商品详情页已存在

  **Acceptance Criteria**:

  **Manual Execution Verification**:

  *For Backend Changes:*
  - [ ] Request: `GET http://localhost:8000/api/dashboard/realtime` (with owner token)
  - [ ] Response includes: `exceptions` field
  - [ ] Response status: 200

  *For Frontend/UI changes:*
  - [ ] Using 微信开发者工具:
    - Navigate to: `运营总览` page
    - Verify: 异常提示横幅显示在顶部3个指标下方
    - Verify: 无异常时显示绿色"经营状况正常"
    - Verify: 有警告异常时显示黄色横幅（如"今日折扣率异常高，请注意定价策略"）
    - Verify: 有严重异常时显示红色横幅（如"销售额骤降30%，请检查促销活动"）
    - Screenshot: Save evidence to `.sisyphus/evidence/task3-no-exceptions.png`
    - Screenshot: Save evidence to `.sisyphus/evidence/task3-warning-exception.png`
    - Screenshot: Save evidence to `.sisyphus/evidence/task3-critical-exception.png`

  *For Functionality:*
  - [ ] 异常检测逻辑正确（通过手动触发异常情况验证）
  - [ ] 异常提示可以关闭（点击"×"按钮）
  - [ ] Clerk角色看不到成本相关的异常（如有）

  **Evidence Required:**
  - [ ] API response screenshot showing exceptions field
  - [ ] Screenshot of exception banner (no exception, warning, critical)
  - [ ] Manual verification checklist completed

  **Commit**: YES (group with task2 or task4)
  - Message: `feat(dashboard): add exception detection and alert mechanism`
  - Files: `backend/app/services/logic_dashboard.py`, `backend/app/api/routes/dashboard.py`, `yh-project-uniapp/pages/dashboard/index.vue`
  - Pre-commit: Manual QA of backend and frontend

---

- [ ] 4. P0-3: 销售排行完整化

  **What to do**:
  - 修改 `yh-project-uniapp/pages/dashboard/index.vue` 中的"快报"卡片
  - 当前显示：Top 5商品名称（用"、"分隔）
  - 改进为：
    - 显示Top 5列表（商品名称 + 金额）
    - 每行可点击，跳转到商品详情页
    - 底部添加"查看全部"按钮，点击展开完整列表（分页）
    - 完整列表显示：商品名称、销售额、利润率、库存、趋势标识（↑↓）
  - 同时改进 `yh-project-uniapp/pages/dashboard/analysis.vue` 中的销售排行卡片

  **Must NOT do**:
  - 修改后端API（当前返回的数据足够）
  - 破坏现有的Top 5快速查看功能

  **Parallelizable**: YES (with 2, 3)

  **References**:

  **Pattern References**:
  - `yh-project-uniapp/pages/dashboard/index.vue:56-70` - "快报"卡片实现
  - `yh-project-uniapp/pages/dashboard/index.vue:241-249` - salesNameLabel/marginNameLabel computed
  - `yh-project-uniapp/pages/dashboard/analysis.vue:34-42` - 销售重心卡片实现
  - `yh-project-uniapp/pages/dashboard/analysis.vue:289-308` - fetchData 方法

  **API/Type References**:
  - `backend/app/api/routes/dashboard.py:124-131` - `/dashboard/sales-rankings` 端点
  - `backend/app/models/schemas.py:264-275` - SalesRankingItem schema

  **Documentation References**:
  - `.sisyphus/drafts/ux-analysis-owner-dashboard.md` - P0-3改进建议详细说明

  **Verified Paths**:
  - `yh-project-uniapp/pages/products/detail.vue` - 商品详情页已存在
  - `yh-project-uniapp/pages/purchase/edit.vue` - 采购单编辑页已存在

  **Acceptance Criteria**:

  **Manual Execution Verification**:

  *For Frontend/UI changes:*
  - [ ] Using 微信开发者工具:
    - Navigate to: `运营总览` page
    - Verify: "快报"卡片显示Top 5商品列表（商品名称 + 金额）
    - Action: 点击某个商品
    - Verify: 跳转到商品详情页（如 `pages/products/detail?id=xxx`）
    - Action: 点击"查看全部"按钮
    - Verify: 展开完整销售排行列表（分页，每页10条）
    - Verify: 列表显示：商品名称、销售额、利润率、库存、趋势标识（↑↓）
    - Action: 滚动或切换页码
    - Verify: 分页功能正常
    - Screenshot: Save evidence to `.sisyphus/evidence/task4-top5-summary.png`
    - Screenshot: Save evidence to `.sisyphus/evidence/task4-full-list.png`

  *For Data Analysis page:*
  - [ ] Navigate to: `数据分析` page
  - Verify: "销售重心"卡片也支持点击展开完整列表
  - Verify: "高毛利潜力"卡片也支持点击展开完整列表

  **Evidence Required:**
  - [ ] Screenshot of Top 5 summary in overview page
  - [ ] Screenshot of full sales rankings list with pagination
  - [ ] Manual verification checklist completed

  **Commit**: YES (group with task2 or task3)
  - Message: `feat(dashboard): add complete sales rankings with pagination`
  - Files: `yh-project-uniapp/pages/dashboard/index.vue`, `yh-project-uniapp/pages/dashboard/analysis.vue`
  - Pre-commit: Manual QA of pagination and navigation

---

- [ ] 5. P1-1: 数据可视化集成

  **What to do**:
  - **选择图表库**：推荐使用 uCharts（UniApp生态）或 ECharts（通过webview）
  - **实现7日销售趋势图**：
    - 在 `yh-project-uniapp/pages/dashboard/analysis.vue` 中添加图表组件
    - 折线图：日期 vs 销售额
    - 支持切换到"订单数"、"利润率"等维度
  - **实现库存周转曲线**：
    - 折线图：日期 vs 库存周转天数
  - **实现销售集中度饼图**：
    - 饼图：Top 5商品销售额占比
  - **后端支持**（如需要）：
    - 确保后端返回的数据格式适合图表渲染
    - 如 `backend/app/services/logic_dashboard.py:433-440` 中的 sales_trend_7d

  **Must NOT do**:
  - 引入重量级图表库影响页面加载性能
  - 破坏移动端体验（图表在小屏幕上必须可读）

  **Parallelizable**: YES (with 6, 7, 8 - partial parallelism possible)

  **References**:

  **Pattern References**:
  - `backend/app/services/logic_dashboard.py:418-440` - sales_trend_7d 数据生成
  - `yh-project-uniapp/pages/dashboard/analysis.vue:234-276` - fetchData 方法

  **External References**:
  - uCharts official docs: https://www.ucharts.cn/
  - ECharts for WeChat Mini Program: https://github.com/ecomfe/echarts-for-weixin

  **Documentation References**:
  - `.sisyphus/drafts/ux-analysis-owner-dashboard.md` - P1-1改进建议详细说明

  **Acceptance Criteria**:

  **Manual Execution Verification**:

  *For 7日销售趋势图:*
  - [ ] Using 微信开发者工具:
    - Navigate to: `数据分析` page
    - Verify: 7日销售趋势图正确显示（折线图）
    - Action: 点击图表
    - Verify: 显示具体数据点的tooltip（日期 + 销售额）
    - Action: 切换到"订单数"维度
    - Verify: 图表更新为订单数趋势
    - Screenshot: Save evidence to `.sisyphus/evidence/task5-sales-trend-chart.png`

  *For 库存周转曲线:*
  - [ ] Verify: 库存周转曲线正确显示（折线图）
  - Screenshot: Save evidence to `.sisyphus/evidence/task5-inventory-turnover-chart.png`

  *For 销售集中度饼图:*
  - [ ] Verify: 销售集中度饼图正确显示（Top 5商品占比）
  - Action: 点击饼图某个扇区
  - Verify: 显示该商品的详细信息
  - Screenshot: Save evidence to `.sisyphus/evidence/task5-sales-concentration-pie.png`

  *For Performance:*
  - [ ] 图表加载时间 < 2秒
  - [ ] 图表在小屏幕上清晰可读（在iPhone SE尺寸模拟器中验证）

  **Evidence Required:**
  - [ ] Screenshot of 7-day sales trend chart
  - [ ] Screenshot of inventory turnover curve
  - [ ] Screenshot of sales concentration pie chart
  - [ ] Manual verification checklist completed

  **Commit**: YES
  - Message: `feat(dashboard): add data visualization charts (trend, turnover, concentration)`
  - Files: `yh-project-uniapp/pages/dashboard/analysis.vue`, possibly `yh-project-uniapp/components/` (chart components)
  - Pre-commit: Manual QA of chart rendering and performance

---

- [ ] 6. P1-2: 时间范围扩展

  **What to do**:

  **Backend Changes**:
  - 修改 `backend/app/services/logic_dashboard.py` 中的函数，支持时间范围参数：
    ```python
    async def _sales_summary(session: AsyncSession, *, start_date: date | None, end_date: date | None) -> dict:
        # 支持按日/周/月/自定义区间查询
        pass
    ```
  - 修改 `backend/app/api/routes/dashboard.py` 中的端点，接受查询参数：
    - `GET /dashboard/sales-rankings?start_date=2026-01-01&end_date=2026-01-07`
  - 新增端点（如需要）：
    - `GET /dashboard/trend?period=week` - 返回周趋势数据
    - `GET /dashboard/trend?period=month` - 返回月趋势数据

  **Frontend Changes**:
  - 在 `yh-project-uniapp/pages/dashboard/analysis.vue` 中添加时间范围选择器
  - 支持选项：今天、本周、本月、自定义区间
  - 当前"当天"/"全部"切换改为"今天"/"本周"/"本月"/"全部"

  **Must NOT do**:
  - 破坏现有的"当天"/"全部"逻辑
  - 删除任何现有数据

  **Parallelizable**: YES (with 5, 7, 8)

  **References**:

  **Pattern References**:
  - `backend/app/services/logic_dashboard.py:217-251` - _sales_summary 函数
  - `backend/app/api/routes/dashboard.py:124-131` - /dashboard/sales-rankings 端点
  - `yh-project-uniapp/pages/dashboard/analysis.vue:6-10` - scope 切换实现

  **Documentation References**:
  - `.sisyphus/drafts/ux-analysis-owner-dashboard.md` - P1-2改进建议详细说明

  **Acceptance Criteria**:

  **Manual Execution Verification**:

  *For Backend Changes:*
  - [ ] Request: `GET http://localhost:8000/api/dashboard/sales-rankings?scope=week` (with owner token)
  - [ ] Response: Contains sales data for current week
  - [ ] Response status: 200
  - [ ] Request: `GET http://localhost:8000/api/dashboard/sales-rankings?start_date=2026-01-01&end_date=2026-01-07`
  - [ ] Response: Contains sales data for custom range
  - [ ] Response status: 200

  *For Frontend/UI changes:*
  - [ ] Using 微信开发者工具:
    - Navigate to: `数据分析` page
    - Verify: 时间范围选择器显示"今天"/"本周"/"本月"/"全部"选项
    - Action: 点击"本周"
    - Verify: 数据更新为本周的排行和概览
    - Action: 点击"本月"
    - Verify: 数据更新为本月的排行和概览
    - Action: 点击"自定义区间"
    - Verify: 弹出日期选择器（开始日期 + 结束日期）
    - Action: 选择自定义区间并确认
    - Verify: 数据更新为自定义区间的数据
    - Screenshot: Save evidence to `.sisyphus/evidence/task6-time-selector.png`

  *For Backward Compatibility:*
  - [ ] 原有的"当天"/"全部"逻辑依然正常工作
  - [ ] 无参数时默认返回"全部"数据

  **Evidence Required:**
  - [ ] API response screenshot showing week/month data
  - [ ] Screenshot of time range selector
  - [ ] Manual verification checklist completed

  **Commit**: YES
  - Message: `feat(dashboard): add extended time range support (week/month/custom)`
  - Files: `backend/app/services/logic_dashboard.py`, `backend/app/api/routes/dashboard.py`, `yh-project-uniapp/pages/dashboard/analysis.vue`
  - Pre-commit: Manual QA of backend API and frontend selector

---

- [ ] 7. P1-3: AI洞察结构化

  **What to do**:

  **Backend Changes**:
  - 修改 `backend/app/services/llm_agent.py` 中的AI洞察生成函数
  - 更新prompt，要求LLM输出结构化JSON而非纯文本：
    ```python
    # 示例JSON格式
    {
      "restock_suggestions": [
        {"product_id": "xxx", "name": "商品A", "reason": "库存不足（2箱），周销量10箱"}
      ],
      "promo_suggestions": [
        {"product_id": "yyy", "name": "商品B", "reason": "利润率低（15%），库存积压"}
      ],
      "risk_alerts": [
        {"type": "inventory_overstock", "message": "滞销品占比35%，建议清仓促销"}
      ]
    }
    ```
  - 新增schema验证LLM输出格式

  **Frontend Changes**:
  - 在 `yh-project-uniapp/pages/dashboard/index.vue` 中重构AI洞察卡片
  - 当前：一行摘要 + 展开全文（纯文本）
  - 改进为：卡片式展示
    - **补货建议**卡片：列出具体商品，每条带"生成采购单"按钮
    - **促销建议**卡片：列出具体商品，每条带"创建促销"按钮
    - **风险提示**卡片：列出风险类型和描述
  - 保留"生成计划"/"生成总结"按钮

  **Must NOT do**:
  - 破坏现有的AI洞察生成逻辑
  - 依赖不稳定的LLM输出格式（必须加fallback）

  **Parallelizable**: YES (with 5, 6, 8)

  **References**:

  **Pattern References**:
  - `backend/app/services/llm_agent.py:238-272` - analyze_dashboard_report 函数
  - `backend/app/services/llm_agent.py:371-389` - analyze_dashboard_restock_advice 函数
  - `yh-project-uniapp/pages/dashboard/index.vue:110-122` - AI洞察卡片实现
  - `yh-project-uniapp/pages/dashboard/index.vue:417-451` - AI洞察生成方法

  **API/Type References**:
  - `backend/app/models/schemas.py:284-306` - DashboardReportLLMResponse schema
  - `backend/app/api/routes/dashboard.py:235-259` - /dashboard/report/analysis 端点

  **Documentation References**:
  - `.sisyphus/drafts/ux-analysis-owner-dashboard.md` - P1-3改进建议详细说明

  **Acceptance Criteria**:

  **Manual Execution Verification**:

  *For Backend Changes:*
  - [ ] Request: `POST http://localhost:8000/api/dashboard/ai/daily-summary` (with owner token)
  - [ ] Response: `analysis` field contains structured JSON (fallback to text if parsing fails)
  - [ ] Response status: 200

  *For Frontend/UI changes:*
  - [ ] Using 微信开发者工具:
    - Navigate to: `运营总览` page
    - Verify: AI洞察显示为卡片式布局
    - Verify: "补货建议"卡片列出具体商品
    - Action: 点击某个补货建议的"生成采购单"按钮
    - Verify: 跳转到采购单创建页面（如 `pages/purchase/edit`）
    - Verify: "促销建议"卡片列出具体商品
    - Action: 点击某个促销建议的"创建促销"按钮
    - Verify: 跳转到促销创建页面（或显示"功能开发中"提示）
    - Verify: "风险提示"卡片列出风险类型
    - Screenshot: Save evidence to `.sisyphus/evidence/task7-structured-ai-insights.png`

  *For Fallback:*
  - [ ] 如果LLM输出格式错误，fallback到纯文本显示
  - [ ] 用户可以看到原始AI建议（即使格式错误）

  **Evidence Required:**
  - [ ] API response screenshot showing structured JSON
  - [ ] Screenshot of structured AI insights cards
  - [ ] Manual verification checklist completed

  **Commit**: YES
  - Message: `feat(dashboard): restructure AI insights as actionable cards`
  - Files: `backend/app/services/llm_agent.py`, `yh-project-uniapp/pages/dashboard/index.vue`
  - Pre-commit: Manual QA of backend parsing and frontend rendering

---

- [ ] 8. P1-4: 数据导出功能

  **What to do**:

  **Backend Changes**:
  - 新增 `backend/app/api/routes/dashboard.py` 端点：
    ```python
    @router.get("/dashboard/export")
    async def export_dashboard_report(
        format: str = "pdf",  # "pdf" or "excel"
        session: AsyncSession = Depends(get_session),
        current_user=Depends(deps.get_current_user),
    ):
        if current_user.role != "owner":
            raise HTTPException(status_code=403)
        # 生成报告（包含所有关键指标和图表）
        # 返回文件流
    ```
  - 实现PDF生成（使用 reportlab 或 weasyprint）
  - 实现Excel生成（使用 openpyxl 或 pandas）

  **Frontend Changes**:
  - 在 `yh-project-uniapp/pages/dashboard/index.vue` 和 `analysis.vue` 中添加"导出报告"按钮
  - 点击后弹出格式选择（PDF/Excel）
  - 调用后端API，下载文件

  **Must NOT do**:
  - 暴露敏感数据给非owner角色
  - 生成过大的文件导致下载超时

  **Parallelizable**: YES (with 5, 6, 7)

  **References**:

  **Pattern References**:
  - `backend/app/api/routes/dashboard.py` - 现有dashboard端点
  - `yh-project-uniapp/pages/dashboard/index.vue:125-164` - 快捷入口实现

  **External References**:
  - reportlab docs: https://docs.reportlab.com/
  - openpyxl docs: https://openpyxl.readthedocs.io/

  **Documentation References**:
  - `.sisyphus/drafts/ux-analysis-owner-dashboard.md` - P1-4改进建议详细说明

  **Acceptance Criteria**:

  **Manual Execution Verification**:

  *For Backend Changes:*
  - [ ] Request: `GET http://localhost:8000/api/dashboard/export?format=pdf` (with owner token)
  - [ ] Response: File download (Content-Type: application/pdf)
  - [ ] Response status: 200
  - [ ] Request: `GET http://localhost:8000/api/dashboard/export?format=excel` (with owner token)
  - [ ] Response: File download (Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
  - [ ] Response status: 200

  *For Frontend/UI changes:*
  - [ ] Using 微信开发者工具:
    - Navigate to: `运营总览` page
    - Verify: "导出报告"按钮存在（可能在快捷入口区域）
    - Action: 点击"导出报告"按钮
    - Verify: 弹出格式选择（PDF/Excel）
    - Action: 选择"PDF"
    - Verify: 文件开始下载
    - Action: 下载完成后打开PDF文件
    - Verify: PDF包含所有关键指标和图表（今日入账、利润率、库存健康度、销售趋势图等）
    - Action: 重复上述步骤，选择"Excel"
    - Verify: Excel文件包含所有关键指标数据
    - Screenshot: Save evidence to `.sisyphus/evidence/task8-export-dialog.png`
    - Screenshot: Save evidence to `.sisyphus/evidence/task8-exported-pdf.png` (first page)
    - Screenshot: Save evidence to `.sisyphus/evidence/task8-exported-excel.png` (first sheet)

  *For Security:*
  - [ ] Clerk角色访问export端点时返回403
  - [ ] 未登录用户访问export端点时返回401

  **Evidence Required:**
  - [ ] Screenshot of export dialog
  - [ ] Screenshot of exported PDF (first page)
  - [ ] Screenshot of exported Excel (first sheet)
  - [ ] Manual verification checklist completed

  **Commit**: YES
  - Message: `feat(dashboard): add data export functionality (PDF/Excel)`
  - Files: `backend/app/api/routes/dashboard.py`, `yh-project-uniapp/pages/dashboard/index.vue`, `yh-project-uniapp/pages/dashboard/analysis.vue`
  - Pre-commit: Manual QA of file generation and download

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 2 | `feat(dashboard): optimize information hierarchy on owner overview page` | `yh-project-uniapp/pages/dashboard/index.vue` | 微信开发者工具验证 |
| 3 | `feat(dashboard): add exception detection and alert mechanism` | `backend/app/services/logic_dashboard.py`, `backend/app/api/routes/dashboard.py`, `yh-project-uniapp/pages/dashboard/index.vue` | 后端API测试 + 前端验证 |
| 4 | `feat(dashboard): add complete sales rankings with pagination` | `yh-project-uniapp/pages/dashboard/index.vue`, `yh-project-uniapp/pages/dashboard/analysis.vue` | 分页和导航验证 |
| 5 | `feat(dashboard): add data visualization charts` | `yh-project-uniapp/pages/dashboard/analysis.vue` | 图表渲染和性能验证 |
| 6 | `feat(dashboard): add extended time range support` | `backend/app/services/logic_dashboard.py`, `backend/app/api/routes/dashboard.py`, `yh-project-uniapp/pages/dashboard/analysis.vue` | 后端API + 前端选择器验证 |
| 7 | `feat(dashboard): restructure AI insights as actionable cards` | `backend/app/services/llm_agent.py`, `yh-project-uniapp/pages/dashboard/index.vue` | 后端解析 + 前端渲染验证 |
| 8 | `feat(dashboard): add data export functionality` | `backend/app/api/routes/dashboard.py`, `yh-project-uniapp/pages/dashboard/index.vue`, `yh-project-uniapp/pages/dashboard/analysis.vue` | 文件生成和下载验证 |

---

## Success Criteria

### Verification Commands
```bash
# 后端API测试
curl -H "Authorization: Bearer <owner_token>" http://localhost:8000/api/dashboard/realtime
curl -H "Authorization: Bearer <owner_token>" http://localhost:8000/api/dashboard/export?format=pdf

# 前端验证（在微信开发者工具中）
# 见各任务的手动验证步骤
```

### Final Checklist
- [ ] P0改进完成（信息层级、异常提示、销售排行）
- [ ] P1改进完成（可视化、时间范围、AI结构化、导出）
- [ ] 所有原有功能保持正常工作（向后兼容）
- [ ] 移动端体验在微信开发者工具中验证通过
- [ ] 老板角色权限控制依然有效
- [ ] Clerk角色看不到敏感数据（成本、利润等）
- [ ] 所有截图和证据已保存到 `.sisyphus/evidence/`

### Performance Targets
- 运营总览页面加载时间 < 2秒
- 图表渲染时间 < 2秒
- 导出PDF文件生成时间 < 10秒
- 导出Excel文件生成时间 < 5秒

---

## Notes

### Test Infrastructure Decision
本项目目前没有测试基础设施。由于这是一个以UI/UX改进为主的前端任务，推荐采用**手动QA + 微信开发者工具验证**的方式。如果用户需要自动化测试，可以在任务1中设置前端测试框架（如vue-test-utils + jest），但工作量较大。

### Chart Library Recommendation
推荐使用 **uCharts**（UniApp生态）而非ECharts，原因：
- 原生支持UniApp/微信小程序
- 体积小，性能好
- 社区活跃，文档完善

### AI Structure Fallback
由于LLM输出格式可能不稳定，必须实现fallback机制：如果JSON解析失败，fallback到纯文本显示，确保用户始终能看到AI建议。

### Security Considerations
- 所有新增的owner-only功能必须在API层强制权限检查
- 导出功能不得暴露给clerk或未登录用户
- AI洞察中的行动按钮跳转到对应的功能页面（如采购单创建）
