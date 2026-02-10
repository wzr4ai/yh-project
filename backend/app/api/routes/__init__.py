from fastapi import APIRouter

from . import (
    ai,
    auth,
    categories,
    dashboard,
    exports,
    imports,
    inventory,
    llm,
    media,
    misc_costs,
    orders,
    pricing,
    products,
    purchases,
    sales,
    shareholders,
    system,
)

router = APIRouter(prefix="/api")

router.include_router(auth.router)
router.include_router(ai.router)
router.include_router(orders.router)
router.include_router(misc_costs.router)
router.include_router(llm.router)
router.include_router(pricing.router)
router.include_router(products.router)
router.include_router(categories.router)
router.include_router(imports.router)
router.include_router(sales.router)
router.include_router(inventory.router)
router.include_router(purchases.router)
router.include_router(dashboard.router)
router.include_router(system.router)
router.include_router(exports.router)
router.include_router(media.router)
router.include_router(shareholders.router)
