"""
导出“问题”品类的商品到 CSV，包含：
- 名称
- 规格
- 库存数量（按：箱数 * 规格 + 散数 计算，聚合所有仓库）
- 单价（按后端同口径：例外价/分类系数/全局系数）
- image 链接（product.img_url）

默认导出到 /var/log/ 目录下，文件名形如：problem_products_20250101_120000.csv

运行：
  cd backend
  set -a; source .env; set +a
  uv run python utils/export_problem_products.py

可选参数：
  --category-name  指定品类名（默认：问题）
  --output-dir     指定导出目录（默认：/var/log）
  --output         指定导出完整路径（优先生效）
"""

import argparse
import asyncio
import csv
import socket
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.exc import OperationalError

from app.models.entities import Category, Inventory, Product, ProductCategory, SystemConfig


DEFAULT_CATEGORY_NAME = "问题"
DEFAULT_OUTPUT_DIR = Path("/var/log")
DEFAULT_FILE_PREFIX = "problem_products"
NUM_RE = re.compile(r"(\d+(?:\.\d+)?)")
DEFAULT_GLOBAL_MULTIPLIER = 1.5


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
    # 支持 backend/.env 与根目录 .env
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

    # 兼容仅提供 POSTGRES_* 的场景（与 app/db.py 同口径）
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


def normalize_spec(spec: str | None) -> Optional[str]:
    if not spec:
        return None
    match = NUM_RE.search(str(spec))
    if match:
        return match.group(1)
    return None


def parse_spec_qty(spec: str | None) -> float:
    clean = normalize_spec(spec)
    if not clean:
        return 1.0
    try:
        val = float(clean)
        return val if val > 0 else 1.0
    except Exception:
        return 1.0


def round2(val: float) -> float:
    return float(f"{val:.2f}")


def format_number(val: float) -> str:
    if abs(val - int(val)) < 1e-9:
        return str(int(val))
    return str(val)


async def get_global_multiplier(session: AsyncSession) -> float:
    stmt = sa.select(SystemConfig).where(SystemConfig.key == "global_multiplier")
    cfg = (await session.execute(stmt)).scalars().first()
    if not cfg:
        return DEFAULT_GLOBAL_MULTIPLIER
    try:
        return float(cfg.value)
    except (TypeError, ValueError):
        return DEFAULT_GLOBAL_MULTIPLIER


def describe_database_url(db_url: str) -> str:
    try:
        parsed = urlparse(db_url)
        host = parsed.hostname or ""
        port = parsed.port or ""
        db_name = (parsed.path or "").lstrip("/")
        return f"{host}:{port}/{db_name}" if host else db_url
    except Exception:
        return db_url


def _print_db_help(db_url: str, exc: Exception) -> bool:
    root: Exception = exc
    if isinstance(exc, OperationalError) and getattr(exc, "orig", None):
        root = exc.orig  # type: ignore[assignment]

    if isinstance(root, socket.gaierror):
        print("数据库连接失败：无法解析主机名。")
        print(f"- 当前连接串：{describe_database_url(db_url)}")
        print("- 常见原因：DATABASE_URL 里 host 写成了 docker compose 的服务名（例如 postgres）。")
        print("- 解决方案：")
        print("  1) 如果你在宿主机/独立容器运行脚本：把 host 改成实际 IP 或 127.0.0.1（并确保端口可达）。")
        print("  2) 如果你用 docker compose 部署：在 compose 的 backend 容器里运行脚本，例如：")
        print("     docker compose exec backend uv run python utils/export_problem_products.py")
        return True

    if isinstance(root, ConnectionRefusedError):
        print("数据库连接失败：连接被拒绝（Connection refused）。")
        print(f"- 当前连接串：{describe_database_url(db_url)}")
        print("- 请检查数据库是否启动、端口是否映射/放通、连接串 host/port 是否正确。")
        return True

    return False


async def export_problem_products_csv(
    category_name: str,
    output_path: Path,
    encoding: str = "utf-8-sig",
    db_url_override: str | None = None,
) -> int:
    db_url = db_url_override or get_database_url()
    if not db_url:
        raise RuntimeError("缺少 DATABASE_URL，请在环境变量或 .env 中配置后重试。")

    engine = create_async_engine(db_url, echo=False, future=True)
    try:
        async with AsyncSession(engine) as session:
            category = (
                (await session.execute(sa.select(Category).where(Category.name == category_name))).scalars().first()
            )
            if not category:
                products: list[Product] = []
            else:
                cat_id = category.id
                subq = sa.select(ProductCategory.product_id).where(ProductCategory.category_id == cat_id)
                stmt = (
                    sa.select(Product)
                    .where(sa.or_(Product.category_id == cat_id, Product.id.in_(subq)))
                    .order_by(Product.name)
                )
                products = (await session.execute(stmt)).scalars().all()

            product_ids = [p.id for p in products]
            inventory_map: dict[str, tuple[int, int]] = {}
            product_to_category_ids: dict[str, list[str]] = {}
            category_map: dict[str, Category] = {}
            global_multiplier = await get_global_multiplier(session)

            if product_ids:
                inv_stmt = (
                    sa.select(Inventory.product_id, sa.func.sum(Inventory.current_stock), sa.func.sum(Inventory.loose_units))
                    .where(Inventory.product_id.in_(product_ids))
                    .group_by(Inventory.product_id)
                )
                pc_stmt = sa.select(ProductCategory.product_id, ProductCategory.category_id).where(
                    ProductCategory.product_id.in_(product_ids)
                )
                inv_rows, pc_rows = await asyncio.gather(session.execute(inv_stmt), session.execute(pc_stmt))

                for pid, box_qty, loose_qty in inv_rows.all():
                    inventory_map[pid] = (int(box_qty or 0), int(loose_qty or 0))

                for pid, cid in pc_rows.all():
                    product_to_category_ids.setdefault(pid, []).append(cid)

                category_ids_needed = set()
                for p in products:
                    if p.category_id:
                        category_ids_needed.add(p.category_id)
                    for cid in product_to_category_ids.get(p.id, []):
                        category_ids_needed.add(cid)
                if category_ids_needed:
                    cats = (
                        (await session.execute(sa.select(Category).where(Category.id.in_(category_ids_needed))))
                        .scalars()
                        .all()
                    )
                    category_map = {c.id: c for c in cats}

        output_path.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with output_path.open("w", newline="", encoding=encoding) as f:
            writer = csv.writer(f)
            writer.writerow(["名称", "规格", "库存数量", "单价", "image链接"])
            for p in products:
                box_qty, loose_qty = inventory_map.get(p.id, (0, 0))
                spec_qty = parse_spec_qty(p.spec)
                spec_clean = normalize_spec(p.spec) or (str(p.spec).strip() if p.spec else "")
                total_units = box_qty * spec_qty + (loose_qty or 0)

                if p.fixed_retail_price is not None and p.fixed_retail_price > 0:
                    unit_price = p.fixed_retail_price
                elif p.retail_multiplier:
                    unit_price = round2(p.base_cost_price * p.retail_multiplier)
                else:
                    multipliers: list[float] = []
                    if p.category_id:
                        cat = category_map.get(p.category_id)
                        if cat and cat.retail_multiplier:
                            multipliers.append(cat.retail_multiplier)
                    for cid in product_to_category_ids.get(p.id, []):
                        cat = category_map.get(cid)
                        if cat and cat.retail_multiplier:
                            multipliers.append(cat.retail_multiplier)
                    if multipliers:
                        unit_price = round2(p.base_cost_price * max(multipliers))
                    else:
                        unit_price = round2(p.base_cost_price * global_multiplier)

                writer.writerow(
                    [p.name, spec_clean, format_number(total_units), f"{unit_price:.2f}", (p.img_url or "").strip()]
                )
                written += 1
        return written
    finally:
        await engine.dispose()


def build_output_path(output: str | None, output_dir: str, category_name: str) -> Path:
    if output:
        return Path(output)
    safe_name = (category_name or DEFAULT_CATEGORY_NAME).strip() or DEFAULT_CATEGORY_NAME
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(output_dir) / f"{DEFAULT_FILE_PREFIX}_{safe_name}_{timestamp}.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出“问题”品类商品 CSV")
    parser.add_argument("--category-name", default=DEFAULT_CATEGORY_NAME, help="品类名（默认：问题）")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="导出目录（默认：/var/log）")
    parser.add_argument("--output", default=None, help="导出完整路径（优先于 --output-dir）")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV 编码（默认：utf-8-sig，Excel 兼容）")
    parser.add_argument("--db-url", default=None, help="直接指定 DATABASE_URL（优先于 .env/环境变量）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = build_output_path(args.output, args.output_dir, args.category_name)
    db_url = args.db_url or get_database_url()
    try:
        written = asyncio.run(
            export_problem_products_csv(
                args.category_name,
                output_path,
                encoding=args.encoding,
                db_url_override=args.db_url,
            )
        )
    except PermissionError:
        print(f"无权限写入：{output_path}（可尝试 sudo，或用 --output-dir 指向可写目录）")
        raise
    except OperationalError as exc:
        if db_url and _print_db_help(db_url, exc):
            return
        raise
    except OSError as exc:
        if db_url and _print_db_help(db_url, exc):
            return
        raise
    print(f"已导出 {written} 条到 {output_path}")


if __name__ == "__main__":
    main()
