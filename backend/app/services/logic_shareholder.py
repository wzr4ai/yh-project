from __future__ import annotations

from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import (
    MiscCost,
    SalesItem,
    Shareholder,
    ShareholderCapital,
    ShareholderDistribution,
)
from app.services.logic_utils import round2


async def list_shareholders(
    session: AsyncSession, *, active_only: bool = True
) -> list[Shareholder]:
    stmt = sa.select(Shareholder)
    if active_only:
        stmt = stmt.where(Shareholder.is_active.is_(True))
    stmt = stmt.order_by(Shareholder.created_at.asc())
    return list((await session.execute(stmt)).scalars().all())


async def create_shareholder(
    session: AsyncSession, payload: schemas.ShareholderCreate
) -> Shareholder:
    ratio = float(payload.share_ratio or 0)
    if ratio < 0:
        raise ValueError("share_ratio must be non-negative")
    record = Shareholder(
        name=payload.name.strip(),
        share_ratio=ratio,
        role=payload.role,
        note=payload.note,
        is_active=payload.is_active,
    )
    session.add(record)
    await session.flush()
    return record


async def update_shareholder(
    session: AsyncSession, shareholder_id: str, payload: schemas.ShareholderUpdate
) -> Shareholder:
    record = await session.get(Shareholder, shareholder_id)
    if not record:
        raise ValueError("shareholder not found")
    if payload.name is not None:
        record.name = payload.name.strip()
    if payload.share_ratio is not None:
        ratio = float(payload.share_ratio)
        if ratio < 0:
            raise ValueError("share_ratio must be non-negative")
        record.share_ratio = ratio
    if payload.role is not None:
        record.role = payload.role
    if payload.note is not None:
        record.note = payload.note
    if payload.is_active is not None:
        record.is_active = payload.is_active
    await session.flush()
    return record


async def create_capital(
    session: AsyncSession, payload: schemas.ShareholderCapitalCreate
) -> ShareholderCapital:
    holder = await session.get(Shareholder, payload.shareholder_id)
    if not holder:
        raise ValueError("shareholder not found")
    if float(payload.amount) <= 0:
        raise ValueError("amount must be positive")
    record = ShareholderCapital(
        shareholder_id=payload.shareholder_id,
        amount=float(payload.amount),
        memo=payload.memo,
        biz_date=payload.biz_date or date.today(),
    )
    session.add(record)
    await session.flush()
    return record


async def create_distribution(
    session: AsyncSession, payload: schemas.ShareholderDistributionCreate
) -> ShareholderDistribution:
    holder = await session.get(Shareholder, payload.shareholder_id)
    if not holder:
        raise ValueError("shareholder not found")
    if float(payload.amount) <= 0:
        raise ValueError("amount must be positive")
    record = ShareholderDistribution(
        shareholder_id=payload.shareholder_id,
        amount=float(payload.amount),
        memo=payload.memo,
        biz_date=payload.biz_date or date.today(),
    )
    session.add(record)
    await session.flush()
    return record


async def list_capital(
    session: AsyncSession,
    *,
    shareholder_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ShareholderCapital]:
    stmt = sa.select(ShareholderCapital)
    if shareholder_id:
        stmt = stmt.where(ShareholderCapital.shareholder_id == shareholder_id)
    if start_date:
        stmt = stmt.where(ShareholderCapital.biz_date >= start_date)
    if end_date:
        stmt = stmt.where(ShareholderCapital.biz_date <= end_date)
    stmt = stmt.order_by(
        ShareholderCapital.biz_date.desc(), ShareholderCapital.created_at.desc()
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_distributions(
    session: AsyncSession,
    *,
    shareholder_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ShareholderDistribution]:
    stmt = sa.select(ShareholderDistribution)
    if shareholder_id:
        stmt = stmt.where(ShareholderDistribution.shareholder_id == shareholder_id)
    if start_date:
        stmt = stmt.where(ShareholderDistribution.biz_date >= start_date)
    if end_date:
        stmt = stmt.where(ShareholderDistribution.biz_date <= end_date)
    stmt = stmt.order_by(
        ShareholderDistribution.biz_date.desc(),
        ShareholderDistribution.created_at.desc(),
    )
    return list((await session.execute(stmt)).scalars().all())


async def _sales_profit(
    session: AsyncSession, *, start_date: date | None, end_date: date | None
) -> tuple[float, float]:
    stmt = sa.select(
        sa.func.coalesce(
            sa.func.sum(SalesItem.actual_sale_price * SalesItem.quantity), 0
        ),
        sa.func.coalesce(sa.func.sum(SalesItem.snapshot_cost * SalesItem.quantity), 0),
    )
    if start_date or end_date:
        date_col = sa.func.date(SalesItem.created_at)
        if start_date:
            stmt = stmt.where(date_col >= start_date)
        if end_date:
            stmt = stmt.where(date_col <= end_date)
    actual_sales, cost_total = (await session.execute(stmt)).first() or (0, 0)
    return float(actual_sales or 0), float(cost_total or 0)


async def _misc_total(
    session: AsyncSession, *, start_date: date | None, end_date: date | None
) -> float:
    stmt = sa.select(
        sa.func.coalesce(sa.func.sum(MiscCost.amount * MiscCost.quantity), 0)
    )
    if start_date or end_date:
        date_col = sa.func.date(MiscCost.created_at)
        if start_date:
            stmt = stmt.where(date_col >= start_date)
        if end_date:
            stmt = stmt.where(date_col <= end_date)
    total = (await session.execute(stmt)).scalar_one()
    return float(total or 0)


async def shareholder_summary(
    session: AsyncSession,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    profit_basis: str = "net",
) -> schemas.ShareholderSummaryResponse:
    shareholders = await list_shareholders(session, active_only=False)
    actual_sales, cost_total = await _sales_profit(
        session, start_date=start_date, end_date=end_date
    )
    gross_profit = actual_sales - cost_total
    misc_total = await _misc_total(session, start_date=start_date, end_date=end_date)
    net_profit = gross_profit - misc_total
    basis = "gross" if profit_basis == "gross" else "net"
    basis_profit = gross_profit if basis == "gross" else net_profit

    active_shareholders = [s for s in shareholders if s.is_active]
    ratio_total = sum(float(s.share_ratio or 0) for s in active_shareholders)
    if ratio_total <= 0:
        ratio_total = 0

    items: list[schemas.ShareholderSummaryItem] = []
    distributable_total = 0.0

    for holder in shareholders:
        raw_ratio = float(holder.share_ratio or 0)
        if holder.is_active and ratio_total > 0:
            effective_ratio = raw_ratio / ratio_total
        else:
            effective_ratio = 0.0
        distributable = basis_profit * effective_ratio
        cap_stmt = sa.select(
            sa.func.coalesce(sa.func.sum(ShareholderCapital.amount), 0)
        ).where(ShareholderCapital.shareholder_id == holder.id)
        dist_stmt = sa.select(
            sa.func.coalesce(sa.func.sum(ShareholderDistribution.amount), 0)
        ).where(ShareholderDistribution.shareholder_id == holder.id)
        if start_date:
            cap_stmt = cap_stmt.where(ShareholderCapital.biz_date >= start_date)
            dist_stmt = dist_stmt.where(ShareholderDistribution.biz_date >= start_date)
        if end_date:
            cap_stmt = cap_stmt.where(ShareholderCapital.biz_date <= end_date)
            dist_stmt = dist_stmt.where(ShareholderDistribution.biz_date <= end_date)
        contributed = float((await session.execute(cap_stmt)).scalar_one() or 0)
        distributed = float((await session.execute(dist_stmt)).scalar_one() or 0)

        balance = distributable + contributed - distributed
        need_topup = abs(balance) if balance < 0 else 0.0
        can_distribute = balance if balance > 0 else 0.0
        distributable_total += distributable

        items.append(
            schemas.ShareholderSummaryItem(
                shareholder_id=holder.id,
                name=holder.name,
                role=holder.role,
                note=holder.note,
                is_active=holder.is_active,
                share_ratio=round2(raw_ratio),
                effective_ratio=round2(effective_ratio),
                profit_basis=round2(basis_profit),
                distributable=round2(distributable),
                contributed=round2(contributed),
                distributed=round2(distributed),
                balance=round2(balance),
                need_topup=round2(need_topup),
                can_distribute=round2(can_distribute),
            )
        )

    return schemas.ShareholderSummaryResponse(
        profit_basis=basis,
        actual_sales=round2(actual_sales),
        cost_total=round2(cost_total),
        gross_profit=round2(gross_profit),
        misc_total=round2(misc_total),
        net_profit=round2(net_profit),
        distributable_total=round2(distributable_total),
        start_date=start_date,
        end_date=end_date,
        items=items,
    )
