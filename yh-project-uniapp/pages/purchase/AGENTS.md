# Purchase Pages

## Overview
- Procurement flows: purchase order list/edit/receive; heavy unit conversion and cost handling.

## Where To Look
- Purchase list: `yh-project-uniapp/pages/purchase/list.vue`
- Purchase edit (large): `yh-project-uniapp/pages/purchase/edit.vue`
- Purchase receive (large): `yh-project-uniapp/pages/purchase/receive.vue`
- Replenishment export: `yh-project-uniapp/pages/purchase/replenishment.vue`

## Conventions
- Receipt/stock math should align with docs in `docs/update_plan.md` (box/unit/piece).

## Anti-Patterns
- Avoid inventing new conversion rules per page; use shared helpers.
- Do not expose cost/profit UI to clerk role.
