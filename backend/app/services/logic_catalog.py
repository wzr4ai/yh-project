import asyncio
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import Category, Inventory, Product, ProductBarcode, ProductCategory
from app.services.logic_pricing import _price_range_for_product, _standard_price_for_product
from app.services.logic_system import get_global_multiplier_range
from app.services.logic_utils import (
    barcode_multiplier,
    get_box_cost_price,
    get_piece_cost_price,
    get_pieces_per_unit,
    get_units_per_box,
    normalize_spec,
    round2,
    _safe_int,
)


def build_product_list_item(
    product: Product,
    *,
    total_units: int,
    category_map: dict[str, Category],
    product_to_category_ids: dict[str, list[str]],
    global_range: tuple[float, float],
    barcode_value: str | None = None,
) -> schemas.ProductListItem:
    price_val, basis = _standard_price_for_product(
        product,
        category_map=category_map,
        product_to_category_ids=product_to_category_ids,
        global_range=global_range,
    )
    price_min, price_max = _price_range_for_product(
        product,
        category_map=category_map,
        product_to_category_ids=product_to_category_ids,
        global_range=global_range,
    )
    category_names: list[str] = []
    category_ids: list[str] = []
    if product.category_id and product.category_id in category_map:
        category = category_map[product.category_id]
        category_names.append(category.name)
        category_ids.append(category.id)
    for cid in product_to_category_ids.get(product.id, []):
        cat = category_map.get(cid)
        if not cat:
            continue
        if cat.name not in category_names:
            category_names.append(cat.name)
        if cat.id not in category_ids:
            category_ids.append(cat.id)
    retail_total = price_val * total_units
    cost_total = get_piece_cost_price(product) * total_units
    spec_clean = normalize_spec(product.spec)
    return schemas.ProductListItem(
        id=product.id,
        name=product.name,
        spec=spec_clean,
        category_name="、".join([n for n in category_names if n]) or None,
        category_ids=category_ids,
        base_cost_price=get_piece_cost_price(product),
        units_per_box=get_units_per_box(product),
        pieces_per_unit=get_pieces_per_unit(product),
        box_cost_price=get_box_cost_price(product),
        standard_price=price_val,
        price_min=price_min,
        price_max=price_max,
        price_basis=basis,
        stock=int(total_units),
        retail_total=round2(price_max * total_units if basis != "例外价" else retail_total),
        cost_total=round2(cost_total),
        video_url=product.video_url,
        effect_url=product.effect_url,
        barcode=barcode_value or product.barcode,
    )


async def replace_product_categories(session: AsyncSession, product_id: str, category_ids: list[str]):
    await session.execute(sa.delete(ProductCategory).where(ProductCategory.product_id == product_id))
    unique_ids = [cid for cid in dict.fromkeys(category_ids) if cid]
    if unique_ids:
        session.add_all([ProductCategory(product_id=product_id, category_id=cid) for cid in unique_ids])
    await session.flush()


async def ensure_product_barcode(session: AsyncSession, product_id: str, barcode: str, level: str) -> None:
    code = (barcode or "").strip()
    if not code:
        return
    existing = (await session.execute(sa.select(ProductBarcode).where(ProductBarcode.barcode == code))).scalars().first()
    if existing:
        if existing.product_id == product_id and level:
            existing.level = level
        return
    session.add(ProductBarcode(product_id=product_id, barcode=code, level=level or "PIECE"))
    await session.flush()


async def replace_product_barcodes(session: AsyncSession, product_id: str, barcodes: list[schemas.ProductBarcode]) -> None:
    await session.execute(sa.delete(ProductBarcode).where(ProductBarcode.product_id == product_id))
    unique_codes: dict[str, str] = {}
    for item in barcodes or []:
        code = (item.barcode or "").strip()
        if not code:
            continue
        if code in unique_codes:
            continue
        unique_codes[code] = (item.level or "PIECE").upper()
    if unique_codes:
        session.add_all(
            [
                ProductBarcode(product_id=product_id, barcode=code, level=level)
                for code, level in unique_codes.items()
            ]
        )
    await session.flush()


def extract_category_ids(categories: list[object]) -> list[str]:
    ids: list[str] = []
    for c in categories:
        if isinstance(c, dict) and "id" in c:
            ids.append(c["id"])
        elif hasattr(c, "id"):
            ids.append(getattr(c, "id"))
        elif isinstance(c, str):
            ids.append(c)
    return ids


async def create_product(session: AsyncSession, payload: schemas.Product) -> Product:
    fixed_price = payload.fixed_retail_price if (payload.fixed_retail_price or 0) > 0 else None
    spec_value = normalize_spec(payload.spec)
    product = Product(
        id=payload.id or None,
        name=payload.name,
        category_id=payload.category_id,
        spec=spec_value,
        units_per_box=_safe_int(payload.units_per_box, default=1),
        pieces_per_unit=_safe_int(payload.pieces_per_unit, default=1),
        box_cost_price=float(payload.box_cost_price or 0),
        base_cost_price=float(payload.base_cost_price or 0),
        fixed_retail_price=fixed_price,
        retail_multiplier=payload.retail_multiplier,
        pack_price_ref=payload.pack_price_ref,
        img_url=payload.img_url,
        video_url=payload.video_url,
        effect_url=payload.effect_url,
        barcode=payload.barcode,
    )
    session.add(product)
    await session.flush()
    if payload.categories:
        category_ids = extract_category_ids(payload.categories)
        await replace_product_categories(session, product.id, category_ids)
    if payload.barcodes is not None:
        await replace_product_barcodes(session, product.id, payload.barcodes)
    elif payload.barcode:
        await ensure_product_barcode(session, product.id, payload.barcode, "PIECE")
    await session.flush()
    product.updated_at = datetime.utcnow()
    return product


async def update_product(session: AsyncSession, product_id: str, payload: schemas.Product) -> Product:
    fixed_price = payload.fixed_retail_price if (payload.fixed_retail_price or 0) > 0 else None
    spec_value = normalize_spec(payload.spec)
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    product.name = payload.name or product.name
    product.category_id = payload.category_id
    product.spec = spec_value
    product.units_per_box = _safe_int(payload.units_per_box, default=product.units_per_box or 1)
    product.pieces_per_unit = _safe_int(payload.pieces_per_unit, default=product.pieces_per_unit or 1)
    product.box_cost_price = float(payload.box_cost_price or 0)
    product.base_cost_price = float(payload.base_cost_price or 0)
    product.fixed_retail_price = fixed_price
    product.retail_multiplier = payload.retail_multiplier
    product.pack_price_ref = payload.pack_price_ref
    product.img_url = payload.img_url
    product.video_url = payload.video_url
    product.effect_url = payload.effect_url
    product.barcode = payload.barcode
    product.updated_at = datetime.utcnow()
    if payload.categories is not None:
        category_ids = extract_category_ids(payload.categories)
        await replace_product_categories(session, product_id, category_ids)
    if payload.barcodes is not None:
        await replace_product_barcodes(session, product_id, payload.barcodes)
    elif payload.barcode:
        await ensure_product_barcode(session, product_id, payload.barcode, "PIECE")
    await session.flush()
    return product


async def update_product_retail_price(session: AsyncSession, product_id: str, new_price: float | None) -> Product:
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    price = None
    if new_price is not None:
        try:
            price_val = float(new_price)
        except Exception:
            price_val = None
        if price_val is not None and price_val > 0:
            price = price_val
    product.fixed_retail_price = price
    product.updated_at = datetime.utcnow()
    await session.flush()
    return product


async def delete_product(session: AsyncSession, product_id: str):
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    await session.execute(sa.delete(ProductCategory).where(ProductCategory.product_id == product_id))
    await session.execute(sa.delete(Inventory).where(Inventory.product_id == product_id))
    await session.delete(product)
    await session.flush()


async def product_with_category(session: AsyncSession, product_id: str) -> schemas.Product:
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    clean_spec = normalize_spec(product.spec)
    category_name = None
    categories: list[schemas.Category] = []
    if product.category_id:
        category = await session.get(Category, product.category_id)
        category_name = category.name if category else None
        if category:
            categories.append(
                schemas.Category(
                    id=category.id,
                    name=category.name,
                    retail_multiplier=category.retail_multiplier,
                    is_custom=category.is_custom,
                )
            )
    stmt = sa.select(Category).join(ProductCategory, Category.id == ProductCategory.category_id).where(
        ProductCategory.product_id == product.id
    )
    extra = (await session.execute(stmt)).scalars().all()
    for c in extra:
        if not any(x.id == c.id for x in categories):
            categories.append(
                schemas.Category(id=c.id, name=c.name, retail_multiplier=c.retail_multiplier, is_custom=c.is_custom)
            )

    barcode_rows = (
        await session.execute(sa.select(ProductBarcode).where(ProductBarcode.product_id == product.id))
    ).scalars().all()
    barcode_items = [schemas.ProductBarcode(id=bc.id, barcode=bc.barcode, level=bc.level) for bc in barcode_rows]

    return schemas.Product(
        id=product.id,
        name=product.name,
        category_id=product.category_id,
        category_name=category_name,
        categories=categories,
        spec=clean_spec,
        units_per_box=get_units_per_box(product),
        pieces_per_unit=get_pieces_per_unit(product),
        box_cost_price=get_box_cost_price(product),
        base_cost_price=get_piece_cost_price(product),
        fixed_retail_price=product.fixed_retail_price,
        retail_multiplier=product.retail_multiplier,
        pack_price_ref=product.pack_price_ref,
        img_url=product.img_url,
        video_url=product.video_url,
        effect_url=product.effect_url,
        barcode=product.barcode,
        barcodes=barcode_items,
    )


async def create_category(session: AsyncSession, payload: schemas.Category) -> Category:
    category = Category(
        id=payload.id or None,
        name=payload.name,
        retail_multiplier=payload.retail_multiplier,
        retail_multiplier_min=payload.retail_multiplier_min,
        retail_multiplier_max=payload.retail_multiplier_max,
        is_custom=payload.is_custom if payload.is_custom is not None else True,
    )
    session.add(category)
    await session.flush()
    return category


async def delete_category(session: AsyncSession, category_id: str, force: bool = False) -> int:
    category = await session.get(Category, category_id)
    if not category:
        raise ValueError("category not found")
    count_stmt = sa.select(sa.func.count()).select_from(Product).where(Product.category_id == category_id)
    count = (await session.execute(count_stmt)).scalar_one()
    if count > 0 and not force:
        raise ValueError(f"category not empty:{count}")
    if count > 0:
        await session.execute(sa.update(Product).where(Product.category_id == category_id).values(category_id=None))
    await session.execute(sa.delete(ProductCategory).where(ProductCategory.category_id == category_id))
    await session.delete(category)
    await session.flush()
    return count


async def upsert_category(session: AsyncSession, category_id: str, payload: schemas.Category) -> Category:
    stmt = sa.select(Category).where(Category.id == category_id)
    existing = (await session.execute(stmt)).scalars().first()
    if existing:
        existing.name = payload.name
        existing.retail_multiplier = payload.retail_multiplier
        existing.retail_multiplier_min = payload.retail_multiplier_min
        existing.retail_multiplier_max = payload.retail_multiplier_max
        if payload.is_custom is not None:
            existing.is_custom = payload.is_custom
        await session.flush()
        return existing
    category = Category(
        id=payload.id or category_id,
        name=payload.name,
        retail_multiplier=payload.retail_multiplier,
        retail_multiplier_min=payload.retail_multiplier_min,
        retail_multiplier_max=payload.retail_multiplier_max,
        is_custom=payload.is_custom if payload.is_custom is not None else True,
    )
    session.add(category)
    await session.flush()
    return category


async def list_products_with_inventory(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 50,
    category_id: str | None = None,
    category_ids: list[str] | None = None,
    custom_category_ids: list[str] | None = None,
    merchant_category_ids: list[str] | None = None,
    keyword: str | None = None,
) -> tuple[list[schemas.ProductListItem], int, str]:
    where_clause = []
    custom_ids = set([c for c in (custom_category_ids or []) if c])
    if category_ids:
        custom_ids.update([c for c in category_ids if c])
    merchant_ids = set([c for c in (merchant_category_ids or []) if c])
    if category_id:
        merchant_ids.add(category_id)

    if merchant_ids:
        if "__uncategorized__" in merchant_ids:
            where_clause.append(
                sa.or_(
                    Product.category_id.is_(None),
                    Product.category_id.in_([m for m in merchant_ids if m != "__uncategorized__"]),
                )
            )
        else:
            where_clause.append(Product.category_id.in_(list(merchant_ids)))
    if custom_ids:
        subq = sa.select(ProductCategory.product_id).where(ProductCategory.category_id.in_(list(custom_ids)))
        where_clause.append(Product.id.in_(subq))
    if keyword:
        like = f"%{keyword}%"
        where_clause.append(Product.name.ilike(like))

    count_stmt = sa.select(sa.func.count()).select_from(Product)
    if where_clause:
        count_stmt = count_stmt.where(*where_clause)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = sa.select(Product)
    if where_clause:
        stmt = stmt.where(*where_clause)
    stmt = stmt.offset(offset).limit(limit)
    products = (await session.execute(stmt)).scalars().all()
    if not products:
        return [], 0, "empty"

    product_ids = [p.id for p in products]

    inv_stmt = (
        sa.select(Inventory.product_id, sa.func.sum(Inventory.current_stock))
        .where(Inventory.product_id.in_(product_ids))
        .group_by(Inventory.product_id)
    )
    pc_stmt = sa.select(ProductCategory.product_id, ProductCategory.category_id).where(
        ProductCategory.product_id.in_(product_ids)
    )
    inv_rows, pc_rows = await asyncio.gather(
        session.execute(inv_stmt),
        session.execute(pc_stmt),
    )

    inventory_map: dict[str, int] = {}
    for pid, total_qty in inv_rows.all():
        inventory_map[pid] = int(total_qty or 0)

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

    result: list[schemas.ProductListItem] = []
    global_range = await get_global_multiplier_range(session)
    max_ts = None
    for product in products:
        total_units = inventory_map.get(product.id, 0)
        price_val, basis = _standard_price_for_product(
            product,
            category_map=category_map,
            product_to_category_ids=product_to_category_ids,
            global_range=global_range,
        )
        price_min, price_max = _price_range_for_product(
            product,
            category_map=category_map,
            product_to_category_ids=product_to_category_ids,
            global_range=global_range,
        )

        retail_total = price_val * total_units
        cost_total = get_piece_cost_price(product) * total_units
        category_name = None
        category_names: list[str] = []
        category_ids: list[str] = []
        if product.category_id and product.category_id in category_map:
            category = category_map[product.category_id]
            category_name = category.name
            category_names.append(category.name)
            category_ids.append(category.id)
        for cid in product_to_category_ids.get(product.id, []):
            cat = category_map.get(cid)
            if not cat:
                continue
            if cat.name not in category_names:
                category_names.append(cat.name)
            if cat.id not in category_ids:
                category_ids.append(cat.id)
        result.append(
            schemas.ProductListItem(
                id=product.id,
                name=product.name,
                spec=normalize_spec(product.spec),
                category_name="、".join([n for n in category_names if n]) or category_name,
                category_ids=category_ids,
                base_cost_price=get_piece_cost_price(product),
                units_per_box=get_units_per_box(product),
                pieces_per_unit=get_pieces_per_unit(product),
                box_cost_price=get_box_cost_price(product),
                standard_price=price_val,
                price_min=price_min,
                price_max=price_max,
                price_basis=basis,
                stock=int(total_units),
                retail_total=round2(price_max * total_units if basis != "例外价" else retail_total),
                cost_total=round2(cost_total),
                video_url=product.video_url,
                effect_url=product.effect_url,
                barcode=product.barcode,
            )
        )
        if product.updated_at:
            max_ts = max(max_ts or product.updated_at, product.updated_at)
    version = (max_ts or datetime.utcnow()).isoformat()
    return result, total, version


async def product_by_barcode(session: AsyncSession, barcode: str) -> schemas.BarcodeLookupResponse:
    code = (barcode or "").strip()
    if not code:
        raise ValueError("barcode empty")
    barcode_row = (
        await session.execute(sa.select(ProductBarcode).where(ProductBarcode.barcode == code))
    ).scalars().first()
    product = None
    level = "PIECE"
    matched_barcode = code
    if barcode_row:
        product = await session.get(Product, barcode_row.product_id)
        level = barcode_row.level
        matched_barcode = barcode_row.barcode
    else:
        product = (await session.execute(sa.select(Product).where(Product.barcode == code))).scalars().first()
    if not product:
        raise ValueError("product not found")

    inv_stmt = sa.select(sa.func.sum(Inventory.current_stock)).where(Inventory.product_id == product.id)
    total_units = int((await session.execute(inv_stmt)).scalar() or 0)

    pc_rows = (
        await session.execute(sa.select(ProductCategory.category_id).where(ProductCategory.product_id == product.id))
    ).all()
    extra_category_ids = [row[0] for row in pc_rows]

    category_ids_needed = set(extra_category_ids)
    if product.category_id:
        category_ids_needed.add(product.category_id)
    category_map: dict[str, Category] = {}
    if category_ids_needed:
        cats = (await session.execute(sa.select(Category).where(Category.id.in_(category_ids_needed)))).scalars().all()
        category_map = {c.id: c for c in cats}

    item = build_product_list_item(
        product,
        total_units=total_units,
        category_map=category_map,
        product_to_category_ids={product.id: extra_category_ids},
        global_range=await get_global_multiplier_range(session),
        barcode_value=matched_barcode,
    )
    multiplier = barcode_multiplier(product, level)
    return schemas.BarcodeLookupResponse(
        product=item,
        barcode=matched_barcode,
        level=level,
        multiplier=multiplier,
    )


async def list_products_by_barcode_suffix(
    session: AsyncSession, suffix: str, limit: int = 10
) -> list[schemas.BarcodeLookupResponse]:
    code = (suffix or "").strip()
    if not code:
        raise ValueError("barcode empty")
    limit = max(1, min(limit, 50))
    stmt = (
        sa.select(ProductBarcode, Product)
        .join(Product, Product.id == ProductBarcode.product_id)
        .where(ProductBarcode.barcode.ilike(f"%{code}"))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    if not rows:
        legacy_stmt = (
            sa.select(Product)
            .where(Product.barcode.is_not(None))
            .where(Product.barcode.ilike(f"%{code}"))
            .limit(limit)
        )
        products = (await session.execute(legacy_stmt)).scalars().all()
        if not products:
            return []
        rows = [(None, p) for p in products]

    products = [row[1] for row in rows]
    product_ids = [p.id for p in products]
    inv_stmt = (
        sa.select(Inventory.product_id, sa.func.sum(Inventory.current_stock))
        .where(Inventory.product_id.in_(product_ids))
        .group_by(Inventory.product_id)
    )
    pc_stmt = sa.select(ProductCategory.product_id, ProductCategory.category_id).where(
        ProductCategory.product_id.in_(product_ids)
    )
    inv_rows, pc_rows = await asyncio.gather(
        session.execute(inv_stmt),
        session.execute(pc_stmt),
    )

    inventory_map: dict[str, int] = {}
    for pid, total_qty in inv_rows.all():
        inventory_map[pid] = int(total_qty or 0)

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

    result: list[schemas.BarcodeLookupResponse] = []
    global_range = await get_global_multiplier_range(session)
    for barcode_row, product in rows:
        total_units = inventory_map.get(product.id, 0)
        barcode_value = barcode_row.barcode if barcode_row else product.barcode
        level = barcode_row.level if barcode_row else "PIECE"
        item = build_product_list_item(
            product,
            total_units=total_units,
            category_map=category_map,
            product_to_category_ids=product_to_category_ids,
            global_range=global_range,
            barcode_value=barcode_value,
        )
        result.append(
            schemas.BarcodeLookupResponse(
                product=item,
                barcode=barcode_value or "",
                level=level,
                multiplier=barcode_multiplier(product, level),
            )
        )
    return result
