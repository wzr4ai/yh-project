from datetime import date, datetime
import os
from typing import Literal, Optional, List, Dict

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
    name: Optional[str] = None
    retail_multiplier: Optional[float] = None
    is_custom: Optional[bool] = False


class Product(ORMBase):
    id: Optional[str] = None
    name: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    categories: List["Category"] = []
    spec: str
    base_cost_price: float
    fixed_retail_price: Optional[float] = None
    retail_multiplier: Optional[float] = None
    pack_price_ref: Optional[float] = None
    img_url: Optional[str] = None
    effect_url: Optional[str] = None


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
    loose_units: int | None = 0


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
    actual_sales: float  # 实际入账（来自入账表）
    expected_sales: float
    receipt_diff: float
    receipt_diff_rate: float
    gross_profit: float
    orders: int
    avg_ticket: float
    gross_margin: float
    manual_receipt: float | None = None


class InventoryValueResponse(BaseModel):
    cost_total: float
    retail_total: float


class PerformanceResponse(BaseModel):
    price_diff: float
    price_diff_rate: float
    expected_sales: float
    actual_sales: float


class ProductListItem(BaseModel):
    id: str
    name: str
    spec: Optional[str] = None
    category_name: Optional[str] = None
    category_ids: List[str] = []
    base_cost_price: float
    standard_price: float
    price_basis: PricingBasis
    stock: int
    retail_total: float
    cost_total: float
    effect_url: Optional[str] = None


class InventoryOverviewItem(BaseModel):
    product_id: str
    name: str
    spec: Optional[str] = None
    category_name: Optional[str] = None
    base_cost_price: float
    box_price: float
    box_count: int
    loose_count: int
    cost_total: float


class ProductListResponse(BaseModel):
    items: List[ProductListItem]
    total: int


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMChatRequest(BaseModel):
    messages: List[LLMMessage]
    model_tier: Literal["low", "mid", "high"] = "mid"
    protocol: Optional[Literal["gemini", "openai", "open"]] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_output_tokens: int = Field(
        default=max(1, min(8192, int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048") or 2048))),
        ge=1,
        le=8192,
    )


class LLMChatResponse(BaseModel):
    content: str
    model: str
    protocol: str
    finish_reason: Optional[str] = None
    raw_usage: Optional[Dict] = None


class OrderAnalyzeRequest(BaseModel):
    raw_text: str


class OrderAnalyzeCandidate(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    score: Optional[float] = None


class OrderAnalyzeItem(BaseModel):
    raw_name: str
    suggested_product_id: Optional[str] = None
    suggested_product_name: Optional[str] = None
    quantity: int = 1
    confidence: Literal["high", "low", "new"] = "low"
    candidates: List[OrderAnalyzeCandidate] = Field(default_factory=list)
    detected_price: Optional[float] = None


class OrderAnalyzeResponse(BaseModel):
    items: List[OrderAnalyzeItem]


class OrderConfirmItem(BaseModel):
    product_id: str
    quantity: int
    actual_price: float
    raw_name: Optional[str] = None


class OrderConfirmRequest(BaseModel):
    items: List[OrderConfirmItem]


class OrderImportFileResponse(BaseModel):
    file_name: str
    stored_path: str
