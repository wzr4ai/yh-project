import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import MiscCost, Shareholder


async def _validate_cost_payer(
    session: AsyncSession,
    *,
    cost_payer_type: str,
    cost_payer_shareholder_id: str | None,
) -> str | None:
    if cost_payer_type == "public":
        return None
    if cost_payer_type != "shareholder":
        raise ValueError("invalid cost payer type")
    shareholder_id = (cost_payer_shareholder_id or "").strip()
    if not shareholder_id:
        raise ValueError("shareholder payer requires shareholder id")
    holder = await session.get(Shareholder, shareholder_id)
    if not holder:
        raise ValueError("shareholder not found")
    return holder.id


async def create_misc_cost(session: AsyncSession, data: schemas.MiscCostCreate) -> MiscCost:
    item = (data.item or "").strip()
    if not item:
        raise ValueError("item is required")
    quantity = float(data.quantity or 1)
    amount = float(data.amount or 0)
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if amount < 0:
        raise ValueError("amount must be non-negative")
    payer_shareholder_id = await _validate_cost_payer(
        session,
        cost_payer_type=data.cost_payer_type,
        cost_payer_shareholder_id=data.cost_payer_shareholder_id,
    )
    record = MiscCost(
        item=item,
        quantity=quantity,
        amount=amount,
        cost_payer_type=data.cost_payer_type,
        cost_payer_shareholder_id=payer_shareholder_id,
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
        item = data.item.strip()
        if not item:
            raise ValueError("item is required")
        record.item = item
    if data.quantity is not None:
        quantity = float(data.quantity)
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        record.quantity = quantity
    if data.amount is not None:
        amount = float(data.amount)
        if amount < 0:
            raise ValueError("amount must be non-negative")
        record.amount = amount
    next_payer_type = record.cost_payer_type
    if data.cost_payer_type is not None:
        next_payer_type = data.cost_payer_type
    next_payer_shareholder_id = record.cost_payer_shareholder_id
    if "cost_payer_shareholder_id" in data.model_fields_set:
        next_payer_shareholder_id = data.cost_payer_shareholder_id
    if (
        data.cost_payer_type is not None
        or "cost_payer_shareholder_id" in data.model_fields_set
    ):
        validated_shareholder_id = await _validate_cost_payer(
            session,
            cost_payer_type=next_payer_type,
            cost_payer_shareholder_id=next_payer_shareholder_id,
        )
        record.cost_payer_type = next_payer_type
        record.cost_payer_shareholder_id = validated_shareholder_id
    if data.created_by is not None:
        record.created_by = data.created_by
    await session.flush()
    return record


async def delete_misc_cost(session: AsyncSession, misc_id: str) -> None:
    record = await session.get(MiscCost, misc_id)
    if not record:
        raise ValueError("misc cost not found")
    await session.delete(record)
