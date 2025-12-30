from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db import get_session
from app.models import schemas
from app.services import logic

router = APIRouter()


@router.get("/system/pricing-multiplier", response_model=schemas.PricingMultiplierConfig)
async def get_pricing_multiplier(
    session: AsyncSession = Depends(get_session), current_user=Depends(deps.get_current_user)
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    min_val, max_val = await logic.get_global_multiplier_range(session)
    return schemas.PricingMultiplierConfig(min_multiplier=min_val, max_multiplier=max_val)


@router.put("/system/pricing-multiplier", response_model=schemas.PricingMultiplierConfig)
async def update_pricing_multiplier(
    payload: schemas.PricingMultiplierConfig,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        min_val, max_val = await logic.set_global_multiplier_range(
            session, payload.min_multiplier, payload.max_multiplier
        )
        await session.commit()
        return schemas.PricingMultiplierConfig(min_multiplier=min_val, max_multiplier=max_val)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
