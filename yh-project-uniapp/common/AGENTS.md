# UniApp Common Modules

## Overview
- Shared client-side utilities: auth, API calls, caching, pricing, unit conversion.

## Where To Look
- API base + Bearer headers + 401 relaunch: `yh-project-uniapp/common/api.js`
- ETag-based list caching: `yh-project-uniapp/common/api.js` (`cachedRequest`)
- Token storage + role parsing: `yh-project-uniapp/common/auth.js`
- Pricing helpers: `yh-project-uniapp/common/pricing.js`
- Unit conversion: `yh-project-uniapp/common/stock.js`

## Conventions
- Storage keys: `yh-token`, `yh-role`, `yh-username` (cleared on 401).
- Cache keys are `cache:<path-with-query>`.

## Anti-Patterns
- Do not swallow auth errors; 401 must clear local session and re-launch login.
- Do not introduce new storage keys without documenting them.
