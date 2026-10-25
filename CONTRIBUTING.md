# Contributing to Epoxa

Welcome to the Epoxa engineering team! Please review these guidelines before contributing code.

---

## 1. Architectural Rules (Non-Negotiable)

1. **Strict Layering**: `Routes (FastAPI) -> Services (Business Logic) -> Repositories (SQL Only) -> Models`.
   - Routes never touch ORM queries directly.
   - Repositories never execute business rules or transactions.
2. **Dependency Direction**: `apps/api` and `apps/agent` import from `packages/core`. `packages/core` never imports from apps. `apps/api` and `apps/agent` never import each other.
3. **No `sys.path` Hacks**: Packages are installable workspace packages with proper `src/` layout.
4. **Voice Invariants**: Any change affecting voice pipeline timing parameters, WebRTC audio track isolation, or non-blocking room SID retrieval requires explicit documented justification and regression testing.

---

## 2. Development Setup

### Prerequisites
- Python 3.12+
- `uv` (Fast Python package manager)
- Node.js 20+ & `pnpm` (via `corepack enable pnpm`)
- Docker & Docker Compose

### Commands
```bash
# Start local infrastructure (Postgres + pgvector)
make dev-db

# Run Alembic migrations
make migrate

# Seed initial data (Epoxcel org, admin, FAQ embeddings)
make seed

# Run linters and formatters
make lint

# Run automated tests
make test
```

---

## 3. Commit Discipline

- Use **Conventional Commits**:
  - `feat: add SSE live transcript stream`
  - `fix: resolve non-blocking room sid background task`
  - `refactor: extract ui tokens to shared package`
  - `test: add escalation regex regression test`
- Never commit secrets, `.env` files, or production credentials.
