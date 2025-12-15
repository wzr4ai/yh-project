"""
导出商品名称与效果链接到 CSV。
- 默认写入 backend/files/product_effect_urls.csv
- 仅包含 effect_url 非空的商品，按名称排序。

运行：
  uv run python backend/utils/export_effect_urls.py
"""
import asyncio
import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.entities import Product

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "files" / "product_effect_urls.csv"


async def export_effect_urls():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with SessionLocal() as session:  # type: AsyncSession
        stmt = select(Product).order_by(Product.name)
        products = (await session.execute(stmt)).scalars().all()

    written = 0
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "effect_url"])
        for p in products:
            url = (p.effect_url or "").strip()
            writer.writerow([p.name, url])
            written += 1

    print(f"已导出 {written} 条到 {OUTPUT_PATH}")


def main():
    asyncio.run(export_effect_urls())


if __name__ == "__main__":
    main()
