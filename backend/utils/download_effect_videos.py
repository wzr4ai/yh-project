"""
从商品表中读取 effect_url（燃放效果网页），抓取网页里的视频文件并下载。

默认下载 >200KB 的视频文件，支持 mp4/mov/webm/m4v。

运行：
  cd backend
  set -a; source .env; set +a
  uv run python utils/download_effect_videos.py

可选参数：
  --output-dir         下载目录（默认：backend/files/effect_videos）
  --log-file           下载日志路径（默认：<output-dir>/effect_videos.csv）
  --min-size-mb        最小文件大小（默认：0.2 = 200KB）
  --limit              最多处理多少个商品（默认：0=不限制）
  --max-per-product    每个商品最多下载几个视频（默认：2）
  --timeout            网络超时时间（秒，默认：15）
  --dry-run            仅打印，不下载
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.entities import Product


ALLOWED_EXTS = {".mp4", ".mov", ".webm", ".m4v"}
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
SRC_RE = re.compile(r"""(?:src|data-src)\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


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
    user = os.getenv("POSTGRES_USER")
    pwd = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DB")
    if not any([user, pwd, host, port, db]):
        return None
    user = user or "postgres"
    pwd = pwd or "postgres"
    host = host or "postgres"
    port = port or "5432"
    db = db or "postgres"
    return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}"


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        return f"https:{raw}"
    parsed = urlparse(raw)
    if not parsed.scheme:
        return f"https://{raw}"
    return raw


def sanitize_name(text: str) -> str:
    cleaned = SAFE_NAME_RE.sub("_", text or "").strip("_")
    return cleaned or "product"


def extract_video_urls(html: str, base_url: str) -> list[str]:
    candidates: list[str] = []
    # 先找所有 src/data-src
    for src in SRC_RE.findall(html or ""):
        url = normalize_url(urljoin(base_url, src))
        if url:
            candidates.append(url)
    # 再补充直接出现的 URL
    for url in URL_RE.findall(html or ""):
        url = normalize_url(url)
        if url:
            candidates.append(url)

    result: list[str] = []
    for url in candidates:
        path = urlparse(url).path.lower()
        ext = Path(path).suffix
        if ext in ALLOWED_EXTS:
            result.append(url)
    # 去重
    dedup: list[str] = []
    seen = set()
    for url in result:
        if url in seen:
            continue
        seen.add(url)
        dedup.append(url)
    return dedup


async def fetch_content_length(client: httpx.AsyncClient, url: str) -> int | None:
    try:
        resp = await client.head(url, follow_redirects=True)
        if resp.status_code >= 400:
            return None
        length = resp.headers.get("Content-Length")
        return int(length) if length and length.isdigit() else None
    except Exception:
        return None


async def download_stream(
    client: httpx.AsyncClient,
    url: str,
    dest_path: Path,
    min_bytes: int,
    timeout: float,
) -> tuple[bool, int]:
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    size = 0
    try:
        async with client.stream("GET", url, follow_redirects=True, timeout=timeout) as resp:
            if resp.status_code >= 400:
                return False, 0
            with tmp_path.open("wb") as f:
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue
                    size += len(chunk)
                    f.write(chunk)
        if size < min_bytes:
            tmp_path.unlink(missing_ok=True)
            return False, size
        tmp_path.replace(dest_path)
        return True, size
    except Exception:
        tmp_path.unlink(missing_ok=True)
        return False, size


def pick_extension(url: str) -> str:
    ext = Path(urlparse(url).path).suffix
    if ext.lower() in ALLOWED_EXTS:
        return ext
    return ".mp4"


async def iter_products(session: AsyncSession, limit: int) -> Iterable[Product]:
    stmt = sa.select(Product).where(Product.effect_url.is_not(None), Product.effect_url != "").order_by(Product.id)
    if limit > 0:
        stmt = stmt.limit(limit)
    result = (await session.execute(stmt)).scalars().all()
    return result


async def run(
    *,
    output_dir: Path,
    log_file: Path,
    min_size_mb: float,
    limit: int,
    max_per_product: int,
    timeout: float,
    dry_run: bool,
) -> None:
    db_url = get_database_url()
    if not db_url:
        raise RuntimeError("缺少 DATABASE_URL，请在环境变量或 .env 中配置后重试。")

    output_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    min_bytes = int(min_size_mb * 1024 * 1024)
    engine = create_async_engine(db_url, echo=False, future=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari",
    }
    try:
        async with AsyncSession(engine) as session, httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            products = await iter_products(session, limit)
            print(f"共发现 {len(products)} 个商品含 effect_url")
            log_fp = None
            csv_writer = None
            if not dry_run:
                is_new = (not log_file.exists()) or log_file.stat().st_size == 0
                log_fp = log_file.open("a", encoding="utf-8", newline="")
                csv_writer = csv.writer(log_fp)
                if is_new:
                    csv_writer.writerow(["product_id", "video_url", "saved_path"])
            for product in products:
                page_url = normalize_url(product.effect_url or "")
                if not page_url:
                    continue
                try:
                    resp = await client.get(page_url, follow_redirects=True)
                    if resp.status_code >= 400:
                        print(f"[跳过] {product.name}: 页面请求失败 {resp.status_code}")
                        continue
                    html = resp.text
                except Exception:
                    print(f"[跳过] {product.name}: 页面请求异常")
                    continue

                video_urls = extract_video_urls(html, page_url)
                if not video_urls:
                    print(f"[无视频] {product.name}")
                    continue

                downloaded = 0
                for idx, video_url in enumerate(video_urls):
                    if max_per_product > 0 and downloaded >= max_per_product:
                        break
                    ext = pick_extension(video_url)
                    file_name = f"{sanitize_name(product.name)}_{product.id}_{idx}{ext}"
                    dest_path = output_dir / file_name
                    if dest_path.exists():
                        print(f"[已存在] {dest_path.name}")
                        if csv_writer:
                            csv_writer.writerow([product.id, video_url, str(dest_path)])
                        downloaded += 1
                        continue

                    size = await fetch_content_length(client, video_url)
                    if size is not None and size < min_bytes:
                        print(f"[小于阈值] {product.name}: {video_url}")
                        if csv_writer:
                            csv_writer.writerow([product.id, video_url, "<200k"])
                        continue

                    if dry_run:
                        print(f"[预览] {product.name}: {video_url}")
                        if csv_writer:
                            csv_writer.writerow([product.id, video_url, "skip"])
                        downloaded += 1
                        continue

                    ok, bytes_written = await download_stream(
                        client, video_url, dest_path, min_bytes=min_bytes, timeout=timeout
                    )
                    if ok:
                        print(f"[已下载] {dest_path.name} ({bytes_written / 1024 / 1024:.2f}MB)")
                        if csv_writer:
                            csv_writer.writerow([product.id, video_url, str(dest_path)])
                        downloaded += 1
                    else:
                        print(f"[失败/过小] {product.name}: {video_url}")
                        if csv_writer:
                            csv_writer.writerow([product.id, video_url, "fail"])
            if log_fp:
                log_fp.close()
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 effect_url 页面中下载 >200KB 的视频文件")
    parser.add_argument("--output-dir", default=None, help="下载目录（默认：backend/files/effect_videos）")
    parser.add_argument("--log-file", default=None, help="下载日志路径（默认：<output-dir>/effect_videos.csv）")
    parser.add_argument("--min-size-mb", type=float, default=0.2, help="最小视频大小（MB，默认 0.2=200KB）")
    parser.add_argument("--limit", type=int, default=0, help="最多处理多少个商品（0=不限）")
    parser.add_argument("--max-per-product", type=int, default=2, help="每个商品最多下载几个视频")
    parser.add_argument("--timeout", type=float, default=15.0, help="网络超时秒数")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不下载")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parent.parent / "files" / "effect_videos"
    log_file = Path(args.log_file) if args.log_file else output_dir / "effect_videos.csv"
    asyncio.run(
        run(
            output_dir=output_dir,
            log_file=log_file,
            min_size_mb=args.min_size_mb,
            limit=args.limit,
            max_per_product=args.max_per_product,
            timeout=args.timeout,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
