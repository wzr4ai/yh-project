from datetime import date, datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(sa.String(100), primary_key=True)
    value: Mapped[str] = mapped_column(sa.String(200), nullable=False)


class DailyReceipt(Base):
    __tablename__ = "daily_receipt"

    date: Mapped[date] = mapped_column(sa.Date, primary_key=True)
    amount: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "category"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    retail_multiplier: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    retail_multiplier_min: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    retail_multiplier_max: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    is_custom: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "product"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    category_id: Mapped[str | None] = mapped_column(sa.String(64), sa.ForeignKey("category.id"), nullable=True)
    spec: Mapped[str] = mapped_column(sa.String(200), nullable=True)
    base_cost_price: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0)
    fixed_retail_price: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    retail_multiplier: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    pack_price_ref: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    img_url: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    effect_url: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped[Category | None] = relationship(back_populates="products")
    aliases: Mapped[list["ProductAlias"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductCategory(Base):
    __tablename__ = "product_category"
    __table_args__ = (sa.PrimaryKeyConstraint("product_id", "category_id", name="product_category_pk"),)

    product_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("product.id"), nullable=False)
    category_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("category.id"), nullable=False)


class ProductAlias(Base):
    __tablename__ = "product_alias"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("product.id"), nullable=False)
    alias_name: Mapped[str] = mapped_column(sa.String(200), nullable=False)

    product: Mapped[Product] = relationship(back_populates="aliases")


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    username: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    role: Mapped[str] = mapped_column(sa.String(10), nullable=False, default="clerk")
    openid: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True)


class Warehouse(Base):
    __tablename__ = "warehouse"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default="default")
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False, default="默认仓")


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (sa.PrimaryKeyConstraint("product_id", "warehouse_id", name="inventory_pk"),)

    product_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("product.id"), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("warehouse.id"), nullable=False, default="default")
    current_stock: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    loose_units: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InventoryLog(Base):
    __tablename__ = "inventory_log"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("product.id"), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("warehouse.id"), nullable=False, default="default")
    change_date: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    change_qty: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)


class PurchaseOrder(Base):
    __tablename__ = "purchase_order"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="待到货")
    supplier: Mapped[str] = mapped_column(sa.String(200), nullable=True)
    expected_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    remark: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_by: Mapped[str] = mapped_column(sa.String(64), nullable=False)

    items: Mapped[list["PurchaseItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_item"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    purchase_order_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("purchase_order.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("product.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    expected_cost: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0)
    received_qty: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    actual_cost: Mapped[float | None] = mapped_column(sa.Float, nullable=True)

    order: Mapped[PurchaseOrder] = relationship(back_populates="items")


class InventoryImportJob(Base):
    __tablename__ = "inventory_import_job"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    file_name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pending")
    total_rows: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    success_rows: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    error_report_url: Mapped[str | None] = mapped_column(sa.String(300), nullable=True)
    created_by: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)


class SalesOrder(Base):
    __tablename__ = "sales_order"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    order_date: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    total_actual_amount: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(sa.String(64), nullable=False)

    items: Mapped[list["SalesItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class SalesItem(Base):
    __tablename__ = "sales_item"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    order_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("sales_order.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("product.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    snapshot_cost: Mapped[float] = mapped_column(sa.Float, nullable=False)
    snapshot_standard_price: Mapped[float] = mapped_column(sa.Float, nullable=False)
    actual_sale_price: Mapped[float] = mapped_column(sa.Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)

    order: Mapped[SalesOrder] = relationship(back_populates="items")


class MiscCost(Base):
    __tablename__ = "misc_cost"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True, default=gen_uuid)
    item: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(sa.Float, nullable=False, default=1)
    amount: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
