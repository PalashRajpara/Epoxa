# Runbook: Secret and Credential Rotation Procedure

## Overview
This runbook documents zero-downtime rotation procedures for all third-party API keys and database credentials.

---

## 1. LiveKit API Key & Secret Rotation
1. Log into LiveKit Cloud Console -> Settings -> Keys.
2. Generate a secondary API Key and Secret (LiveKit allows multiple active keys simultaneously).
3. Update environment variables in container deployment configuration:
   - `LIVEKIT_API_KEY`: New secondary key
   - `LIVEKIT_API_SECRET`: New secondary secret
4. Trigger rolling restart of `apps/api` and `apps/agent`.
5. Verify live call connection works.
6. Delete the deprecated primary key in LiveKit Cloud Console.

---

## 2. Supabase Service Role Key & JWT Secret
1. In Supabase Dashboard -> Project Settings -> API.
2. If using asymmetric JWKS: JWKS keys rotate automatically with public keys cached under local TTL (1 hour).
3. If rotating the Service Role Secret:
   - Generate new service-role secret.
   - Update `SUPABASE_SERVICE_ROLE_KEY` across `apps/api`.
   - Restart `apps/api`.

---

## 3. Deepgram STT/TTS API Key Rotation
1. Log into Deepgram Console -> API Keys.
2. Create a new project API key with `Member` role.
3. Update `DEEPGRAM_STT_API_KEY` and `DEEPGRAM_TTS_API_KEY` in `apps/agent`.
4. Trigger rolling deployment of `apps/agent`.
5. Revoke old Deepgram API key.

---

## 4. Groq API Key Rotation
1. In Groq Cloud Console -> API Keys.
2. Create a new API Key.
3. Update `GROQ_API_KEY` in `apps/agent` and `apps/api`.
4. Trigger rolling restart of workers.
5. Revoke old Groq key.
