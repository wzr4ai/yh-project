from typing import Dict

from app.models.schemas import Product, Category, PriceCalcResponse


def _pieces_per_box(product: Product) -> float:
    units = int(product.units_per_box or 1)
    pieces = int(product.pieces_per_unit or 1)
    units = units if units > 0 else 1
    pieces = pieces if pieces > 0 else 1
    return units * pieces


def _piece_cost(product: Product) -> float:
    if product.box_cost_price:
        return float(product.box_cost_price) / _pieces_per_box(product)
    return float(product.base_cost_price or 0)


def calculate_standard_price(
    product: Product,
    category_lookup: Dict[str, Category],
    global_multiplier: float,
) -> PriceCalcResponse:
    cost = _piece_cost(product)
    if product.fixed_retail_price is not None:
        return PriceCalcResponse(price=product.fixed_retail_price, basis="例外价")

    category = category_lookup.get(product.category_id)
    if category and category.retail_multiplier:
        return PriceCalcResponse(price=round2(cost * category.retail_multiplier), basis="分类系数")

    return PriceCalcResponse(price=round2(cost * global_multiplier), basis="全局系数")


def round2(value: float) -> float:
    return round(value + 1e-9, 2)
