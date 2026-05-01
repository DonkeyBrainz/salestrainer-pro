# Frontend: Luxe Sales Coach v2

React TypeScript frontend for the E.A.S.Y. Selling System training platform.

## Getting Started

### Prerequisites
- Node.js 18+
- Backend running on `http://localhost:8000`

### Setup

```bash
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`. Vite proxies API calls to the backend.

## Architecture

```
Frontend (React 19 + TypeScript)
|
├── Pages (Router-based views)
|   ├── HomePage - Mode selection and navigation
|   ├── SessionPage - Voice training/evaluation wrapper
|   └── LoginPage - Google OAuth entry point
|
├── Components (Reusable UI)
|   ├── VoiceSession - Main session container
|   ├── CoachHUD - Real-time coaching hints display
|   ├── EASYChecklist - E.A.S.Y. methodology tracker
|   ├── ControlBar - Play/stop/settings controls
|   ├── Visualizer - Audio waveform display
|   ├── Transcript - Session transcript viewer
|   ├── PersonaSelector - AI persona picker
|   ├── UserMenu - Auth and settings
|   └── AmbientBackground - Visual ambiance
|
├── Hooks (Stateful logic)
|   ├── useWebSocket - WebSocket connection and messaging
|   ├── useAudio - Audio capture (16kHz) and playback (24kHz)
|   └── useAuthContext - Authentication state
|
├── Services (External integrations)
|   ├── websocketService - WebSocket singleton with reconnection
|   ├── authService - Google OAuth and session management
|   └── API client (via Vite proxy)
|
├── Contexts (Global state)
|   └── AuthContext - User auth and session state
|
└── Types (TypeScript definitions)
    ├── auth.ts - Auth types
    └── index.ts - Shared types

Data Flow:
  User Input -> Component -> Hook -> Service -> Backend WebSocket/API
  Backend Response -> Service -> Hook -> Component -> UI Update
```

## Key Features

- **Real-time Voice Sessions**: WebSocket connection for bidirectional communication with Gemini Live API
- **CoachHUD**: Displays real-time coaching hints during conversations
- **E.A.S.Y. Checklist**: Interactive checklist for the E.A.S.Y. selling methodology
- **Audio Pipeline**: 16kHz capture, 24kHz playback with PCM codec
- **OAuth Authentication**: Google Sign-In with JWT token management
- **Responsive Design**: Mobile-friendly UI with Lucide icons

## Development

### Commands

```bash
npm run dev          # Start dev server (port 3000)
npm run build        # Production build
npm run preview      # Preview production build
npm run typecheck    # Type checking
npm run test         # Run tests in watch mode
npm run test:run     # Run tests once
npm run test:coverage # Generate coverage report
```

### Project Structure

```
frontend/
├── src/
|   ├── components/     # Reusable UI components
|   ├── pages/          # Route-based pages
|   ├── hooks/          # Custom React hooks
|   ├── services/       # Business logic and API clients
|   ├── contexts/       # React context providers
|   ├── types/          # TypeScript definitions
|   ├── data/           # Static data (E.A.S.Y. content)
|   ├── test/           # Test setup and mocks
|   ├── App.tsx         # Main router
|   └── main.tsx        # Entry point
├── package.json        # Dependencies and scripts
├── tsconfig.json       # TypeScript config
├── vite.config.ts      # Build config and proxy rules
└── vitest.config.ts    # Test runner config
```

## Backend Integration

The frontend communicates with the backend via:

1. **REST API**: `/api/*` endpoints for CRUD operations
2. **WebSocket**: `/ws` for real-time voice sessions
3. **OAuth**: `/auth/callback` for login flow
4. **Health Check**: `/health` for monitoring

Vite proxy routes all backend calls automatically in development.

## Testing

Unit tests use Vitest with React Testing Library. MSW mocks HTTP requests.

```bash
npm run test         # Watch mode
npm run test:run     # Single run
npm run test:coverage # With coverage
```

Test files are co-located with source (e.g., `useWebSocket.test.ts` next to `useWebSocket.ts`).

## Deployment

Build for production:

```bash
npm run build
```

Output goes to `dist/`. Deploy as a static SPA with proper routing fallback to `index.html`.

Environment variables via `.env.local`:
- `VITE_API_BASE_URL` - Backend URL (default: proxied locally)
