# ADR 0006: Frontend Toolchain Modernization (Vite + TypeScript + pnpm)

## Status
Accepted

## Context
The prototype frontends used deprecated Create React App (CRA) with untyped JavaScript, fragmented design files, and duplicated API schemas. Build times were slow, and bundle sizes were unoptimized.

## Decision
1. Modernize both frontends (`apps/web` and `apps/dashboard`) using Vite + React 18 + TypeScript (`strict: true`) inside a `pnpm` workspace.
2. Extract design tokens, dark glassmorphism styling, and glowing orb animation keyframes into a shared package `@epoxa/ui-tokens`.
3. Generate strongly-typed API clients and contracts into `@epoxa/api-client` derived directly from FastAPI's OpenAPI schema.
4. Replace client polling loops with Server-Sent Events (SSE) for real-time live calls and transcript streaming.

## Consequences
- Fast sub-second HMR and deterministic builds.
- Zero drift between backend endpoints and frontend data contracts.
- Visual aesthetics preserved with shared design tokens.
