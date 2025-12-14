"""
One-off script to normalize product.spec to pure numbers.
Usage:
  uv run python utils/normalize_spec.py
"""
import asyncio
import os
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.entities import Product
from app.db import get_sessionmaker_async_from_env

NUMBER_RE = re.compile(r"(\\d+(?:\\.\\d+)?)")


def normalize_spec_value(spec: Optional[str]) -> Optional[str]:
    if not spec:
        return None
    match = NUMBER_RE.search(str(spec))
    if match:
        return match.group(1)
    return None


async def normalize_all():
    SessionLocal = get_sessionmaker_async_from_env()
    async with SessionLocal() as session:  # type: AsyncSession
        stmt = select(Product)
        products = (await session.execute(stmt)).scalars().all()
        updated = 0
        for p in products:
            clean = normalize_spec_value(p.spec)
            if clean != p.spec:
                p.spec = clean
                updated += 1
        if updated:
            await session.commit()
        print(f"Checked {len(products)} products, updated {updated}.")


def main():
    asyncio.run(normalize_all())


if __name__ == "__main__":
    main()
