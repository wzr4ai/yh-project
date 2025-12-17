import csv
import io
import math
from typing import Literal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Category, Inventory, Product, ProductCategory
from app.services import logic


NeedMode = Literal["below_target", "out_of_stock"]
PriceMode = Literal["cost", "standard"]


async def _resolve_category_ids(
    session: AsyncSession, category_id: str | None, category_name: str | None
) -> list[str]:
    if category_id:
        return [category_id]
    if not category_name:
        return []
    cat = (await session.execute(sa.select(Category).where(Category.name == category_name))).scalars().first()
    if not cat:
        raise ValueError("category not found")
    return [cat.id]


def _csv_bytes(text: str, encoding: str = "utf-8-sig") -> bytes:
    return text.encode(encoding)


def _price_for_product(
    *,
    product: Product,
    price_mode: PriceMode,
    category_map: dict[str, Category],
    product_to_category_ids: dict[str, list[str]],
    global_multiplier: float,
) -> float:
    if price_mode == "cost":
        return float(product.base_cost_price or 0)

    if product.fixed_retail_price is not None and product.fixed_retail_price > 0:
        return float(product.fixed_retail_price)

    if product.retail_multiplier:
        return logic.round2(float(product.base_cost_price or 0) * float(product.retail_multiplier))

    multipliers: list[float] = []
    if product.category_id:
        cat = category_map.get(product.category_id)
        if cat and cat.retail_multiplier:
            multipliers.append(float(cat.retail_multiplier))
    for cid in product_to_category_ids.get(product.id, []):
        cat = category_map.get(cid)
        if cat and cat.retail_multiplier:
            multipliers.append(float(cat.retail_multiplier))

    if multipliers:
        return logic.round2(float(product.base_cost_price or 0) * max(multipliers))
    return logic.round2(float(product.base_cost_price or 0) * float(global_multiplier))


async def export_replenishment_csv(
    session: AsyncSession,
    *,
    category_id: str | None = None,
    category_name: str | None = None,
    target_boxes: float = 0,
    need_mode: NeedMode = "below_target",
    only_need: bool = True,
    price_mode: PriceMode = "cost",
    warehouse_id: str | None = None,
    encoding: str = "utf-8-sig",
) -> bytes:
    if target_boxes <= 0:
        raise ValueError("target_boxes must be > 0")

    category_ids = await _resolve_category_ids(session, category_id, category_name)

    where_clause = []
    if category_ids:
        subq = sa.select(ProductCategory.product_id).where(ProductCategory.category_id.in_(category_ids))
        where_clause.append(sa.or_(Product.category_id.in_(category_ids), Product.id.in_(subq)))

    stmt = sa.select(Product).order_by(Product.name)
    if where_clause:
        stmt = stmt.where(*where_clause)
    products = (await session.execute(stmt)).scalars().all()

    product_ids = [p.id for p in products]
    inventory_map: dict[str, tuple[int, int]] = {}
    product_to_category_ids: dict[str, list[str]] = {}
    category_map: dict[str, Category] = {}
    global_multiplier = 1.0

    if product_ids:
        inv_stmt = (
            sa.select(Inventory.product_id, sa.func.sum(Inventory.current_stock), sa.func.sum(Inventory.loose_units))
            .where(Inventory.product_id.in_(product_ids))
            .group_by(Inventory.product_id)
        )
        if warehouse_id:
            inv_stmt = inv_stmt.where(Inventory.warehouse_id == warehouse_id)
        inv_rows = await session.execute(inv_stmt)
        for pid, box_qty, loose_qty in inv_rows.all():
            inventory_map[pid] = (int(box_qty or 0), int(loose_qty or 0))

        if price_mode == "standard":
            pc_stmt = sa.select(ProductCategory.product_id, ProductCategory.category_id).where(
                ProductCategory.product_id.in_(product_ids)
            )
            pc_rows = await session.execute(pc_stmt)
            for pid, cid in pc_rows.all():
                product_to_category_ids.setdefault(pid, []).append(cid)

            category_ids_needed = set()
            for p in products:
                if p.category_id:
                    category_ids_needed.add(p.category_id)
                for cid in product_to_category_ids.get(p.id, []):
                    category_ids_needed.add(cid)
            if category_ids_needed:
                cats = (
                    (await session.execute(sa.select(Category).where(Category.id.in_(category_ids_needed))))
                    .scalars()
                    .all()
                )
                category_map = {c.id: c for c in cats}
            global_multiplier = await logic.get_global_multiplier(session)

    buf = io.StringIO()
    writer = csv.writer(buf)
    price_header = "进价" if price_mode == "cost" else "标准零售价"
    writer.writerow(["名称", "规格", "当前箱数", "当前散数", "建议补货箱数", price_header, "image链接"])

    written = 0
    for p in products:
        box_qty, loose_qty = inventory_map.get(p.id, (0, 0))
        spec_qty = logic.parse_spec_qty(p.spec)
        total_units = box_qty * spec_qty + (loose_qty or 0)
        current_boxes_equiv = (total_units / spec_qty) if spec_qty else float(box_qty)

        if need_mode == "out_of_stock":
            should_include = current_boxes_equiv <= 0
        else:
            should_include = current_boxes_equiv < target_boxes

        suggest_boxes = max(0, int(math.ceil(target_boxes - current_boxes_equiv))) if should_include else 0
        if only_need and suggest_boxes <= 0:
            continue

        unit_price = _price_for_product(
            product=p,
            price_mode=price_mode,
            category_map=category_map,
            product_to_category_ids=product_to_category_ids,
            global_multiplier=global_multiplier,
        )
        writer.writerow(
            [
                p.name,
                p.spec or "",
                int(box_qty or 0),
                int(loose_qty or 0),
                int(suggest_boxes),
                f"{float(unit_price):.2f}",
                (p.img_url or "").strip(),
            ]
        )
        written += 1

    return _csv_bytes(buf.getvalue(), encoding=encoding)
