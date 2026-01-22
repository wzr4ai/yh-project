# UniApp Frontend

## Overview
- UniApp (Vue) targeting WeChat Mini Program; HBuilderX-style project (no `package.json`).

## Structure
```
yh-project-uniapp/
├── App.vue            # global guards (role/token)
├── main.js            # app bootstrap
├── pages.json         # routes + globalStyle
├── manifest.json      # app config (mp-weixin, appid, etc.)
├── uni.scss           # shared style tokens
├── common/            # api/auth/pricing/stock utilities
└── pages/             # feature pages
```

## Where To Look
- Route list + titles: `yh-project-uniapp/pages.json`
- Global auth/role guard: `yh-project-uniapp/App.vue`
- API requests + ETag caching: `yh-project-uniapp/common/api.js`
- Token/role helpers: `yh-project-uniapp/common/auth.js`
- Unit conversion helpers: `yh-project-uniapp/common/stock.js`
- Pricing helpers: `yh-project-uniapp/common/pricing.js`

## Conventions
- Page folders are feature-scoped under `yh-project-uniapp/pages/<feature>/`.
- Local config: create `yh-project-uniapp/common/config.js` from `yh-project-uniapp/common/config.js.example`.

## Anti-Patterns
- Clerk UX restrictions are not enough; backend must enforce field pruning.
- Avoid duplicating inventory unit conversion rules across pages; reuse `common/stock.js`.
