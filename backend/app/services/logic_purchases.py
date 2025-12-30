import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import schemas
from app.models.entities import Product, PurchaseItem, PurchaseOrder
from app.services.logic_inventory import apply_unit_delta, get_inventory_record, log_inventory
from app.services.logic_utils import get_pieces_per_box


async def receive_purchase(session: AsyncSession, po_id: str, items: list[schemas.PurchaseItem]) -> PurchaseOrder:
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
        target.received_qty = int(min(target.quantity or 0, new_units // pieces_per_box))
        actual_cost = update.actual_cost if update.actual_cost is not None else target.expected_cost
        target.actual_cost = actual_cost
        inv = await get_inventory_record(session, update.product_id, create_if_missing=True)
        if product and actual_cost is not None and actual_cost > 0:
            delta_units = int(target.received_units or 0) - int(previous_units or 0)
            if delta_units:
                apply_unit_delta(inv, product, delta_units)
                await log_inventory(session, update.product_id, delta_units, "purchase", ref_id=order.id)
    await session.flush()
    return order


async def create_purchase_order(session: AsyncSession, po: schemas.PurchaseOrder) -> PurchaseOrder:
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
            received_units=item.received_units if item.received_units is not None else 0,
            actual_cost=item.actual_cost,
        )
        for item in po.items
    ]
    session.add(order)
    await session.flush()
    return order


async def update_purchase_order(session: AsyncSession, po_id: str, po: schemas.PurchaseOrder) -> PurchaseOrder:
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
