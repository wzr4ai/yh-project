# Backend Services

## Overview
- Business logic layer. Routes should call into here.

## Where To Look
- Facade (preferred import surface): `backend/app/services/logic.py`
- Pricing rules: `backend/app/services/logic_pricing.py` (fixed > category > global)
- Inventory math + conversions: `backend/app/services/logic_inventory.py`, `backend/app/services/logic_utils.py`
- Catalog/category projections: `backend/app/services/logic_catalog.py`
- Sales + snapshots: `backend/app/services/logic_sales.py` (snapshot cost + standard price at sale time)
- Purchases/receiving: `backend/app/services/logic_purchases.py`
- Dashboard aggregations: `backend/app/services/logic_dashboard.py`
- Auth + JWT + WeChat: `backend/app/services/auth.py`
- Media storage: `backend/app/services/minio_service.py`

## Conventions
- Centralize cross-cutting helpers in `logic_utils.py` (rounding, spec parsing, unit conversion).
- Keep DTO shape decisions aligned with `backend/app/models/schemas.py`.

## Anti-Patterns
- Never let a later price/cost edit rewrite historical sales reporting; use snapshot fields.
- Avoid hiding authorization mistakes by returning partial success; fail explicitly.
