"""
Backfill units_per_box and box_cost_price from existing spec/base_cost_price.

Logic:
1) units_per_box = spec (parsed as number, rounded to int).
2) box_cost_price = round(base_cost_price * spec).

Usage:
  set -a; source .env; set +a
  uv run python utils/backfill_spec_to_units_and_box_cost.py
  uv run python utils/backfill_spec_to_units_and_box_cost.py --dry-run
"""
import argparse
import asyncio
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.entities import Product

NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")


def parse_spec_value(spec: Optional[str]) -> Optional[float]:
    if not spec:
        return None
    match = NUMBER_RE.search(str(spec))
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    return value if value > 0 else None


async def backfill(dry_run: bool = False) -> None:
    async with SessionLocal() as session:  # type: AsyncSession
        products = (await session.execute(select(Product))).scalars().all()
        updated = 0
        skipped_no_spec = 0
        skipped_no_cost = 0
        fractional_specs = 0

        for product in products:
            spec_val = parse_spec_value(product.spec)
            if spec_val is None:
                skipped_no_spec += 1
                continue

            units_per_box = int(round(spec_val))
            if abs(spec_val - units_per_box) > 1e-6:
                fractional_specs += 1

            base_cost = product.base_cost_price
            if base_cost is None:
                skipped_no_cost += 1
                continue
            box_cost_price = int(round(float(base_cost) * spec_val))

            if product.units_per_box != units_per_box or product.box_cost_price != box_cost_price:
                product.units_per_box = units_per_box
                product.box_cost_price = box_cost_price
                updated += 1

        if updated and not dry_run:
            await session.commit()

        print(
            "Checked {total} products, updated {updated}, skipped_no_spec {no_spec}, "
            "skipped_no_cost {no_cost}, fractional_specs {fractional}.".format(
                total=len(products),
                updated=updated,
                no_spec=skipped_no_spec,
                no_cost=skipped_no_cost,
                fractional=fractional_specs,
            )
        )
        if dry_run:
            print("Dry run only; no changes committed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Calculate counts without committing changes.")
    args = parser.parse_args()
    asyncio.run(backfill(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
