import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import schemas
from app.models.entities import Product, PurchaseItem, PurchaseOrder
from app.services.logic_inventory import (
    apply_unit_delta,
    get_inventory_record,
    log_inventory,
)
from app.services.logic_utils import get_pieces_per_box


async def list_purchase_order_summaries(
    session: AsyncSession,
) -> list[schemas.PurchaseOrderSummary]:
    stmt = (
        sa.select(
            PurchaseOrder,
            sa.func.count(PurchaseItem.id).label("item_count"),
            sa.func.coalesce(sa.func.sum(PurchaseItem.quantity), 0).label("total_qty"),
            sa.func.coalesce(sa.func.sum(PurchaseItem.received_qty), 0).label(
                "received_qty"
            ),
            sa.func.coalesce(
                sa.func.sum(PurchaseItem.quantity * PurchaseItem.expected_cost), 0.0
            ).label("expected_cost_total"),
        )
        .join(
            PurchaseItem,
            PurchaseItem.purchase_order_id == PurchaseOrder.id,
            isouter=True,
        )
        .group_by(PurchaseOrder.id)
        .order_by(sa.desc(PurchaseOrder.expected_date), sa.desc(PurchaseOrder.id))
    )
    rows = (await session.execute(stmt)).all()
    out: list[schemas.PurchaseOrderSummary] = []
    for order, item_count, total_qty, received_qty, expected_cost_total in rows:
        out.append(
            schemas.PurchaseOrderSummary(
                id=order.id,
                status=order.status,
                supplier=order.supplier,
                expected_date=order.expected_date,
                remark=order.remark,
                created_by=order.created_by,
                item_count=int(item_count or 0),
                total_qty=int(total_qty or 0),
                received_qty=int(received_qty or 0),
                expected_cost_total=float(expected_cost_total or 0.0),
            )
        )
    return out


async def list_purchase_order_items(
    session: AsyncSession,
    po_id: str,
    offset: int = 0,
    limit: int = 50,
    keyword: str | None = None,
) -> tuple[list[schemas.PurchaseOrderItemRow], int]:
    where_clause = [PurchaseItem.purchase_order_id == po_id]
    if keyword:
        like = f"%{keyword}%"
        where_clause.append(
            sa.or_(
                Product.name.ilike(like),
                Product.spec.ilike(like),
                PurchaseItem.product_id.ilike(like),
            )
        )
    total_stmt = sa.select(sa.func.count()).select_from(PurchaseItem)
    if keyword:
        total_stmt = total_stmt.join(Product, Product.id == PurchaseItem.product_id)
    total_stmt = total_stmt.where(*where_clause)
    total = int((await session.execute(total_stmt)).scalar() or 0)
    if total == 0:
        return [], 0

    stmt = (
        sa.select(PurchaseItem, Product)
        .join(Product, Product.id == PurchaseItem.product_id)
        .where(*where_clause)
        .order_by(PurchaseItem.id)
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    items: list[schemas.PurchaseOrderItemRow] = []
    for item, product in rows:
        items.append(
            schemas.PurchaseOrderItemRow(
                id=item.id,
                product_id=item.product_id,
                product_name=product.name,
                product_spec=product.spec,
                quantity=item.quantity,
                expected_cost=item.expected_cost,
                received_qty=item.received_qty,
                received_units=item.received_units,
                actual_cost=item.actual_cost,
            )
        )
    return items, total


async def get_purchase_order_item(
    session: AsyncSession, po_id: str, item_id: str
) -> schemas.PurchaseOrderItemRow | None:
    stmt = (
        sa.select(PurchaseItem, Product)
        .join(Product, Product.id == PurchaseItem.product_id)
        .where(PurchaseItem.purchase_order_id == po_id)
        .where(PurchaseItem.id == item_id)
    )
    row = (await session.execute(stmt)).first()
    if not row:
        return None
    item, product = row
    return schemas.PurchaseOrderItemRow(
        id=item.id,
        product_id=item.product_id,
        product_name=product.name,
        product_spec=product.spec,
        quantity=item.quantity,
        expected_cost=item.expected_cost,
        received_qty=item.received_qty,
        received_units=item.received_units,
        actual_cost=item.actual_cost,
    )


async def update_purchase_order_item(
    session: AsyncSession, po_id: str, item_id: str, patch: schemas.PurchaseItemUpdate
) -> PurchaseItem | None:
    stmt = (
        sa.select(PurchaseItem)
        .where(PurchaseItem.purchase_order_id == po_id)
        .where(PurchaseItem.id == item_id)
        .with_for_update()
    )
    item = (await session.execute(stmt)).scalars().first()
    if not item:
        return None

    if patch.quantity is not None:
        qty = int(patch.quantity)
        if qty < 0:
            qty = 0
        item.quantity = qty

    if patch.expected_cost is not None:
        cost = float(patch.expected_cost)
        if cost < 0:
            cost = 0.0
        item.expected_cost = cost

    if patch.actual_cost is not None or ("actual_cost" in patch.model_fields_set):
        # allow explicit null
        if patch.actual_cost is None:
            item.actual_cost = None
        else:
            actual = float(patch.actual_cost)
            if actual < 0:
                actual = 0.0
            item.actual_cost = actual

    # Keep received values within bounds after edits.
    product = await session.get(Product, item.product_id)
    pieces_per_box = get_pieces_per_box(product) if product else 1
    max_units = int((item.quantity or 0) * pieces_per_box)
    if item.received_units is None:
        item.received_units = int((item.received_qty or 0) * pieces_per_box)
    if max_units and item.received_units > max_units:
        item.received_units = max_units
    item.received_qty = int(
        min(item.quantity or 0, int(item.received_units or 0) // pieces_per_box)
    )

    await session.flush()
    return item


async def receive_purchase(
    session: AsyncSession, po_id: str, items: list[schemas.PurchaseItem]
) -> PurchaseOrder:
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
        product = await session.get(Product, update.product_id)
        pieces_per_box = get_pieces_per_box(product) if product else 1
        previous_units = target.received_units
        min_units = (target.received_qty or 0) * pieces_per_box
        if previous_units is None or previous_units < min_units:
            previous_units = min_units
        new_units = (
            update.received_units
            if update.received_units is not None
            else (update.received_qty or 0) * pieces_per_box
        )
        if new_units < 0:
            new_units = 0
        max_units = (target.quantity or 0) * pieces_per_box
        if max_units and new_units > max_units:
            new_units = max_units
        target.received_units = int(new_units)
        target.received_qty = int(
            min(target.quantity or 0, new_units // pieces_per_box)
        )
        actual_cost = (
            update.actual_cost
            if update.actual_cost is not None
            else target.expected_cost
        )
        target.actual_cost = actual_cost
        inv = await get_inventory_record(
            session, update.product_id, create_if_missing=True
        )
        if inv is None:
            continue
        if product and actual_cost is not None and actual_cost > 0:
            delta_units = int(target.received_units or 0) - int(previous_units or 0)
            if delta_units:
                apply_unit_delta(inv, product, delta_units)
                await log_inventory(
                    session, update.product_id, delta_units, "purchase", ref_id=order.id
                )
    await session.flush()
    return order


async def create_purchase_order(
    session: AsyncSession, po: schemas.PurchaseOrder
) -> PurchaseOrder:
    order = PurchaseOrder(
        status=po.status,
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
            received_units=item.received_units
            if item.received_units is not None
            else 0,
            actual_cost=item.actual_cost,
        )
        for item in po.items
    ]
    session.add(order)
    await session.flush()
    return order


async def update_purchase_order(
    session: AsyncSession, po_id: str, po: schemas.PurchaseOrder
) -> PurchaseOrder:
    stmt = (
        sa.select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
        .with_for_update()
    )
    order = (await session.execute(stmt)).scalars().first()
    if not order:
        raise ValueError("purchase order not found")

    order.status = po.status or order.status
    order.supplier = po.supplier
    order.expected_date = po.expected_date
    order.remark = po.remark
    if po.created_by:
        order.created_by = po.created_by

    existing_units = {item.product_id: item.received_units for item in order.items}
    order.items.clear()
    order.items = [
        PurchaseItem(
            product_id=item.product_id,
            quantity=item.quantity,
            expected_cost=item.expected_cost,
            received_qty=item.received_qty,
            received_units=item.received_units
            if item.received_units is not None
            else (existing_units.get(item.product_id) or 0),
            actual_cost=item.actual_cost,
        )
        for item in po.items
    ]
    await session.flush()
    return order


async def delete_purchase_order(session: AsyncSession, po_id: str) -> None:
    order = await session.get(PurchaseOrder, po_id)
    if not order:
        raise ValueError("purchase order not found")
    await session.delete(order)
    await session.flush()
