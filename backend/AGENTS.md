# Backend (FastAPI)

## Overview
- FastAPI app under `backend/app/`; async SQLAlchemy + Postgres; uv-managed dependencies.

## Structure
```
backend/
├── app/                 # FastAPI code (routes/services/models)
├── utils/               # one-off scripts (migrations/import/export/backups)
├── Dockerfile           # container build (Tencent mirror defaults)
├── pyproject.toml       # uv project
└── uv.lock              # locked deps
```

## Where To Look
- App entry/middleware/lifespan: `backend/app/main.py`
- DB session + auth deps: `backend/app/api/deps.py`
- HTTP routes: `backend/app/api/routes/`
- Business logic: `backend/app/services/` (prefers `logic.py` facade)
- ORM + DTOs: `backend/app/models/entities.py`, `backend/app/models/schemas.py`
- Runtime assets/data: `backend/files/` (git-ignored)

## Conventions
- Routes generally: `router = APIRouter()` + `Depends(get_session)` + `response_model=schemas.*`.
- Prefer putting calculations and DB orchestration in `backend/app/services/*` (routes stay thin).

## Anti-Patterns
- Do not expose cost/profit fields to clerk role; enforce on API layer.
- Do not treat `backend/files/` as source; do not commit artifacts from there.
- Avoid editing data via scripts without a dry-run path; prefer running scripts inside the compose container when DB hostname is `postgres`.

## Commands
```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# inside compose network
docker compose exec backend uv run python utils/test_db.py
```
