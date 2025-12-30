from typing import List
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import schemas
from app.models.entities import InventoryLog
from app.services import logic

router = APIRouter()


@router.post("/inventory/adjust", response_model=schemas.InventoryRecord)
async def adjust_inventory(
    req: schemas.InventoryAdjustRequest, username: str = "owner", session: AsyncSession = Depends(get_session)
):
    try:
        inv = await logic.adjust_inventory(session, req, username)
        await session.commit()
        return inv
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/inventory/overview", response_model=list[schemas.InventoryOverviewItem])
async def inventory_overview(
    session: AsyncSession = Depends(get_session), request: Request = None, response: Response = None
):
    items, version = await logic.inventory_overview(session, with_version=True)
    etag = f'W/"{version}"'
    inm = request.headers.get("if-none-match") if request else None
    if inm == etag:
        return Response(status_code=304)
    response.headers["ETag"] = etag
    return items


@router.get("/inventory/{product_id}", response_model=schemas.InventoryRecord)
async def get_inventory(product_id: str, session: AsyncSession = Depends(get_session)):
    inv = await logic.get_inventory_record(session, product_id, create_if_missing=False)
    if not inv:
        raise HTTPException(status_code=404, detail="product not found")
    return inv


@router.get("/inventory/logs", response_model=List[schemas.InventoryLog])
async def inventory_logs(session: AsyncSession = Depends(get_session)):
    logs = (await session.execute(sa.select(InventoryLog))).scalars().all()
    return logs
