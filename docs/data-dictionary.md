# Epoxa Data Dictionary

This document specifies table definitions, column types, nullability, defaults, constraints, and retention policies.

## 1. Hierarchy & Identity Tables

### `organizations`
Primary tenant root. Every organizational asset is scoped to an organization.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `name` | VARCHAR(255) | No | None | Display name of the tenant |
| `slug` | VARCHAR(100) | No | None | Unique URL-safe identifier (`UNIQUE`) |
| `status` | VARCHAR(50) | No | `'active'` | Organization status (`active`, `suspended`) |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `businesses`
Sub-entity under an organization (e.g. business unit, brand).
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `organization_id` | UUID | No | None | FK to `organizations.id` (`ON DELETE CASCADE`) |
| `name` | VARCHAR(255) | No | None | Business name |
| `category` | VARCHAR(100) | Yes | None | Category (retail, wholesale, healthcare) |
| `status` | VARCHAR(50) | No | `'active'` | Status |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `business_locations`
Physical or virtual branches of a business.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `business_id` | UUID | No | None | FK to `businesses.id` (`ON DELETE CASCADE`) |
| `name` | VARCHAR(255) | No | None | Location branch name |
| `address` | TEXT | Yes | None | Street address / location metadata |
| `timezone` | VARCHAR(100) | No | `'UTC'` | Local timezone |
| `status` | VARCHAR(50) | No | `'active'` | Status |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `supervisor_profiles`
Internal user profile linked to Supabase Auth User ID.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | None | Primary Key; Matches Supabase `auth.users.id` |
| `email` | VARCHAR(255) | No | None | Email address |
| `full_name` | VARCHAR(255) | No | None | Supervisor display name |
| `status` | VARCHAR(50) | No | `'active'` | Status |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `organization_memberships`
Join table linking supervisors to authorized organizations.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `organization_id` | UUID | No | None | FK to `organizations.id` (`ON DELETE CASCADE`) |
| `supervisor_id` | UUID | No | None | FK to `supervisor_profiles.id` (`ON DELETE CASCADE`) |
| `role` | VARCHAR(50) | No | `'supervisor'` | Role (`admin`, `supervisor`) |
| `status` | VARCHAR(50) | No | `'active'` | Status |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| **Constraint** | UNIQUE(`organization_id`, `supervisor_id`) | | | |

---

## 2. Customer & Voice Call Tables

### `customers`
Customer contact records without user login credentials.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `business_id` | UUID | Yes | None | FK to `businesses.id` |
| `display_name` | VARCHAR(255) | Yes | None | Customer caller name |
| `phone_number` | VARCHAR(50) | Yes | None | Phone number (E.164 formatted if provided) |
| `email` | VARCHAR(255) | Yes | None | Email address |
| `company_name` | VARCHAR(255) | Yes | None | For wholesale / B2B callers |
| `metadata` | JSONB | No | `'{}'` | Custom attributes / notes |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `call_sessions`
Live and historical voice call sessions.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `business_id` | UUID | Yes | None | FK to `businesses.id` |
| `customer_id` | UUID | Yes | None | FK to `customers.id` |
| `room_name` | VARCHAR(120) | No | None | LiveKit Room identifier (`UNIQUE`) |
| `status` | VARCHAR(50) | No | `'initiating'` | Status: `initiating`, `active`, `escalated`, `supervisor_takeover`, `completed`, `failed` |
| `handoff_state` | VARCHAR(50) | No | `'none'` | State: `none`, `requested`, `accepted`, `rejected`, `returned_to_ai` |
| `started_at` | TIMESTAMPTZ | Yes | None | Session start timestamp |
| `ended_at` | TIMESTAMPTZ | Yes | None | Session end timestamp |
| `duration_seconds`| INTEGER | Yes | None | Total call duration |
| `termination_reason` | VARCHAR(100) | Yes | None | Reason for disconnect |
| `metadata` | JSONB | No | `'{}'` | Session telemetry & metrics |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `transcripts`
Individual conversational speech turns. **Subject to 30-Day Retention**.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `call_session_id` | UUID | No | None | FK to `call_sessions.id` (`ON DELETE CASCADE`) |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `speaker` | VARCHAR(50) | No | None | `customer`, `ai_agent`, `supervisor` |
| `content` | TEXT | Yes | None | Transcribed speech. Redacted after 30 days. |
| `is_purged` | BOOLEAN | No | `FALSE` | Purged/Redacted flag for 30-day retention |
| `purged_at` | TIMESTAMPTZ | Yes | None | Timestamp when content was redacted |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC (Indexed for retention queries) |

### `call_summaries`
Generated AI summary and intent metadata for completed calls.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `call_session_id` | UUID | No | None | FK to `call_sessions.id` (`UNIQUE`, `ON DELETE CASCADE`) |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `summary` | TEXT | No | None | Concise objective call summary |
| `primary_intent` | VARCHAR(100) | Yes | None | Intent classified by orchestrator |
| `detected_sentiment`| VARCHAR(50) | Yes | None | Sentiment (`positive`, `neutral`, `negative`, `frustrated`) |
| `follow_up_required`| BOOLEAN | No | `FALSE` | Flag indicating supervisor action needed |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

---

## 3. Support Tickets & Escalation Tables

### `support_tickets`
Customer issue tickets created during or after calls.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `business_id` | UUID | Yes | None | FK to `businesses.id` |
| `customer_id` | UUID | Yes | None | FK to `customers.id` |
| `call_session_id` | UUID | Yes | None | FK to `call_sessions.id` |
| `assigned_supervisor_id` | UUID | Yes | None | FK to `supervisor_profiles.id` |
| `ticket_number` | VARCHAR(50) | No | None | Unique human-readable ticket ID (`UNIQUE`) |
| `title` | VARCHAR(255) | No | None | Short summary of issue |
| `description` | TEXT | No | None | Detailed description |
| `category` | VARCHAR(50) | No | `'general'` | `general`, `technical`, `billing`, `escalation` |
| `priority` | VARCHAR(50) | No | `'medium'` | `low`, `medium`, `high`, `urgent` |
| `status` | VARCHAR(50) | No | `'open'` | `open`, `in_progress`, `pending_customer`, `resolved`, `closed` |
| `resolved_at` | TIMESTAMPTZ | Yes | None | Resolution timestamp |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `escalations`
Tracks live escalation requests from callers.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `call_session_id` | UUID | No | None | FK to `call_sessions.id` |
| `support_ticket_id` | UUID | Yes | None | FK to `support_tickets.id` |
| `reason` | VARCHAR(255) | No | None | Reason for escalation |
| `state` | VARCHAR(50) | No | `'pending'` | `pending`, `accepted`, `handoff_complete`, `fallback_ticket_created` |
| `requested_at` | TIMESTAMPTZ | No | `NOW()` | Request timestamp |
| `resolved_at` | TIMESTAMPTZ | Yes | None | Resolution timestamp |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `takeover_events`
Audit log of supervisor actions during a live call.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `call_session_id` | UUID | No | None | FK to `call_sessions.id` |
| `supervisor_id` | UUID | No | None | FK to `supervisor_profiles.id` |
| `action` | VARCHAR(50) | No | None | `takeover_started`, `handback_to_ai`, `call_ended` |
| `notes` | TEXT | Yes | None | Supervisor notes / context |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

---

## 4. Knowledge Retrieval & Agent Configuration

### `knowledge_documents`
Collection of approved company FAQs, guidelines, and manuals.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `business_id` | UUID | Yes | None | FK to `businesses.id` |
| `title` | VARCHAR(255) | No | None | Document title |
| `document_type` | VARCHAR(50) | No | `'faq'` | `faq`, `policy`, `guide` |
| `status` | VARCHAR(50) | No | `'active'` | Status |
| `metadata` | JSONB | No | `'{}'` | Source / version metadata |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `knowledge_chunks`
Text chunks for grounding AI responses.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `document_id` | UUID | No | None | FK to `knowledge_documents.id` (`ON DELETE CASCADE`) |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `chunk_content` | TEXT | No | None | Plaintext passage |
| `chunk_hash` | VARCHAR(64) | No | None | SHA256 of content for deduplication |
| `metadata` | JSONB | No | `'{}'` | Section headers, keywords |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |

### `agent_configs`
Configurable agent system prompts, speech parameters, and model settings.
| Column | Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | UUID | No | `uuid_generate_v4()` | Primary Key |
| `organization_id` | UUID | No | None | FK to `organizations.id` |
| `business_id` | UUID | Yes | None | FK to `businesses.id` |
| `system_prompt` | TEXT | No | None | Core instructions & guardrails |
| `voice_model` | VARCHAR(100) | No | `'aura-asteria-en'` | TTS voice ID |
| `llm_model` | VARCHAR(100) | No | `'llama-3.3-70b-versatile'` | LLM identifier |
| `temperature` | FLOAT | No | `0.1` | Model sampling temperature |
| `is_active` | BOOLEAN | No | `TRUE` | Whether this configuration is active |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Timestamp in UTC |
