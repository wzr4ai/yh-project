# 烟花爆竹后台管理系统开发规划 (最终执行版)

## 🚀 一、项目技术栈与架构

* **前端:** Uniapp (发布目标: **微信小程序**)
* **后端:** FastAPI (Python)
* **数据库:** PostgreSQL
* **包管理:** uv
* **容器化:** Docker + Docker Compose
* **网关/安全:** **Nginx** (必须，用于反向代理和 **SSL 证书**配置，满足小程序 HTTPS 要求)
* **权限模型:** 轻量 RBAC，仅有 **老板**、**店员** 两个角色。老板全量可见/可操作；店员仅可见销售价格与销售相关功能，不可见成本、毛利、采购金额等敏感数据。

## 🧠 二、核心业务逻辑 (精细化)

### 1. 价格体系 (优先级: 例外 > 分类 > 全局)
系统在计算商品的**“标准零售价”**时，遵循以下逻辑：
1.  **第一优先级 (例外):** 检查商品是否设置了 `fixed_retail_price` (固定零售价)。如果有，直接使用。
2.  **第二优先级 (分类):** 检查商品所属分类是否设置了 `category_multiplier`。如果有，标准零售价 = `base_cost` * `category_multiplier`。
3.  **第三优先级 (全局):** 使用系统全局配置的 `global_multiplier`。标准零售价 = `base_cost` * `global_multiplier`。

### 2. 角色与权限原则
* **老板:** 可访问全部模块与数据 (采购、库存、成本、毛利、报表、配置)。
* **店员:** 仅能执行销售录入、查看可售商品及其标准零售价/实际成交价、执行库存扣减；不可查看成本、进价、毛利、库存货值、采购单金额。
* **数据隔离:** API 层按角色裁剪字段；前端路由与组件层隐藏敏感入口。

### 3. 数据导入 (商品录入)
* 支持 **CSV/Excel** 批量导入商品、分类映射和别名。
* 提供导入模板与字段校验，错误行需返回具体原因并可下载错误行。
* 单仓起步，但表结构保留 `warehouse_id` 扩展空间 (当前固定默认仓)。

### 4. 采购与到货
* **采购单** 创建后不立刻影响库存；到货确认后才入库。
* 到货时写入 `inventory` 与 `inventory_log`，并将进价写入采购明细，便于审计。
* 采购单状态：草稿 -> 待到货 -> 部分到货 -> 完成 -> 关闭。

### 5. 财务与销售分析逻辑
* **进价模式 (2A):** 利润计算基于商品当前的 `base_cost_price` (不进行复杂的加权平均，依靠人工更新进价)。
* **销售快照:** 为了保证历史数据的准确性，销售成交的一瞬间，必须将当时的 **进价** 和 **计算出的标准零售价** 写入销售明细表 (`sales_item`)，防止未来改价影响历史报表。
* **核心指标计算:**
    * **库存潜在货值:** $\sum (\text{当前库存} \times \text{标准零售价})$
    * **实际销售额:** $\sum \text{实际成交价}$
    * **期望销售额:** $\sum \text{标准零售价 (快照)}$
    * **溢价/折价差值:** $\text{实际销售额} - \text{期望销售额}$ (正数代表多卖了，负数代表打折了)
    * **实际毛利:** $\text{实际销售额} - \sum (\text{进价} \times \text{数量})$

## 🛠️ 三、数据库设计 (PostgreSQL 最终版)

### 1. 配置与基础表
| 表名 | 字段 (关键) | 描述 |
| :--- | :--- | :--- |
| `system_config` | `key` (PK), `value` | 存储 `global_retail_multiplier` (全局系数)。 |
| `category` | `id`, `name`, **`retail_multiplier` (Nullable)** | 分类信息及分类系数。 |
| `product` | `id`, `name`, `category_id`, `spec`, `base_cost_price`, **`fixed_retail_price` (Nullable)**, `img_url` | 商品主表。`fixed_retail_price` 不为空即为“例外价格”。 |
| `product_alias` | `id`, `product_id`, `alias_name` | 商品别名，辅助搜索。 |
| `user` | `id`, `username`, `password_hash`, `role` (`owner`/`clerk`) | 基础账号表。 |
| `warehouse` (预留) | `id`, `name` | 单仓模式下固定一条默认仓记录，便于未来扩展多仓。 |

### 2. 业务记录表
| 表名 | 字段 (关键) | 描述 |
| :--- | :--- | :--- |
| `inventory` | `product_id`, `warehouse_id`, `current_stock` | 实时库存。 |
| `inventory_log` | `id`, `product_id`, `warehouse_id`, `change_date`, `change_qty`, `type`, `ref_type`, `ref_id` | 每日库存变动日志 (入库/出库/盘点/采购到货/销售)。 |
| `purchase_order` | `id`, `status`, `supplier`, `expected_date`, `created_by`, `remark` | 采购单主表。 |
| `purchase_item` | `id`, `purchase_order_id`, `product_id`, `quantity`, `expected_cost`, `received_qty`, `actual_cost` | 采购明细，支持部分到货。 |
| `inventory_import_job` | `id`, `file_name`, `status`, `total_rows`, `success_rows`, `error_rows`, `error_report_url`, `created_by` | CSV/Excel 导入任务记录。 |
| `sales_order` | `id`, `order_date`, `total_actual_amount`, `created_by` | 销售主单。 |
| `sales_item` | `id`, `order_id`, `product_id`, `quantity`, **`snapshot_cost`**, **`snapshot_standard_price`**, **`actual_sale_price`** | **核心:** 记录销售时的进价、系统算出的标准价、实际成交价。 |

## ⚙️ 四、API 接口规划 (FastAPI)

### 1. 认证与权限
* `POST /api/auth/login`: 登录，返回 token；token 携带角色信息。
* 中间件按角色裁剪响应字段 (店员不可看到成本/毛利/采购金额)。

### 2. 商品与价格管理
* `GET /api/price/calculate/{product_id}`: 后端执行 3 级价格逻辑，返回该商品的当前“标准零售价”和“计算依据 (是例外、分类还是全局)”。
* `POST /api/products`: 录入商品，支持设置 `fixed_retail_price`。
* `PUT /api/categories/{id}`: 设置分类的 `retail_multiplier`。
* `POST /api/import/products`: 上传 CSV/Excel，异步解析；返回导入任务 ID，提供错误报告下载。
* `GET /api/import/{job_id}`: 查询导入状态。

### 3. 销售与库存
* `POST /api/sales`: 提交销售单。
    * **后端处理:** 接收 `product_id`, `quantity`, `actual_price`。
    * **自动处理:** 查询当前的 `base_cost` 和 `standard_price`，连同前端传来的 `actual_price` 一起存入 `sales_item`。
    * **库存处理:** 扣减 `inventory`，插入 `inventory_log`。
* `POST /api/inventory/adjust`: 手工调整库存 (老板权限)。
* `GET /api/inventory/logs`: 查询库存变动历史，支持按商品/时间筛选。

### 4. 采购
* `POST /api/purchase-orders`: 创建采购单 (草稿)。
* `PUT /api/purchase-orders/{id}/receive`: 到货确认，支持部分到货；入库并写库存日志。
* `GET /api/purchase-orders`: 列表/状态筛选。

### 5. 报表分析 (Dashboard)
* `GET /api/dashboard/realtime`:
    * 返回：当日实际销售额、当日毛利、订单数、客单价。
* `GET /api/dashboard/inventory_value`:
    * 返回：当前库存总成本、**当前库存潜在总售价** (基于当前价格体系计算)。
* `GET /api/dashboard/performance`:
    * 返回：指定时间段内的 **“销售差值”** (实际卖出的钱 vs 应该卖出的钱)，用于评估门店是否存在过度打折或溢价销售情况。
* **维度/对比:** 支持日/周/月/自定义区间；同比/环比；按分类、单品、店员维度拆解；输出毛利率、折扣率分布。店员角色仅展示销售额与订单量，不展示成本/毛利。

### 6. 导出（进货/补货单）
* `GET /api/exports/replenishment.csv`：生成并下载 CSV 进货/补货单（默认仅老板可用）。
    * 典型用途：根据当前库存与目标库存（箱数）自动计算建议补货数量，并导出给供应商/采购人员。
    * 参数（QueryString）：
        * `category_id` / `category_name`：可选，限定某个分类（例如“问题”）。
        * `target_boxes`：目标库存（箱）。用于计算 `建议补货箱数 = ceil(target_boxes - 当前库存折算箱数)`。
        * `need_mode`：`below_target`（补货：低于目标）/ `out_of_stock`（进货：仅缺货）。
        * `only_need`：是否仅导出需要补货的商品（默认 true）。
        * `price_mode`：`cost`（进价）/ `standard`（标准零售价）。
    * CSV 字段（建议）：名称、规格、当前箱数、当前散数、建议补货箱数、单价（口径可选）、image 链接。

## 🐳 五、部署架构 (Docker Compose / 现有 Nginx)

由于目标是 **微信小程序**，必须配置 SSL。服务器已有 Nginx，Docker Compose 仅需起后端与数据库，Nginx 使用宿主机现有进程。

```yaml
version: '3.8'

services:
  # 1. 数据库
  db:
    image: postgres:18
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: fireworks_db

  # 2. 后端 API
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 12
    environment:
      DATABASE_URL: postgresql://user:password@db/fireworks_db
    depends_on:
      - db
    ports:
      - "8000:8000"  # 供宿主机 Nginx 反代
```

### 部署约定 (腾讯云 + 宿主机 Nginx)
* 环境：单生产环境，无灰度；若需预发布，使用相同 compose 结构独立 namespace/端口。
* 证书：腾讯云上通过 acme 已有证书，放在宿主机 Nginx 证书路径；续期后 reload Nginx。
* Nginx 反向代理：在宿主机 Nginx `conf.d` 新增站点，反代到 `http://127.0.0.1:8000`，开启 HTTPS、强制 301 跳转，限制后端仅内网可访问。
* 小程序合规：仅暴露 HTTPS 域名，后端不直接暴露公网端口（如需排障，可临时开放安全组并及时关闭）。
