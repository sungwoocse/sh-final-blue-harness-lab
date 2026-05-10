# Frontend

SoftBank Hackathon FaaS 플랫폼의 React 기반 운영 콘솔입니다. 워크스페이스/함수를 생성하고, Builder Service와 연동해 Spin 애플리케이션을 빌드·배포하며, Loki/Prometheus로 관측 데이터를 노출하는 UI를 제공합니다.

## Stack & Tooling

| Layer | Selection |
|-------|-----------|
| Framework | React 18 + TypeScript + Vite |
| State/Data | Custom `AppContext` + TanStack Query + React Router 6 |
| UI | shadcn/ui (Radix), Tailwind CSS, Lucide icons |
| Editors/Charts | Monaco Editor, Recharts |
| Observability UX | Sonner toasts, custom metrics/log tables |
| i18n | i18next (ko default, en/ja bundles) |

Dev tooling: SWC React plugin, ESLint 9 + typescript-eslint 8, PostCSS/Autoprefixer, Tailwind Typography.

## Features

- Workspace lifecycle: landing page lists live workspaces from the FastAPI backend, supports creation and navigation.
- Function lifecycle: create, update, enable/disable, delete functions with Monaco-based editor and HTTP method toggles. Payloads are Base64 encoded before hitting the backend.
- Build/deploy automation: Function Detail page can trigger `/api/v1/build-and-push` + `/api/v1/deploy`, poll task states, and surface builder errors. Newly created functions auto-deploy when status is `building`.
- Invocation & testing: inline JSON request editor executes `/api/workspaces/{id}/functions/{fn}/invoke`, then streams logs/metrics into UI metrics cards and tables.
- Observability: real-time Loki log tab, Prometheus CPU chart (instant + range query) with derived stats (avg/peak).
- Localization-ready UI copy via `src/lib/i18n.ts`, currently shipping Korean/English/Japanese dictionaries.
- Responsive layout system built on shadcn components and custom `AppLayout`/`WorkspaceSidebar`.

## Application Flow

```
Frontend (React Router)
	│
	├─ Landing → list/create workspaces via AppContext → GET/POST /api/workspaces
	├─ WorkspaceDashboard → aggregate metrics/logs already cached in context
	├─ FunctionsList → query + filter functions per workspace
	├─ NewFunction → Base64 encode code → POST /api/workspaces/{ws}/functions
	└─ FunctionDetail
			 ├─ Invoke tab → POST /api/.../invoke
			 ├─ Build & Deploy → POST /api/v1/build-and-push → poll tasks → POST /api/v1/deploy
			 ├─ Logs tab → GET /api/.../logs + GET /api/functions/{fn}/loki-logs
			 └─ Metrics tab → GET /api/functions/{fn}/metrics
```

Data fetching is centralized in `AppContext`. Workspaces/functions/logs are stored in local state, while builder/observability calls are performed on demand. React Query is configured globally for future caching (currently delegated to context for finer control).

## Environment Setup

Requirements
- Node.js 22.x (matching CI toolchain)
- npm 11.x

Install deps
```bash
cd frontend
npm install
```

Environment variables (create `frontend/.env` or export)
```
VITE_API_URL=https://api.eunha.icu   # or http://localhost:8000 when running backend locally
```
If omitted, the app falls back to `window.location.origin` (useful when frontend is reverse-proxied behind the same domain as the backend).

Scripts
```bash
npm run dev         # Vite dev server (defaults to http://localhost:5173)
npm run build       # Production build + type checking
npm run build:dev   # Development-mode bundle (keeps source maps, faster)
npm run preview     # Preview build output on a local server
npm run lint        # ESLint (flat config) across TS/TSX
```

## Routing Surface

| Route | Screen | Notes |
|-------|--------|-------|
| `/` | Landing | Lists workspaces, create dialog, workspace metrics cards |
| `/workspaces/:workspaceId` | WorkspaceDashboard | Summary metrics, recent invocation table |
| `/workspaces/:workspaceId/functions` | FunctionsList | Search/filter, status toggle, delete |
| `/workspaces/:workspaceId/functions/new` | NewFunction | Config forms + Monaco editor |
| `/workspaces/:workspaceId/functions/:functionId` | FunctionDetail | Tabs for overview/test/logs/realtime/metrics/code; deploy button |
| `/workspaces/:workspaceId/settings` | WorkspaceSettings (skeleton) |
| `*` | NotFound |

## Source Layout

```
src/
├─ App.tsx               # Providers (React Query, i18n, Router)
├─ main.tsx              # Mount + i18n bootstrap + title helper
├─ components/
│   ├─ AppLayout.tsx     # Shell + top nav + workspace selector
│   ├─ WorkspaceSidebar.tsx
│   ├─ CodeEditor.tsx    # Monaco wrapper with sensible defaults
│   ├─ MetricsCard.tsx
│   ├─ EmptyState.tsx, AppFooter.tsx, etc.
│   └─ ui/               # shadcn-generated primitives
├─ contexts/AppContext.tsx
│   ├─ Holds workspaces/functions/logs state
│   ├─ Encodes/decodes Base64 function code
│   └─ Wraps lib/api calls + exposes helpers (invoke, deploy, metrics, Loki)
├─ lib/
│   ├─ api.ts            # REST client, builder/deploy helpers, error class
│   ├─ i18n.ts           # i18next bootstrap (ko/en/ja)
│   └─ utils.ts          # date helpers, formatting
├─ pages/                # Route-level screens listed above
├─ hooks/                # Responsive helpers (e.g., use-mobile)
└─ locales/              # JSON dictionaries
```

## API Integration Details

- Base URL is `import.meta.env.VITE_API_URL` (defaults to `http://localhost:8000`).
- Every request is routed through `lib/api.ts`. Errors throw `ApiError` with HTTP status and parsed backend payload.
- Function code is Base64 encoded before POST/PATCH and decoded back for editing.
- Build/deploy flow uses multipart form uploads (`/api/v1/build-and-push`) and polls `/api/v1/tasks/{taskId}` until `completed/done`. On success the UI immediately calls `/api/v1/deploy` with `function_id` and surfaces endpoints to the user.
- Observability tabs hit `/api/functions/{functionId}/loki-logs` and `/api/functions/{functionId}/metrics`. Errors show inline fallback text so the UI remains usable even if Loki/Prometheus is down.

## Localization & Theming

- `src/lib/i18n.ts` registers Korean (default), English, Japanese resource bundles; translations live under `src/locales/`.
- `setAppTitle.ts` updates the document title based on the current workspace or page context.
- `next-themes` is prepared for future dark/light theme toggles (currently static light theme with Tailwind tokens).

## Development Notes

- The frontend assumes the backend from `../backend` repo is reachable; see backend README for how to start FastAPI locally via Docker Compose.
- Monaco Editor requires `--host 0.0.0.0` when running inside containers (Vite already handles this if you pass `npm run dev -- --host`).
- When testing build/deploy locally, ensure the backend Builder Service proxy (api → builder) has network access; otherwise the deploy tab will show toast errors surfaced from `ApiError`.
- React Query is available for future data synchronization but the current implementation keeps caching logic inside `AppContext`; be cautious when introducing new hooks to avoid double fetching.

## Future Enhancements

- Hook `WorkspaceSettings` to backend PATCH/DELETE endpoints.
- Add automated tests (Cypress or React Testing Library) covering builder and observability flows.
- Expose historical metrics (Prometheus range selects) and log search filters (Loki query builder).

---
Last updated: 2025-12-07
