from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import (
    Category,
    Inventory,
    InventoryLog,
    Product,
    ProductCategory,
)
from app.services.logic_pricing import _price_range_for_product
from app.services.logic_system import get_global_multiplier_range
from app.services.logic_utils import (
    get_box_cost_price,
    get_piece_cost_price,
    get_pieces_per_box,
    get_pieces_per_unit,
    get_units_per_box,
    round2,
    split_stock,
)


async def get_inventory_record(
    session: AsyncSession,
    product_id: str,
    warehouse_id: str = "default",
    create_if_missing: bool = True,
) -> Inventory | None:
    stmt = (
        sa.select(Inventory)
        .where(
            Inventory.product_id == product_id, Inventory.warehouse_id == warehouse_id
        )
        .with_for_update()
    )
    inv = (await session.execute(stmt)).scalars().first()
    if inv:
        return inv
    if not create_if_missing:
        return None
    inv = Inventory(
        product_id=product_id, warehouse_id=warehouse_id, current_stock=0, loose_units=0
    )
    session.add(inv)
    await session.flush()
    return inv


def apply_unit_delta(inv: Inventory, product: Product, delta_units: int) -> None:
    total_units = int(inv.current_stock or 0) + int(delta_units or 0)
    if total_units < 0:
        total_units = 0
    inv.current_stock = int(total_units)
    inv.loose_units = 0
    inv.updated_at = datetime.utcnow()


async def log_inventory(
    session: AsyncSession,
    product_id: str,
    qty: int,
    ref_type: str,
    ref_id: str,
    warehouse_id: str = "default",
):
    log = InventoryLog(
        product_id=product_id,
        warehouse_id=warehouse_id,
        change_qty=qty,
        type="auto",
        ref_type=ref_type,
        ref_id=ref_id,
    )
    session.add(log)
    await session.flush()


async def adjust_inventory(
    session: AsyncSession, req: schemas.InventoryAdjustRequest, username: str
) -> Inventory:
    product = await session.get(Product, req.product_id)
    if not product:
        raise ValueError("product not found")
    inv = await get_inventory_record(session, req.product_id, create_if_missing=True)
    if not inv:
        raise ValueError("inventory record not found")
    assert inv is not None
    apply_unit_delta(inv, product, req.delta)
    await log_inventory(session, req.product_id, req.delta, "adjust", ref_id=username)
    return inv


async def dashboard_inventory_value(
    session: AsyncSession,
) -> tuple[float, float, float, int, float]:
    cost_total = 0.0
    retail_min_total = 0.0
    retail_max_total = 0.0
    sku_with_stock = set()
    total_boxes = 0.0
    inv_rows = (await session.execute(sa.select(Inventory))).scalars().all()
    global_range = await get_global_multiplier_range(session)
    for inv in inv_rows:
        product = await session.get(Product, inv.product_id)
        if not product:
            continue
        stmt_pc = sa.select(ProductCategory.category_id).where(
            ProductCategory.product_id == product.id
        )
        pc_ids = [row[0] for row in (await session.execute(stmt_pc)).all()]
        category_ids_needed = set(pc_ids)
        if product.category_id:
            category_ids_needed.add(product.category_id)
        category_map: dict[str, Category] = {}
        if category_ids_needed:
            cats = (
                (
                    await session.execute(
                        sa.select(Category).where(Category.id.in_(category_ids_needed))
                    )
                )
                .scalars()
                .all()
            )
            category_map = {c.id: c for c in cats}
        price_min, price_max = _price_range_for_product(
            product,
            category_map=category_map,
            product_to_category_ids={product.id: pc_ids},
            global_range=global_range,
        )
        total_units = int(inv.current_stock or 0)
        if total_units > 0:
            sku_with_stock.add(product.id)
            total_boxes += total_units / get_pieces_per_box(product)
        cost_total += get_piece_cost_price(product) * total_units
        retail_min_total += price_min * total_units
        retail_max_total += price_max * total_units
    return (
        cost_total,
        retail_min_total,
        retail_max_total,
        len(sku_with_stock),
        round2(total_boxes),
    )


async def inventory_by_category(session: AsyncSession) -> list[dict]:
    categories = (
        (await session.execute(sa.select(Category).where(Category.is_custom.is_(True))))
        .scalars()
        .all()
    )
    all_categories = (await session.execute(sa.select(Category))).scalars().all()
    category_map_all = {c.id: c for c in all_categories}

    cat_map = {c.id: c for c in categories}
    cat_data = {
        c.id: {
            "id": c.id,
            "name": c.name,
            "sku": 0,
            "boxes": 0.0,
            "cost": 0.0,
            "retail": 0.0,
            "retail_min": 0.0,
            "retail_max": 0.0,
        }
        for c in categories
    }
    uncategorized_id = "__uncategorized__"
    cat_data[uncategorized_id] = {
        "id": uncategorized_id,
        "name": "未分组",
        "sku": 0,
        "boxes": 0.0,
        "cost": 0.0,
        "retail": 0.0,
        "retail_min": 0.0,
        "retail_max": 0.0,
    }

    if cat_map:
        pc_rows = (
            await session.execute(
                sa.select(
                    ProductCategory.product_id, ProductCategory.category_id
                ).where(ProductCategory.category_id.in_(list(cat_map.keys())))
            )
        ).all()
        product_to_custom: dict[str, set[str]] = {}
        for pid, cid in pc_rows:
            product_to_custom.setdefault(pid, set()).add(cid)
    else:
        product_to_custom = {}

    inv_rows = (await session.execute(sa.select(Inventory))).scalars().all()
    global_range = await get_global_multiplier_range(session)
    for inv in inv_rows:
        product = await session.get(Product, inv.product_id)
        if not product:
            continue
        custom_ids: set[str] = set()
        if product.category_id and product.category_id in cat_map:
            custom_ids.add(product.category_id)
        if product.id in product_to_custom:
            custom_ids.update(product_to_custom[product.id])
        if not custom_ids:
            custom_ids.add(uncategorized_id)

        price_min, price_max = _price_range_for_product(
            product,
            category_map=category_map_all,
            product_to_category_ids={product.id: list(custom_ids)},
            global_range=global_range,
        )
        total_units = int(inv.current_stock or 0)
        if total_units <= 0:
            continue
        for cid in custom_ids:
            category = cat_map.get(cid)
            data = cat_data.setdefault(
                cid,
                {
                    "id": cid,
                    "name": category.name if category else "未分组",
                    "sku": 0,
                    "boxes": 0.0,
                    "cost": 0.0,
                    "retail": 0.0,
                    "retail_min": 0.0,
                    "retail_max": 0.0,
                },
            )
            data["sku"] += 1
            data["boxes"] += total_units / get_pieces_per_box(product)
            data["cost"] += get_piece_cost_price(product) * total_units
            data["retail"] += price_max * total_units
            data["retail_min"] += price_min * total_units
            data["retail_max"] += price_max * total_units

    for d in cat_data.values():
        d["boxes"] = round2(d["boxes"])
        d["cost"] = round2(d["cost"])
        d["retail"] = round2(d["retail"])
        d["retail_min"] = round2(d.get("retail_min") or 0)
        d["retail_max"] = round2(d.get("retail_max") or d.get("retail") or 0)
    return sorted(cat_data.values(), key=lambda x: x["cost"], reverse=True)


async def inventory_overview(
    session: AsyncSession, with_version: bool = False
) -> (
    tuple[list[schemas.InventoryOverviewItem], str]
    | list[schemas.InventoryOverviewItem]
):
    inv_rows = (await session.execute(sa.select(Inventory))).scalars().all()
    items: list[schemas.InventoryOverviewItem] = []
    max_ts = None
    for inv in inv_rows:
        product = await session.get(Product, inv.product_id)
        if not product:
            continue
        total_units = int(inv.current_stock or 0)
        box_count, unit_count, piece_count = split_stock(total_units, product)
        box_price = get_box_cost_price(product)
        category_name = None
        if product.category_id:
            category = await session.get(Category, product.category_id)
            category_name = category.name if category else None
        cost_total = get_piece_cost_price(product) * total_units
        items.append(
            schemas.InventoryOverviewItem(
                product_id=product.id,
                name=product.name,
                spec=product.spec,
                category_name=category_name,
                base_cost_price=get_piece_cost_price(product),
                box_cost_price=get_box_cost_price(product),
                units_per_box=get_units_per_box(product),
                pieces_per_unit=get_pieces_per_unit(product),
                box_price=round2(box_price),
                box_count=box_count,
                loose_count=unit_count,
                unit_count=unit_count,
                piece_count=piece_count,
                cost_total=round2(cost_total),
            )
        )
        if inv.updated_at:
            max_ts = max(max_ts or inv.updated_at, inv.updated_at)
    version = (max_ts or datetime.utcnow()).isoformat()
    return (items, version) if with_version else items
