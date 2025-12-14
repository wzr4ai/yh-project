"""
将 files/a.csv 导入到数据库 product 表，自动创建分类（按 CSV 第一列）。

列假设：
0: 类别
1: 序号（忽略）
2: 产品名称
3: 规格
4: 单个价(元) -> base_cost_price
5: 箱价(元) -> 如果存在且 > 单个价则作为 fixed_retail_price，否则为空
6: 备注（忽略）

运行方式：
  uv run python backend/utils/import_csv_to_products.py

使用前确保 .env 中 DATABASE_URL 指向目标数据库，并已创建表（运行后端一次会建表）。
"""

import asyncio
import csv
import os
from pathlib import Path
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.entities import Category, Product


CSV_PATH = Path(__file__).resolve().parent.parent / "files" / "a.csv"


def get_database_url() -> str | None:
  url = os.getenv("DATABASE_URL")
  if not url:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
      for line in env_path.read_text().splitlines():
        if line.strip().startswith("DATABASE_URL"):
          _, _, val = line.partition("=")
          url = val.strip().strip('"').strip("'")
          break
  if not url:
    return None
  if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
  return url


async def main():
  if not CSV_PATH.exists():
    print(f"CSV 不存在: {CSV_PATH}")
    return
  db_url = get_database_url()
  if not db_url:
    print("缺少 DATABASE_URL 环境变量，请在 .env 中配置后重试。")
    return

  engine = create_async_engine(db_url, echo=False, future=True)
  try:
    async with AsyncSession(engine) as session:
      category_cache = {}

      async def get_or_create_category(name: str) -> str:
        if name in category_cache:
          return category_cache[name]
        stmt = sa.select(Category).where(Category.name == name)
        cat = (await session.execute(stmt)).scalars().first()
        if not cat:
          cat = Category(name=name)
          session.add(cat)
          await session.flush()
        category_cache[name] = cat.id
        return cat.id

      created = 0
      async for row in read_csv():
        category_name, _, product_name, spec, single_price, box_price = row
        cat_id = await get_or_create_category(category_name)
        try:
          base_cost = float(single_price)
        except ValueError:
          base_cost = 0.0
        fixed_retail = None
        try:
          box_val = float(box_price)
          if box_val > base_cost:
            fixed_retail = box_val
        except ValueError:
          pass
        product = Product(
          name=product_name,
          category_id=cat_id,
          spec=spec,
          base_cost_price=base_cost,
          fixed_retail_price=fixed_retail,
        )
        session.add(product)
        created += 1

      await session.commit()
      print(f"导入完成，新增 {created} 个商品，涉及分类 {len(category_cache)} 个。")
  finally:
    await engine.dispose()


async def read_csv():
  loop = asyncio.get_event_loop()
  with CSV_PATH.open("r", encoding="utf-8") as f:
    reader = csv.reader(f)
    # 跳过表头
    next(reader, None)
    for row in reader:
      # 填充缺失列
      while len(row) < 6:
        row.append("")
      yield row[:6]


if __name__ == "__main__":
  asyncio.run(main())
