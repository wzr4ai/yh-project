from __future__ import annotations

import os
from datetime import timedelta

from minio import Minio


def _bool_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_minio_client() -> Minio:
    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    secure = _bool_env(os.getenv("MINIO_SECURE"), default=False)
    if not endpoint or not access_key or not secret_key:
        raise ValueError("MINIO_ENDPOINT/MINIO_ACCESS_KEY/MINIO_SECRET_KEY 未配置")
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def presign_get_object(bucket: str, object_name: str, expires_days: int | None = None) -> str:
    bucket = (bucket or "").strip()
    object_name = (object_name or "").strip().lstrip("/")
    if not bucket or not object_name:
        raise ValueError("bucket/object_name 不能为空")
    client = _get_minio_client()
    days = expires_days if expires_days is not None else int(os.getenv("MINIO_PRESIGN_EXPIRE_DAYS", "7") or 7)
    days = max(1, min(days, 30))
    return client.presigned_get_object(bucket, object_name, expires=timedelta(days=days))


def resolve_bucket_and_object(value: str) -> tuple[str, str]:
    raw = (value or "").strip().lstrip("/")
    if not raw:
        raise ValueError("video_url 不能为空")
    default_bucket = (os.getenv("MINIO_VIDEO_BUCKET") or "").strip()
    if default_bucket:
        prefix = f"{default_bucket}/"
        if raw.startswith(prefix):
            return default_bucket, raw[len(prefix):]
        return default_bucket, raw
    parts = raw.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    raise ValueError("MINIO_VIDEO_BUCKET 未配置，且 video_url 未包含 bucket 前缀")
