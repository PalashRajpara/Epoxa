# Runbook: Epoxa Production Deployment & Release Procedure

## Overview
This runbook covers the pre-flight checklist, database migration procedure, container deployment, and smoke validation for deploying Epoxa to staging and production.

---

## 1. Pre-Flight Checklist
- [ ] Staging and production Supabase projects provisioned.
- [ ] Database extensions enabled: `citext`, `pgcrypto`, `vector`.
- [ ] Application roles configured: `epoxa_api`, `epoxa_agent`, `epoxa_migrator`.
- [ ] LiveKit Cloud project credentials validated (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`).
- [ ] Deepgram STT/TTS and Groq API keys active with adequate credit allowances.
- [ ] Supabase Auth public sign-up disabled.
- [ ] All CI workflow status checks green on `main`.

---

## 2. Database Migration Procedure (Release Job)

> [!CAUTION]
> Never execute migrations automatically during container startup. Migrations must execute inside a dedicated, isolated release task.

1. Connect to the Supabase **Session Mode** Pooler or Direct Host (port 5432):
   ```bash
   export MIGRATION_DATABASE_URL="postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
   ```
2. Execute migration upgrade:
   ```bash
   make migrate
   # Or directly:
   uv run alembic -c db/alembic.ini upgrade head
   ```
3. Run idempotent database seeds (default org, initial admin, FAQ embeddings):
   ```bash
   make seed
   # Or directly:
   uv run python db/seeds/seed.py
   ```

---

## 3. Application Runtime Database Connection (Port 6543)
- Connect FastAPI (`epoxa_api`) and Agent (`epoxa_agent`) via the **Supavisor Transaction Pooler** (port 6543).
- Ensure `DATABASE_URL` specifies `statement_cache_size=0` to comply with asyncpg and transaction pooling.

---

## 4. Container Deployment
Deploy non-root Docker images to target infrastructure (e.g., AWS ECS, GCP Cloud Run, or Kubernetes):
- `apps/api`: HTTP service with health check on `/health/live` and `/health/ready`.
- `apps/agent`: Long-lived stateful worker with adequate CPU for real-time audio buffering.
- `apps/web`: Static SPA served via Nginx.
- `apps/dashboard`: Static SPA served via Nginx.

---

## 5. Post-Deployment Smoke Verification
1. Verify `/health/ready` returns `200 OK`.
2. Log into the Supervisor Dashboard with initial admin credentials.
3. Open Customer Web App in an incognito window and initiate a test voice call.
4. Verify Epixa greets caller, schedules a test appointment, and confirm record in PostgreSQL.
5. In Supervisor Console, verify live call appears via SSE, execute takeover, speak into microphone, and hand back to AI.
6. Verify transcript turns and latency logs are persisted in PostgreSQL.
