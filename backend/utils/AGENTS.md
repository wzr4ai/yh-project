# Backend Utils

## Overview
- One-off scripts for migrations, imports/exports, backups, and LLM/media tooling.

## Where To Look
- Lightweight schema alignment: `backend/utils/schema_migrate.py`
- DB backup/restore: `backend/utils/db_backup_restore.py`
- DB connectivity smoke test: `backend/utils/test_db.py`
- Product imports/normalization: `backend/utils/import_csv_to_products.py`, `backend/utils/normalize_spec.py`
- Effect video pipeline: `backend/utils/download_effect_videos.py`, `backend/utils/import_effect_videos_to_product.py`

## Conventions
- Prefer `uv run python utils/<script>.py` (run from `backend/`).
- If DB runs in docker and `DATABASE_URL` uses `postgres` hostname, run scripts via `docker compose exec backend ...`.

## Anti-Patterns
- Before running a migration/import script, check for `--dry-run` and use it first.
- Do not commit artifacts written to `backend/files/`.

## Commands
```bash
cd backend
set -a; source .env; set +a
uv run python utils/test_db.py

# inside compose
docker compose exec backend uv run python utils/schema_migrate.py
```
