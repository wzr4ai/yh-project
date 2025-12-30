import os
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db import get_session
from app.models.entities import Product
from app.services import minio_service

router = APIRouter()


@router.get("/minio/presign")
async def minio_presign(
    bucket: str,
    object_name: str,
    expires_days: int | None = None,
    current_user=Depends(deps.get_current_user),
):
    try:
        url = minio_service.presign_get_object(bucket, object_name, expires_days=expires_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"url": url}


@router.get("/products/{product_id}/video-url")
async def get_product_video_url(
    product_id: str,
    expires_days: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    product = await session.get(Product, product_id)
    if not product or not product.video_url:
        raise HTTPException(status_code=404, detail="video not found")
    try:
        bucket, obj = minio_service.resolve_bucket_and_object(product.video_url)
        url = minio_service.presign_get_object(bucket, obj, expires_days=expires_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="minio unavailable") from exc
    days = expires_days if expires_days is not None else int(os.getenv("MINIO_PRESIGN_EXPIRE_DAYS", "7") or 7)
    days = max(1, min(days, 30))
    expires_at = int(time.time()) + days * 86400
    return {"url": url, "expires_at": expires_at}
