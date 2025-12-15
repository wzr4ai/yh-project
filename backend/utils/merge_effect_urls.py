"""
Merge effect URLs and style categories into DB from backend/files/product_effect_urls.csv.

Usage:
  uv run python backend/utils/merge_effect_urls.py

Rules:
- Match product by name (exact match after strip).
- Update product.effect_url when provided (overwrite existing if different).
- Style => category name; create if missing (is_custom=True, no multiplier).
- Link product to style category via product_category (add mapping, do not replace existing fields).
"""

import asyncio
import csv
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.entities import Category, Product, ProductCategory


CSV_PATH = Path(__file__).resolve().parent.parent / "files" / "product_effect_urls.csv"


async def main():
    if not CSV_PATH.exists():
        print(f"CSV not found: {CSV_PATH}")
        return

    async with SessionLocal() as session:  # type: AsyncSession
        rows = list(read_csv(CSV_PATH))
        updated_effect = 0
        linked = 0
        created_cat = 0

        for name, effect_url, style in rows:
            prod = await get_product_by_name(session, name)
            if not prod:
                continue
            # update effect url
            if effect_url and prod.effect_url != effect_url:
                prod.effect_url = effect_url
                updated_effect += 1

            # ensure category
            cat = None
            if style:
                cat = await get_or_create_category(session, style)
                if cat and not await has_mapping(session, prod.id, cat.id):
                    session.add(ProductCategory(product_id=prod.id, category_id=cat.id))
                    linked += 1
                    if getattr(cat, "_created_new", False):
                        created_cat += 1

        await session.commit()
        print(f"Processed {len(rows)} rows.")
        print(f"Updated effect_url: {updated_effect}")
        print(f"New category mappings: {linked}")
        if created_cat:
            print(f"New categories created: {created_cat}")


def read_csv(path: Path):
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row.get("name", "").strip(), row.get("effect_url", "").strip(), row.get("style", "").strip()


async def get_product_by_name(session: AsyncSession, name: str) -> Product | None:
    if not name:
        return None
    stmt = sa.select(Product).where(Product.name == name)
    return (await session.execute(stmt)).scalars().first()


async def get_or_create_category(session: AsyncSession, name: str) -> Category | None:
    if not name:
        return None
    stmt = sa.select(Category).where(Category.name == name)
    cat = (await session.execute(stmt)).scalars().first()
    if cat:
        return cat
    cat = Category(name=name, is_custom=True, retail_multiplier=None)
    session.add(cat)
    await session.flush()
    # mark for stats
    cat._created_new = True  # type: ignore[attr-defined]
    return cat


async def has_mapping(session: AsyncSession, product_id: str, category_id: str) -> bool:
    stmt = sa.select(ProductCategory).where(
        ProductCategory.product_id == product_id, ProductCategory.category_id == category_id
    )
    return (await session.execute(stmt)).scalars().first() is not None


if __name__ == "__main__":
    asyncio.run(main())
