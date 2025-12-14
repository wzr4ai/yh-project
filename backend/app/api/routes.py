from datetime import datetime
from typing import List

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.db import get_session
from app.models import schemas
from app.models.entities import InventoryLog, Product, PurchaseOrder
from app.services import auth, logic

router = APIRouter(prefix="/api")


@router.post("/auth/weapp", response_model=schemas.LoginResponse)
async def login_weapp(payload: schemas.WeappLoginRequest, session: AsyncSession = Depends(get_session)):
    try:
        openid = await auth.weapp_code_to_openid(payload.code)
    except ValueError:
        # fallback: 未配置或微信返回错误时，使用本地 mock，便于开发环境
        openid = auth.make_openid_from_code(payload.code)
    user = await logic.get_or_create_user_by_openid(session, openid, payload.nickname)
    await session.commit()
    token = auth.create_access_token(user)
    return schemas.LoginResponse(token=token, username=user.username, role=user.role)


@router.get("/me", response_model=schemas.UserOut)
async def me(current_user=Depends(deps.get_current_user)):
    return current_user


@router.get("/price/calculate/{product_id}", response_model=schemas.PriceCalcResponse)
async def calculate_price(product_id: str, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    return await logic.calculate_price_for_product(session, product)


@router.post("/products", response_model=schemas.Product)
async def create_product(product: schemas.Product, session: AsyncSession = Depends(get_session)):
    exists = await session.get(Product, product.id) if product.id else None
    if exists:
        raise HTTPException(status_code=400, detail="product id already exists")
    created = await logic.create_product(session, product)
    await session.commit()
    return schemas.Product(
        id=created.id,
        name=created.name,
        category_id=created.category_id,
        spec=created.spec,
        base_cost_price=created.base_cost_price,
        fixed_retail_price=created.fixed_retail_price,
        img_url=created.img_url,
    )


@router.get("/products", response_model=schemas.ProductListResponse)
async def list_products(offset: int = 0, limit: int = 20, session: AsyncSession = Depends(get_session)):
    limit = max(1, min(limit, 100))
    items, total = await logic.list_products_with_inventory(session, offset=offset, limit=limit)
    return schemas.ProductListResponse(items=items, total=total)


@router.get("/products/{product_id}", response_model=schemas.Product)
async def get_product(product_id: str, session: AsyncSession = Depends(get_session)):
    try:
        return await logic.product_with_category(session, product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/products/{product_id}", response_model=schemas.Product)
async def update_product(product_id: str, payload: schemas.Product, session: AsyncSession = Depends(get_session)):
    try:
        updated = await logic.update_product(session, product_id, payload)
        await session.commit()
        return updated
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/categories/{category_id}", response_model=schemas.Category)
async def update_category(category_id: str, category: schemas.Category, session: AsyncSession = Depends(get_session)):
    updated = await logic.upsert_category(session, category_id, category)
    await session.commit()
    return schemas.Category(id=updated.id, name=updated.name, retail_multiplier=updated.retail_multiplier)


@router.post("/import/products", response_model=schemas.ProductImportJob)
async def import_products(file_name: str):
    # 仍为占位逻辑
    job = schemas.ProductImportJob(
        id=f"job-{int(datetime.utcnow().timestamp())}",
        file_name=file_name,
        status="processing",
        total_rows=120,
        success_rows=0,
        error_rows=0,
    )
    return job


@router.get("/import/{job_id}", response_model=schemas.ProductImportJob)
async def get_import_job(job_id: str):
    return schemas.ProductImportJob(
        id=job_id,
        file_name="mock.xlsx",
        status="success",
        total_rows=120,
        success_rows=118,
        error_rows=2,
        error_report_url="/mock/error-report.xlsx",
    )


@router.post("/sales", response_model=schemas.SalesOrder)
async def create_sales(
    items: List[schemas.SalesItemPayload],
    username: str = "owner",
    session: AsyncSession = Depends(get_session),
):
    try:
        order = await logic.create_sales_order(session, items, username)
        await session.commit()
        return order
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/inventory/adjust", response_model=schemas.InventoryRecord)
async def adjust_inventory(
    req: schemas.InventoryAdjustRequest, username: str = "owner", session: AsyncSession = Depends(get_session)
):
    inv = await logic.adjust_inventory(session, req, username)
    await session.commit()
    return inv


@router.get("/inventory/logs", response_model=List[schemas.InventoryLog])
async def inventory_logs(session: AsyncSession = Depends(get_session)):
    logs = (await session.execute(sa.select(InventoryLog))).scalars().all()
    return logs


@router.get("/purchase-orders", response_model=List[schemas.PurchaseOrder])
async def list_purchase_orders(session: AsyncSession = Depends(get_session)):
    orders = (
        await session.execute(sa.select(PurchaseOrder).options(selectinload(PurchaseOrder.items)))
    ).scalars().all()
    return orders


@router.post("/purchase-orders", response_model=schemas.PurchaseOrder)
async def create_purchase_order(po: schemas.PurchaseOrder, session: AsyncSession = Depends(get_session)):
    order = await logic.create_purchase_order(session, po)
    await session.commit()
    return order


@router.put("/purchase-orders/{po_id}/receive", response_model=schemas.PurchaseOrder)
async def receive_purchase(po_id: str, items: List[schemas.PurchaseItem], session: AsyncSession = Depends(get_session)):
    try:
        order = await logic.receive_purchase(session, po_id, items)
        await session.commit()
        return order
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/dashboard/realtime", response_model=schemas.DashboardRealtime)
async def dashboard_realtime(session: AsyncSession = Depends(get_session)):
    actual, gp, orders, avg = await logic.dashboard_realtime(session)
    gross_margin = (gp / actual * 100) if actual else 0
    return schemas.DashboardRealtime(
        actual_sales=round(actual, 2),
        gross_profit=round(gp, 2),
        orders=orders,
        avg_ticket=round(avg, 2),
        gross_margin=round(gross_margin, 2),
    )


@router.get("/dashboard/inventory_value", response_model=schemas.InventoryValueResponse)
async def dashboard_inventory_value(session: AsyncSession = Depends(get_session)):
    cost, retail = await logic.dashboard_inventory_value(session)
    return schemas.InventoryValueResponse(cost_total=round(cost, 2), retail_total=round(retail, 2))


@router.get("/dashboard/performance", response_model=schemas.PerformanceResponse)
async def dashboard_performance(session: AsyncSession = Depends(get_session)):
    return await logic.dashboard_performance(session)


@router.get("/inventory/overview", response_model=list[schemas.InventoryOverviewItem])
async def inventory_overview(session: AsyncSession = Depends(get_session)):
    return await logic.inventory_overview(session)
