# 数据库表说明（基于后端 ORM 模型）

本文档根据 `backend/app/models/entities.py` 整理，说明各表的业务含义与主要字段用途。

## system_config
- **用途**：系统级配置项存储（如全局定价系数）。
- **字段**：`key`（主键、配置键），`value`（配置值）。

## daily_receipt
- **用途**：每日真实入账记录，用于看板与对账。
- **字段**：`date`（主键、业务日期），`amount`（当日入账金额），`created_at`（记录创建时间）。

## category
- **用途**：商品分类（包含商家主分类与自定义分类）。
- **字段**：`name`（分类名），`retail_multiplier`（分类定价系数），`retail_multiplier_min/max`（定价系数范围），`is_custom`（是否自定义分类），`updated_at`（更新时间）。
- **关联**：`product.category_id` 为商家主分类；`product_category` 维护自定义多选分类。

## product
- **用途**：商品主表。
- **字段**：
  - `name`（商品名），`spec`（规格/描述）
  - `units_per_box`（每箱包含多少“单位”），`pieces_per_unit`（每单位包含多少“最小件”）
  - `box_cost_price`（整箱成本），`base_cost_price`（最小单位成本）
  - `fixed_retail_price`（固定零售价，优先级最高）
  - `retail_multiplier`（商品级定价系数）
  - `pack_price_ref`（外部参考价/组合包参考价）
  - `img_url`/`video_url`/`effect_url`（素材链接）
  - `barcode`（主条码）
  - `category_id`（商家主分类）
  - `updated_at`（更新时间）
- **关联**：`product_alias`（别名）、`product_barcode`（多条码）、`inventory`、`inventory_log`、`purchase_item`、`sales_item`。

## product_category
- **用途**：商品与自定义分类的多对多关联表。
- **字段**：`product_id`、`category_id`（联合主键）。

## product_alias
- **用途**：商品别名，用于搜索/匹配。
- **字段**：`product_id`（关联商品），`alias_name`（别名）。

## product_barcode
- **用途**：商品条码表，支持一物多码与包装层级。
- **字段**：`product_id`（关联商品），`barcode`（条码，唯一），`level`（包装层级：BOX/UNIT/PIECE）。

## user_account
- **用途**：用户账户（老板/店员/普通用户），用于登录与权限。
- **字段**：`username`（用户名），`role`（角色），`openid`（微信 openid，唯一）。

## warehouse
- **用途**：仓库信息，目前为单仓默认值。
- **字段**：`id`（主键，默认 `default`），`name`（仓库名）。

## inventory
- **用途**：库存当前量（按商品+仓库维度）。
- **字段**：`product_id`、`warehouse_id`（联合主键），`current_stock`（最小单位总数），`loose_units`（历史兼容字段），`updated_at`（更新时间）。
- **备注**：库存以最小单位计数，前端可按箱/单位/件换算展示。

## inventory_log
- **用途**：库存变动日志。
- **字段**：`product_id`、`warehouse_id`、`change_qty`（变动数量）、`type`（变动类型）、`ref_type/ref_id`（关联来源）、`change_date`（变动时间）。

## purchase_order
- **用途**：采购单头信息。
- **字段**：`status`（状态，默认“待到货”），`supplier`（供应商），`expected_date`（预计到货），`remark`（备注），`created_by`（创建人）。

## purchase_item
- **用途**：采购单行项目。
- **字段**：`purchase_order_id`（所属采购单），`product_id`，`quantity`（采购数量），`expected_cost`（预计成本），`received_qty`/`received_units`（到货数量），`actual_cost`（实际成本）。

## inventory_import_job
- **用途**：库存/商品导入任务记录（预留/扩展用）。
- **字段**：`file_name`、`status`（pending/processing/success/failed）、`total_rows`、`success_rows`、`error_rows`、`error_report_url`、`created_by`。

## sales_order
- **用途**：销售单头信息。
- **字段**：`order_date`（下单时间），`total_actual_amount`（实收金额），`created_by`（创建人）。

## sales_item
- **用途**：销售单行项目，保存销售时快照。
- **字段**：`order_id`、`product_id`、`quantity`、`snapshot_cost`（销售时成本快照）、`snapshot_standard_price`（销售时标准价快照）、`actual_sale_price`（成交单价）、`created_at`。
- **备注**：快照字段用于历史报表，后续改价不影响历史数据。

## misc_cost
- **用途**：杂项费用记录（如运费、耗材等）。
- **字段**：`item`（费用项），`quantity`（数量/次数），`amount`（金额），`created_at`，`created_by`。

## shareholder
- **用途**：股东信息。
- **字段**：`name`、`share_ratio`（分红比例）、`role`（角色/身份）、`note`、`is_active`、`created_at`、`updated_at`。

## shareholder_capital
- **用途**：股东出资记录。
- **字段**：`shareholder_id`（关联股东），`amount`（出资金额），`memo`，`biz_date`（业务日期），`created_at`。

## shareholder_distribution
- **用途**：股东分红发放记录。
- **字段**：`shareholder_id`（关联股东），`amount`（分红金额），`memo`，`biz_date`（业务日期），`created_at`。
