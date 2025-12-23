"""
将 effect_videos.csv 中的 saved_path 写入 product.video_url。

规则：
- 仅处理 saved_path 为有效文件路径的行（跳过 fail / <200k / skip / 空）
- 若 saved_path 含指定前缀，则去掉前缀，仅保存文件名

运行：
  cd backend
  set -a; source .env; set +a
  uv run python utils/import_effect_videos_to_product.py

可选参数：
  --csv-path       CSV 路径（默认自动查找 backend/files/effect_videos.csv 或 backend/files/effect_videos/effect_videos.csv）
  --strip-prefix   需要去掉的路径前缀（默认：/home/wzr/dev/yh-project/backend/files/effect_videos/）
  --dry-run        仅打印，不写入数据库
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.entities import Product


DEFAULT_PREFIX = "/home/wzr/dev/yh-project/backend/files/effect_videos/"
SKIP_TOKENS = {"fail", "<200k", "skip", ""}


def _load_env_file_if_present(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, _, val = raw.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def ensure_env_loaded() -> None:
    env_candidates = [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for env_path in env_candidates:
        _load_env_file_if_present(env_path)


def get_database_url() -> str | None:
    ensure_env_loaded()
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    return None


def resolve_csv_path(arg_path: str | None) -> Path:
    if arg_path:
        return Path(arg_path)
    candidates = [
        Path(__file__).resolve().parent.parent / "files" / "effect_videos.csv",
        Path(__file__).resolve().parent.parent / "files" / "effect_videos" / "effect_videos.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def clean_saved_path(saved_path: str, strip_prefix: str) -> str:
    raw = (saved_path or "").strip()
    if raw in SKIP_TOKENS:
        return ""
    if strip_prefix and raw.startswith(strip_prefix):
        raw = raw[len(strip_prefix):]
    # 统一仅保存文件名
    return Path(raw).name


def parse_csv(csv_path: Path, strip_prefix: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 不存在: {csv_path}")
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_id = (row.get("product_id") or "").strip()
            saved_path = (row.get("saved_path") or "").strip()
            if not product_id:
                continue
            cleaned = clean_saved_path(saved_path, strip_prefix)
            if not cleaned:
                continue
            # 若同一商品重复出现，保留第一条有效记录
            if product_id not in mapping:
                mapping[product_id] = cleaned
    return mapping


async def run(csv_path: Path, strip_prefix: str, dry_run: bool) -> None:
    db_url = get_database_url()
    if not db_url:
        raise RuntimeError("缺少 DATABASE_URL，请在环境变量或 .env 中配置后重试。")
    mapping = parse_csv(csv_path, strip_prefix)
    if not mapping:
        print("未找到可写入的记录。")
        return

    engine = create_async_engine(db_url, echo=False, future=True)
    try:
        async with AsyncSession(engine) as session:
            updated = 0
            for product_id, filename in mapping.items():
                if dry_run:
                    print(f"[预览] {product_id} -> {filename}")
                    continue
                product = await session.get(Product, product_id)
                if not product:
                    print(f"[跳过] 商品不存在: {product_id}")
                    continue
                product.video_url = filename
                updated += 1
            if not dry_run:
                await session.commit()
            print(f"处理完成，写入 {updated} 条记录。")
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 effect_videos.csv 写入 product.video_url")
    parser.add_argument("--csv-path", default=None, help="CSV 路径")
    parser.add_argument("--strip-prefix", default=DEFAULT_PREFIX, help="需要去掉的路径前缀")
    parser.add_argument("--dry-run", action="store_true", help="仅打印不写入")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = resolve_csv_path(args.csv_path)
    run_kwargs = {
        "csv_path": csv_path,
        "strip_prefix": args.strip_prefix or "",
        "dry_run": args.dry_run,
    }
    import asyncio

    asyncio.run(run(**run_kwargs))


if __name__ == "__main__":
    main()
