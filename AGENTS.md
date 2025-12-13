# Repository Guidelines

## Project Structure & Module Organization
- `docs/plan.md`: business and system blueprint; keep updated before coding pivots.
- `yh-project-uniapp/`: UniApp front end targeting WeChat Mini Program; entry `App.vue`, runtime setup `main.js`, routing and window config `pages.json`, shared styles `uni.scss`, static assets in `static/`.
- `backend/`: placeholder for the FastAPI service planned in `docs/plan.md`; keep backend code here with its own `uv`/Docker setup when added.

## Build, Test, and Development Commands
- UniApp (front end): open `yh-project-uniapp/` in HBuilderX; use “Run” → “WeChat Mini Program” for live preview. If you prefer CLI, add a `package.json` and use `npm install` followed by `npm run dev:mp-weixin` (uni-app CLI) for local dev, `npm run build:mp-weixin` for release.
- Backend (future): follow `docs/plan.md`—use `uv run fastapi dev` (or `uvicorn main:app --reload`) once the service exists; `docker compose up --build` to run db/backend/nginx stack when compose files are added.

## Coding Style & Naming Conventions
- Vue/UniApp: 2-space indentation; single quotes in JS; keep lifecycle hooks minimal and prefer composition functions for shared logic. Page paths live under `pages/feature/screen`.
- Styles: scope per page where possible; prefer variables in `uni.scss`; keep color and spacing tokens centralized.
- Files: kebab-case for Vue page folders and files (`pages/inventory/list.vue`), snake_case for backend modules, PascalCase for Python classes and Vue components.

## Testing Guidelines
- Front end: add page-level tests with your chosen runner (e.g., vitest) before merging behavior-heavy changes; snapshot UI for navigation flows. Mock API calls so tests do not require backend.
- Backend (future): use pytest with coverage; aim for critical-path coverage (pricing logic, sales snapshotting) and encode the 3-level pricing rules as parameterized tests. Name tests `test_<module>.py` and functions `test_<behavior>`.

## Commit & Pull Request Guidelines
- History is sparse; follow a Conventional Commit style (`feat:`, `fix:`, `chore:`) in present tense with a short scope (`feat: add inventory list page`). Keep PR titles aligned to the main commit.
- PRs: include purpose, key screenshots for UI-facing changes, test evidence (commands + results), and linked issue/plan reference (e.g., section in `docs/plan.md`). Keep diffs scoped; split backend vs front-end changes when practical.

## Security & Configuration Tips
- Keep secrets out of the repo; use environment variables for `DATABASE_URL` and any WeChat credentials. For local SSL, follow the nginx layout in `docs/plan.md` (`nginx/conf.d`, `nginx/ssl` for certs).
- When touching pricing or sales logic, document assumptions in `docs/plan.md` and mirror validation on both client and server once the backend lands.
