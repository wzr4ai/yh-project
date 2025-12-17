import re
import asyncio
from datetime import datetime
from typing import Any, List, Tuple

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import schemas
from app.models.entities import (
    Category,
    DailyReceipt,
    Inventory,
    InventoryLog,
    MiscCost,
    Product,
    ProductAlias,
    ProductCategory,
    PurchaseItem,
    PurchaseOrder,
    SalesItem,
    SalesOrder,
    SystemConfig,
    User,
    Warehouse,
)
DEFAULT_GLOBAL_MULTIPLIER = 1.5


def normalize_spec(spec: str | None) -> str | None:
    if not spec:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(spec))
    if match:
        return match.group(1)
    return None


def compute_version_from_models(models: list[Any]) -> str:
    max_ts = None
    for m in models:
        ts = getattr(m, "updated_at", None)
        if ts:
            max_ts = max(max_ts or ts, ts)
    from datetime import datetime

    return (max_ts or datetime.utcnow()).isoformat()


def parse_spec_qty(spec: str | None) -> float:
    clean = normalize_spec(spec)
    if not clean:
        return 1.0
    try:
        val = float(clean)
        return val if val > 0 else 1.0
    except Exception:
        return 1.0


async def replace_product_categories(session: AsyncSession, product_id: str, category_ids: list[str]):
    await session.execute(sa.delete(ProductCategory).where(ProductCategory.product_id == product_id))
    unique_ids = [cid for cid in dict.fromkeys(category_ids) if cid]
    if unique_ids:
        session.add_all([ProductCategory(product_id=product_id, category_id=cid) for cid in unique_ids])
    await session.flush()


def extract_category_ids(categories: list[Any]) -> list[str]:
    ids: list[str] = []
    for c in categories:
        if isinstance(c, dict) and "id" in c:
            ids.append(c["id"])
        elif hasattr(c, "id"):
            ids.append(getattr(c, "id"))
        elif isinstance(c, str):
            ids.append(c)
    return ids


async def record_alias_if_new(session: AsyncSession, product: Product, raw_name: str | None):
    if not raw_name:
        return
    raw_clean = raw_name.strip()
    if not raw_clean:
        return
    raw_lower = raw_clean.lower()
    if product.name and product.name.lower() == raw_lower:
        return
    name_exists = (
        await session.execute(sa.select(Product.id).where(sa.func.lower(Product.name) == raw_lower))
    ).scalar_one_or_none()
    if name_exists:
        return
    alias_exists = (
        await session.execute(sa.select(ProductAlias.id).where(sa.func.lower(ProductAlias.alias_name) == raw_lower))
    ).scalar_one_or_none()
    if alias_exists:
        return
    session.add(ProductAlias(product_id=product.id, alias_name=raw_clean))
    await session.flush()


async def ensure_defaults(session: AsyncSession):
    await ensure_default_config(session)
    await ensure_default_warehouse(session)
    await session.commit()


async def ensure_default_config(session: AsyncSession):
    stmt = sa.select(SystemConfig).where(SystemConfig.key == "global_multiplier")
    result = await session.execute(stmt)
    cfg = result.scalars().first()
    if not cfg:
        session.add(SystemConfig(key="global_multiplier", value=str(DEFAULT_GLOBAL_MULTIPLIER)))


async def ensure_default_warehouse(session: AsyncSession):
    stmt = sa.select(Warehouse).where(Warehouse.id == "default")
    result = await session.execute(stmt)
    wh = result.scalars().first()
    if not wh:
        session.add(Warehouse(id="default", name="默认仓"))


async def get_global_multiplier(session: AsyncSession) -> float:
    stmt = sa.select(SystemConfig).where(SystemConfig.key == "global_multiplier")
    cfg = (await session.execute(stmt)).scalars().first()
    if not cfg:
        await ensure_default_config(session)
        await session.commit()
        return DEFAULT_GLOBAL_MULTIPLIER
    try:
        return float(cfg.value)
    except (TypeError, ValueError):
        return DEFAULT_GLOBAL_MULTIPLIER


async def get_or_create_user_by_openid(session: AsyncSession, openid: str, nickname: str | None = None) -> User:
    stmt = sa.select(User).where(User.openid == openid)
    user = (await session.execute(stmt)).scalars().first()
    if user:
        return user
    user = User(username=nickname or "店员", role="clerk", openid=openid)
    session.add(user)
    await session.flush()
    return user


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    stmt = sa.select(User).where(User.id == user_id)
    return (await session.execute(stmt)).scalars().first()


async def calculate_price_for_product(session: AsyncSession, product: Product) -> schemas.PriceCalcResponse:
    if product.fixed_retail_price is not None and product.fixed_retail_price > 0:
        return schemas.PriceCalcResponse(price=product.fixed_retail_price, basis="例外价")

    if product.retail_multiplier:
        return schemas.PriceCalcResponse(price=round2(product.base_cost_price * product.retail_multiplier), basis="分类系数")

    multipliers: list[float] = []
    # 多分类
    stmt_pc = sa.select(ProductCategory.category_id).where(ProductCategory.product_id == product.id)
    pc_ids = [row[0] for row in (await session.execute(stmt_pc)).all()]
    if pc_ids:
        stmt = sa.select(Category).where(Category.id.in_(pc_ids))
        categories = (await session.execute(stmt)).scalars().all()
        multipliers = [c.retail_multiplier for c in categories if c.retail_multiplier]

    if product.category_id and not multipliers:
        category = await session.get(Category, product.category_id)
        if category and category.retail_multiplier:
            multipliers.append(category.retail_multiplier)

    if multipliers:
        chosen = max(multipliers)
        # 回写商品系数，便于下次直接使用
        product.retail_multiplier = chosen
        await session.flush()
        return schemas.PriceCalcResponse(price=round2(product.base_cost_price * chosen), basis="分类系数")

    multiplier = await get_global_multiplier(session)
    return schemas.PriceCalcResponse(price=round2(product.base_cost_price * multiplier), basis="全局系数")


async def create_product(session: AsyncSession, payload: schemas.Product) -> Product:
    fixed_price = payload.fixed_retail_price if (payload.fixed_retail_price or 0) > 0 else None
    spec_value = normalize_spec(payload.spec)
    product = Product(
        id=payload.id or None,
        name=payload.name,
        category_id=payload.category_id,
        spec=spec_value,
        base_cost_price=payload.base_cost_price,
        fixed_retail_price=fixed_price,
        retail_multiplier=payload.retail_multiplier,
        pack_price_ref=payload.pack_price_ref,
        img_url=payload.img_url,
        effect_url=payload.effect_url,
    )
    session.add(product)
    await session.flush()
    if payload.categories:
        category_ids = extract_category_ids(payload.categories)
        await replace_product_categories(session, product.id, category_ids)
    await session.flush()
    product.updated_at = datetime.utcnow()
    return product


async def update_product(session: AsyncSession, product_id: str, payload: schemas.Product) -> Product:
    fixed_price = payload.fixed_retail_price if (payload.fixed_retail_price or 0) > 0 else None
    spec_value = normalize_spec(payload.spec)
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    product.name = payload.name or product.name
    product.category_id = payload.category_id
    product.spec = spec_value
    product.base_cost_price = payload.base_cost_price
    product.fixed_retail_price = fixed_price
    product.retail_multiplier = payload.retail_multiplier
    product.pack_price_ref = payload.pack_price_ref
    product.img_url = payload.img_url
    product.effect_url = payload.effect_url
    product.updated_at = datetime.utcnow()
    if payload.categories is not None:
        category_ids = extract_category_ids(payload.categories)
        await replace_product_categories(session, product_id, category_ids)
    await session.flush()
    return product


async def delete_product(session: AsyncSession, product_id: str):
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    await session.execute(sa.delete(ProductCategory).where(ProductCategory.product_id == product_id))
    await session.execute(sa.delete(Inventory).where(Inventory.product_id == product_id))
    await session.delete(product)
    await session.flush()


async def product_with_category(session: AsyncSession, product_id: str) -> schemas.Product:
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    clean_spec = normalize_spec(product.spec)
    category_name = None
    categories: list[schemas.Category] = []
    if product.category_id:
        category = await session.get(Category, product.category_id)
        category_name = category.name if category else None
        if category:
            categories.append(
                schemas.Category(
                    id=category.id,
                    name=category.name,
                    retail_multiplier=category.retail_multiplier,
                    is_custom=category.is_custom,
                )
            )
    stmt = sa.select(Category).join(ProductCategory, Category.id == ProductCategory.category_id).where(
        ProductCategory.product_id == product.id
    )
    extra = (await session.execute(stmt)).scalars().all()
    for c in extra:
        if not any(x.id == c.id for x in categories):
            categories.append(schemas.Category(id=c.id, name=c.name, retail_multiplier=c.retail_multiplier, is_custom=c.is_custom))

    return schemas.Product(
        id=product.id,
        name=product.name,
        category_id=product.category_id,
        category_name=category_name,
        categories=categories,
        spec=clean_spec,
        base_cost_price=product.base_cost_price,
        fixed_retail_price=product.fixed_retail_price,
        retail_multiplier=product.retail_multiplier,
        pack_price_ref=product.pack_price_ref,
        img_url=product.img_url,
        effect_url=product.effect_url,
    )


async def create_category(session: AsyncSession, payload: schemas.Category) -> Category:
    category = Category(
        id=payload.id or None,
        name=payload.name,
        retail_multiplier=payload.retail_multiplier,
        is_custom=payload.is_custom if payload.is_custom is not None else True,
    )
    session.add(category)
    await session.flush()
    return category


async def delete_category(session: AsyncSession, category_id: str, force: bool = False) -> int:
    category = await session.get(Category, category_id)
    if not category:
        raise ValueError("category not found")
    # count products
    count_stmt = sa.select(sa.func.count()).select_from(Product).where(Product.category_id == category_id)
    count = (await session.execute(count_stmt)).scalar_one()
    if count > 0 and not force:
        raise ValueError(f"category not empty:{count}")
    if count > 0:
        await session.execute(sa.update(Product).where(Product.category_id == category_id).values(category_id=None))
    # clear many-to-many mappings
    await session.execute(sa.delete(ProductCategory).where(ProductCategory.category_id == category_id))
    await session.delete(category)
    await session.flush()
    return count


async def upsert_category(session: AsyncSession, category_id: str, payload: schemas.Category) -> Category:
    stmt = sa.select(Category).where(Category.id == category_id)
    existing = (await session.execute(stmt)).scalars().first()
    if existing:
        existing.name = payload.name
        existing.retail_multiplier = payload.retail_multiplier
        if payload.is_custom is not None:
            existing.is_custom = payload.is_custom
        await session.flush()
        return existing
    category = Category(
        id=payload.id or category_id,
        name=payload.name,
        retail_multiplier=payload.retail_multiplier,
        is_custom=payload.is_custom if payload.is_custom is not None else True,
    )
    session.add(category)
    await session.flush()
    return category


async def get_product_with_lock(session: AsyncSession, product_id: str) -> Product | None:
    stmt = sa.select(Product).where(Product.id == product_id).with_for_update()
    return (await session.execute(stmt)).scalars().first()


async def get_inventory_record(
    session: AsyncSession, product_id: str, warehouse_id: str = "default", create_if_missing: bool = True
) -> Inventory | None:
    stmt = (
        sa.select(Inventory)
        .where(Inventory.product_id == product_id, Inventory.warehouse_id == warehouse_id)
        .with_for_update()
    )
    inv = (await session.execute(stmt)).scalars().first()
    if inv:
        return inv
    if not create_if_missing:
        return None
    inv = Inventory(product_id=product_id, warehouse_id=warehouse_id, current_stock=0, loose_units=0)
    session.add(inv)
    await session.flush()
    return inv


def apply_unit_delta(inv: Inventory, product: Product, delta_units: int) -> None:
    spec_qty = parse_spec_qty(product.spec)
    if spec_qty <= 0:
        spec_qty = 1
    total_units = inv.current_stock * spec_qty + (inv.loose_units or 0)
    total_units += delta_units
    if total_units < 0:
        total_units = 0
    if spec_qty == 1:
        inv.current_stock = int(total_units)
        inv.loose_units = 0
    else:
        inv.current_stock = int(total_units // spec_qty)
        inv.loose_units = int(total_units % spec_qty)
    inv.updated_at = datetime.utcnow()


async def log_inventory(session: AsyncSession, product_id: str, qty: int, ref_type: str, ref_id: str, warehouse_id: str = "default"):
    log = InventoryLog(
        product_id=product_id,
        warehouse_id=warehouse_id,
        change_qty=qty,
        type="auto",
        ref_type=ref_type,
        ref_id=ref_id,
    )
    session.add(log)
    await session.flush()


async def create_sales_order(
    session: AsyncSession, payloads: List[schemas.SalesItemPayload | schemas.OrderConfirmItem], username: str
) -> SalesOrder:
    items: list[SalesItem] = []
    total_actual = 0.0
    for payload in payloads:
        product = await get_product_with_lock(session, payload.product_id)
        if not product:
            raise ValueError(f"product {payload.product_id} not found")
        await record_alias_if_new(session, product, getattr(payload, "raw_name", None))
        price_info = await calculate_price_for_product(session, product)
        total_actual += payload.actual_price * payload.quantity
        sales_item = SalesItem(
            product_id=payload.product_id,
            quantity=payload.quantity,
            snapshot_cost=product.base_cost_price,
            snapshot_standard_price=price_info.price,
            actual_sale_price=payload.actual_price,
        )
        items.append(sales_item)

        # deduct inventory
        inv = await get_inventory_record(session, payload.product_id, create_if_missing=True)
        apply_unit_delta(inv, product, -payload.quantity)
        await log_inventory(session, payload.product_id, -payload.quantity, "sales", ref_id="auto")

    order = SalesOrder(total_actual_amount=total_actual, created_by=username)
    order.items = items
    session.add(order)
    await session.flush()
    return order


async def adjust_inventory(session: AsyncSession, req: schemas.InventoryAdjustRequest, username: str) -> Inventory:
    product = await session.get(Product, req.product_id)
    if not product:
        raise ValueError("product not found")
    inv = await get_inventory_record(session, req.product_id, create_if_missing=True)
    apply_unit_delta(inv, product, req.delta)
    await log_inventory(session, req.product_id, req.delta, "adjust", ref_id=username)
    return inv


async def receive_purchase(session: AsyncSession, po_id: str, items: List[schemas.PurchaseItem]) -> PurchaseOrder:
    stmt = (
        sa.select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
        .with_for_update()
    )
    order = (await session.execute(stmt)).scalars().first()
    if not order:
        raise ValueError("purchase order not found")

    item_map = {i.product_id: i for i in order.items}
    for update in items:
        target = item_map.get(update.product_id)
        if not target:
            continue
        previous_received = target.received_qty or 0
        target.received_qty = update.received_qty
        target.actual_cost = update.actual_cost or target.expected_cost
        inv = await get_inventory_record(session, update.product_id, create_if_missing=True)
        delta = max(0, update.received_qty - previous_received)
        if delta:
            inv.current_stock += delta
            await log_inventory(session, update.product_id, delta, "purchase", ref_id=order.id)

    if all(i.received_qty >= i.quantity for i in order.items):
        order.status = "完成"
    elif any(i.received_qty > 0 for i in order.items):
        order.status = "部分到货"
    else:
        order.status = "待到货"
    await session.flush()
    return order


async def create_purchase_order(session: AsyncSession, po: schemas.PurchaseOrder) -> PurchaseOrder:
    order = PurchaseOrder(
        id=po.id or None,
        status=po.status or "待到货",
        supplier=po.supplier,
        expected_date=po.expected_date,
        remark=po.remark,
        created_by=po.created_by,
    )
    order.items = [
        PurchaseItem(
          product_id=item.product_id,
          quantity=item.quantity,
          expected_cost=item.expected_cost,
          received_qty=item.received_qty,
          actual_cost=item.actual_cost,
        )
        for item in po.items
    ]
    session.add(order)
    await session.flush()
    return order


async def dashboard_realtime(session: AsyncSession) -> Tuple[float, float, float, float, float, int, float, float | None]:
    from datetime import datetime, timezone

    today = datetime.utcnow().date()
    stmt = sa.select(SalesItem).where(sa.func.date(SalesItem.created_at) == today)
    items = (await session.execute(stmt)).scalars().all()
    orders = len(items)
    actual = sum(item.actual_sale_price * item.quantity for item in items)
    expected = sum(item.snapshot_standard_price * item.quantity for item in items)
    cost = sum(item.snapshot_cost * item.quantity for item in items)
    gross_profit = actual - cost
    avg_ticket = actual / orders if orders else 0
    receipt_diff = actual - expected
    diff_rate = (receipt_diff / expected * 100) if expected else 0
    manual = await get_manual_receipt(session)
    actual_display = manual if manual is not None else actual
    receipt_diff_display = actual_display - expected
    diff_rate_display = (receipt_diff_display / expected * 100) if expected else 0
    return actual_display, expected, receipt_diff_display, diff_rate_display, gross_profit, orders, avg_ticket, manual


async def get_manual_receipt(session: AsyncSession) -> float | None:
    today = datetime.utcnow().date()
    rec = (await session.execute(sa.select(DailyReceipt).where(DailyReceipt.date == today))).scalars().first()
    if rec:
        return rec.amount
    return None


async def set_manual_receipt(session: AsyncSession, value: float):
    today = datetime.utcnow().date()
    rec = (await session.execute(sa.select(DailyReceipt).where(DailyReceipt.date == today))).scalars().first()
    if rec:
        rec.amount = value
    else:
        session.add(DailyReceipt(date=today, amount=value))
    await session.flush()


async def dashboard_inventory_value(session: AsyncSession) -> Tuple[float, float, int, float]:
    cost_total = 0.0
    retail_total = 0.0
    sku_with_stock = set()
    total_boxes = 0.0
    inv_rows = (await session.execute(sa.select(Inventory))).scalars().all()
    for inv in inv_rows:
        product = await session.get(Product, inv.product_id)
        if not product:
            continue
        price_info = await calculate_price_for_product(session, product)
        spec_qty = parse_spec_qty(product.spec)
        total_units = inv.current_stock * spec_qty + (inv.loose_units or 0)
        if total_units > 0:
            sku_with_stock.add(product.id)
            total_boxes += total_units / spec_qty
        cost_total += product.base_cost_price * total_units
        retail_total += price_info.price * total_units
    return cost_total, retail_total, len(sku_with_stock), round2(total_boxes)


async def inventory_by_category(session: AsyncSession) -> list[dict]:
    # Only include custom categories (is_custom = true); additionally put uncategorized into a fallback bucket
    categories = (await session.execute(sa.select(Category).where(Category.is_custom.is_(True)))).scalars().all()
    cat_map = {c.id: c for c in categories}
    cat_data = {c.id: {"id": c.id, "name": c.name, "sku": 0, "boxes": 0.0, "cost": 0.0, "retail": 0.0} for c in categories}
    uncategorized_id = "__uncategorized__"
    cat_data[uncategorized_id] = {"id": uncategorized_id, "name": "未分组", "sku": 0, "boxes": 0.0, "cost": 0.0, "retail": 0.0}

    # map product -> custom categories via many-to-many
    if cat_map:
        pc_rows = (
            await session.execute(
                sa.select(ProductCategory.product_id, ProductCategory.category_id).where(
                    ProductCategory.category_id.in_(list(cat_map.keys()))
                )
            )
        ).all()
        product_to_custom: dict[str, set[str]] = {}
        for pid, cid in pc_rows:
            product_to_custom.setdefault(pid, set()).add(cid)
    else:
        product_to_custom = {}

    inv_rows = (await session.execute(sa.select(Inventory))).scalars().all()
    for inv in inv_rows:
        product = await session.get(Product, inv.product_id)
        if not product:
            continue
        custom_ids: set[str] = set()
        if product.category_id and product.category_id in cat_map:
            custom_ids.add(product.category_id)
        if product.id in product_to_custom:
            custom_ids.update(product_to_custom[product.id])
        # fallback bucket if no custom category matched
        if not custom_ids:
            custom_ids.add(uncategorized_id)

        price_info = await calculate_price_for_product(session, product)
        spec_qty = parse_spec_qty(product.spec)
        total_units = inv.current_stock * spec_qty + (inv.loose_units or 0)
        if total_units <= 0:
            continue
        for cid in custom_ids:
            data = cat_data.setdefault(
                cid,
                {"id": cid, "name": cat_map.get(cid).name if cid in cat_map else "未分组", "sku": 0, "boxes": 0.0, "cost": 0.0, "retail": 0.0},
            )
            data["sku"] += 1
            data["boxes"] += total_units / spec_qty
            data["cost"] += product.base_cost_price * total_units
            data["retail"] += price_info.price * total_units

    # round numbers
    for d in cat_data.values():
        d["boxes"] = round2(d["boxes"])
        d["cost"] = round2(d["cost"])
        d["retail"] = round2(d["retail"])
    # sort by cost desc
    return sorted(cat_data.values(), key=lambda x: x["cost"], reverse=True)


async def create_misc_cost(session: AsyncSession, data: schemas.MiscCostCreate) -> MiscCost:
    record = MiscCost(
        item=data.item,
        quantity=data.quantity or 1,
        amount=data.amount,
        created_by=data.created_by,
    )
    session.add(record)
    await session.flush()
    return record


async def list_misc_costs(session: AsyncSession, limit: int = 100, offset: int = 0) -> list[MiscCost]:
    stmt = sa.select(MiscCost).order_by(MiscCost.created_at.desc()).offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_misc_cost(session: AsyncSession, misc_id: str, data: schemas.MiscCostUpdate) -> MiscCost:
    record = await session.get(MiscCost, misc_id)
    if not record:
        raise ValueError("misc cost not found")
    if data.item is not None:
        record.item = data.item
    if data.quantity is not None:
        record.quantity = data.quantity
    if data.amount is not None:
        record.amount = data.amount
    if data.created_by is not None:
        record.created_by = data.created_by
    await session.flush()
    return record


async def dashboard_performance(session: AsyncSession) -> schemas.PerformanceResponse:
    stmt = sa.select(SalesItem)
    items = (await session.execute(stmt)).scalars().all()
    expected = sum(item.snapshot_standard_price * item.quantity for item in items)
    actual = sum(item.actual_sale_price * item.quantity for item in items)
    diff = actual - expected
    rate = (diff / expected * 100) if expected else 0
    return schemas.PerformanceResponse(
        price_diff=round(diff, 2),
        price_diff_rate=round(rate, 2),
        expected_sales=round(expected, 2),
        actual_sales=round(actual, 2),
    )


async def total_receipts(session: AsyncSession) -> float:
    total = (await session.execute(sa.select(sa.func.coalesce(sa.func.sum(DailyReceipt.amount), 0)))).scalar_one()
    return float(total or 0)


def round2(value: float) -> float:
    return round(value + 1e-9, 2)


async def list_products_with_inventory(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 50,
    category_id: str | None = None,
    category_ids: list[str] | None = None,
    custom_category_ids: list[str] | None = None,
    merchant_category_ids: list[str] | None = None,
    keyword: str | None = None,
) -> tuple[list[schemas.ProductListItem], int, str]:
    where_clause = []
    custom_ids = set([c for c in (custom_category_ids or []) if c])
    if category_ids:
        custom_ids.update([c for c in category_ids if c])
    merchant_ids = set([c for c in (merchant_category_ids or []) if c])
    if category_id:
        merchant_ids.add(category_id)

    if merchant_ids:
        if "__uncategorized__" in merchant_ids:
            where_clause.append(
                sa.or_(Product.category_id.is_(None), Product.category_id.in_([m for m in merchant_ids if m != "__uncategorized__"]))
            )
        else:
            where_clause.append(Product.category_id.in_(list(merchant_ids)))
    if custom_ids:
        subq = sa.select(ProductCategory.product_id).where(ProductCategory.category_id.in_(list(custom_ids)))
        where_clause.append(Product.id.in_(subq))
    if keyword:
        like = f"%{keyword}%"
        where_clause.append(Product.name.ilike(like))

    count_stmt = sa.select(sa.func.count()).select_from(Product)
    if where_clause:
        count_stmt = count_stmt.where(*where_clause)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = sa.select(Product)
    if where_clause:
        stmt = stmt.where(*where_clause)
    stmt = stmt.offset(offset).limit(limit)
    products = (await session.execute(stmt)).scalars().all()
    if not products:
        return [], 0, "empty"

    product_ids = [p.id for p in products]

    # 并行获取库存与分类关联
    inv_stmt = (
        sa.select(Inventory.product_id, sa.func.sum(Inventory.current_stock), sa.func.sum(Inventory.loose_units))
        .where(Inventory.product_id.in_(product_ids))
        .group_by(Inventory.product_id)
    )
    pc_stmt = sa.select(ProductCategory.product_id, ProductCategory.category_id).where(
        ProductCategory.product_id.in_(product_ids)
    )
    inv_rows, pc_rows = await asyncio.gather(
        session.execute(inv_stmt),
        session.execute(pc_stmt),
    )

    inventory_map: dict[str, int] = {}
    for pid, box_qty, loose_qty in inv_rows.all():
        inventory_map[pid] = (int(box_qty or 0), int(loose_qty or 0))

    product_to_category_ids: dict[str, list[str]] = {}
    for pid, cid in pc_rows.all():
        product_to_category_ids.setdefault(pid, []).append(cid)

    # 收集需要的分类 ID
    category_ids_needed = set()
    for p in products:
        if p.category_id:
            category_ids_needed.add(p.category_id)
        for cid in product_to_category_ids.get(p.id, []):
            category_ids_needed.add(cid)
    category_map: dict[str, Category] = {}
    if category_ids_needed:
        cats = (await session.execute(sa.select(Category).where(Category.id.in_(category_ids_needed)))).scalars().all()
        category_map = {c.id: c for c in cats}

    result: list[schemas.ProductListItem] = []
    global_multiplier = await get_global_multiplier(session)
    max_ts = None
    for product in products:
        spec_clean = normalize_spec(product.spec)
        box_qty, loose_qty = inventory_map.get(product.id, (0, 0))
        total_units = box_qty * parse_spec_qty(product.spec) + loose_qty
        stock = total_units
        # 价格计算纯内存
        if product.fixed_retail_price is not None and product.fixed_retail_price > 0:
            price_val = product.fixed_retail_price
            basis = "例外价"
        elif product.retail_multiplier:
            price_val = round2(product.base_cost_price * product.retail_multiplier)
            basis = "分类系数"
        else:
            multipliers: list[float] = []
            if product.category_id:
                cat = category_map.get(product.category_id)
                if cat and cat.retail_multiplier:
                    multipliers.append(cat.retail_multiplier)
            for cid in product_to_category_ids.get(product.id, []):
                cat = category_map.get(cid)
                if cat and cat.retail_multiplier:
                    multipliers.append(cat.retail_multiplier)
            if multipliers:
                chosen = max(multipliers)
                price_val = round2(product.base_cost_price * chosen)
                basis = "分类系数"
            else:
                price_val = round2(product.base_cost_price * global_multiplier)
                basis = "全局系数"

        retail_total = price_val * total_units
        cost_total = product.base_cost_price * total_units
        category_name = None
        category_names: list[str] = []
        category_ids: list[str] = []
        if product.category_id and product.category_id in category_map:
            category = category_map[product.category_id]
            category_name = category.name
            category_names.append(category.name)
            category_ids.append(category.id)
        for cid in product_to_category_ids.get(product.id, []):
            cat = category_map.get(cid)
            if not cat:
                continue
            if cat.name not in category_names:
                category_names.append(cat.name)
            if cat.id not in category_ids:
                category_ids.append(cat.id)
        result.append(
            schemas.ProductListItem(
                id=product.id,
                name=product.name,
                spec=spec_clean,
                category_name="、".join([n for n in category_names if n]) or category_name,
                category_ids=category_ids,
                base_cost_price=product.base_cost_price,
                standard_price=price_val,
                price_basis=basis,
                stock=stock,
                retail_total=round2(retail_total),
                cost_total=round2(cost_total),
                effect_url=product.effect_url,
            )
        )
        if product.updated_at:
            max_ts = max(max_ts or product.updated_at, product.updated_at)
    version = (max_ts or datetime.utcnow()).isoformat()
    return result, total, version


async def list_pricing_overview(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    keyword: str | None = None,
) -> tuple[list[schemas.PricingOverviewItem], int, str]:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    where_clause = []
    if keyword:
        like = f"%{keyword}%"
        where_clause.append(Product.name.ilike(like))

    count_stmt = sa.select(sa.func.count()).select_from(Product)
    if where_clause:
        count_stmt = count_stmt.where(*where_clause)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = sa.select(Product)
    if where_clause:
        stmt = stmt.where(*where_clause)
    stmt = stmt.order_by(Product.name).offset(offset).limit(limit)
    products = (await session.execute(stmt)).scalars().all()
    if not products:
        return [], 0, "empty"

    product_ids = [p.id for p in products]

    pc_stmt = sa.select(ProductCategory.product_id, ProductCategory.category_id).where(
        ProductCategory.product_id.in_(product_ids)
    )
    pc_rows = await session.execute(pc_stmt)
    product_to_category_ids: dict[str, list[str]] = {}
    for pid, cid in pc_rows.all():
        product_to_category_ids.setdefault(pid, []).append(cid)

    category_ids_needed = set()
    for p in products:
        if p.category_id:
            category_ids_needed.add(p.category_id)
        for cid in product_to_category_ids.get(p.id, []):
            category_ids_needed.add(cid)
    category_map: dict[str, Category] = {}
    if category_ids_needed:
        cats = (await session.execute(sa.select(Category).where(Category.id.in_(category_ids_needed)))).scalars().all()
        category_map = {c.id: c for c in cats}

    global_multiplier = await get_global_multiplier(session)

    result: list[schemas.PricingOverviewItem] = []
    max_ts = None
    for product in products:
        spec_clean = normalize_spec(product.spec)
        if product.fixed_retail_price is not None and product.fixed_retail_price > 0:
            price_val = product.fixed_retail_price
            basis = "例外价"
        elif product.retail_multiplier:
            price_val = round2(product.base_cost_price * product.retail_multiplier)
            basis = "分类系数"
        else:
            multipliers: list[float] = []
            if product.category_id:
                cat = category_map.get(product.category_id)
                if cat and cat.retail_multiplier:
                    multipliers.append(cat.retail_multiplier)
            for cid in product_to_category_ids.get(product.id, []):
                cat = category_map.get(cid)
                if cat and cat.retail_multiplier:
                    multipliers.append(cat.retail_multiplier)
            if multipliers:
                chosen = max(multipliers)
                price_val = round2(product.base_cost_price * chosen)
                basis = "分类系数"
            else:
                price_val = round2(product.base_cost_price * global_multiplier)
                basis = "全局系数"

        category_names: list[str] = []
        if product.category_id and product.category_id in category_map:
            category_names.append(category_map[product.category_id].name)
        for cid in product_to_category_ids.get(product.id, []):
            cat = category_map.get(cid)
            if cat and cat.name not in category_names:
                category_names.append(cat.name)
        category_label = "、".join([n for n in category_names if n]) or None

        result.append(
            schemas.PricingOverviewItem(
                id=product.id,
                name=product.name,
                spec=spec_clean,
                category_name=category_label,
                standard_price=price_val,
                price_basis=basis,
                img_url=product.img_url,
                effect_url=product.effect_url,
            )
        )
        if product.updated_at:
            max_ts = max(max_ts or product.updated_at, product.updated_at)
    version = (max_ts or datetime.utcnow()).isoformat()
    return result, total, version


async def inventory_overview(session: AsyncSession, with_version: bool = False) -> tuple[list[schemas.InventoryOverviewItem], str] | list[schemas.InventoryOverviewItem]:
    inv_rows = (await session.execute(sa.select(Inventory))).scalars().all()
    items: list[schemas.InventoryOverviewItem] = []
    max_ts = None
    for inv in inv_rows:
        product = await session.get(Product, inv.product_id)
        if not product:
            continue
        spec_qty = parse_spec_qty(product.spec)
        box_price = product.base_cost_price * spec_qty
        if spec_qty == 1:
            box_count = inv.current_stock
            loose_count = 0
        else:
            box_count = inv.current_stock
            loose_count = inv.loose_units or 0
        category_name = None
        if product.category_id:
            category = await session.get(Category, product.category_id)
            category_name = category.name if category else None
        total_units = box_count * spec_qty + loose_count
        cost_total = product.base_cost_price * total_units
        items.append(
            schemas.InventoryOverviewItem(
                product_id=product.id,
                name=product.name,
                spec=product.spec,
                category_name=category_name,
                base_cost_price=product.base_cost_price,
                box_price=round2(box_price),
                box_count=box_count,
                loose_count=loose_count,
                cost_total=round2(cost_total),
            )
        )
        if inv.updated_at:
            max_ts = max(max_ts or inv.updated_at, inv.updated_at)
    version = (max_ts or datetime.utcnow()).isoformat()
    return (items, version) if with_version else items
