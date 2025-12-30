from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db import get_session
from app.services import exports as export_service

router = APIRouter()


@router.get("/exports/replenishment.csv")
async def export_replenishment_csv(
    target_boxes: float,
    category_id: str | None = None,
    category_name: str | None = None,
    need_mode: str = "below_target",
    only_need: bool = True,
    price_mode: str = "cost",
    warehouse_id: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    if not current_user or getattr(current_user, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="forbidden")
    if need_mode not in ("below_target", "out_of_stock"):
        raise HTTPException(status_code=400, detail="invalid need_mode")
    if price_mode not in ("cost", "standard"):
        raise HTTPException(status_code=400, detail="invalid price_mode")
    try:
        content = await export_service.export_replenishment_csv(
            session,
            category_id=category_id,
            category_name=category_name,
            target_boxes=target_boxes,
            need_mode=need_mode,  # type: ignore[arg-type]
            only_need=only_need,
            price_mode=price_mode,  # type: ignore[arg-type]
            warehouse_id=warehouse_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"replenishment_{ts}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
