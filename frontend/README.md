# SalesTrainer Pro — Frontend

React 19 + TypeScript + Vite SPA for real-time voice roleplay with AI customer personas, built around the **C.O.R.E. Selling System** (Connect → Observe → Recommend → Execute). Traffic streams over a WebSocket audio relay to the FastAPI backend; the frontend holds no LLM keys.

## Stack

- React 19, React Router 7, TypeScript 5.8
- Vite 6 (dev server + build), Vitest 3 + Testing Library + MSW (tests)
- `lucide-react` icons; in-house **voiceprint** design system (`src/components/voiceprint/`, `src/styles/voiceprint.ts`)

## Commands

```bash
npm install
npm run dev            # Vite dev server on :3000 (proxies to backend on :8000)
npm run build          # tsc typecheck + vite build -> dist/
npm run preview        # serve the production build
npm run typecheck      # tsc --noEmit
npm run test           # vitest watch
npm run test:run       # vitest single run
npm run test:coverage  # coverage report
```

Requires Node 18+ and the backend reachable at `http://localhost:8000`.

## Environment

Copy `.env.example` to `.env` (or `.env.local`). Only one var is read by app code:

- `VITE_API_BASE_URL` — full backend origin for production (e.g. `https://api.example.com`). **Leave empty in dev**: an empty value routes all calls through the Vite proxy against `localhost:8000`.

`GEMINI_API_KEY` in `vite.config.ts` is legacy (direct-Gemini path, superseded by the backend relay) and unused by `src/`.

## Backend integration

Everything targets the backend via `VITE_API_BASE_URL` (empty ⇒ relative, proxied). Proxy rules live in `vite.config.ts` (`/api`, `/auth/*`, `/ws`, `/health`).

- **REST** — `${VITE_API_BASE_URL}/api/v1/*`. Service singletons: `authService`, `personaService`, `productService`, `sessionService`, `statsService`, `orgStatsService`.
- **Voice WebSocket** — `websocketService` connects to `/ws/gemini/live?mode={training|evaluation}`. In prod it rewrites `VITE_API_BASE_URL`'s `http(s)` → `ws(s)`; in dev it derives the URL from `window.location` (Vite proxies the upgrade). Auth is passed as a `token` query param (WS can't set headers), pulled from an injected `setTokenProvider` callback; `persona_id` and product context are appended. Includes exponential-backoff reconnect (5 attempts, 1s→30s).
- **Auth** — Google OAuth. `authService` POSTs `/auth/login` → callback → `/auth/refresh` / `/auth/me` / `/auth/logout`, all with `credentials: 'include'` (cookie-based refresh). `AuthContext` holds session state; `ProtectedRoute` gates authenticated routes. Note the proxy lets **GET** `/auth/callback` fall through to React Router (`AuthCallback` page) while proxying POST to the backend.
- **Audio** — `useAudio`: mic capture at 16 kHz, playback at 24 kHz, raw PCM (`audio/pcm;rate=16000` upstream). `useWebSocket` bridges the audio pipeline to `websocketService`.

## Routes

| Path | Page | Notes |
|------|------|-------|
| `/` | `HomePage` | Mode / persona entry |
| `/training`, `/evaluation` | `SessionPage` | Same page, WS `mode` differs |
| `/history`, `/history/:sessionId` | `HistoryPage` | Past sessions + detail |
| `/admin` | `AdminPage` | Content/admin ops |
| `/team` | `TeamPage` | Team landing |
| `/team/manager` | `ManagerDashboardPage` | Manager analytics |
| `/team/admin` | `AdminDashboardPage` | Org analytics |
| `*` | → `/` | Redirect |

`LoginPage` and `AuthCallback` sit outside the table (unauthenticated / OAuth return).

## Layout

```
src/
├── pages/         # route views (see table)
├── components/    # VoiceSession, ReportCard, PersonaSelector, UserMenu,
│   │              # SessionCard, SessionDetailModal, ProtectedRoute
│   ├── voiceprint/  # design-system primitives (DraftingLoader, SpeakerUnit, MiniPlan)
│   └── dashboard/   # DashboardChrome
├── hooks/         # useAudio, useWebSocket
├── services/      # REST + WS singletons, audioUtils, logger
├── contexts/      # AuthContext
├── styles/        # voiceprint.ts design tokens
├── data/          # CoreSellingSystem.ts (C.O.R.E. methodology content)
├── types/         # shared + auth + stats types
└── main.tsx / App.tsx
```

## Testing

Vitest + React Testing Library, jsdom, MSW for HTTP mocks. Tests are co-located (`*.test.ts[x]`). See `src/test/` for setup.

## Deployment

`npm run build` emits a static SPA to `dist/`. Serve with an `index.html` fallback for client-side routing, and set `VITE_API_BASE_URL` to the backend origin at build time.
