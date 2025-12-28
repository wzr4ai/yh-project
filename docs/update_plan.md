# 烟花爆竹进销存系统：规格、条码与库存重构方案

## 1. 业务背景
烟花爆竹行业存在典型的“大进小出”场景：
- **进货单位**：箱（由供应商提供箱价）。
- **零售单位**：盒、把、个（规格多样，如 1x10x6 或 1x20）。
- **条码识别**：箱体与内包装通常有不同条码。

## 2. 数据库模型修改 (Database Schema)

### 2.1 商品表 (Product)
- **新增字段**：
  - `units_per_box` (Integer): 每箱包含的中包装数量（如：10盒/箱）。
  - `pieces_per_unit` (Integer): 每个中包装包含的最小单位数量（如：6个/盒）。
  - `box_cost_price` (Float): 整箱进货成本价。
- **废弃/调整字段**：
  - `spec`: 由字符串改为纯描述性文本。
  - `base_cost_price`: 建议改为 `box_cost_price`。

### 2.2 条码关联表 (ProductBarcode) - [新增]
用于处理一物多码及条码对应的包装层级。
- `id` (UUID)
- `product_id` (ForeignKey)
- `barcode` (String, Unique): 扫描到的条码。
- `level` (Enum): 层级标识。可选值：`BOX` (箱), `UNIT` (中包装), `PIECE` (最小单位)。

### 2.3 库存表 (Inventory)
- **字段逻辑变更**：
  - `current_stock`: 含义变更为“最小物理单位的总数”。
  - **示例**：规格为 1x10x6 的商品，若有 1箱，则 `current_stock` 记录为 60。

---

## 3. 核心业务逻辑实现 (Business Logic)

### 3.1 扫码识别逻辑 (Barcode Parsing)
后端接收条码后，应执行以下换算倍率逻辑：
1. 根据 `barcode` 查询 `ProductBarcode` 表。
2. 获取 `level`：
   - 若为 `BOX`：倍率 $M = units\_per\_box \times pieces\_per\_unit$
   - 若为 `UNIT`：倍率 $M = pieces\_per\_unit$
   - 若为 `PIECE`：倍率 $M = 1$
3. 返回商品信息及对应倍率给前端。

### 3.2 价格计算公式
- **中包装成本** = `box_cost_price` / `units_per_box`
- **最小单位成本** = `box_cost_price` / (`units_per_box` * `pieces_per_unit`)
- **建议零售价** = `单位成本` * `retail_multiplier` (结果需进行四舍五入取整)

### 3.3 库存展示逻辑 (Human-Readable Stock)
前端或接口返回时，需将 `current_stock` (总数 $S$) 转换为：
- 箱数 = $S // (units\_per\_box \times pieces\_per\_unit)$
- 零散中包装 = $(S \% (units\_per\_box \times pieces\_per\_unit)) // pieces\_per\_unit$
- 零散最小单位 = $S \% pieces\_per\_unit$

---

## 4. 后端接口调整建议

### 4.1 商品编辑接口
- 允许用户设置 `units_per_box` 和 `pieces_per_unit`。
- 如果只有两级（箱 -> 个），则设置 `units_per_box = 1`。

### 4.2 销售出库接口
- 提交参数：`product_id`, `quantity` (扫码倍率后的总数), `actual_price`。
- 逻辑：直接从 `Inventory.current_stock` 减去 `quantity`。

### 4.3 进货入库接口
- 提交参数：`box_count` (进货箱数), `box_cost_price`。
- 逻辑：`current_stock += box_count * units_per_box * pieces_per_unit`。
- 同步更新商品的最新 `box_cost_price`。