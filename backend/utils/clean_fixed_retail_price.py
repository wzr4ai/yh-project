"""
清理商品固定零售价。
- 规则：若 base_cost_price * spec 与 fixed_retail_price 相差不超过 ±5%，则清除 fixed_retail_price（置为空）。
- 未清除的商品打印日志（ID、名称、base_cost_price、spec、fixed_retail_price、预期箱价）。

运行：
  uv run python backend/utils/clean_fixed_retail_price.py
"""
import asyncio
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.entities import Product

NUM_RE = re.compile(r"(\d+(?:\.\d+)?)")
TOLERANCE = 0.05  # 5%


def parse_spec(spec: Optional[str]) -> float:
    if not spec:
        return 1.0
    match = NUM_RE.search(str(spec))
    if not match:
        return 1.0
    try:
        val = float(match.group(1))
        return val if val > 0 else 1.0
    except Exception:
        return 1.0


async def main():
    async with SessionLocal() as session:  # type: AsyncSession
        products = (await session.execute(select(Product))).scalars().all()
        cleaned = 0
        kept: list[tuple[str, str, float, float, float, float]] = []
        for p in products:
            if p.fixed_retail_price is None:
                continue
            spec_qty = parse_spec(p.spec)
            expected_pack = p.base_cost_price * spec_qty
            if expected_pack == 0:
                kept.append((p.id, p.name, p.base_cost_price, spec_qty, p.fixed_retail_price, expected_pack))
                continue
            diff_ratio = abs(p.fixed_retail_price - expected_pack) / expected_pack
            if diff_ratio <= TOLERANCE:
                p.fixed_retail_price = None
                cleaned += 1
            else:
                kept.append((p.id, p.name, p.base_cost_price, spec_qty, p.fixed_retail_price, expected_pack))
        if cleaned:
            await session.commit()
        print(f"清理完成，清除 {cleaned} 条固定零售价。")
        if kept:
            print("未清除的商品（供检查）：")
            for pid, name, cost, spec_qty, fixed, expected in kept:
                print(f"- {pid} | {name} | cost={cost} | spec={spec_qty} | fixed={fixed} | expected_pack={expected}")


if __name__ == "__main__":
    asyncio.run(main())
