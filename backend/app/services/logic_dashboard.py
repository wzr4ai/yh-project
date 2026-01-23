from datetime import date, datetime, timedelta
import os
from typing import Any
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import (
    DailyReceipt,
    Inventory,
    InventoryLog,
    Product,
    PurchaseItem,
    SalesItem,
    SalesOrder,
)
from app.services.logic_inventory import dashboard_inventory_value
from app.services.logic_utils import (
    get_piece_cost_price,
    get_pieces_per_box,
    get_pieces_per_unit,
    get_units_per_box,
    round2,
    split_stock,
)


async def dashboard_realtime(
    session: AsyncSession,
) -> tuple[float, float, float, float, float, int, float, float | None]:
    today = datetime.utcnow().date()
    stmt = sa.select(SalesItem).where(sa.func.date(SalesItem.created_at) == today)
    items = (await session.execute(stmt)).scalars().all()
    orders = len(items)
    actual = sum(item.actual_sale_price * item.quantity for item in items)
    expected = sum(item.snapshot_standard_price * item.quantity for item in items)
    cost = sum(item.snapshot_cost * item.quantity for item in items)
    gross_profit = actual - cost
    avg_ticket = actual / orders if orders else 0
    receipt_diff_display = actual - expected
    diff_rate_display = (receipt_diff_display / expected * 100) if expected else 0
    return (
        actual,
        expected,
        receipt_diff_display,
        diff_rate_display,
        gross_profit,
        orders,
        avg_ticket,
        None,
    )


async def get_manual_receipt(session: AsyncSession) -> float | None:
    today = datetime.utcnow().date()
    rec = (
        (
            await session.execute(
                sa.select(DailyReceipt).where(DailyReceipt.date == today)
            )
        )
        .scalars()
        .first()
    )
    if rec:
        return rec.amount
    return None


async def set_manual_receipt(session: AsyncSession, value: float):
    today = datetime.utcnow().date()
    rec = (
        (
            await session.execute(
                sa.select(DailyReceipt).where(DailyReceipt.date == today)
            )
        )
        .scalars()
        .first()
    )
    if rec:
        rec.amount = value
    else:
        session.add(DailyReceipt(date=today, amount=value))
    await session.flush()


async def dashboard_performance(session: AsyncSession) -> schemas.PerformanceResponse:
    stmt = sa.select(SalesItem)
    items = (await session.execute(stmt)).scalars().all()
    expected = sum(item.snapshot_standard_price * item.quantity for item in items)
    actual = sum(item.actual_sale_price * item.quantity for item in items)
    cost_total = sum(item.snapshot_cost * item.quantity for item in items)
    purchase_total = await total_purchase_cost(session)
    diff = actual - expected
    rate = (diff / expected * 100) if expected else 0
    gross_profit = actual - cost_total
    return schemas.PerformanceResponse(
        price_diff=round(diff, 2),
        price_diff_rate=round(rate, 2),
        expected_sales=round(expected, 2),
        actual_sales=round(actual, 2),
        cost_total=round(cost_total, 2),
        gross_profit=round(gross_profit, 2),
        purchase_cost_total=round(purchase_total, 2),
    )


async def total_receipts(session: AsyncSession) -> float:
    total = (
        await session.execute(
            sa.select(sa.func.coalesce(sa.func.sum(DailyReceipt.amount), 0))
        )
    ).scalar_one()
    return float(total or 0)


async def total_purchase_cost(session: AsyncSession) -> float:
    rows = (
        await session.execute(
            sa.select(PurchaseItem, Product).join(
                Product, Product.id == PurchaseItem.product_id
            )
        )
    ).all()
    total = 0.0
    for item, product in rows:
        cost_per_box = (
            item.actual_cost if item.actual_cost is not None else item.expected_cost
        )
        cost_per_box = float(cost_per_box or 0)
        if cost_per_box <= 0:
            continue
        pieces_per_box = get_pieces_per_box(product) if product else 1
        received_units = item.received_units
        if received_units is not None and received_units > 0:
            boxes_equiv = received_units / float(pieces_per_box or 1)
        else:
            boxes_equiv = float(item.received_qty or 0)
        if boxes_equiv <= 0:
            continue
        total += boxes_equiv * cost_per_box
    return float(total)


def _build_sales_rows(rows: list[tuple[Any, ...]]) -> tuple[list[dict], dict]:
    items: list[dict] = []
    totals = {
        "quantity": 0,
        "sales_amount": 0.0,
        "cost_amount": 0.0,
        "standard_amount": 0.0,
    }
    for row in rows:
        pid, qty, sales_amount, cost_amount, standard_amount = row
        qty_val = int(qty or 0)
        sales_val = float(sales_amount or 0)
        cost_val = float(cost_amount or 0)
        standard_val = float(standard_amount or 0)
        profit = sales_val - cost_val
        margin = (profit / sales_val * 100) if sales_val > 0 else 0.0
        price_diff = sales_val - standard_val
        discount_rate = (price_diff / standard_val * 100) if standard_val > 0 else 0.0
        items.append(
            {
                "product_id": pid,
                "quantity": qty_val,
                "sales_amount": round2(sales_val),
                "cost_amount": round2(cost_val),
                "profit_amount": round2(profit),
                "profit_margin": round2(margin),
                "standard_amount": round2(standard_val),
                "price_diff": round2(price_diff),
                "discount_rate": round2(discount_rate),
                "avg_price": round2(sales_val / qty_val) if qty_val > 0 else 0.0,
                "avg_cost": round2(cost_val / qty_val) if qty_val > 0 else 0.0,
            }
        )
        totals["quantity"] += qty_val
        totals["sales_amount"] += sales_val
        totals["cost_amount"] += cost_val
        totals["standard_amount"] += standard_val

    totals["sales_amount"] = round2(totals["sales_amount"])
    totals["cost_amount"] = round2(totals["cost_amount"])
    totals["standard_amount"] = round2(totals["standard_amount"])
    totals["profit_amount"] = round2(totals["sales_amount"] - totals["cost_amount"])
    totals["profit_margin"] = round2(
        (
            (totals["sales_amount"] - totals["cost_amount"])
            / totals["sales_amount"]
            * 100
        )
        if totals["sales_amount"] > 0
        else 0.0
    )
    totals["price_diff"] = round2(totals["sales_amount"] - totals["standard_amount"])
    totals["discount_rate"] = round2(
        (totals["price_diff"] / totals["standard_amount"] * 100)
        if totals["standard_amount"] > 0
        else 0.0
    )
    totals["avg_price"] = (
        round2(totals["sales_amount"] / totals["quantity"])
        if totals["quantity"] > 0
        else 0.0
    )
    totals["avg_cost"] = (
        round2(totals["cost_amount"] / totals["quantity"])
        if totals["quantity"] > 0
        else 0.0
    )
    return items, totals


async def _sales_summary(session: AsyncSession, *, target_date: date | None) -> dict:
    stmt = sa.select(
        SalesItem.product_id,
        sa.func.sum(SalesItem.quantity).label("qty"),
        sa.func.sum(SalesItem.actual_sale_price * SalesItem.quantity).label(
            "sales_amount"
        ),
        sa.func.sum(SalesItem.snapshot_cost * SalesItem.quantity).label("cost_amount"),
        sa.func.sum(SalesItem.snapshot_standard_price * SalesItem.quantity).label(
            "standard_amount"
        ),
    ).group_by(SalesItem.product_id)
    if target_date:
        stmt = stmt.where(sa.func.date(SalesItem.created_at) == target_date)
    rows_raw = (await session.execute(stmt)).all()
    rows: list[tuple[Any, ...]] = [tuple(row) for row in rows_raw]
    items, totals = _build_sales_rows(rows)
    if not rows_raw:
        return {"items": [], "totals": totals}

    product_ids = [row[0] for row in rows if row[0]]
    products = (
        (await session.execute(sa.select(Product).where(Product.id.in_(product_ids))))
        .scalars()
        .all()
    )
    product_map = {p.id: p for p in products}
    for item in items:
        product = product_map.get(item["product_id"])
        if product:
            item["name"] = product.name
            item["units_per_box"] = get_units_per_box(product)
            item["pieces_per_unit"] = get_pieces_per_unit(product)
    items = sorted(items, key=lambda x: x["sales_amount"], reverse=True)
    return {"items": items, "totals": totals}


async def _inventory_change_summary(
    session: AsyncSession, *, target_date: date | None
) -> dict:
    stmt = sa.select(
        InventoryLog.product_id,
        InventoryLog.ref_type,
        sa.func.sum(InventoryLog.change_qty).label("delta"),
    ).group_by(InventoryLog.product_id, InventoryLog.ref_type)
    if target_date:
        stmt = stmt.where(sa.func.date(InventoryLog.change_date) == target_date)
    rows = (await session.execute(stmt)).all()
    if not rows:
        return {
            "total_delta": 0,
            "increase": 0,
            "decrease": 0,
            "by_type": {},
            "by_product": [],
        }

    product_ids = [row[0] for row in rows if row[0]]
    products = (
        (await session.execute(sa.select(Product).where(Product.id.in_(product_ids))))
        .scalars()
        .all()
    )
    product_map = {p.id: p for p in products}

    by_type: dict[str, int] = {}
    product_map_change: dict[str, dict] = {}
    total_delta = 0
    total_increase = 0
    total_decrease = 0
    for pid, ref_type, delta_val in rows:
        delta = int(delta_val or 0)
        total_delta += delta
        if delta >= 0:
            total_increase += delta
        else:
            total_decrease += abs(delta)
        ref_key = ref_type or "unknown"
        by_type[ref_key] = by_type.get(ref_key, 0) + delta

        product = product_map.get(pid)
        entry = product_map_change.setdefault(
            pid,
            {
                "product_id": pid,
                "name": product.name if product else pid,
                "delta_total": 0,
                "increase": 0,
                "decrease": 0,
                "by_type": {},
            },
        )
        entry["delta_total"] += delta
        if delta >= 0:
            entry["increase"] += delta
        else:
            entry["decrease"] += abs(delta)
        entry["by_type"][ref_key] = entry["by_type"].get(ref_key, 0) + delta

    by_product = sorted(
        product_map_change.values(), key=lambda x: abs(x["delta_total"]), reverse=True
    )
    return {
        "total_delta": total_delta,
        "increase": total_increase,
        "decrease": total_decrease,
        "by_type": by_type,
        "by_product": by_product,
    }


async def dashboard_report(session: AsyncSession) -> schemas.DashboardReportResponse:
    now = datetime.utcnow()
    today = now.date()
    cny_eve_str = os.getenv("CNY_EVE_DATE")
    cny_eve = None
    if cny_eve_str:
        try:
            cny_eve = datetime.strptime(cny_eve_str, "%Y-%m-%d").date()
        except ValueError:
            cny_eve = None
    season_start_str = os.getenv("CNY_SEASON_START")
    season_end_str = os.getenv("CNY_SEASON_END")
    season_start = None
    season_end = None
    if season_start_str:
        try:
            season_start = datetime.strptime(season_start_str, "%Y-%m-%d").date()
        except ValueError:
            season_start = None
    if season_end_str:
        try:
            season_end = datetime.strptime(season_end_str, "%Y-%m-%d").date()
        except ValueError:
            season_end = None
    sales_today = await _sales_summary(session, target_date=today)
    sales_all = await _sales_summary(session, target_date=None)

    order_today = (
        await session.execute(
            sa.select(sa.func.count(SalesOrder.id)).where(
                sa.func.date(SalesOrder.order_date) == today
            )
        )
    ).scalar_one()
    order_all = (
        await session.execute(sa.select(sa.func.count(SalesOrder.id)))
    ).scalar_one()

    day_items = (
        (
            await session.execute(
                sa.select(SalesItem).where(sa.func.date(SalesItem.created_at) == today)
            )
        )
        .scalars()
        .all()
    )
    hourly = {h: {"hour": h, "sales_amount": 0.0, "quantity": 0} for h in range(24)}
    for item in day_items:
        hour = int(item.created_at.hour)
        bucket = hourly.get(hour)
        if bucket is None:
            continue
        bucket["sales_amount"] += float(item.actual_sale_price or 0) * int(
            item.quantity or 0
        )
        bucket["quantity"] += int(item.quantity or 0)
    hourly_list = [
        {
            "hour": h,
            "sales_amount": round2(v["sales_amount"]),
            "quantity": v["quantity"],
        }
        for h, v in hourly.items()
    ]

    start_7d = today - timedelta(days=6)
    trend_rows = (
        await session.execute(
            sa.select(
                sa.func.date(SalesItem.created_at).label("day"),
                sa.func.sum(SalesItem.actual_sale_price * SalesItem.quantity).label(
                    "sales_amount"
                ),
                sa.func.sum(SalesItem.quantity).label("qty"),
            )
            .where(sa.func.date(SalesItem.created_at) >= start_7d)
            .group_by(sa.func.date(SalesItem.created_at))
            .order_by(sa.func.date(SalesItem.created_at))
        )
    ).all()
    sales_trend_7d = [
        {
            "date": str(day),
            "sales_amount": round2(sales_amount or 0),
            "quantity": int(qty or 0),
        }
        for day, sales_amount, qty in trend_rows
    ]

    inv_rows = (
        await session.execute(
            sa.select(Inventory, Product).join(
                Product, Product.id == Inventory.product_id
            )
        )
    ).all()
    inventory_items: list[dict] = []
    total_units = 0
    total_cost = 0.0
    for inv, product in inv_rows:
        stock_units = int(inv.current_stock or 0)
        total_units += stock_units
        cost_per_piece = get_piece_cost_price(product)
        cost_total = cost_per_piece * stock_units
        total_cost += cost_total
        boxes, units, pieces = split_stock(stock_units, product)
        inventory_items.append(
            {
                "product_id": product.id,
                "name": product.name,
                "stock_units": stock_units,
                "stock_boxes": round2(stock_units / float(get_pieces_per_box(product))),
                "stock_split": {"boxes": boxes, "units": units, "pieces": pieces},
                "cost_per_piece": round2(cost_per_piece),
                "cost_total": round2(cost_total),
            }
        )

    inventory_items = sorted(
        inventory_items, key=lambda x: x["stock_units"], reverse=True
    )
    low_stock_threshold = 10
    low_stock = [
        item for item in inventory_items if item["stock_units"] <= low_stock_threshold
    ]

    inv_change_today = await _inventory_change_summary(session, target_date=today)
    inv_change_all = await _inventory_change_summary(session, target_date=None)

    last_sale_rows = (
        await session.execute(
            sa.select(
                SalesItem.product_id,
                sa.func.max(SalesItem.created_at).label("last_sold_at"),
            ).group_by(SalesItem.product_id)
        )
    ).all()
    last_sale_map = {
        pid: last_sold_at.date()
        for pid, last_sold_at in last_sale_rows
        if pid and last_sold_at
    }

    sales_7d_rows = (
        await session.execute(
            sa.select(
                SalesItem.product_id,
                sa.func.sum(SalesItem.quantity).label("qty"),
            )
            .where(sa.func.date(SalesItem.created_at) >= start_7d)
            .group_by(SalesItem.product_id)
        )
    ).all()
    sales_7d_map = {pid: int(qty or 0) for pid, qty in sales_7d_rows}
    sales_all_map = {item["product_id"]: item for item in sales_all["items"]}

    velocity_list = []
    for item in inventory_items:
        pid = item["product_id"]
        sold_7d = sales_7d_map.get(pid, 0)
        sold_all = sales_all_map.get(pid, {}).get("quantity", 0)
        avg_daily = sold_7d / 7 if sold_7d > 0 else 0
        days_cover = (item["stock_units"] / avg_daily) if avg_daily > 0 else None
        sell_through = (
            sold_all / float(sold_all + item["stock_units"])
            if (sold_all + item["stock_units"]) > 0
            else 0.0
        )
        velocity_list.append(
            {
                "product_id": pid,
                "name": item["name"],
                "sold_7d": sold_7d,
                "avg_daily_sales_7d": round2(avg_daily),
                "days_cover_7d": round2(days_cover) if days_cover is not None else None,
                "sell_through_rate": round2(sell_through * 100),
                "stock_units": item["stock_units"],
            }
        )

    velocity_list = sorted(
        velocity_list, key=lambda x: (x["avg_daily_sales_7d"] or 0), reverse=True
    )
    fast_movers = [v for v in velocity_list if (v["avg_daily_sales_7d"] or 0) > 0][:10]
    slow_movers = [
        v
        for v in velocity_list
        if (v["avg_daily_sales_7d"] or 0) == 0 and v["stock_units"] > 0
    ][:10]
    dead_stock_cutoff = today - timedelta(days=14)
    dead_stock = []
    for v in velocity_list:
        if v["stock_units"] <= 0:
            continue
        last_sale_date = last_sale_map.get(v["product_id"])
        if last_sale_date is None or last_sale_date <= dead_stock_cutoff:
            dead_stock.append(v)
    dead_stock = dead_stock[:10]
    restock_candidates = [
        v
        for v in velocity_list
        if (v["avg_daily_sales_7d"] or 0) > 0
        and v["stock_units"] <= low_stock_threshold
    ][:10]
    promo_candidates = [
        item
        for item in sales_all["items"]
        if (item.get("profit_margin") or 0) <= 20 and item.get("sales_amount", 0) > 0
    ][:10]

    total_standard = sales_all["totals"].get("standard_amount", 0) or 0
    total_price_diff = sales_all["totals"].get("price_diff", 0) or 0
    avg_discount_rate = (
        (total_price_diff / total_standard * 100) if total_standard else 0.0
    )
    high_discount_products = [
        item
        for item in sales_all["items"]
        if (item.get("discount_rate") or 0) <= -15 and item.get("sales_amount", 0) > 0
    ][:10]
    premium_products = [
        item
        for item in sales_all["items"]
        if (item.get("discount_rate") or 0) >= 5 and item.get("sales_amount", 0) > 0
    ][:10]
    potential_profit_recovery = sum(
        max(0.0, -(item.get("price_diff") or 0))
        for item in sales_all["items"]
        if item.get("sales_amount", 0) > 0
    )

    total_sold_units = sales_all["totals"].get("quantity", 0) or 0
    overall_sell_through = (
        total_sold_units / float(total_sold_units + total_units) * 100
        if (total_sold_units + total_units) > 0
        else 0.0
    )
    sell_through_list = []
    for item in inventory_items:
        pid = item["product_id"]
        sold_qty = sales_all_map.get(pid, {}).get("quantity", 0)
        stock_units = item["stock_units"]
        denom = sold_qty + stock_units
        rate = (sold_qty / float(denom) * 100) if denom > 0 else 0.0
        sell_through_list.append(
            {
                "product_id": pid,
                "name": item["name"],
                "sold_units": int(sold_qty or 0),
                "stock_units": int(stock_units or 0),
                "sell_through_rate": round2(rate),
            }
        )
    sell_through_list = sorted(
        sell_through_list, key=lambda x: x["sell_through_rate"], reverse=True
    )

    fast_bucket = []
    normal_bucket = []
    slow_bucket = []
    for item in velocity_list:
        avg_daily = item["avg_daily_sales_7d"] or 0
        days_cover = item["days_cover_7d"]
        if avg_daily <= 0 and item["stock_units"] > 0:
            slow_bucket.append(item)
        elif days_cover is not None and days_cover <= 7:
            fast_bucket.append(item)
        elif days_cover is not None and days_cover <= 15:
            normal_bucket.append(item)
    avg_turnover_days = None
    turnover_values = [
        item["days_cover_7d"]
        for item in velocity_list
        if item.get("days_cover_7d") is not None
    ]
    if turnover_values:
        avg_turnover_days = round2(sum(turnover_values) / len(turnover_values))

    top_sales_today = sales_today["items"][:5]
    top_sales_all = sales_all["items"][:5]
    sales_concentration_today = round2(
        (
            sum(item["sales_amount"] for item in top_sales_today)
            / sales_today["totals"]["sales_amount"]
            * 100
        )
        if sales_today["totals"]["sales_amount"] > 0
        else 0.0
    )
    sales_concentration_all = round2(
        (
            sum(item["sales_amount"] for item in top_sales_all)
            / sales_all["totals"]["sales_amount"]
            * 100
        )
        if sales_all["totals"]["sales_amount"] > 0
        else 0.0
    )

    (
        cost,
        retail_min,
        retail_max,
        sku_count,
        total_boxes,
    ) = await dashboard_inventory_value(session)

    phase_code = None
    phase_label = None
    if season_start and today < season_start:
        phase_code = "preheat"
        phase_label = "预热期"
    elif cny_eve and today <= cny_eve:
        days_to_peak = (cny_eve - today).days
        if days_to_peak <= 3:
            phase_code = "peak"
            phase_label = "高峰期"
        elif days_to_peak <= 10:
            phase_code = "surge"
            phase_label = "爆发期"
        else:
            phase_code = "warmup"
            phase_label = "升温期"
    elif season_end and today <= season_end:
        phase_code = "tail"
        phase_label = "尾期"
    elif season_start and season_end:
        phase_code = "post"
        phase_label = "季后"

    time_progress_pct = None
    if season_start and season_end and season_start <= season_end:
        total_days = (season_end - season_start).days + 1
        elapsed_days = (today - season_start).days + 1
        if total_days > 0:
            elapsed_days = max(0, min(elapsed_days, total_days))
            time_progress_pct = round2(elapsed_days / total_days * 100)

    report = {
        "meta": {
            "generated_at": now.isoformat(),
            "timezone": "UTC",
            "report_version": "v1",
        },
        "seasonality": {
            "season_start": season_start.isoformat() if season_start else None,
            "season_end": season_end.isoformat() if season_end else None,
            "cny_eve_date": cny_eve.isoformat() if cny_eve else None,
            "days_to_peak": (cny_eve - today).days if cny_eve else None,
            "current_phase": phase_code,
            "phase_label": phase_label,
            "time_progress_pct": time_progress_pct,
        },
        "seasonality_context": {
            "business_type": "烟花爆竹销售",
            "season_window": "2026年2月7日（腊月20）至2026年3月3日（正月15）",
            "peak_days": ["除夕（2026年2月16日）", "大年初一"],
            "peak_share_estimate": "除夕+初一约占全年销售额50%",
            "tail_day_estimate": "正月15约占除夕的20%~25%",
            "low_period": "正月2-正月14销量偏低",
            "target": "尽量在正月15前售完或减少存货",
        },
        "sales": {
            "today": {
                **sales_today["totals"],
                "orders": int(order_today or 0),
                "top_products": top_sales_today,
                "hourly": hourly_list,
            },
            "all_time": {
                **sales_all["totals"],
                "orders": int(order_all or 0),
                "top_products": top_sales_all,
            },
            "by_product_today": sales_today["items"],
            "by_product_all_time": sales_all["items"],
            "trend_7d": sales_trend_7d,
            "concentration": {
                "top5_share_today": sales_concentration_today,
                "top5_share_all_time": sales_concentration_all,
            },
        },
        "inventory": {
            "summary": {
                "stock_units_total": total_units,
                "sku_count": sku_count or 0,
                "total_boxes": total_boxes,
                "cost_total": round2(cost),
                "retail_total_min": round2(retail_min),
                "retail_total_max": round2(retail_max),
            },
            "current_stock": inventory_items,
            "low_stock": low_stock,
            "changes": {
                "today": inv_change_today,
                "all_time": inv_change_all,
            },
        },
        "inventory_health": {
            "fast_moving": {"count": len(fast_bucket), "products": fast_bucket[:10]},
            "normal": {"count": len(normal_bucket), "products": normal_bucket[:10]},
            "slow_moving": {"count": len(slow_bucket), "products": slow_bucket[:10]},
            "dead_stock": {"count": len(dead_stock), "products": dead_stock},
            "avg_turnover_days": avg_turnover_days,
        },
        "sell_through": {
            "overall_rate": round2(overall_sell_through),
            "by_product": sell_through_list[:20],
        },
        "pricing_analysis": {
            "avg_discount_rate": round2(avg_discount_rate),
            "high_discount_products": high_discount_products,
            "premium_products": premium_products,
            "potential_profit_recovery": round2(potential_profit_recovery),
        },
        "signals": {
            "fast_movers": fast_movers,
            "slow_movers": slow_movers,
            "restock_candidates": restock_candidates,
            "promo_candidates": promo_candidates,
            "clearance_candidates": dead_stock,
        },
    }

    return schemas.DashboardReportResponse(
        generated_at=now, report=report, version="v1"
    )
