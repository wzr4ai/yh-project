import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import SystemConfig, User, Warehouse

DEFAULT_GLOBAL_MULTIPLIER = 1.5
DEFAULT_GLOBAL_MIN = 1.5
DEFAULT_GLOBAL_MAX = 1.5


async def ensure_defaults(session: AsyncSession):
    await ensure_default_config(session)
    await ensure_default_warehouse(session)
    await session.commit()


async def ensure_default_config(session: AsyncSession):
    stmt = sa.select(SystemConfig).where(SystemConfig.key == "global_multiplier")
    result = await session.execute(stmt)
    cfg = result.scalars().first()
    if not cfg:
        session.add(SystemConfig(key="global_multiplier", value=str(DEFAULT_GLOBAL_MULTIPLIER)))
    cfg_min = (
        await session.execute(sa.select(SystemConfig).where(SystemConfig.key == "global_multiplier_min"))
    ).scalars().first()
    if not cfg_min:
        session.add(SystemConfig(key="global_multiplier_min", value=str(DEFAULT_GLOBAL_MIN)))
    cfg_max = (
        await session.execute(sa.select(SystemConfig).where(SystemConfig.key == "global_multiplier_max"))
    ).scalars().first()
    if not cfg_max:
        session.add(SystemConfig(key="global_multiplier_max", value=str(DEFAULT_GLOBAL_MAX)))


async def ensure_default_warehouse(session: AsyncSession):
    stmt = sa.select(Warehouse).where(Warehouse.id == "default")
    result = await session.execute(stmt)
    wh = result.scalars().first()
    if not wh:
        session.add(Warehouse(id="default", name="默认仓"))


async def get_global_multiplier(session: AsyncSession) -> float:
    stmt = sa.select(SystemConfig).where(SystemConfig.key == "global_multiplier")
    cfg = (await session.execute(stmt)).scalars().first()
    if not cfg:
        await ensure_default_config(session)
        await session.commit()
        return DEFAULT_GLOBAL_MULTIPLIER
    try:
        return float(cfg.value)
    except (TypeError, ValueError):
        return DEFAULT_GLOBAL_MULTIPLIER


async def get_global_multiplier_range(session: AsyncSession) -> tuple[float, float]:
    stmt = sa.select(SystemConfig).where(SystemConfig.key.in_(["global_multiplier_min", "global_multiplier_max"]))
    cfgs = {c.key: c.value for c in (await session.execute(stmt)).scalars().all()}
    if not cfgs:
        await ensure_default_config(session)
        await session.commit()
        cfgs = {}
    try:
        min_val = float(cfgs.get("global_multiplier_min", DEFAULT_GLOBAL_MIN))
    except (TypeError, ValueError):
        min_val = DEFAULT_GLOBAL_MIN
    try:
        max_val = float(cfgs.get("global_multiplier_max", DEFAULT_GLOBAL_MAX))
    except (TypeError, ValueError):
        max_val = DEFAULT_GLOBAL_MAX
    if max_val < min_val:
        max_val = min_val
    return min_val, max_val


async def set_global_multiplier_range(session: AsyncSession, min_val: float, max_val: float) -> tuple[float, float]:
    min_val = float(min_val)
    max_val = float(max_val)
    if min_val < 0 or max_val < 0:
        raise ValueError("multiplier must be non-negative")
    if max_val < min_val:
        max_val = min_val
    stmt = sa.select(SystemConfig).where(
        SystemConfig.key.in_(["global_multiplier", "global_multiplier_min", "global_multiplier_max"])
    )
    cfgs = {c.key: c for c in (await session.execute(stmt)).scalars().all()}

    def upsert(key: str, value: float):
        if key in cfgs:
            cfgs[key].value = str(value)
        else:
            session.add(SystemConfig(key=key, value=str(value)))

    upsert("global_multiplier_min", min_val)
    upsert("global_multiplier_max", max_val)
    upsert("global_multiplier", min_val)
    await session.flush()
    return min_val, max_val


async def get_or_create_user_by_openid(session: AsyncSession, openid: str, nickname: str | None = None) -> User:
    stmt = sa.select(User).where(User.openid == openid)
    user = (await session.execute(stmt)).scalars().first()
    if user:
        return user
    user = User(username=nickname or "用户", role="user", openid=openid)
    session.add(user)
    await session.flush()
    return user


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    stmt = sa.select(User).where(User.id == user_id)
    return (await session.execute(stmt)).scalars().first()
