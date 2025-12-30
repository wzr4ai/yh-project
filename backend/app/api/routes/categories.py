import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import schemas
from app.models.entities import Category, ProductCategory
from app.services import logic

router = APIRouter()


@router.get("/categories", response_model=list[schemas.Category])
async def list_categories(session: AsyncSession = Depends(get_session), request: Request = None, response: Response = None):
    cats = (await session.execute(sa.select(logic.Category))).scalars().all()
    version = logic.compute_version_from_models(cats)
    etag = f'W/"{version}"'
    inm = request.headers.get("if-none-match") if request else None
    if inm == etag:
        return Response(status_code=304)
    response.headers["ETag"] = etag
    return cats


@router.post("/categories", response_model=schemas.Category)
async def create_category(category: schemas.Category, session: AsyncSession = Depends(get_session)):
    created = await logic.create_category(session, category)
    await session.commit()
    return schemas.Category(
        id=created.id,
        name=created.name,
        retail_multiplier=created.retail_multiplier,
        retail_multiplier_min=created.retail_multiplier_min,
        retail_multiplier_max=created.retail_multiplier_max,
        is_custom=created.is_custom,
    )


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, force: bool = False, session: AsyncSession = Depends(get_session)):
    try:
        cleared = await logic.delete_category(session, category_id, force=force)
        await session.commit()
        return {"cleared_products": cleared}
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/categories/{category_id}/products")
async def replace_products_in_category(category_id: str, data: dict, session: AsyncSession = Depends(get_session)):
    product_ids = data.get("product_ids") or []
    if not isinstance(product_ids, list):
        raise HTTPException(status_code=400, detail="product_ids must be list")
    cat = await session.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="category not found")
    unique_ids = [pid for pid in dict.fromkeys(product_ids) if pid]
    await session.execute(sa.delete(ProductCategory).where(ProductCategory.category_id == category_id))
    if unique_ids:
        session.add_all([ProductCategory(product_id=pid, category_id=category_id) for pid in unique_ids])
    await session.commit()
    return {"count": len(unique_ids)}


@router.put("/categories/{category_id}", response_model=schemas.Category)
async def update_category(category_id: str, category: schemas.Category, session: AsyncSession = Depends(get_session)):
    updated = await logic.upsert_category(session, category_id, category)
    await session.commit()
    return schemas.Category(
        id=updated.id,
        name=updated.name,
        retail_multiplier=updated.retail_multiplier,
        retail_multiplier_min=updated.retail_multiplier_min,
        retail_multiplier_max=updated.retail_multiplier_max,
        is_custom=updated.is_custom,
    )
