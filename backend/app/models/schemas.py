from datetime import date, datetime
import os
from typing import Any, Literal, Optional, List, Dict

from pydantic import BaseModel, Field, ConfigDict


Role = Literal["owner", "clerk", "user"]
BarcodeLevel = Literal["BOX", "UNIT", "PIECE"]
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
    retail_multiplier_min: Optional[float] = None
    retail_multiplier_max: Optional[float] = None
    is_custom: Optional[bool] = False


class Product(ORMBase):
    id: Optional[str] = None
    name: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    categories: List["Category"] = []
    spec: Optional[str] = None
    units_per_box: int = 1
    pieces_per_unit: int = 1
    box_cost_price: float = 0
    base_cost_price: float = 0
    fixed_retail_price: Optional[float] = None
    retail_multiplier: Optional[float] = None
    pack_price_ref: Optional[float] = None
    img_url: Optional[str] = None
    video_url: Optional[str] = None
    effect_url: Optional[str] = None
    barcode: Optional[str] = None
    barcodes: List["ProductBarcode"] = []


class ProductBarcode(BaseModel):
    id: Optional[str] = None
    barcode: str
    level: BarcodeLevel = "PIECE"


class ProductBarcodeCreate(BaseModel):
    barcode: str
    level: BarcodeLevel = "PIECE"


Product.model_rebuild()


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
    received_units: Optional[int] = None
    actual_cost: Optional[float] = None


class PurchaseItemUpdate(BaseModel):
    quantity: Optional[int] = None
    expected_cost: Optional[float] = None
    actual_cost: Optional[float] = None


class PurchaseOrderSummary(BaseModel):
    id: str
    status: str
    supplier: Optional[str] = None
    expected_date: Optional[date] = None
    remark: Optional[str] = None
    created_by: Optional[str] = None
    item_count: int = 0
    total_qty: int = 0
    received_qty: int = 0
    expected_cost_total: float = 0


class PurchaseOrderItemRow(BaseModel):
    id: str
    product_id: str
    product_name: Optional[str] = None
    product_spec: Optional[str] = None
    quantity: int
    expected_cost: float
    received_qty: int = 0
    received_units: Optional[int] = None
    actual_cost: Optional[float] = None


class PurchaseOrderItemsResponse(BaseModel):
    items: List[PurchaseOrderItemRow]
    total: int


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
    retail_total_min: float | None = None
    retail_total_max: float | None = None
    sku_count: int | None = None
    total_boxes: float | None = None


class InventoryCategoryStat(BaseModel):
    id: str
    name: str
    sku: int
    boxes: float
    cost: float
    retail: float
    retail_min: float | None = None
    retail_max: float | None = None


class InventoryBreakdownResponse(BaseModel):
    cost_total: float
    retail_total: float
    retail_total_min: float | None = None
    retail_total_max: float | None = None
    sku_count: int
    total_boxes: float
    categories: list[InventoryCategoryStat]


class PerformanceResponse(BaseModel):
    price_diff: float
    price_diff_rate: float
    expected_sales: float
    actual_sales: float
    cost_total: float = 0
    gross_profit: float = 0
    purchase_cost_total: float = 0


SalesRankingScope = Literal["day", "all"]


class SalesRankingItem(BaseModel):
    product_id: str
    name: str
    stock: int = 0
    sales_amount: float = 0
    profit_margin: float = 0


class SalesRankingResponse(BaseModel):
    scope: SalesRankingScope
    top_sales: List[SalesRankingItem]
    top_margin: List[SalesRankingItem]


class DashboardReportResponse(BaseModel):
    generated_at: datetime
    version: str = "v1"
    report: Dict[str, Any]


class DashboardReportLLMResponse(BaseModel):
    generated_at: datetime
    version: str = "v1"
    report: Dict[str, Any]
    analysis: str = ""
    analysis_error: Optional[str] = None
    model: Optional[str] = None
    protocol: Optional[str] = None
    finish_reason: Optional[str] = None
    raw_usage: Optional[Dict] = None


class DashboardReportAnalyzeRequest(BaseModel):
    provider: Literal["gemini", "deepseek"] = "gemini"
    model_tier: Literal["low", "mid", "high"] = "high"
    model: Optional[str] = None


class DashboardAIBasicRequest(BaseModel):
    provider: Literal["gemini", "deepseek"] = "gemini"
    model_tier: Literal["low", "mid", "high"] = "low"
    model: Optional[str] = None


DashboardInsightType = Literal["morning", "evening"]


class DashboardInsightGenerateRequest(DashboardAIBasicRequest):
    insight_type: DashboardInsightType = "morning"
    insight_date: Optional[date] = None
    force: bool = False


class DashboardInsightResponse(BaseModel):
    id: str
    insight_date: date
    insight_type: DashboardInsightType
    content: str
    model: Optional[str] = None
    protocol: Optional[str] = None
    finish_reason: Optional[str] = None
    raw_usage: Optional[Dict] = None
    created_at: datetime


class PricingMultiplierConfig(BaseModel):
    min_multiplier: float
    max_multiplier: float


class ProductListItem(BaseModel):
    id: str
    name: str
    spec: Optional[str] = None
    category_name: Optional[str] = None
    category_ids: List[str] = []
    base_cost_price: float
    units_per_box: int = 1
    pieces_per_unit: int = 1
    box_cost_price: float = 0
    standard_price: float
    price_min: float
    price_max: float
    price_basis: PricingBasis
    stock: int
    retail_total: float
    cost_total: float
    video_url: Optional[str] = None
    effect_url: Optional[str] = None
    barcode: Optional[str] = None


class InventoryOverviewItem(BaseModel):
    product_id: str
    name: str
    spec: Optional[str] = None
    category_name: Optional[str] = None
    base_cost_price: float
    box_cost_price: float = 0
    units_per_box: int = 1
    pieces_per_unit: int = 1
    box_price: float
    box_count: int
    loose_count: int
    unit_count: int = 0
    piece_count: int = 0
    cost_total: float


class ProductListResponse(BaseModel):
    items: List[ProductListItem]
    total: int


class BarcodeLookupResponse(BaseModel):
    product: ProductListItem
    barcode: str
    level: BarcodeLevel
    multiplier: int


class PricingOverviewItem(BaseModel):
    id: str
    name: str
    spec: Optional[str] = None
    category_name: Optional[str] = None
    category_ids: List[str] = []
    custom_category_ids: List[str] = []
    stock: int = 0
    units_per_box: int = 1
    pieces_per_unit: int = 1
    standard_price: float
    price_basis: PricingBasis
    img_url: Optional[str] = None
    video_url: Optional[str] = None
    effect_url: Optional[str] = None
    barcode: Optional[str] = None


class PricingOverviewResponse(BaseModel):
    items: List[PricingOverviewItem]
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
        default=max(
            1, min(8192, int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048") or 2048))
        ),
        ge=1,
        le=8192,
    )


class LLMChatResponse(BaseModel):
    content: str
    model: str
    protocol: str
    finish_reason: Optional[str] = None
    raw_usage: Optional[Dict] = None


class AIChatRequest(BaseModel):
    messages: List[LLMMessage]
    model_tier: Literal["low", "mid", "high"] = "mid"
    protocol: Optional[Literal["gemini", "openai", "open"]] = None
    model: Optional[str] = None
    temperature: float = 0.4
    max_output_tokens: int = Field(
        default=max(
            1, min(8192, int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048") or 2048))
        ),
        ge=1,
        le=8192,
    )


class AIAction(BaseModel):
    type: str
    title: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False
    preview: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


class AIChatResponse(BaseModel):
    reply: str
    actions: List[AIAction] = Field(default_factory=list)


class AIActionRequest(BaseModel):
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class AIActionResponse(BaseModel):
    reply: str
    result: Optional[Dict[str, Any]] = None


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


class MiscCostBase(BaseModel):
    item: str
    quantity: float = 1
    amount: float
    created_by: Optional[str] = None


class MiscCostCreate(MiscCostBase):
    pass


class MiscCost(ORMBase, MiscCostBase):
    id: str
    created_at: datetime


class MiscCostUpdate(BaseModel):
    item: Optional[str] = None
    quantity: Optional[float] = None
    amount: Optional[float] = None
    created_by: Optional[str] = None


class ShareholderBase(BaseModel):
    name: str
    share_ratio: float = 0
    role: Optional[str] = None
    note: Optional[str] = None
    is_active: bool = True


class ShareholderCreate(ShareholderBase):
    pass


class ShareholderUpdate(BaseModel):
    name: Optional[str] = None
    share_ratio: Optional[float] = None
    role: Optional[str] = None
    note: Optional[str] = None
    is_active: Optional[bool] = None


class Shareholder(ORMBase, ShareholderBase):
    id: str
    created_at: datetime
    updated_at: datetime


class ShareholderCapitalCreate(BaseModel):
    shareholder_id: str
    amount: float
    memo: Optional[str] = None
    biz_date: Optional[date] = None


class ShareholderCapital(ORMBase):
    id: str
    shareholder_id: str
    amount: float
    memo: Optional[str] = None
    biz_date: date
    created_at: datetime


class ShareholderDistributionCreate(BaseModel):
    shareholder_id: str
    amount: float
    memo: Optional[str] = None
    biz_date: Optional[date] = None


class ShareholderDistribution(ORMBase):
    id: str
    shareholder_id: str
    amount: float
    memo: Optional[str] = None
    biz_date: date
    created_at: datetime


class ShareholderSummaryItem(BaseModel):
    shareholder_id: str
    name: str
    role: Optional[str] = None
    note: Optional[str] = None
    is_active: bool = True
    share_ratio: float
    effective_ratio: float
    profit_basis: float
    distributable: float
    contributed: float
    distributed: float
    balance: float
    need_topup: float
    can_distribute: float


class ShareholderSummaryResponse(BaseModel):
    profit_basis: Literal["net", "gross"]
    actual_sales: float
    cost_total: float
    gross_profit: float
    misc_total: float
    net_profit: float
    distributable_total: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    items: list[ShareholderSummaryItem]
