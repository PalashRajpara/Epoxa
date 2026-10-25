# Epoxa Tenant Isolation Matrix & Security Design

## 1. Principles of Tenant Isolation
Epoxa enforces tenant isolation through a multi-layered defense-in-depth model:
1. **Server-Side Token Resolution**: Supervisor identity (`auth.users.id`) is verified via cryptographic signature against Supabase JWKS. The user's active tenant (`organization_id`) is determined from verified `organization_memberships` in PostgreSQL.
2. **Explicit Query Scoping**: Every service and repository function requires `organization_id` as an explicit parameter. No generic `SELECT * FROM table WHERE id = :id` is permitted without appending `AND organization_id = :org_id`.
3. **Database Schema Constraints**:
   - Composite foreign keys and check constraints prevent cross-tenant referencing.
   - For example, if a `support_tickets` row has `organization_id = OrgA`, it cannot link to a `customer_id` belonging to `OrgB`.
4. **PostgreSQL Row Level Security (RLS)**: Provides defense-in-depth on Supabase PostgreSQL.

## 2. Tenant Isolation Matrix

| Entity | Primary Tenant Scope Column | Secondary Hierarchy Scopes | Cross-Tenant Protection Mechanism |
|---|---|---|---|
| `organizations` | `id` | - | Unique Slug, Primary Key isolation |
| `businesses` | `organization_id` | - | Foreign Key with Cascade Delete |
| `business_locations` | - | `business_id` (-> `organization_id`) | Indirect parent scoping via `businesses` |
| `supervisor_profiles` | `id` (Supabase Auth UID) | - | Global identity, scoped via memberships |
| `organization_memberships` | `organization_id` | `supervisor_id` | Unique(`organization_id`, `supervisor_id`) |
| `customers` | `organization_id` | `business_id` (optional) | Scoped lookup; matching queries strictly scoped to `organization_id` |
| `call_sessions` | `organization_id` | `business_id`, `customer_id` | Scoped token generation; LiveKit rooms partitioned by `org_id` |
| `call_events` | - | `call_session_id` (-> `organization_id`)| Scoped via parent `call_sessions` |
| `transcripts` | `organization_id` | `call_session_id` | Direct `organization_id` index + parent cascade |
| `call_summaries` | `organization_id` | `call_session_id` | Direct `organization_id` + unique parent FK |
| `support_tickets` | `organization_id` | `business_id`, `customer_id` | Composite validation ensuring customer and call belong to same tenant |
| `escalations` | `organization_id` | `call_session_id`, `support_ticket_id` | Tenant check on escalation creation |
| `takeover_events` | `organization_id` | `call_session_id`, `supervisor_id` | Supervisor membership in `organization_id` verified before takeover |
| `knowledge_documents` | `organization_id` | `business_id` (optional) | Retrieval queries filtered strictly by caller's `organization_id` |
| `knowledge_chunks` | `organization_id` | `document_id` | Direct tenant filter in chunk matching queries |
| `agent_configs` | `organization_id` | `business_id` (optional) | Configuration retrieved by `organization_id` |

## 3. Threat Modeling & Mitigation

### Scenario A: Insecure Direct Object Reference (IDOR)
*Threat*: A supervisor in Tenant A attempts to view a ticket by guessing a UUID belonging to Tenant B (`GET /api/v1/tickets/{tenant_b_ticket_uuid}`).
*Mitigation*: FastAPI route extracts `organization_id` from the verified supervisor session and invokes:
```python
await ticket_repo.get_by_id(db, ticket_id=ticket_id, organization_id=current_user.organization_id)
```
If the ticket does not belong to `current_user.organization_id`, a `404 Not Found` (or `403 Forbidden`) is returned. The existence of records in other tenants is never leaked.

### Scenario B: Cross-Tenant Customer Record Match
*Threat*: Customer calls in Tenant A with phone number `+15551234567`. A customer with the same number exists in Tenant B.
*Mitigation*: Customer lookup tools and services ALWAYS execute queries with `WHERE organization_id = :org_id AND phone_number = :phone`. A match is never returned across tenant borders.

### Scenario C: Unauthorized Call Takeover
*Threat*: A rogue supervisor attempts to hijack a LiveKit room belonging to another company's active call.
*Mitigation*: The `/api/v1/calls/{id}/takeover` endpoint verifies that `call.organization_id == supervisor.organization_id`. LiveKit tokens are issued only after passing this check.
