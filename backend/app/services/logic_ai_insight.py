from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import DashboardAIInsight


async def get_insight(
    session: AsyncSession, *, insight_type: str, insight_date: date
) -> DashboardAIInsight | None:
    stmt = sa.select(DashboardAIInsight).where(
        DashboardAIInsight.insight_type == insight_type,
        DashboardAIInsight.insight_date == insight_date,
    )
    return (await session.execute(stmt)).scalars().first()


async def get_latest_insight(
    session: AsyncSession, *, insight_type: str | None = None
) -> DashboardAIInsight | None:
    stmt = sa.select(DashboardAIInsight)
    if insight_type:
        stmt = stmt.where(DashboardAIInsight.insight_type == insight_type)
    stmt = stmt.order_by(
        DashboardAIInsight.insight_date.desc(), DashboardAIInsight.created_at.desc()
    )
    return (await session.execute(stmt)).scalars().first()


async def upsert_insight(
    session: AsyncSession,
    *,
    insight_type: str,
    insight_date: date,
    content: str,
    model: str | None = None,
    protocol: str | None = None,
    finish_reason: str | None = None,
    raw_usage: dict | None = None,
) -> DashboardAIInsight:
    existing = await get_insight(
        session, insight_type=insight_type, insight_date=insight_date
    )
    if existing:
        existing.content = content
        existing.model = model
        existing.protocol = protocol
        existing.finish_reason = finish_reason
        existing.raw_usage = raw_usage
        existing.created_at = datetime.utcnow()
        await session.flush()
        return existing
    insight = DashboardAIInsight(
        insight_type=insight_type,
        insight_date=insight_date,
        content=content,
        model=model,
        protocol=protocol,
        finish_reason=finish_reason,
        raw_usage=raw_usage,
    )
    session.add(insight)
    await session.flush()
    return insight
