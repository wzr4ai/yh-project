# Backend Routes

## Overview
- One module per domain; all mounted under `/api` by `backend/app/api/routes/__init__.py`.

## Where To Look
- Route aggregation/prefix: `backend/app/api/routes/__init__.py`
- Auth + identity: `backend/app/api/routes/auth.py` (`/api/auth/weapp`, `/api/me`)
- Catalog: `backend/app/api/routes/products.py`, `backend/app/api/routes/categories.py`
- Pricing: `backend/app/api/routes/pricing.py`, `backend/app/api/routes/system.py`
- Inventory: `backend/app/api/routes/inventory.py`
- Purchases: `backend/app/api/routes/purchases.py`
- Sales/orders: `backend/app/api/routes/sales.py`, `backend/app/api/routes/orders.py`
- Media/presign: `backend/app/api/routes/media.py`
- Dashboard: `backend/app/api/routes/dashboard.py`

## Conventions
- Keep HTTP concerns here (query parsing, status codes); defer calculations/DB write flows to `backend/app/services/`.
- Most endpoints use `session: AsyncSession = Depends(get_session)`.

## Anti-Patterns
- Avoid duplicating pricing/unit logic in route handlers; call service helpers.
- Do not add role-based field pruning in the frontend only; enforce on API responses.
