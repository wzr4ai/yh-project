from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db import get_session
from app.models import schemas
from app.services import llm_agent, logic
from app.services.llm import LLMServiceError

router = APIRouter()


@router.get("/dashboard/realtime", response_model=schemas.DashboardRealtime)
async def dashboard_realtime(session: AsyncSession = Depends(get_session)):
    (
        actual,
        expected,
        diff,
        diff_rate,
        gp,
        orders,
        avg,
        manual,
    ) = await logic.dashboard_realtime(session)
    gross_margin = (gp / actual * 100) if actual else 0
    return schemas.DashboardRealtime(
        actual_sales=round(actual, 2),
        expected_sales=round(expected, 2),
        receipt_diff=round(diff, 2),
        receipt_diff_rate=round(diff_rate, 2),
        gross_profit=round(gp, 2),
        orders=orders,
        avg_ticket=round(avg, 2),
        gross_margin=round(gross_margin, 2),
        manual_receipt=manual,
    )


@router.post("/dashboard/manual_receipt")
async def set_manual_receipt(
    payload: dict,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    val = payload.get("value")
    try:
        amount = float(val)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid value")
    await logic.set_manual_receipt(session, amount)
    await session.commit()
    return {"status": "ok", "value": amount}


@router.get("/dashboard/inventory_value", response_model=schemas.InventoryValueResponse)
async def dashboard_inventory_value(session: AsyncSession = Depends(get_session)):
    (
        cost,
        retail_min,
        retail_max,
        sku_count,
        total_boxes,
    ) = await logic.dashboard_inventory_value(session)
    return schemas.InventoryValueResponse(
        cost_total=round(cost, 2),
        retail_total=round(retail_max, 2),
        retail_total_min=round(retail_min, 2),
        retail_total_max=round(retail_max, 2),
        sku_count=sku_count,
        total_boxes=total_boxes,
    )


@router.get(
    "/dashboard/inventory_breakdown", response_model=schemas.InventoryBreakdownResponse
)
async def dashboard_inventory_breakdown(session: AsyncSession = Depends(get_session)):
    (
        cost,
        retail_min,
        retail_max,
        sku_count,
        total_boxes,
    ) = await logic.dashboard_inventory_value(session)
    categories = await logic.inventory_by_category(session)
    return schemas.InventoryBreakdownResponse(
        cost_total=round(cost, 2),
        retail_total=round(retail_max, 2),
        retail_total_min=round(retail_min, 2),
        retail_total_max=round(retail_max, 2),
        sku_count=sku_count,
        total_boxes=total_boxes,
        categories=[
            schemas.InventoryCategoryStat(
                id=cat["id"],
                name=cat["name"],
                sku=cat["sku"],
                boxes=cat["boxes"],
                cost=cat["cost"],
                retail=cat["retail"],
                retail_min=cat.get("retail_min"),
                retail_max=cat.get("retail_max"),
            )
            for cat in categories
        ],
    )


@router.get("/dashboard/receipt_total")
async def dashboard_receipt_total(session: AsyncSession = Depends(get_session)):
    total = await logic.total_receipts(session)
    return {"total": round(total, 2)}


@router.get("/dashboard/performance", response_model=schemas.PerformanceResponse)
async def dashboard_performance(session: AsyncSession = Depends(get_session)):
    return await logic.dashboard_performance(session)


@router.get("/dashboard/sales-rankings", response_model=schemas.SalesRankingResponse)
async def dashboard_sales_rankings(
    scope: str = "day", session: AsyncSession = Depends(get_session)
):
    try:
        return await logic.sales_rankings(session, scope=scope, limit=5)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dashboard/report", response_model=schemas.DashboardReportResponse)
async def dashboard_report(
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    return await logic.dashboard_report(session)


async def _run_dashboard_report_analysis(
    session: AsyncSession,
    payload: schemas.DashboardReportAnalyzeRequest,
) -> schemas.DashboardReportLLMResponse:
    report = await logic.dashboard_report(session)
    analysis_text = ""
    analysis_error = None
    model = None
    protocol = None
    finish_reason = None
    raw_usage = None
    try:
        llm_resp = await llm_agent.analyze_dashboard_report(
            report.report,
            provider=payload.provider,
            model_tier=payload.model_tier,
            model=payload.model,
        )
        analysis_text = llm_resp.content
        model = llm_resp.model
        protocol = llm_resp.protocol
        finish_reason = llm_resp.finish_reason
        raw_usage = llm_resp.raw_usage
    except (ValueError, LLMServiceError) as exc:
        analysis_error = str(exc)
    return schemas.DashboardReportLLMResponse(
        generated_at=report.generated_at,
        version=report.version,
        report=report.report,
        analysis=analysis_text,
        analysis_error=analysis_error,
        model=model,
        protocol=protocol,
        finish_reason=finish_reason,
        raw_usage=raw_usage,
    )


async def _run_dashboard_ai_analysis(
    session: AsyncSession,
    payload: schemas.DashboardAIBasicRequest,
    analyzer,
) -> schemas.DashboardReportLLMResponse:
    report = await logic.dashboard_report(session)
    analysis_text = ""
    analysis_error = None
    model = None
    protocol = None
    finish_reason = None
    raw_usage = None
    try:
        llm_resp = await analyzer(
            report.report,
            provider=payload.provider,
            model_tier=payload.model_tier,
            model=payload.model,
        )
        analysis_text = llm_resp.content
        model = llm_resp.model
        protocol = llm_resp.protocol
        finish_reason = llm_resp.finish_reason
        raw_usage = llm_resp.raw_usage
    except (ValueError, LLMServiceError) as exc:
        analysis_error = str(exc)
    return schemas.DashboardReportLLMResponse(
        generated_at=report.generated_at,
        version=report.version,
        report=report.report,
        analysis=analysis_text,
        analysis_error=analysis_error,
        model=model,
        protocol=protocol,
        finish_reason=finish_reason,
        raw_usage=raw_usage,
    )


def _insight_to_response(insight) -> schemas.DashboardInsightResponse:
    return schemas.DashboardInsightResponse(
        id=insight.id,
        insight_date=insight.insight_date,
        insight_type=insight.insight_type,
        content=insight.content,
        model=insight.model,
        protocol=insight.protocol,
        finish_reason=insight.finish_reason,
        raw_usage=insight.raw_usage,
        created_at=insight.created_at,
    )


@router.post(
    "/dashboard/report/analysis", response_model=schemas.DashboardReportLLMResponse
)
async def dashboard_report_analysis(
    payload: schemas.DashboardReportAnalyzeRequest,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    return await _run_dashboard_report_analysis(session, payload)


@router.get(
    "/dashboard/report/analysis", response_model=schemas.DashboardReportLLMResponse
)
async def dashboard_report_analysis_default(
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    return await _run_dashboard_report_analysis(
        session, schemas.DashboardReportAnalyzeRequest()
    )


@router.post(
    "/dashboard/ai/restock-advice", response_model=schemas.DashboardReportLLMResponse
)
async def dashboard_ai_restock_advice(
    payload: schemas.DashboardAIBasicRequest,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    return await _run_dashboard_ai_analysis(
        session, payload, llm_agent.analyze_dashboard_restock_advice
    )


@router.post(
    "/dashboard/ai/daily-summary", response_model=schemas.DashboardReportLLMResponse
)
async def dashboard_ai_daily_summary(
    payload: schemas.DashboardAIBasicRequest,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    return await _run_dashboard_ai_analysis(
        session, payload, llm_agent.analyze_dashboard_daily_summary
    )


@router.post(
    "/dashboard/ai/clearance-plan", response_model=schemas.DashboardReportLLMResponse
)
async def dashboard_ai_clearance_plan(
    payload: schemas.DashboardAIBasicRequest,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    return await _run_dashboard_ai_analysis(
        session, payload, llm_agent.analyze_dashboard_clearance_plan
    )


@router.get("/dashboard/ai/insights", response_model=schemas.DashboardInsightResponse)
async def dashboard_ai_insight(
    insight_type: schemas.DashboardInsightType,
    insight_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    target_date = insight_date or date.today()
    insight = await logic.get_insight(
        session, insight_type=insight_type, insight_date=target_date
    )
    if not insight:
        raise HTTPException(status_code=404, detail="not found")
    return _insight_to_response(insight)


@router.get(
    "/dashboard/ai/insights/latest", response_model=schemas.DashboardInsightResponse
)
async def dashboard_ai_insight_latest(
    insight_type: schemas.DashboardInsightType | None = None,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    insight = await logic.get_latest_insight(session, insight_type=insight_type)
    if not insight:
        raise HTTPException(status_code=404, detail="not found")
    return _insight_to_response(insight)


@router.post(
    "/dashboard/ai/insights/generate",
    response_model=schemas.DashboardInsightResponse,
)
async def dashboard_ai_insight_generate(
    payload: schemas.DashboardInsightGenerateRequest,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    target_date = payload.insight_date or date.today()
    if not payload.force:
        existing = await logic.get_insight(
            session, insight_type=payload.insight_type, insight_date=target_date
        )
        if existing:
            return _insight_to_response(existing)
    report = await logic.dashboard_report(session)
    if payload.insight_type == "morning":
        llm_resp = await llm_agent.analyze_dashboard_morning_plan(
            report.report,
            provider=payload.provider,
            model_tier=payload.model_tier,
            model=payload.model,
        )
    else:
        llm_resp = await llm_agent.analyze_dashboard_daily_summary(
            report.report,
            provider=payload.provider,
            model_tier=payload.model_tier,
            model=payload.model,
        )
    insight = await logic.upsert_insight(
        session,
        insight_type=payload.insight_type,
        insight_date=target_date,
        content=llm_resp.content,
        model=llm_resp.model,
        protocol=llm_resp.protocol,
        finish_reason=llm_resp.finish_reason,
        raw_usage=llm_resp.raw_usage,
    )
    await session.commit()
    return _insight_to_response(insight)
