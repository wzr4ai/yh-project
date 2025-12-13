from typing import Dict

from app.models.schemas import Product, Category, PriceCalcResponse


def calculate_standard_price(
    product: Product,
    category_lookup: Dict[str, Category],
    global_multiplier: float,
) -> PriceCalcResponse:
    cost = product.base_cost_price or 0
    if product.fixed_retail_price is not None:
        return PriceCalcResponse(price=product.fixed_retail_price, basis="例外价")

    category = category_lookup.get(product.category_id)
    if category and category.retail_multiplier:
        return PriceCalcResponse(price=round2(cost * category.retail_multiplier), basis="分类系数")

    return PriceCalcResponse(price=round2(cost * global_multiplier), basis="全局系数")


def round2(value: float) -> float:
    return round(value + 1e-9, 2)
