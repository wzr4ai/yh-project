from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db import get_session
from app.models import schemas
from app.models.entities import Product
from app.services import logic

router = APIRouter()


@router.get("/price/calculate/{product_id}", response_model=schemas.PriceCalcResponse)
async def calculate_price(product_id: str, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    return await logic.calculate_price_for_product(session, product)


@router.get("/pricing/overview", response_model=schemas.PricingOverviewResponse)
async def pricing_overview(
    offset: int = 0,
    limit: int = 200,
    keyword: str | None = None,
    only_in_stock: bool = False,
    custom_category_id: str | None = None,
    session: AsyncSession = Depends(get_session),
    request: Request = None,
    response: Response = None,
    current_user=Depends(deps.get_current_user),
):
    limit = max(1, min(limit, 500))
    items, total, version = await logic.list_pricing_overview(
        session,
        offset=offset,
        limit=limit,
        keyword=keyword,
        only_in_stock=only_in_stock,
        custom_category_id=custom_category_id,
    )
    etag = f'W/"{version}"'
    inm = request.headers.get("if-none-match") if request else None
    if inm == etag:
        return Response(status_code=304)
    response.headers["ETag"] = etag
    return schemas.PricingOverviewResponse(items=items, total=total)
