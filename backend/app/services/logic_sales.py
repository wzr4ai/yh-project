import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import Inventory, Product, ProductAlias, SalesItem, SalesOrder
from app.services.logic_inventory import apply_unit_delta, get_inventory_record, log_inventory
from app.services.logic_pricing import calculate_price_for_product
from app.services.logic_utils import get_piece_cost_price


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


async def get_product_with_lock(session: AsyncSession, product_id: str) -> Product | None:
    stmt = sa.select(Product).where(Product.id == product_id).with_for_update()
    return (await session.execute(stmt)).scalars().first()


async def create_sales_order(
    session: AsyncSession, payloads: list[schemas.SalesItemPayload | schemas.OrderConfirmItem], username: str
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
            snapshot_cost=get_piece_cost_price(product),
            snapshot_standard_price=price_info.price,
            actual_sale_price=payload.actual_price,
        )
        items.append(sales_item)

        inv = await get_inventory_record(session, payload.product_id, create_if_missing=True)
        apply_unit_delta(inv, product, -payload.quantity)
        await log_inventory(session, payload.product_id, -payload.quantity, "sales", ref_id="auto")

    order = SalesOrder(total_actual_amount=total_actual, created_by=username)
    order.items = items
    session.add(order)
    await session.flush()
    return order


async def sales_rankings(
    session: AsyncSession,
    *,
    scope: str = "day",
    limit: int = 5,
) -> schemas.SalesRankingResponse:
    from datetime import datetime

    scope = (scope or "day").lower()
    if scope not in ("day", "all"):
        raise ValueError("invalid scope")
    limit = max(1, min(limit, 20))

    stmt = (
        sa.select(
            SalesItem.product_id,
            sa.func.sum(SalesItem.actual_sale_price * SalesItem.quantity).label("sales_amount"),
            sa.func.sum(SalesItem.snapshot_cost * SalesItem.quantity).label("cost_amount"),
        )
        .group_by(SalesItem.product_id)
    )

    if scope == "day":
        today = datetime.utcnow().date()
        stmt = stmt.where(sa.func.date(SalesItem.created_at) == today)

    rows = (await session.execute(stmt)).all()
    if not rows:
        return schemas.SalesRankingResponse(scope=scope, top_sales=[], top_margin=[])

    product_ids = [row[0] for row in rows if row[0]]
    products = (await session.execute(sa.select(Product).where(Product.id.in_(product_ids)))).scalars().all()
    product_map = {p.id: p for p in products}

    inv_stmt = (
        sa.select(Inventory.product_id, sa.func.sum(Inventory.current_stock))
        .where(Inventory.product_id.in_(product_ids))
        .group_by(Inventory.product_id)
    )
    inv_rows = (await session.execute(inv_stmt)).all()
    inventory_map = {pid: int(total or 0) for pid, total in inv_rows}

    items: list[schemas.SalesRankingItem] = []
    for pid, sales_amount, cost_amount in rows:
        sales_val = float(sales_amount or 0)
        cost_val = float(cost_amount or 0)
        margin = (sales_val - cost_val) / sales_val if sales_val > 0 else 0.0
        product = product_map.get(pid)
        items.append(
            schemas.SalesRankingItem(
                product_id=pid,
                name=product.name if product else pid,
                stock=inventory_map.get(pid, 0),
                sales_amount=round(sales_val, 2),
                profit_margin=round(margin * 100, 2),
            )
        )

    top_sales = sorted(items, key=lambda x: x.sales_amount, reverse=True)[:limit]
    top_margin = sorted(items, key=lambda x: x.profit_margin, reverse=True)[:limit]
    return schemas.SalesRankingResponse(scope=scope, top_sales=top_sales, top_margin=top_margin)
