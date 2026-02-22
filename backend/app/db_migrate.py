import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Connection


def ensure_columns(conn: Connection) -> None:
    inspector = sa.inspect(conn)
    if not inspector.has_table("product"):
        return

    product_columns = {col["name"] for col in inspector.get_columns("product")}
    has_category = inspector.has_table("category")
    has_inventory = inspector.has_table("inventory")
    has_purchase_item = inspector.has_table("purchase_item")
    has_misc_cost = inspector.has_table("misc_cost")
    category_columns = {col["name"] for col in inspector.get_columns("category")} if has_category else set()
    inventory_columns = {col["name"] for col in inspector.get_columns("inventory")} if has_inventory else set()
    purchase_item_columns = {col["name"] for col in inspector.get_columns("purchase_item")} if has_purchase_item else set()
    misc_cost_columns = {col["name"] for col in inspector.get_columns("misc_cost")} if has_misc_cost else set()

    if "retail_multiplier" not in product_columns:
        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS retail_multiplier double precision"))
    if "pack_price_ref" not in product_columns:
        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS pack_price_ref double precision"))
    if "effect_url" not in product_columns:
        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS effect_url varchar(500)"))
    if "video_url" not in product_columns:
        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS video_url varchar(500)"))
    if "units_per_box" not in product_columns:
        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS units_per_box integer DEFAULT 1"))
    if "pieces_per_unit" not in product_columns:
        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS pieces_per_unit integer DEFAULT 1"))
    if "box_cost_price" not in product_columns:
        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS box_cost_price double precision DEFAULT 0"))
    if "barcode" not in product_columns:
        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS barcode varchar(200)"))
    if "updated_at" not in product_columns:
        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT now()"))

    if has_category:
        if "is_custom" not in category_columns:
            conn.execute(text("ALTER TABLE category ADD COLUMN IF NOT EXISTS is_custom boolean DEFAULT false"))
        if "retail_multiplier_min" not in category_columns:
            conn.execute(text("ALTER TABLE category ADD COLUMN IF NOT EXISTS retail_multiplier_min double precision"))
        if "retail_multiplier_max" not in category_columns:
            conn.execute(text("ALTER TABLE category ADD COLUMN IF NOT EXISTS retail_multiplier_max double precision"))
        if "updated_at" not in category_columns:
            conn.execute(text("ALTER TABLE category ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT now()"))

    if has_inventory:
        if "loose_units" not in inventory_columns:
            conn.execute(text("ALTER TABLE inventory ADD COLUMN IF NOT EXISTS loose_units integer DEFAULT 0"))
        if "updated_at" not in inventory_columns:
            conn.execute(text("ALTER TABLE inventory ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT now()"))

    if has_purchase_item:
        if "received_units" not in purchase_item_columns:
            conn.execute(text("ALTER TABLE purchase_item ADD COLUMN IF NOT EXISTS received_units integer DEFAULT 0"))
    if has_misc_cost:
        if "cost_payer_type" not in misc_cost_columns:
            conn.execute(
                text(
                    "ALTER TABLE misc_cost ADD COLUMN IF NOT EXISTS cost_payer_type varchar(20) DEFAULT 'public'"
                )
            )
            conn.execute(text("UPDATE misc_cost SET cost_payer_type = 'public' WHERE cost_payer_type IS NULL"))
            conn.execute(text("ALTER TABLE misc_cost ALTER COLUMN cost_payer_type SET NOT NULL"))
        if "cost_payer_shareholder_id" not in misc_cost_columns:
            conn.execute(
                text(
                    "ALTER TABLE misc_cost ADD COLUMN IF NOT EXISTS cost_payer_shareholder_id varchar(64)"
                )
            )
