from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from app.models import schemas
from app.services import mock_store

router = APIRouter(prefix="/api")


@router.post("/auth/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest):
    token = f"mock-token-{payload.role}-{payload.username}"
    return schemas.LoginResponse(token=token, username=payload.username, role=payload.role)


@router.get("/price/calculate/{product_id}", response_model=schemas.PriceCalcResponse)
def calculate_price(product_id: str):
    product = mock_store.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    return mock_store.calculate_price(product)


@router.post("/products", response_model=schemas.Product)
def create_product(product: schemas.Product):
    if mock_store.get_product(product.id):
        raise HTTPException(status_code=400, detail="product id already exists")
    mock_store.PRODUCTS.append(product)
    return product


@router.put("/categories/{category_id}", response_model=schemas.Category)
def update_category(category_id: str, category: schemas.Category):
    for idx, cat in enumerate(mock_store.CATEGORIES):
        if cat.id == category_id:
            mock_store.CATEGORIES[idx] = category
            return category
    mock_store.CATEGORIES.append(category)
    return category


@router.post("/import/products", response_model=schemas.ProductImportJob)
def import_products(file_name: str):
    # 模拟异步导入任务
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
def get_import_job(job_id: str):
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
def create_sales(items: List[schemas.SalesItemPayload], username: str = "owner"):
    try:
        return mock_store.create_sales_order(items, username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/inventory/adjust", response_model=schemas.InventoryRecord)
def adjust_inventory(req: schemas.InventoryAdjustRequest, username: str = "owner"):
    return mock_store.adjust_inventory(req, username)


@router.get("/inventory/logs", response_model=List[schemas.InventoryLog])
def inventory_logs():
    return mock_store.list_inventory_logs()


@router.get("/purchase-orders", response_model=List[schemas.PurchaseOrder])
def list_purchase_orders():
    return mock_store.list_purchase_orders()


@router.post("/purchase-orders", response_model=schemas.PurchaseOrder)
def create_purchase_order(po: schemas.PurchaseOrder):
    return mock_store.create_purchase_order(po)


@router.put("/purchase-orders/{po_id}/receive", response_model=schemas.PurchaseOrder)
def receive_purchase(po_id: str, items: List[schemas.PurchaseItem]):
    try:
        return mock_store.receive_purchase_order(po_id, items)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/dashboard/realtime", response_model=schemas.DashboardRealtime)
def dashboard_realtime():
    actual, gp, orders, avg = mock_store.dashboard_realtime()
    gross_margin = (gp / actual * 100) if actual else 0
    return schemas.DashboardRealtime(
        actual_sales=round(actual, 2),
        gross_profit=round(gp, 2),
        orders=orders,
        avg_ticket=round(avg, 2),
        gross_margin=round(gross_margin, 2),
    )


@router.get("/dashboard/inventory_value", response_model=schemas.InventoryValueResponse)
def dashboard_inventory_value():
    cost, retail = mock_store.inventory_value()
    return schemas.InventoryValueResponse(cost_total=round(cost, 2), retail_total=round(retail, 2))


@router.get("/dashboard/performance", response_model=schemas.PerformanceResponse)
def dashboard_performance():
    return mock_store.performance()
