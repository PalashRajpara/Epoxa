# ADR 0001: Multi-Tenant Architecture Foundation

## Status
Accepted

## Context
Epoxa was originally built as a single-tenant prototype with customer and call tables implicitly assuming a single organization. Retrofitting multi-tenancy later requires painful schema migrations, complex data backfilling, and dangerous authorization refactors. Epoxa needs to support multi-tenant isolation from day one, seeded initially for Epoxcel.

## Decision
1. Introduce an `organizations` table as the root tenant boundary:
   - `id UUID PRIMARY KEY`, `name TEXT`, `slug TEXT UNIQUE`, `timezone TEXT`, `settings JSONB`.
2. Every business table (`customers`, `call_sessions`, `appointments`, `tickets`, `audit_logs`, `kb_documents`, `kb_chunks`) contains a mandatory foreign key `organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE`.
3. Organization timezone and business hours (`Asia/Kolkata`, Mon-Sat 09:00-18:00) are stored in `organizations.settings`.
4. All FastAPI queries and agent operations are strictly scoped by `organization_id` extracted from JWT claims or worker configuration, never from untrusted client query parameters.

## Alternatives Considered
- **Single-tenant schema**: Rejected because multi-tenancy was deemed non-negotiable for enterprise SaaS launch.
- **Schema-per-tenant (PostgreSQL schemas)**: Rejected due to migration maintenance overhead across dozens of tenant schemas. Row-level multi-tenancy with foreign keys and compound indexes provides optimal maintainability.

## Consequences
- Clean tenant boundary for all queries.
- Compound unique indexes required (e.g. `(organization_id, phone_e164)`).
- RLS and query dependencies must always enforce `organization_id`.
