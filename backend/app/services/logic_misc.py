import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import MiscCost


async def create_misc_cost(session: AsyncSession, data: schemas.MiscCostCreate) -> MiscCost:
    record = MiscCost(
        item=data.item,
        quantity=data.quantity or 1,
        amount=data.amount,
        created_by=data.created_by,
    )
    session.add(record)
    await session.flush()
    return record


async def list_misc_costs(session: AsyncSession, limit: int = 100, offset: int = 0) -> list[MiscCost]:
    stmt = sa.select(MiscCost).order_by(MiscCost.created_at.desc()).offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_misc_cost(session: AsyncSession, misc_id: str, data: schemas.MiscCostUpdate) -> MiscCost:
    record = await session.get(MiscCost, misc_id)
    if not record:
        raise ValueError("misc cost not found")
    if data.item is not None:
        record.item = data.item
    if data.quantity is not None:
        record.quantity = data.quantity
    if data.amount is not None:
        record.amount = data.amount
    if data.created_by is not None:
        record.created_by = data.created_by
    await session.flush()
    return record
