from datetime import date, datetime
from typing import Literal, Optional, List

from pydantic import BaseModel, Field, ConfigDict


Role = Literal["owner", "clerk"]
PricingBasis = Literal["例外价", "分类系数", "全局系数"]


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    role: Role


class LoginResponse(BaseModel):
    token: str
    username: str
    role: Role


class WeappLoginRequest(BaseModel):
    code: str
    nickname: Optional[str] = None


class User(BaseModel):
    id: str
    username: str
    role: Role
    openid: str


class UserOut(BaseModel):
    id: str
    username: str
    role: Role


class Category(ORMBase):
    id: Optional[str] = None
    name: str
    retail_multiplier: Optional[float] = None


class Product(ORMBase):
    id: Optional[str] = None
    name: str
    category_id: str
    spec: str
    base_cost_price: float
    fixed_retail_price: Optional[float] = None
    img_url: Optional[str] = None


class PriceCalcResponse(BaseModel):
    price: float
    basis: PricingBasis


class ProductImportJob(BaseModel):
    id: Optional[str] = None
    file_name: str
    status: Literal["pending", "processing", "success", "failed"]
    total_rows: int
    success_rows: int
    error_rows: int
    error_report_url: Optional[str] = None


class SalesItemPayload(BaseModel):
    product_id: str
    quantity: int
    actual_price: float


class SalesItem(ORMBase):
    id: Optional[str] = None
    product_id: str
    quantity: int
    snapshot_cost: float
    snapshot_standard_price: float
    actual_sale_price: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SalesOrder(ORMBase):
    id: Optional[str] = None
    order_date: datetime
    items: List[SalesItem]
    total_actual_amount: float
    created_by: str


class InventoryRecord(ORMBase):
    product_id: str
    warehouse_id: str = "default"
    current_stock: int


class InventoryLog(ORMBase):
    id: Optional[str] = None
    product_id: str
    warehouse_id: str
    change_date: datetime
    change_qty: int
    type: str
    ref_type: Optional[str] = None
    ref_id: Optional[str] = None


class InventoryAdjustRequest(BaseModel):
    product_id: str
    delta: int
    reason: str


class PurchaseItem(ORMBase):
    id: Optional[str] = None
    product_id: str
    quantity: int
    expected_cost: float
    received_qty: int = 0
    actual_cost: Optional[float] = None


class PurchaseOrder(ORMBase):
    id: Optional[str] = None
    status: str
    supplier: str
    expected_date: date
    remark: Optional[str] = None
    items: List[PurchaseItem]
    created_by: str


class DashboardRealtime(BaseModel):
    actual_sales: float
    gross_profit: float
    orders: int
    avg_ticket: float
    gross_margin: float


class InventoryValueResponse(BaseModel):
    cost_total: float
    retail_total: float


class PerformanceResponse(BaseModel):
    price_diff: float
    price_diff_rate: float
    expected_sales: float
    actual_sales: float
