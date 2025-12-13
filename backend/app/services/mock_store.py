from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List

from app.models.schemas import (
    Category,
    InventoryAdjustRequest,
    InventoryLog,
    InventoryRecord,
    PerformanceResponse,
    PriceCalcResponse,
    Product,
    PurchaseItem,
    PurchaseOrder,
    SalesItem,
    SalesItemPayload,
    SalesOrder,
    User,
)
from app.services.pricing import calculate_standard_price
from app.services import auth


GLOBAL_MULTIPLIER = 1.5
SYSTEM_CONFIG = {"global_multiplier": GLOBAL_MULTIPLIER}

CATEGORIES: List[Category] = [
    Category(id="sparkler", name="烟花组合", retail_multiplier=1.8),
    Category(id="cracker", name="鞭炮", retail_multiplier=1.6),
    Category(id="toy", name="玩具烟花", retail_multiplier=None),
]

PRODUCTS: List[Product] = [
    Product(
        id="p1",
        name="吉祥如意组合",
        category_id="sparkler",
        spec="16 发 / 箱",
        base_cost_price=68,
        fixed_retail_price=None,
        img_url="/static/fireworks-1.png",
    ),
    Product(
        id="p2",
        name="喜庆连环炮",
        category_id="cracker",
        spec="1000 响",
        base_cost_price=42,
        fixed_retail_price=96,
        img_url="/static/fireworks-2.png",
    ),
    Product(
        id="p3",
        name="星河梦幻棒",
        category_id="toy",
        spec="10 支 / 袋",
        base_cost_price=12,
        fixed_retail_price=None,
        img_url="/static/fireworks-3.png",
    ),
]

INVENTORY: List[InventoryRecord] = [
    InventoryRecord(product_id="p1", warehouse_id="default", current_stock=120),
    InventoryRecord(product_id="p2", warehouse_id="default", current_stock=80),
    InventoryRecord(product_id="p3", warehouse_id="default", current_stock=260),
]

INVENTORY_LOGS: List[InventoryLog] = []

SALES_ITEMS: List[SalesItem] = [
    SalesItem(
        id="s1",
        product_id="p2",
        quantity=4,
        actual_sale_price=105,
        snapshot_cost=42,
        snapshot_standard_price=96,
    ),
    SalesItem(
        id="s2",
        product_id="p1",
        quantity=2,
        actual_sale_price=130,
        snapshot_cost=68,
        snapshot_standard_price=122.4,
    ),
]

USERS: List[User] = [
    User(id="u-owner", username="老板", role="owner", openid="owner"),
]

PURCHASE_ORDERS: List[PurchaseOrder] = [
    PurchaseOrder(
        id="po-20240201",
        status="部分到货",
        supplier="A 供应商",
        expected_date=date(2024, 2, 3),
        remark="春节补货",
        created_by="owner",
        items=[
            PurchaseItem(
                product_id="p1",
                quantity=50,
                expected_cost=68,
                received_qty=20,
                actual_cost=68,
            ),
            PurchaseItem(
                product_id="p2",
                quantity=30,
                expected_cost=42,
                received_qty=0,
                actual_cost=None,
            ),
        ],
    ),
    PurchaseOrder(
        id="po-20240120",
        status="完成",
        supplier="B 供应商",
        expected_date=date(2024, 1, 22),
        remark="常规补货",
        created_by="owner",
        items=[
            PurchaseItem(
                product_id="p3",
                quantity=120,
                expected_cost=12,
                received_qty=120,
                actual_cost=12,
            )
        ],
    ),
]


def category_lookup() -> Dict[str, Category]:
    return {c.id: c for c in CATEGORIES}


def get_product(product_id: str) -> Product | None:
    for p in PRODUCTS:
        if p.id == product_id:
            return p
    return None


def get_user_by_openid(openid: str) -> User | None:
    for u in USERS:
        if u.openid == openid:
            return u
    return None


def get_user_by_id(user_id: str) -> User | None:
    for u in USERS:
        if u.id == user_id:
            return u
    return None


def get_or_create_user_by_openid(openid: str, nickname: str | None = None) -> User:
    existing = get_user_by_openid(openid)
    if existing:
        return existing
    user = User(
        id=f"u-{len(USERS)+1}",
        username=nickname or f"店员{len(USERS)+1}",
        role="clerk",
        openid=openid,
    )
    USERS.append(user)
    return user


def get_inventory_record(product_id: str) -> InventoryRecord:
    for inv in INVENTORY:
        if inv.product_id == product_id:
            return inv
    record = InventoryRecord(product_id=product_id, warehouse_id="default", current_stock=0)
    INVENTORY.append(record)
    return record


def log_inventory_change(product_id: str, change_qty: int, ref_type: str, ref_id: str):
    INVENTORY_LOGS.append(
        InventoryLog(
            id=f"log-{len(INVENTORY_LOGS)+1}",
            product_id=product_id,
            warehouse_id="default",
            change_date=datetime.utcnow(),
            change_qty=change_qty,
            type="auto",
            ref_type=ref_type,
            ref_id=ref_id,
        )
    )


def calculate_price(product: Product) -> PriceCalcResponse:
    return calculate_standard_price(product, category_lookup(), SYSTEM_CONFIG["global_multiplier"])


def create_sales_order(payloads: List[SalesItemPayload], username: str) -> SalesOrder:
    items: List[SalesItem] = []
    total_actual = 0.0
    for idx, payload in enumerate(payloads, start=1):
        product = get_product(payload.product_id)
        if not product:
            raise ValueError(f"product {payload.product_id} not found")
        price_info = calculate_price(product)
        item_total = payload.actual_price * payload.quantity
        total_actual += item_total
        sales_item = SalesItem(
            id=f"order-item-{len(SALES_ITEMS)+idx}",
            product_id=payload.product_id,
            quantity=payload.quantity,
            snapshot_cost=product.base_cost_price,
            snapshot_standard_price=price_info.price,
            actual_sale_price=payload.actual_price,
        )
        items.append(sales_item)
        SALES_ITEMS.append(sales_item)

        # deduct inventory
        inv = get_inventory_record(payload.product_id)
        inv.current_stock = max(0, inv.current_stock - payload.quantity)
        log_inventory_change(payload.product_id, -payload.quantity, "sales", sales_item.id)

    order = SalesOrder(
        id=f"so-{len(SALES_ITEMS)}",
        order_date=datetime.utcnow(),
        items=items,
        total_actual_amount=total_actual,
        created_by=username or "owner",
    )
    return order


def adjust_inventory(req: InventoryAdjustRequest, username: str) -> InventoryRecord:
    inv = get_inventory_record(req.product_id)
    inv.current_stock += req.delta
    log_inventory_change(req.product_id, req.delta, "adjust", username)
    return inv


def list_inventory_logs() -> List[InventoryLog]:
    return sorted(INVENTORY_LOGS, key=lambda x: x.change_date, reverse=True)


def list_purchase_orders() -> List[PurchaseOrder]:
    return PURCHASE_ORDERS


def create_purchase_order(po: PurchaseOrder) -> PurchaseOrder:
    PURCHASE_ORDERS.append(po)
    return po


def receive_purchase_order(po_id: str, item_receipts: List[PurchaseItem]) -> PurchaseOrder:
    order = next((o for o in PURCHASE_ORDERS if o.id == po_id), None)
    if not order:
        raise ValueError("purchase order not found")

    for update in item_receipts:
        target = next((i for i in order.items if i.product_id == update.product_id), None)
        if not target:
            continue
        target.received_qty = update.received_qty
        target.actual_cost = update.actual_cost or target.expected_cost
        # sync inventory
        inv = get_inventory_record(update.product_id)
        delta = update.received_qty
        inv.current_stock += delta
        log_inventory_change(update.product_id, delta, "purchase", order.id)

    # status update
    if all(i.received_qty >= i.quantity for i in order.items):
        order.status = "完成"
    elif any(i.received_qty > 0 for i in order.items):
        order.status = "部分到货"
    else:
        order.status = "待到货"
    return order


def inventory_value() -> tuple[float, float]:
    cost_total = 0.0
    retail_total = 0.0
    for inv in INVENTORY:
        product = get_product(inv.product_id)
        if not product:
            continue
        price_info = calculate_price(product)
        cost_total += product.base_cost_price * inv.current_stock
        retail_total += price_info.price * inv.current_stock
    return cost_total, retail_total


def dashboard_realtime() -> tuple[float, float, int, float]:
    orders = len(SALES_ITEMS)
    actual = sum(item.actual_sale_price * item.quantity for item in SALES_ITEMS)
    cost = sum(item.snapshot_cost * item.quantity for item in SALES_ITEMS)
    gross_profit = actual - cost
    avg_ticket = actual / orders if orders else 0
    return actual, gross_profit, orders, avg_ticket


def performance() -> PerformanceResponse:
    expected = sum(item.snapshot_standard_price * item.quantity for item in SALES_ITEMS)
    actual = sum(item.actual_sale_price * item.quantity for item in SALES_ITEMS)
    diff = actual - expected
    rate = (diff / expected * 100) if expected else 0
    return PerformanceResponse(
        price_diff=round(diff, 2),
        price_diff_rate=round(rate, 2),
        expected_sales=round(expected, 2),
        actual_sales=round(actual, 2),
    )
