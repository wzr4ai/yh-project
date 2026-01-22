# Project Knowledge Base

Generated: 2026-01-22
Branch: dev
Commit: 75fcd8e

## Overview
- Stack: UniApp (Vue, WeChat Mini Program) + FastAPI (async SQLAlchemy, Postgres) in a single repo.
- Core domain: retail inventory/pricing/sales for fireworks shop; roles: owner vs clerk vs user (clerk cannot see cost/profit).

## Structure
```
./
├── docs/                 # business rules + schema + caching plan
├── yh-project-uniapp/    # UniApp mini program (HBuilderX-style)
└── backend/              # FastAPI service + Docker/uv + maintenance scripts
```

## Where To Look
| Task | Location | Notes |
|------|----------|------|
| Pricing rules (3-level) | docs/plan.md | fixed > category multiplier > global multiplier |
| ETag caching strategy | docs/data-caching-plan.md | list endpoints + If-None-Match/304 |
| Unit conversion (box/unit/piece) | docs/update_plan.md, yh-project-uniapp/common/stock.js | inventory stores smallest-unit count |
| Frontend auth/guard | yh-project-uniapp/App.vue | route guard via `uni.addInterceptor` |
| Frontend API wrapper + caching | yh-project-uniapp/common/api.js | Bearer header + ETag cache store |
| Backend entry + middleware | backend/app/main.py | FastAPI app + lifespan init |
| Backend routes | backend/app/api/routes/ | one module per domain |
| Backend business logic | backend/app/services/ | `logic_*.py` modules + facade |
| Backend schema/models | backend/app/models/ | `entities.py` (ORM) + `schemas.py` (Pydantic) |
| Ops scripts | backend/utils/ | imports/exports/migrations/backups; prefer `--dry-run` |

## Conventions
- Vue/UniApp: 2-space indentation; prefer single quotes in JS; keep `App.vue` lifecycle hooks minimal.
- Files: UniApp pages in `yh-project-uniapp/pages/<feature>/<screen>.vue`; Python modules snake_case; components/classes PascalCase.
- Data artifacts: `backend/files/` is runtime data (videos, CSV, db backups); do not treat as source.

## Anti-Patterns (This Repo)
- RBAC: never return cost/profit/purchase amounts to `clerk` role (API must enforce field pruning).
- Sales correctness: on sale, always snapshot cost + standard price into sales items; later price edits must not affect historical reports.
- Secrets: do not commit `.env` or credentials; `yh-project-uniapp/common/config.js` is local-only.
- Repo bloat: do not add anything under `backend/files/` (git-ignored); avoid relying on `backend/.venv/` in automation.

## Commands
```bash
# backend (local)
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# backend (docker)
cp .env.example .env
docker compose up --build

# schema alignment (lightweight)
cd backend
set -a; source .env; set +a
uv run python backend/utils/schema_migrate.py
```

## Notes / Gotchas
- `backend/pyproject.toml` pins `requires-python = ">=3.14"` but `backend/README.md` says 3.11+; align before standardizing tooling.
- `backend/Dockerfile` assumes Tencent Cloud mirrors; building elsewhere may require switching mirrors.
- Root `.gitignore` ignores `docker-compose.yml`; this repo currently has it committed anyway (treat as environment-specific).
