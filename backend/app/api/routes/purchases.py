from typing import List
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import schemas
from app.models.entities import PurchaseOrder
from app.services import logic

router = APIRouter()


@router.get(
    "/purchase-orders/summary", response_model=List[schemas.PurchaseOrderSummary]
)
async def list_purchase_orders_summary(session: AsyncSession = Depends(get_session)):
    return await logic.list_purchase_order_summaries(session)


@router.get("/purchase-orders", response_model=List[schemas.PurchaseOrder])
async def list_purchase_orders(session: AsyncSession = Depends(get_session)):
    orders = (
        (
            await session.execute(
                sa.select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
            )
        )
        .scalars()
        .all()
    )
    return orders


@router.get("/purchase-orders/{po_id}", response_model=schemas.PurchaseOrder)
async def get_purchase_order(po_id: str, session: AsyncSession = Depends(get_session)):
    order = (
        (
            await session.execute(
                sa.select(PurchaseOrder)
                .options(selectinload(PurchaseOrder.items))
                .where(PurchaseOrder.id == po_id)
            )
        )
        .scalars()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="purchase order not found")
    return order


@router.get(
    "/purchase-orders/{po_id}/items",
    response_model=schemas.PurchaseOrderItemsResponse,
)
async def list_purchase_order_items(
    po_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    items, total = await logic.list_purchase_order_items(
        session, po_id, offset=offset, limit=limit
    )
    return {"items": items, "total": total}


@router.get(
    "/purchase-orders/{po_id}/items/{item_id}",
    response_model=schemas.PurchaseOrderItemRow,
)
async def get_purchase_order_item(
    po_id: str,
    item_id: str,
    session: AsyncSession = Depends(get_session),
):
    row = await logic.get_purchase_order_item(session, po_id, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="purchase item not found")
    return row


@router.patch(
    "/purchase-orders/{po_id}/items/{item_id}",
    response_model=schemas.PurchaseOrderItemRow,
)
async def patch_purchase_order_item(
    po_id: str,
    item_id: str,
    patch: schemas.PurchaseItemUpdate,
    session: AsyncSession = Depends(get_session),
):
    try:
        updated = await logic.update_purchase_order_item(session, po_id, item_id, patch)
        if not updated:
            raise HTTPException(status_code=404, detail="purchase item not found")
        await session.commit()
        row = await logic.get_purchase_order_item(session, po_id, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="purchase item not found")
        return row
    except HTTPException:
        await session.rollback()
        raise
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/purchase-orders", response_model=schemas.PurchaseOrder)
async def create_purchase_order(
    po: schemas.PurchaseOrder, session: AsyncSession = Depends(get_session)
):
    order = await logic.create_purchase_order(session, po)
    await session.commit()
    return order


@router.put("/purchase-orders/{po_id}", response_model=schemas.PurchaseOrder)
async def update_purchase_order(
    po_id: str, po: schemas.PurchaseOrder, session: AsyncSession = Depends(get_session)
):
    try:
        order = await logic.update_purchase_order(session, po_id, po)
        await session.commit()
        return order
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/purchase-orders/{po_id}")
async def delete_purchase_order(
    po_id: str, session: AsyncSession = Depends(get_session)
):
    try:
        await logic.delete_purchase_order(session, po_id)
        await session.commit()
        return {"status": "ok"}
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/purchase-orders/{po_id}/receive", response_model=schemas.PurchaseOrder)
async def receive_purchase(
    po_id: str,
    items: List[schemas.PurchaseItem],
    session: AsyncSession = Depends(get_session),
):
    try:
        order = await logic.receive_purchase(session, po_id, items)
        await session.commit()
        return order
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
