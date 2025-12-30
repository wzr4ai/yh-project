import re
from datetime import datetime
from typing import Any

from app.models.entities import Product


def normalize_spec(spec: str | None) -> str | None:
    if not spec:
        return None
    return str(spec).strip()


def compute_version_from_models(models: list[Any]) -> str:
    max_ts = None
    for m in models:
        ts = getattr(m, "updated_at", None)
        if ts:
            max_ts = max(max_ts or ts, ts)
    return (max_ts or datetime.utcnow()).isoformat()


def parse_spec_qty(spec: str | None) -> float:
    if not spec:
        return 1.0
    match = re.search(r"(\d+(?:\.\d+)?)", str(spec))
    if not match:
        return 1.0
    try:
        val = float(match.group(1))
        return val if val > 0 else 1.0
    except Exception:
        return 1.0


def _safe_int(value: int | float | None, default: int = 1) -> int:
    try:
        val = int(value)
    except (TypeError, ValueError):
        return default
    return val if val > 0 else default


def get_units_per_box(product: Product) -> int:
    val = _safe_int(getattr(product, "units_per_box", None), default=1)
    if val <= 0:
        fallback = parse_spec_qty(getattr(product, "spec", None))
        val = _safe_int(fallback, default=1)
    return val


def get_pieces_per_unit(product: Product) -> int:
    return _safe_int(getattr(product, "pieces_per_unit", None), default=1)


def get_pieces_per_box(product: Product) -> int:
    return max(1, get_units_per_box(product) * get_pieces_per_unit(product))


def get_box_cost_price(product: Product) -> float:
    box_cost = float(getattr(product, "box_cost_price", 0) or 0)
    if box_cost > 0:
        return box_cost
    base_cost = float(getattr(product, "base_cost_price", 0) or 0)
    if base_cost > 0:
        return base_cost * get_pieces_per_box(product)
    return 0.0


def get_piece_cost_price(product: Product) -> float:
    box_cost = float(getattr(product, "box_cost_price", 0) or 0)
    if box_cost > 0:
        return box_cost / get_pieces_per_box(product)
    base_cost = float(getattr(product, "base_cost_price", 0) or 0)
    return base_cost


def split_stock(total_pieces: int, product: Product) -> tuple[int, int, int]:
    total = max(0, int(total_pieces or 0))
    pieces_per_box = get_pieces_per_box(product)
    pieces_per_unit = get_pieces_per_unit(product)
    boxes = total // pieces_per_box
    remain = total % pieces_per_box
    units = remain // pieces_per_unit
    pieces = remain % pieces_per_unit
    return boxes, units, pieces


def barcode_multiplier(product: Product, level: str) -> int:
    lvl = (level or "").upper()
    if lvl == "BOX":
        return get_pieces_per_box(product)
    if lvl == "UNIT":
        return get_pieces_per_unit(product)
    return 1


def round2(value: float) -> float:
    return round(value + 1e-9, 2)
