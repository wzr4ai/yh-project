import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db import get_session
from app.models import schemas
from app.models.entities import Product, ProductBarcode
from app.services import logic

router = APIRouter()


@router.post("/products", response_model=schemas.Product)
async def create_product(product: schemas.Product, session: AsyncSession = Depends(get_session)):
    exists = await session.get(Product, product.id) if product.id else None
    if exists:
        raise HTTPException(status_code=400, detail="product id already exists")
    created = await logic.create_product(session, product)
    await session.commit()
    return await logic.product_with_category(session, created.id)


@router.get("/products", response_model=schemas.ProductListResponse)
async def list_products(
    offset: int = 0,
    limit: int = 20,
    category_id: str | None = None,
    category_ids: str | None = None,
    custom_category_ids: str | None = None,
    merchant_category_ids: str | None = None,
    keyword: str | None = None,
    session: AsyncSession = Depends(get_session),
    request: Request = None,
    response: Response = None,
):
    limit = max(1, min(limit, 100))
    ids_list = [c for c in (category_ids.split(",") if category_ids else []) if c]
    custom_ids_list = [c for c in (custom_category_ids.split(",") if custom_category_ids else []) if c]
    merchant_ids_list = [c for c in (merchant_category_ids.split(",") if merchant_category_ids else []) if c]
    if custom_ids_list and not ids_list:
        ids_list = custom_ids_list
    items, total, version = await logic.list_products_with_inventory(
        session,
        offset=offset,
        limit=limit,
        category_id=category_id,
        category_ids=ids_list,
        custom_category_ids=custom_ids_list,
        merchant_category_ids=merchant_ids_list,
        keyword=keyword,
    )
    etag = f'W/"{version}"'
    inm = request.headers.get("if-none-match") if request else None
    if inm == etag:
        return Response(status_code=304)
    response.headers["ETag"] = etag
    return schemas.ProductListResponse(items=items, total=total)


@router.get("/products/by-barcode", response_model=schemas.BarcodeLookupResponse)
async def get_product_by_barcode(
    barcode: str,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    try:
        return await logic.product_by_barcode(session, barcode)
    except ValueError as exc:
        status = 400 if str(exc) == "barcode empty" else 404
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/products/by-barcode-suffix", response_model=list[schemas.BarcodeLookupResponse])
async def get_products_by_barcode_suffix(
    query: str,
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    try:
        return await logic.list_products_by_barcode_suffix(session, query, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/products/{product_id}/barcodes", response_model=schemas.ProductBarcode)
async def add_product_barcode(
    product_id: str,
    payload: schemas.ProductBarcodeCreate,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    code = (payload.barcode or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="barcode empty")
    existing = (await session.execute(sa.select(ProductBarcode).where(ProductBarcode.barcode == code))).scalars().first()
    if existing and existing.product_id != product_id:
        raise HTTPException(status_code=409, detail="barcode already bound")
    await logic.ensure_product_barcode(session, product_id, code, payload.level)
    await session.commit()
    result = (await session.execute(sa.select(ProductBarcode).where(ProductBarcode.barcode == code))).scalars().first()
    if not result:
        raise HTTPException(status_code=500, detail="barcode not saved")
    return schemas.ProductBarcode(id=result.id, barcode=result.barcode, level=result.level)


@router.get("/products/{product_id}", response_model=schemas.Product)
async def get_product(product_id: str, session: AsyncSession = Depends(get_session)):
    try:
        return await logic.product_with_category(session, product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/products/{product_id}", response_model=schemas.Product)
async def update_product(product_id: str, payload: schemas.Product, session: AsyncSession = Depends(get_session)):
    try:
        await logic.update_product(session, product_id, payload)
        await session.commit()
        return await logic.product_with_category(session, product_id)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, session: AsyncSession = Depends(get_session)):
    try:
        await logic.delete_product(session, product_id)
        await session.commit()
        return {"status": "ok"}
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
