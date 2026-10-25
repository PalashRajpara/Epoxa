# Epoxa Security, Privacy & Data Governance

## 1. Zero Trust Client Architecture
- **No Direct Database Access**: Browser clients cannot connect to PostgreSQL directly. All reads and writes must pass through the versioned FastAPI application layer.
- **Short-Lived Room Tokens**: Real-time voice tokens issued to customers expire within 15 minutes. LiveKit API secrets are kept strictly server-side.
- **Supabase Auth JWT / JWKS Verification**: Supervisor tokens are cryptographically verified using Supabase public keys (JWKS). The backend enforces audience (`authenticated`), expiration, and issuer checks.
- **Server-Derived Tenant Membership**: Organization ID is derived from the supervisor's database membership record linked to their verified Auth UID (`sub`). Client-provided organization IDs in request payloads are rejected.

## 2. 30-Day Transcript Retention & Data Minimization
- **Conversational Speech Turns**: Transcripts are stored in a dedicated `transcripts` table indexed by `created_at`.
- **Automated Purge Job**: An idempotent background job runs periodically to purge speech text older than 30 days:
  ```sql
  UPDATE transcripts 
  SET content = '[PURGED_BY_RETENTION_POLICY]', is_purged = TRUE, purged_at = NOW() 
  WHERE created_at < NOW() - INTERVAL '30 days' AND is_purged = FALSE;
  ```
- **Metadata Preservation**: Call duration, timestamps, status, participant links, and objective summaries remain intact for quality auditing and operational reporting.
- **No Audio Recording Storage**: Raw audio recordings are not stored to minimize data exposure.

## 3. Defense-in-Depth Tenant Isolation
- **Composite Constraints**: Foreign keys and unique constraints in PostgreSQL prevent records in Tenant A from referencing entities in Tenant B.
- **Repository Scoping**: Every database lookup explicitly filters by `organization_id`.
- **Customer Privacy**: Customer matching queries require exact phone or email matches strictly scoped to `organization_id`.
- **IDOR Prevention**: Attempting to view or mutate entities belonging to another organization returns a `404 Not Found` without leaking the existence of other tenant data.

## 4. Secrets Management
- All sensitive credentials (`DATABASE_URL`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, `GROQ_API_KEY`) reside in `.env`.
- `.gitignore` strictly excludes `.env`, `*.pem`, `*.key`, and secret artifacts from version control.
- Structured logger includes an automated censorship processor that redacts keys matching `secret`, `token`, `password`, `key`, `transcript`, or `authorization`.
