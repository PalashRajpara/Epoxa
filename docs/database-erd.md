# Epoxa Database Entity Relationship Diagram (ERD)

## 1. Mermaid Entity-Relationship Diagram

```mermaid
erDiagram
    ORGANIZATION ||--o{ BUSINESS : "owns"
    ORGANIZATION ||--o{ SUPERVISOR_PROFILE : "registers"
    ORGANIZATION ||--o{ ORGANIZATION_MEMBERSHIP : "has"
    ORGANIZATION ||--o{ CUSTOMER : "manages"
    ORGANIZATION ||--o{ CALL_SESSION : "records"
    ORGANIZATION ||--o{ SUPPORT_TICKET : "tracks"
    ORGANIZATION ||--o{ KNOWLEDGE_DOCUMENT : "stores"
    ORGANIZATION ||--o{ AGENT_CONFIG : "configures"

    BUSINESS ||--o{ BUSINESS_LOCATION : "operates"
    BUSINESS ||--o{ BUSINESS_MEMBERSHIP : "assigns"
    BUSINESS ||--o{ CALL_SESSION : "handles"
    BUSINESS ||--o{ SUPPORT_TICKET : "routes"

    SUPERVISOR_PROFILE ||--o{ ORGANIZATION_MEMBERSHIP : "holds"
    SUPERVISOR_PROFILE ||--o{ BUSINESS_MEMBERSHIP : "holds"
    SUPERVISOR_PROFILE ||--o{ TAKEOVER_EVENT : "initiates"
    SUPERVISOR_PROFILE ||--o{ SUPPORT_TICKET : "assigned_to"

    CUSTOMER ||--o{ CALL_SESSION : "initiates"
    CUSTOMER ||--o{ SUPPORT_TICKET : "subject_of"

    CALL_SESSION ||--o{ CALL_EVENT : "logs"
    CALL_SESSION ||--o{ TRANSCRIPT : "records"
    CALL_SESSION ||--o| CALL_SUMMARY : "summarized_by"
    CALL_SESSION ||--o{ ESCALATION : "triggers"
    CALL_SESSION ||--o{ TAKEOVER_EVENT : "undergoes"
    CALL_SESSION ||--o{ SUPPORT_TICKET : "generates"

    KNOWLEDGE_DOCUMENT ||--o{ KNOWLEDGE_CHUNK : "split_into"

    ORGANIZATION {
        uuid id PK
        string name
        string slug UK
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    BUSINESS {
        uuid id PK
        uuid organization_id FK
        string name
        string category
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    BUSINESS_LOCATION {
        uuid id PK
        uuid business_id FK
        string name
        string address
        string timezone
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    SUPERVISOR_PROFILE {
        uuid id PK "Matches Supabase Auth User ID"
        string email
        string full_name
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    ORGANIZATION_MEMBERSHIP {
        uuid id PK
        uuid organization_id FK
        uuid supervisor_id FK
        string role "admin | supervisor"
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    BUSINESS_MEMBERSHIP {
        uuid id PK
        uuid business_id FK
        uuid supervisor_id FK
        string role
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    CUSTOMER {
        uuid id PK
        uuid organization_id FK
        uuid business_id FK
        string display_name
        string phone_number
        string email
        string company_name
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    CALL_SESSION {
        uuid id PK
        uuid organization_id FK
        uuid business_id FK
        uuid customer_id FK
        string room_name UK
        string status "initiating | active | escalated | supervisor_takeover | completed | failed"
        string handoff_state "none | requested | accepted | rejected | returned_to_ai"
        timestamptz started_at
        timestamptz ended_at
        integer duration_seconds
        string termination_reason
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    CALL_EVENT {
        uuid id PK
        uuid call_session_id FK
        string event_type
        string actor "customer | ai_agent | supervisor | system"
        jsonb payload
        timestamptz created_at
    }

    TRANSCRIPT {
        uuid id PK
        uuid call_session_id FK
        uuid organization_id FK
        string speaker "customer | ai_agent | supervisor"
        text content
        boolean is_purged
        timestamptz purged_at
        timestamptz created_at
    }

    CALL_SUMMARY {
        uuid id PK
        uuid call_session_id FK UK
        uuid organization_id FK
        text summary
        string primary_intent
        string detected_sentiment
        boolean follow_up_required
        timestamptz created_at
        timestamptz updated_at
    }

    SUPPORT_TICKET {
        uuid id PK
        uuid organization_id FK
        uuid business_id FK
        uuid customer_id FK
        uuid call_session_id FK
        uuid assigned_supervisor_id FK
        string ticket_number UK
        string title
        text description
        string category "general | technical | billing | escalation"
        string priority "low | medium | high | urgent"
        string status "open | in_progress | pending_customer | resolved | closed"
        timestamptz resolved_at
        timestamptz created_at
        timestamptz updated_at
    }

    ESCALATION {
        uuid id PK
        uuid organization_id FK
        uuid call_session_id FK
        uuid support_ticket_id FK
        string reason
        string state "pending | accepted | handoff_complete | fallback_ticket_created"
        timestamptz requested_at
        timestamptz resolved_at
        timestamptz created_at
    }

    TAKEOVER_EVENT {
        uuid id PK
        uuid organization_id FK
        uuid call_session_id FK
        uuid supervisor_id FK
        string action "takeover_started | handback_to_ai | call_ended"
        text notes
        timestamptz created_at
    }

    KNOWLEDGE_DOCUMENT {
        uuid id PK
        uuid organization_id FK
        uuid business_id FK
        string title
        string document_type "faq | policy | guide"
        string status "active | archived"
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    KNOWLEDGE_CHUNK {
        uuid id PK
        uuid document_id FK
        uuid organization_id FK
        text chunk_content
        string chunk_hash
        jsonb metadata
        timestamptz created_at
    }

    AGENT_CONFIG {
        uuid id PK
        uuid organization_id FK
        uuid business_id FK
        string system_prompt
        string voice_model
        string llm_model
        float temperature
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
```
