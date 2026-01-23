from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db import get_session
from app.models import schemas
from app.services import logic

router = APIRouter()


def _ensure_owner(user) -> None:
    if not user or getattr(user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")


@router.get("/shareholders", response_model=list[schemas.Shareholder])
async def list_shareholders(
    active_only: bool = True,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    return await logic.list_shareholders(session, active_only=active_only)


@router.post("/shareholders", response_model=schemas.Shareholder)
async def create_shareholder(
    payload: schemas.ShareholderCreate,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    try:
        record = await logic.create_shareholder(session, payload)
        await session.commit()
        return record
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/shareholders/{shareholder_id}", response_model=schemas.Shareholder)
async def update_shareholder(
    shareholder_id: str,
    payload: schemas.ShareholderUpdate,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    try:
        record = await logic.update_shareholder(session, shareholder_id, payload)
        await session.commit()
        return record
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/shareholders/summary", response_model=schemas.ShareholderSummaryResponse)
async def shareholder_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    profit_basis: str = "net",
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    return await logic.shareholder_summary(
        session, start_date=start_date, end_date=end_date, profit_basis=profit_basis
    )


@router.post("/shareholders/capital", response_model=schemas.ShareholderCapital)
async def create_capital(
    payload: schemas.ShareholderCapitalCreate,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    try:
        record = await logic.create_capital(session, payload)
        await session.commit()
        return record
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/shareholders/capital", response_model=list[schemas.ShareholderCapital])
async def list_capital(
    shareholder_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    return await logic.list_capital(
        session, shareholder_id=shareholder_id, start_date=start_date, end_date=end_date
    )


@router.post(
    "/shareholders/distribution", response_model=schemas.ShareholderDistribution
)
async def create_distribution(
    payload: schemas.ShareholderDistributionCreate,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    try:
        record = await logic.create_distribution(session, payload)
        await session.commit()
        return record
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/shareholders/distribution", response_model=list[schemas.ShareholderDistribution]
)
async def list_distributions(
    shareholder_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    return await logic.list_distributions(
        session, shareholder_id=shareholder_id, start_date=start_date, end_date=end_date
    )
