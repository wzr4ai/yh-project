from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import schemas
from app.services import logic

router = APIRouter()


@router.post("/sales", response_model=schemas.SalesOrder)
async def create_sales(
    items: List[schemas.SalesItemPayload],
    username: str = "owner",
    session: AsyncSession = Depends(get_session),
):
    try:
        order = await logic.create_sales_order(session, items, username)
        await session.commit()
        return order
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
