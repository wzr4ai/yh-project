# Checkout Pages

## Overview
- Scanning + checkout flow; state-heavy (multi-order, barcode lookups, pricing/discount logic).

## Where To Look
- Main scanner (large): `yh-project-uniapp/pages/checkout/scan.vue`

## Conventions
- Barcode lookups go through `yh-project-uniapp/common/api.js` (e.g., `/api/products/by-barcode`).

## Anti-Patterns
- Never bypass auth guard by direct `navigateTo`; keep routing consistent with `yh-project-uniapp/App.vue` interceptors.
- Do not let clerk access owner-only modules (even if hidden in UI).
