from datetime import datetime
from typing import List, Tuple

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import schemas
from app.models.entities import (
    Category,
    Inventory,
    InventoryLog,
    Product,
    PurchaseItem,
    PurchaseOrder,
    SalesItem,
    SalesOrder,
    SystemConfig,
    User,
    Warehouse,
)
DEFAULT_GLOBAL_MULTIPLIER = 1.5


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
    if product.fixed_retail_price is not None:
        return schemas.PriceCalcResponse(price=product.fixed_retail_price, basis="例外价")

    if product.category_id:
        stmt = sa.select(Category).where(Category.id == product.category_id)
        category = (await session.execute(stmt)).scalars().first()
        if category and category.retail_multiplier:
            return schemas.PriceCalcResponse(price=round2(product.base_cost_price * category.retail_multiplier), basis="分类系数")

    multiplier = await get_global_multiplier(session)
    return schemas.PriceCalcResponse(price=round2(product.base_cost_price * multiplier), basis="全局系数")


async def create_product(session: AsyncSession, payload: schemas.Product) -> Product:
    product = Product(
        id=payload.id or None,
        name=payload.name,
        category_id=payload.category_id,
        spec=payload.spec,
        base_cost_price=payload.base_cost_price,
        fixed_retail_price=payload.fixed_retail_price,
        img_url=payload.img_url,
    )
    session.add(product)
    await session.flush()
    return product


async def update_product(session: AsyncSession, product_id: str, payload: schemas.Product) -> Product:
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    product.name = payload.name or product.name
    product.category_id = payload.category_id
    product.spec = payload.spec
    product.base_cost_price = payload.base_cost_price
    product.fixed_retail_price = payload.fixed_retail_price
    product.img_url = payload.img_url
    await session.flush()
    return product


async def product_with_category(session: AsyncSession, product_id: str) -> schemas.Product:
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    category_name = None
    if product.category_id:
        category = await session.get(Category, product.category_id)
        category_name = category.name if category else None
    return schemas.Product(
        id=product.id,
        name=product.name,
        category_id=product.category_id,
        category_name=category_name,
        spec=product.spec,
        base_cost_price=product.base_cost_price,
        fixed_retail_price=product.fixed_retail_price,
        img_url=product.img_url,
    )


async def upsert_category(session: AsyncSession, category_id: str, payload: schemas.Category) -> Category:
    stmt = sa.select(Category).where(Category.id == category_id)
    existing = (await session.execute(stmt)).scalars().first()
    if existing:
        existing.name = payload.name
        existing.retail_multiplier = payload.retail_multiplier
        await session.flush()
        return existing
    category = Category(id=payload.id or category_id, name=payload.name, retail_multiplier=payload.retail_multiplier)
    session.add(category)
    await session.flush()
    return category


async def get_product_with_lock(session: AsyncSession, product_id: str) -> Product | None:
    stmt = sa.select(Product).where(Product.id == product_id).with_for_update()
    return (await session.execute(stmt)).scalars().first()


async def get_inventory_record(session: AsyncSession, product_id: str, warehouse_id: str = "default") -> Inventory:
    stmt = (
        sa.select(Inventory)
        .where(Inventory.product_id == product_id, Inventory.warehouse_id == warehouse_id)
        .with_for_update()
    )
    inv = (await session.execute(stmt)).scalars().first()
    if inv:
        return inv
    inv = Inventory(product_id=product_id, warehouse_id=warehouse_id, current_stock=0)
    session.add(inv)
    await session.flush()
    return inv


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


async def create_sales_order(session: AsyncSession, payloads: List[schemas.SalesItemPayload], username: str) -> SalesOrder:
    items: list[SalesItem] = []
    total_actual = 0.0
    for payload in payloads:
        product = await get_product_with_lock(session, payload.product_id)
        if not product:
            raise ValueError(f"product {payload.product_id} not found")
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
        inv = await get_inventory_record(session, payload.product_id)
        inv.current_stock = max(0, inv.current_stock - payload.quantity)
        await log_inventory(session, payload.product_id, -payload.quantity, "sales", ref_id="auto")

    order = SalesOrder(total_actual_amount=total_actual, created_by=username)
    order.items = items
    session.add(order)
    await session.flush()
    return order


async def adjust_inventory(session: AsyncSession, req: schemas.InventoryAdjustRequest, username: str) -> Inventory:
    inv = await get_inventory_record(session, req.product_id)
    inv.current_stock += req.delta
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
        inv = await get_inventory_record(session, update.product_id)
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


async def dashboard_realtime(session: AsyncSession) -> Tuple[float, float, int, float]:
    stmt = sa.select(SalesItem)
    items = (await session.execute(stmt)).scalars().all()
    orders = len(items)
    actual = sum(item.actual_sale_price * item.quantity for item in items)
    cost = sum(item.snapshot_cost * item.quantity for item in items)
    gross_profit = actual - cost
    avg_ticket = actual / orders if orders else 0
    return actual, gross_profit, orders, avg_ticket


async def dashboard_inventory_value(session: AsyncSession) -> Tuple[float, float]:
    cost_total = 0.0
    retail_total = 0.0
    inv_rows = (await session.execute(sa.select(Inventory))).scalars().all()
    for inv in inv_rows:
        product = await session.get(Product, inv.product_id)
        if not product:
            continue
        price_info = await calculate_price_for_product(session, product)
        cost_total += product.base_cost_price * inv.current_stock
        retail_total += price_info.price * inv.current_stock
    return cost_total, retail_total


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


def round2(value: float) -> float:
    return round(value + 1e-9, 2)


async def list_products_with_inventory(
    session: AsyncSession, offset: int = 0, limit: int = 50, category_id: str | None = None
) -> tuple[list[schemas.ProductListItem], int]:
    where_clause = []
    if category_id:
        where_clause.append(Product.category_id == category_id)

    count_stmt = sa.select(sa.func.count()).select_from(Product)
    if where_clause:
        count_stmt = count_stmt.where(*where_clause)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = sa.select(Product)
    if where_clause:
        stmt = stmt.where(*where_clause)
    stmt = stmt.offset(offset).limit(limit)
    products = (await session.execute(stmt)).scalars().all()
    inventory_map: dict[str, int] = {}
    for inv in (await session.execute(sa.select(Inventory))).scalars().all():
        inventory_map[inv.product_id] = inventory_map.get(inv.product_id, 0) + inv.current_stock
    result: list[schemas.ProductListItem] = []
    for product in products:
        price_info = await calculate_price_for_product(session, product)
        stock = inventory_map.get(product.id, 0)
        retail_total = price_info.price * stock
        cost_total = product.base_cost_price * stock
        category_name = None
        if product.category_id:
            category = await session.get(Category, product.category_id)
            category_name = category.name if category else None
        result.append(
            schemas.ProductListItem(
                id=product.id,
                name=product.name,
                spec=product.spec,
                category_name=category_name,
                base_cost_price=product.base_cost_price,
                standard_price=price_info.price,
                price_basis=price_info.basis,
                stock=stock,
                retail_total=round2(retail_total),
                cost_total=round2(cost_total),
            )
        )
    return result, total


async def inventory_overview(session: AsyncSession) -> list[schemas.InventoryOverviewItem]:
    inv_rows = (await session.execute(sa.select(Inventory))).scalars().all()
    items: list[schemas.InventoryOverviewItem] = []
    for inv in inv_rows:
        product = await session.get(Product, inv.product_id)
        if not product:
            continue
        price_info = await calculate_price_for_product(session, product)
        category_name = None
        if product.category_id:
            category = await session.get(Category, product.category_id)
            category_name = category.name if category else None
        retail_total = price_info.price * inv.current_stock
        cost_total = product.base_cost_price * inv.current_stock
        items.append(
            schemas.InventoryOverviewItem(
                product_id=product.id,
                name=product.name,
                spec=product.spec,
                category_name=category_name,
                stock=inv.current_stock,
                standard_price=price_info.price,
                price_basis=price_info.basis,
                retail_total=round2(retail_total),
                base_cost_price=product.base_cost_price,
                cost_total=round2(cost_total),
            )
        )
    return items
