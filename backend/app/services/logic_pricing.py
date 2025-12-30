import math
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import Category, Inventory, Product, ProductCategory
from app.services.logic_system import get_global_multiplier_range
from app.services.logic_utils import get_piece_cost_price, normalize_spec, round2, get_units_per_box, get_pieces_per_unit


def _mult_range_from_category(cat: Category | None) -> tuple[float, float] | None:
    if not cat:
        return None
    min_val = cat.retail_multiplier_min if cat.retail_multiplier_min is not None else cat.retail_multiplier
    max_val = cat.retail_multiplier_max if cat.retail_multiplier_max is not None else cat.retail_multiplier
    if min_val is None and max_val is None:
        return None
    if min_val is None:
        min_val = max_val
    if max_val is None:
        max_val = min_val
    min_val = float(min_val or 0)
    max_val = float(max_val or 0)
    if max_val < min_val:
        max_val = min_val
    return min_val, max_val


def _pick_price_from_range(base_cost: float, min_mult: float, max_mult: float) -> float:
    min_mult = float(min_mult or 0)
    max_mult = float(max_mult or 0)
    if min_mult <= 0 and max_mult <= 0:
        return round2(base_cost)
    if max_mult < min_mult:
        max_mult = min_mult
    min_price = max(0.0, base_cost * min_mult)
    max_price = max(min_price, base_cost * max_mult)
    if max_price <= 0:
        return 0.0

    lower = math.ceil(min_price / 5.0) * 5.0
    upper = math.floor(max_price / 5.0) * 5.0
    if lower <= upper:
        mid = (min_price + max_price) / 2.0
        cand = round(mid / 5.0) * 5.0
        cand = min(max(cand, lower), upper)
        return round2(cand if cand > 0 else lower or upper or min_price)

    cand = round(min_price / 5.0) * 5.0
    if cand < min_price:
        cand = min_price
    if cand > max_price:
        cand = max_price
    return round2(cand)


def _standard_price_for_product(
    product: Product,
    *,
    category_map: dict[str, Category],
    product_to_category_ids: dict[str, list[str]],
    global_range: tuple[float, float],
) -> tuple[float, str]:
    base_cost = get_piece_cost_price(product)
    if product.fixed_retail_price is not None and product.fixed_retail_price > 0:
        return float(product.fixed_retail_price), "例外价"

    if product.retail_multiplier:
        rng = (float(product.retail_multiplier), float(product.retail_multiplier))
        price = _pick_price_from_range(base_cost, rng[0], rng[1])
        return price, "分类系数"

    best_range: tuple[float, float] | None = None
    best_max = -1.0

    def consider(cat_id: str | None):
        nonlocal best_range, best_max
        if not cat_id:
            return
        cat = category_map.get(cat_id)
        rng = _mult_range_from_category(cat)
        if not rng:
            return
        if rng[1] > best_max:
            best_range = rng
            best_max = rng[1]

    consider(product.category_id)
    for cid in product_to_category_ids.get(product.id, []):
        consider(cid)

    if best_range:
        price = _pick_price_from_range(base_cost, best_range[0], best_range[1])
        return price, "分类系数"

    g_min, g_max = global_range
    price = _pick_price_from_range(base_cost, g_min, g_max)
    return price, "全局系数"


def _price_range_for_product(
    product: Product,
    *,
    category_map: dict[str, Category],
    product_to_category_ids: dict[str, list[str]],
    global_range: tuple[float, float],
) -> tuple[float, float]:
    def snap_range(min_price: float, max_price: float) -> tuple[float, float]:
        if max_price < min_price:
            max_price = min_price
        lower = math.ceil(min_price / 5.0) * 5.0
        upper = math.floor(max_price / 5.0) * 5.0
        if lower <= upper:
            return round2(lower), round2(upper)
        approx = round(min_price / 5.0) * 5.0
        if approx < min_price:
            approx = min_price
        if approx > max_price:
            approx = max_price
        return round2(approx), round2(approx)

    base = get_piece_cost_price(product)
    if product.fixed_retail_price is not None and product.fixed_retail_price > 0:
        val = float(product.fixed_retail_price)
        return val, val
    if product.retail_multiplier:
        val = base * float(product.retail_multiplier)
        return round2(val), round2(val)

    best_range: tuple[float, float] | None = None
    best_max = -1.0

    def consider(cat_id: str | None):
        nonlocal best_range, best_max
        if not cat_id:
            return
        cat = category_map.get(cat_id)
        rng = _mult_range_from_category(cat)
        if not rng:
            return
        if rng[1] > best_max:
            best_range = rng
            best_max = rng[1]

    consider(product.category_id)
    for cid in product_to_category_ids.get(product.id, []):
        consider(cid)

    if best_range:
        return snap_range(base * best_range[0], base * best_range[1])

    gmin, gmax = global_range
    return snap_range(base * gmin, base * gmax)


async def calculate_price_for_product(session: AsyncSession, product: Product) -> schemas.PriceCalcResponse:
    stmt_pc = sa.select(ProductCategory.category_id).where(ProductCategory.product_id == product.id)
    pc_ids = [row[0] for row in (await session.execute(stmt_pc)).all()]
    category_ids_needed = set(pc_ids)
    if product.category_id:
        category_ids_needed.add(product.category_id)
    category_map: dict[str, Category] = {}
    if category_ids_needed:
        cats = (await session.execute(sa.select(Category).where(Category.id.in_(category_ids_needed)))).scalars().all()
        category_map = {c.id: c for c in cats}
    product_to_category_ids = {product.id: pc_ids}
    global_range = await get_global_multiplier_range(session)

    price, basis = _standard_price_for_product(
        product,
        category_map=category_map,
        product_to_category_ids=product_to_category_ids,
        global_range=global_range,
    )
    return schemas.PriceCalcResponse(price=price, basis=basis)


async def list_pricing_overview(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    keyword: str | None = None,
    only_in_stock: bool = False,
    custom_category_id: str | None = None,
) -> tuple[list[schemas.PricingOverviewItem], int, str]:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    where_clause = []
    if keyword:
        like = f"%{keyword}%"
        where_clause.append(Product.name.ilike(like))
    if custom_category_id:
        subq = sa.select(ProductCategory.product_id).where(ProductCategory.category_id == custom_category_id)
        where_clause.append(Product.id.in_(subq))

    count_stmt = sa.select(sa.func.count()).select_from(Product)
    if where_clause:
        count_stmt = count_stmt.where(*where_clause)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = sa.select(Product)
    if where_clause:
        stmt = stmt.where(*where_clause)
    stmt = stmt.order_by(Product.name).offset(offset).limit(limit)
    products = (await session.execute(stmt)).scalars().all()
    if not products:
        return [], 0, "empty"

    product_ids = [p.id for p in products]

    inv_stmt = (
        sa.select(Inventory.product_id, sa.func.sum(Inventory.current_stock))
        .where(Inventory.product_id.in_(product_ids))
        .group_by(Inventory.product_id)
    )
    inv_rows = await session.execute(inv_stmt)
    inventory_map: dict[str, int] = {}
    for pid, total_qty in inv_rows.all():
        inventory_map[pid] = int(total_qty or 0)

    pc_stmt = sa.select(ProductCategory.product_id, ProductCategory.category_id).where(
        ProductCategory.product_id.in_(product_ids)
    )
    pc_rows = await session.execute(pc_stmt)
    product_to_category_ids: dict[str, list[str]] = {}
    for pid, cid in pc_rows.all():
        product_to_category_ids.setdefault(pid, []).append(cid)

    category_ids_needed = set()
    for p in products:
        if p.category_id:
            category_ids_needed.add(p.category_id)
        for cid in product_to_category_ids.get(p.id, []):
            category_ids_needed.add(cid)
    category_map: dict[str, Category] = {}
    if category_ids_needed:
        cats = (await session.execute(sa.select(Category).where(Category.id.in_(category_ids_needed)))).scalars().all()
        category_map = {c.id: c for c in cats}

    result: list[schemas.PricingOverviewItem] = []
    global_range = await get_global_multiplier_range(session)
    max_ts = None
    for product in products:
        stock_units = int(inventory_map.get(product.id, 0))
        if only_in_stock and stock_units <= 0:
            continue

        spec_clean = normalize_spec(product.spec)
        price_val, basis = _standard_price_for_product(
            product,
            category_map=category_map,
            product_to_category_ids=product_to_category_ids,
            global_range=global_range,
        )

        category_names: list[str] = []
        all_category_ids: list[str] = []
        custom_category_ids: list[str] = []
        if product.category_id and product.category_id in category_map:
            cat = category_map[product.category_id]
            category_names.append(cat.name)
            all_category_ids.append(cat.id)
            if getattr(cat, "is_custom", False):
                custom_category_ids.append(cat.id)
        for cid in product_to_category_ids.get(product.id, []):
            cat = category_map.get(cid)
            if cat and cat.name not in category_names:
                category_names.append(cat.name)
            if cat and cat.id not in all_category_ids:
                all_category_ids.append(cat.id)
            if cat and getattr(cat, "is_custom", False) and cat.id not in custom_category_ids:
                custom_category_ids.append(cat.id)
        category_label = "、".join([n for n in category_names if n]) or None

        result.append(
            schemas.PricingOverviewItem(
                id=product.id,
                name=product.name,
                spec=spec_clean,
                category_name=category_label,
                category_ids=all_category_ids,
                custom_category_ids=custom_category_ids,
                stock=stock_units,
                units_per_box=get_units_per_box(product),
                pieces_per_unit=get_pieces_per_unit(product),
                standard_price=price_val,
                price_basis=basis,
                img_url=product.img_url,
                video_url=product.video_url,
                effect_url=product.effect_url,
                barcode=product.barcode,
            )
        )
        if product.updated_at:
            max_ts = max(max_ts or product.updated_at, product.updated_at)
    version = (max_ts or datetime.utcnow()).isoformat()
    return result, total, version
