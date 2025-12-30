from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import schemas
from app.services import logic

router = APIRouter()


@router.post("/misc-costs", response_model=schemas.MiscCost)
async def create_misc_cost(payload: schemas.MiscCostCreate, session: AsyncSession = Depends(get_session)):
    try:
        record = await logic.create_misc_cost(session, payload)
        await session.commit()
        return record
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/misc-costs", response_model=list[schemas.MiscCost])
async def list_misc_costs(limit: int = 100, offset: int = 0, session: AsyncSession = Depends(get_session)):
    limit = max(1, min(limit, 500))
    return await logic.list_misc_costs(session, limit=limit, offset=offset)


@router.put("/misc-costs/{misc_id}", response_model=schemas.MiscCost)
async def update_misc_cost(misc_id: str, payload: schemas.MiscCostUpdate, session: AsyncSession = Depends(get_session)):
    try:
        record = await logic.update_misc_cost(session, misc_id, payload)
        await session.commit()
        return record
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
