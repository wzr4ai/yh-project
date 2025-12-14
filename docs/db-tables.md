# 数据库表概览

本文档简要说明当前后端使用的主要表结构及用途，便于开发和排查。

## system_config
- **用途**：存储全局配置，如全局定价系数 `global_multiplier`。
- **关键字段**：`key`（主键）、`value`。
- **备注**：不再用于手动入账。

## category
- **用途**：商品分类，包含自定义与商家类别。
- **关键字段**：`name`、`retail_multiplier`（分类定价系数）、`is_custom`（是否自定义）。
- **关联**：`product.category_id`（主分类，商家类目），`product_category`（多对多自定义分类）。

## product
- **用途**：商品主表。
- **关键字段**：`name`、`spec`（规格，数字化）、`base_cost_price`、`fixed_retail_price`、`retail_multiplier`、`pack_price_ref`、`img_url`、`category_id`（商家主分类）。
- **关联**：`product_category`（自定义分类多选）、`inventory`、`inventory_log`、`sales_item`、`purchase_item`。

## product_category
- **用途**：商品与自定义分类的多对多关联。
- **主键**：`product_id` + `category_id`。

## product_alias
- **用途**：商品别名表。
- **关键字段**：`product_id`、`alias_name`。

## user_account
- **用途**：用户账户表（老板/店员、微信 openid）。
- **关键字段**：`username`、`role`、`openid`。

## warehouse
- **用途**：仓库信息，目前默认 `default` 单仓。
- **关键字段**：`name`。

## inventory
- **用途**：库存记录（按商品+仓库）。
- **主键**：`product_id` + `warehouse_id`。
- **关键字段**：`current_stock`（箱数或件数，按规格为箱）、`loose_units`（散件数量，规格为 1 时为 0）。

## inventory_log
- **用途**：库存变动日志。
- **关键字段**：`product_id`、`warehouse_id`、`change_qty`、`type`、`ref_type/ref_id`、`change_date`。

## purchase_order / purchase_item
- **用途**：采购单与行项目。
- **purchase_order 关键字段**：`status`、`supplier`、`expected_date`、`remark`、`created_by`。
- **purchase_item 关键字段**：`product_id`、`quantity`、`expected_cost`、`received_qty`、`actual_cost`。

## sales_order / sales_item
- **用途**：销售单与行项目。
- **sales_order 关键字段**：`order_date`、`total_actual_amount`、`created_by`。
- **sales_item 关键字段**：`product_id`、`quantity`、`snapshot_cost`、`snapshot_standard_price`、`actual_sale_price`、`created_at`。

## inventory_import_job
- **用途**：库存导入任务记录（占位，未来扩展）。
- **关键字段**：`file_name`、`status`、`total_rows`、`success_rows`、`error_rows`、`error_report_url`、`created_by`。

## daily_receipt
- **用途**：每日真实入账记录。
- **关键字段**：`date`（主键）、`amount`、`created_at`。
- **备注**：Dashboard “今日入账”与“总营业额”统计使用此表。
