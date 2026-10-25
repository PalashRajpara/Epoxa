# Epoxa: Production Voice AI Agent Platform

> Enterprise real-time Voice AI agent platform for customer support, automated appointment booking, grievance registration, and supervisor live takeover.

---

## 🚀 Quickstart (Under 10 Minutes)

### Option 1: Docker Compose (Recommended)
Launch the entire system (PostgreSQL with pgvector, FastAPI, Agent worker, Web client, and Supervisor Dashboard) with one command:

```bash
# 1. Clone the repository and configure environment
cp .env.example .env
# Edit .env with your LiveKit, Deepgram, and Groq credentials

# 2. Launch all services
docker compose -f infra/docker/compose.dev.yml up --build
```
- **Customer Web App:** [http://localhost:3000](http://localhost:3000)
- **Supervisor Dashboard:** [http://localhost:3001](http://localhost:3001)
- **FastAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Local Development Workflow

#### Prerequisites
- **Python 3.12+** and [`uv`](https://docs.astral.sh/uv/)
- **Node.js 20+** and `pnpm` (`corepack enable pnpm`)
- **Docker** (for local PostgreSQL with pgvector)

```bash
# 1. Install dependencies
uv sync
pnpm install

# 2. Start PostgreSQL container
docker run -d --name epoxa-postgres -p 5432:5432 \
  -e POSTGRES_DB=epoxa_dev \
  -e POSTGRES_PASSWORD=postgrespassword \
  pgvector/pgvector:pg16

# 3. Run database migrations & seed initial organization
make migrate
make seed

# 4. Start services (each in separate terminal or background)
# Terminal 1: FastAPI API Service
uv run uvicorn epoxa_api.main:app --port 8000 --reload

# Terminal 2: LiveKit Voice Agent Worker
uv run python -m epoxa_agent.main start

# Terminal 3: Customer Web App
pnpm --filter epoxa-web dev

# Terminal 4: Supervisor Console
pnpm --filter epoxa-dashboard dev
```

---

## 📁 Monorepo Layout

```
epoxa/
├── apps/
│   ├── api/                  # FastAPI REST & SSE service (epoxa_api)
│   ├── agent/                # LiveKit voice worker & LangGraph (epoxa_agent)
│   ├── web/                  # Customer voice client (Vite + React 18 + TS)
│   └── dashboard/            # Supervisor operations console (Vite + React 18 + TS)
├── packages/
│   ├── core/                 # Shared domain models, repos, services (epoxa_core)
│   ├── api-client/           # Typed TS client generated from OpenAPI (@epoxa/api-client)
│   └── ui-tokens/            # Shared glassmorphism CSS design tokens (@epoxa/ui-tokens)
├── db/
│   ├── alembic.ini
│   ├── migrations/           # Alembic versioned migrations
│   └── seeds/                # Idempotent seed scripts (Epoxcel org, admin, FAQ docs)
├── infra/
│   ├── docker/               # Multi-stage non-root Dockerfiles + compose.dev.yml
│   └── scripts/              # Automation and deployment helpers
├── docs/                     # Architecture, ADRs, database, security, and runbooks
├── pyproject.toml            # Root uv workspace configuration
├── pnpm-workspace.yaml       # Root pnpm workspace configuration
└── Makefile                  # Development commands (dev, test, lint, migrate, seed)
```

---

## 🛠️ Developer Commands

| Command | Description |
| :--- | :--- |
| `make lint` | Run `ruff` linter and `mypy --strict` type checker |
| `make format` | Format code automatically using `ruff format` |
| `make test` | Execute automated test suite across all workspace packages |
| `make migrate` | Apply latest Alembic database migrations to PostgreSQL |
| `make seed` | Seed Epoxcel tenant organization, admin, and FAQ vectors |
| `make gen-client` | Export OpenAPI schema and regenerate TypeScript client |

---

## 🛡️ Security & Invariants
- **Row Level Security (RLS)** is enabled and forced across all 12 database tables.
- **Least-Privilege Roles**: Services connect via `epoxa_api` and `epoxa_agent` roles with minimum necessary grants.
- **Voice Invariants**: Audio track isolation (`agent_*` and `human_*`), non-blocking `room.sid`, word-boundary escalation regex, and calibrated voice pipeline timings (`interrupt=0.7s`, `endpointing=0.6s`).

For more details, see [docs/architecture/overview.md](file:///Users/palashrajpara/Developer/AI/voice-ai-agent/docs/architecture/overview.md) and [SECURITY.md](file:///Users/palashrajpara/Developer/AI/voice-ai-agent/SECURITY.md).
