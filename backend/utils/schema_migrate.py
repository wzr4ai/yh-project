"""
Lightweight schema migration to align DB with current models.
Creates missing tables from SQLAlchemy metadata and adds known new columns if absent.

Usage:
  uv run python backend/utils/schema_migrate.py

Reads DATABASE_URL from environment (asyncpg URL will be converted to sync driver).
This script is idempotent but limited (only handles a few columns); use a full
migration tool like Alembic for complex changes.
"""

import os
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.engine import create_engine

from app.models.entities import Base


def load_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.strip().startswith("DATABASE_URL"):
                    _, _, val = line.partition("=")
                    url = val.strip().strip('"').strip("'")
                    break
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def ensure_columns(engine: Engine):
    inspector = sa.inspect(engine)
    product_columns = {col["name"] for col in inspector.get_columns("product")}
    category_columns = {col["name"] for col in inspector.get_columns("category")}
    inventory_columns = {col["name"] for col in inspector.get_columns("inventory")}

    with engine.begin() as conn:
        if "retail_multiplier" not in product_columns:
            conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS retail_multiplier double precision"))
        if "pack_price_ref" not in product_columns:
            conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS pack_price_ref double precision"))
        if "effect_url" not in product_columns:
            conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS effect_url varchar(500)"))
        if "updated_at" not in product_columns:
            conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT now()"))
        if "is_custom" not in category_columns:
            conn.execute(text("ALTER TABLE category ADD COLUMN IF NOT EXISTS is_custom boolean DEFAULT false"))
        if "updated_at" not in category_columns:
            conn.execute(text("ALTER TABLE category ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT now()"))
        if "loose_units" not in inventory_columns:
            conn.execute(text("ALTER TABLE inventory ADD COLUMN IF NOT EXISTS loose_units integer DEFAULT 0"))
        if "updated_at" not in inventory_columns:
            conn.execute(text("ALTER TABLE inventory ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT now()"))


def ensure_product_category(engine: Engine):
    inspector = sa.inspect(engine)
    if "product_category" in inspector.get_table_names():
        return
    meta = sa.MetaData()
    sa.Table(
        "product_category",
        meta,
        sa.Column("product_id", sa.String(64), sa.ForeignKey("product.id"), primary_key=True),
        sa.Column("category_id", sa.String(64), sa.ForeignKey("category.id"), primary_key=True),
    )
    meta.create_all(engine)

def ensure_daily_receipt(engine: Engine):
    inspector = sa.inspect(engine)
    if "daily_receipt" in inspector.get_table_names():
        return
    meta = sa.MetaData()
    sa.Table(
        "daily_receipt",
        meta,
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("amount", sa.Float, nullable=False, default=0),
        sa.Column("created_at", sa.DateTime),
    )
    meta.create_all(engine)


def main():
    url = load_database_url()
    engine = create_engine(url, future=True)

    # Create missing tables (won't alter existing columns)
    Base.metadata.create_all(engine)

    # Add known new columns
    ensure_columns(engine)

    # Ensure product_category table exists
    ensure_product_category(engine)
    ensure_daily_receipt(engine)

    print("Schema migration done.")


if __name__ == "__main__":
    main()
