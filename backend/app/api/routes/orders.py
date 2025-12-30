from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import schemas
from app.services import logic, llm_agent
from app.services.llm import LLMServiceError

router = APIRouter()


@router.post("/orders/analyze", response_model=schemas.OrderAnalyzeResponse)
async def analyze_orders(payload: schemas.OrderAnalyzeRequest, session: AsyncSession = Depends(get_session)):
    context, product_lookup = await llm_agent.build_product_context(session)
    try:
        llm_resp = await llm_agent.analyze_order_text(payload.raw_text, context)
        return await llm_agent.parse_and_validate(llm_resp.content, product_lookup)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/orders/import", response_model=schemas.SalesOrder)
async def import_orders(payload: schemas.OrderConfirmRequest, session: AsyncSession = Depends(get_session)):
    try:
        order = await logic.create_sales_order(session, payload.items, username="owner")
        await session.commit()
        return order
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/import-file", response_model=schemas.OrderImportFileResponse)
async def import_orders_file(file: UploadFile = File(...), filename: str = Form(None)):
    target_name = filename or file.filename or "orders.csv"
    safe_name = target_name.replace("/", "_")
    dest_path = f"/tmp/{safe_name}"
    try:
        content = await file.read()
        with open(dest_path, "wb") as f:
            f.write(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to store file: {exc}") from exc
    return schemas.OrderImportFileResponse(file_name=safe_name, stored_path=dest_path)
