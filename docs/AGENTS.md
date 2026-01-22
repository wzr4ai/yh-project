# Docs

## Overview
- Business rules and system design. Treat as source of truth when changing core logic.

## Where To Look
- System blueprint + RBAC + pricing + deployment: `docs/plan.md`
- Caching plan (ETag/If-None-Match/optimistic concurrency): `docs/data-caching-plan.md`
- DB table glossary: `docs/db-tables.md`
- Unit/stock model (box/unit/piece) + barcode levels: `docs/update_plan.md`

## Conventions
- Update docs when changing pricing, inventory math, role visibility, or deployment assumptions.

## Anti-Patterns
- Avoid implementing pricing/inventory changes without reflecting the rule changes here.
