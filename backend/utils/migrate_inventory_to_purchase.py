"""
One-off script to migrate inventory into a purchase order snapshot.

Rules:
1) inventory.current_stock -> purchase_item.quantity
2) product.box_cost_price -> purchase_item.expected_cost (and actual_cost)
3) Other fields filled with sensible defaults (status=完成, received_qty=quantity).

Usage:
  set -a; source .env; set +a
  uv run python utils/migrate_inventory_to_purchase.py
  uv run python utils/migrate_inventory_to_purchase.py --dry-run
"""
import argparse
import asyncio
from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.entities import Inventory, Product, PurchaseItem, PurchaseOrder


async def migrate_inventory_to_purchase(
    *,
    created_by: str,
    supplier: str,
    remark: str,
    expected_date: date,
    dry_run: bool,
    include_zero: bool,
) -> None:
    async with SessionLocal() as session:  # type: AsyncSession
        rows = (
            await session.execute(
                sa.select(Inventory.product_id, sa.func.sum(Inventory.current_stock))
                .group_by(Inventory.product_id)
            )
        ).all()
        if not rows:
            print("No inventory rows found.")
            return

        qty_map = {pid: int(total or 0) for pid, total in rows}
        product_ids = list(qty_map.keys())
        products = (
            await session.execute(sa.select(Product).where(Product.id.in_(product_ids)))
        ).scalars().all()
        product_map = {p.id: p for p in products}

        items: list[PurchaseItem] = []
        skipped_missing = 0
        skipped_zero = 0
        for pid, qty in qty_map.items():
            if qty <= 0 and not include_zero:
                skipped_zero += 1
                continue
            product = product_map.get(pid)
            if not product:
                skipped_missing += 1
                continue
            expected_cost = float(product.box_cost_price or 0)
            items.append(
                PurchaseItem(
                    product_id=pid,
                    quantity=qty,
                    expected_cost=expected_cost,
                    received_qty=0,
                    actual_cost=None,
                )
            )

        if not items:
            print("No purchase items to create.")
            return

        order = PurchaseOrder(
            status="待到货",
            supplier=supplier,
            expected_date=expected_date,
            remark=remark,
            created_by=created_by,
            items=items,
        )
        session.add(order)

        if dry_run:
            await session.rollback()
            print(
                f"Dry run: would create 1 order with {len(items)} items. "
                f"Skipped missing products {skipped_missing}, skipped zero qty {skipped_zero}."
            )
            return

        await session.commit()
        print(
            f"Created 1 order with {len(items)} items. "
            f"Skipped missing products {skipped_missing}, skipped zero qty {skipped_zero}."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--created-by", default="migration", help="purchase_order.created_by")
    parser.add_argument("--supplier", default="库存迁移", help="purchase_order.supplier")
    parser.add_argument("--remark", default="inventory migration", help="purchase_order.remark")
    parser.add_argument("--expected-date", default=str(date.today()), help="purchase_order.expected_date (YYYY-MM-DD)")
    parser.add_argument("--include-zero", action="store_true", help="Include zero-quantity items.")
    parser.add_argument("--dry-run", action="store_true", help="Do not commit changes.")
    args = parser.parse_args()

    try:
        expected = date.fromisoformat(args.expected_date)
    except ValueError as exc:
        raise SystemExit(f"Invalid --expected-date: {args.expected_date}") from exc

    asyncio.run(
        migrate_inventory_to_purchase(
            created_by=args.created_by,
            supplier=args.supplier,
            remark=args.remark,
            expected_date=expected,
            dry_run=args.dry_run,
            include_zero=args.include_zero,
        )
    )


if __name__ == "__main__":
    main()
