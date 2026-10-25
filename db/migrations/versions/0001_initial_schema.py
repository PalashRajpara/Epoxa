"""Initial production schema with 12 tables, triggers, RLS, and grants

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-25 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "citext";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')

    # 2. Trigger function for set_updated_at()
    op.execute("""
    CREATE OR REPLACE FUNCTION set_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 3. organizations table
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("timezone", sa.String(length=50), server_default="Asia/Kolkata", nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])
    op.execute("CREATE TRIGGER trg_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # 4. profiles table
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_profiles"),
        sa.UniqueConstraint("email", name="uq_profiles_email"),
    )
    op.create_index("ix_profiles_email", "profiles", ["email"])
    op.execute("CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # 5. memberships table
    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="supervisor", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'admin', 'supervisor')", name="ck_memberships_role"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_memberships_organization_id_organizations", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], name="fk_memberships_profile_id_profiles", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.UniqueConstraint("organization_id", "profile_id", name="uq_memberships_org_profile"),
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_index("ix_memberships_profile_id", "memberships", ["profile_id"])
    op.execute("CREATE TRIGGER trg_memberships_updated_at BEFORE UPDATE ON memberships FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # 6. customers table
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("tier", sa.String(length=20), server_default="Standard", nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("tier IN ('Basic', 'Standard', 'Premium', 'VIP')", name="ck_customers_tier"),
        sa.CheckConstraint("phone_e164 ~ '^\\+[1-9][0-9]{7,14}$'", name="ck_customers_phone_e164"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_customers_organization_id_organizations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
    )
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"])
    op.create_index("idx_customers_org_phone", "customers", ["organization_id", "phone_e164"], unique=True, postgresql_where=sa.text("anonymized_at IS NULL"))
    op.execute("CREATE TRIGGER trg_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # 7. call_sessions table
    op.create_table(
        "call_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_name", sa.String(length=128), nullable=False),
        sa.Column("livekit_room_sid", sa.String(length=64), nullable=True),
        sa.Column("participant_identity", sa.String(length=64), nullable=True),
        sa.Column("participant_name", sa.String(length=150), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("handoff_state", sa.String(length=20), server_default="ai", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("end_reason", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("agent_version", sa.String(length=30), server_default="1.0.0", nullable=False),
        sa.Column("prompt_version", sa.String(length=30), server_default="v1", nullable=False),
        sa.Column("llm_model", sa.String(length=60), server_default="llama-3.1-8b-instant", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("status IN ('active', 'escalated', 'completed', 'dropped', 'timeout', 'error')", name="ck_call_sessions_status"),
        sa.CheckConstraint("handoff_state IN ('ai', 'human_pending', 'human_active')", name="ck_call_sessions_handoff_state"),
        sa.CheckConstraint("duration_seconds >= 0", name="ck_call_sessions_duration_nonneg"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_call_sessions_customer_id_customers", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_call_sessions_organization_id_organizations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_call_sessions"),
        sa.UniqueConstraint("room_name", name="uq_call_sessions_room_name"),
    )
    op.create_index("ix_call_sessions_organization_id", "call_sessions", ["organization_id"])
    op.create_index("ix_call_sessions_customer_id", "call_sessions", ["customer_id"])
    op.create_index("idx_call_sessions_org_status_started", "call_sessions", ["organization_id", "status", "started_at"])
    op.execute("CREATE TRIGGER trg_call_sessions_updated_at BEFORE UPDATE ON call_sessions FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # 8. call_transcripts table
    op.create_table(
        "call_transcripts",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("speaker_identity", sa.String(length=64), nullable=True),
        sa.Column("content", sa.String(length=4000), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("spoken_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.CheckConstraint("role IN ('user', 'agent', 'supervisor')", name="ck_transcripts_role"),
        sa.ForeignKeyConstraint(["session_id"], ["call_sessions.id"], name="fk_call_transcripts_session_id_call_sessions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_call_transcripts"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_transcripts_session_sequence"),
    )
    op.create_index("ix_call_transcripts_session_id", "call_transcripts", ["session_id"])

    # 9. latency_logs table
    op.create_table(
        "latency_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("step", sa.String(length=20), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("step IN ('stt', 'llm', 'tts', 'e2e')", name="ck_latency_step"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_latency_duration_nonneg"),
        sa.ForeignKeyConstraint(["session_id"], ["call_sessions.id"], name="fk_latency_logs_session_id_call_sessions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_latency_logs"),
    )
    op.create_index("idx_latency_session_id", "latency_logs", ["session_id"])
    op.create_index("idx_latency_logged_at", "latency_logs", ["logged_at"])

    # 10. handoff_events table (append-only)
    op.create_table(
        "handoff_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("action IN ('takeover_requested', 'takeover', 'return_to_ai', 'disconnect')", name="ck_handoff_action"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], name="fk_handoff_events_profile_id_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["call_sessions.id"], name="fk_handoff_events_session_id_call_sessions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_handoff_events"),
    )
    op.create_index("ix_handoff_events_session_id", "handoff_events", ["session_id"])
    op.create_index("ix_handoff_events_profile_id", "handoff_events", ["profile_id"])

    # 11. appointments table
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default="30", nullable=False),
        sa.Column("timezone", sa.String(length=50), server_default="Asia/Kolkata", nullable=False),
        sa.Column("confirmation_code", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="confirmed", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("status IN ('confirmed', 'cancelled', 'completed', 'rescheduled', 'no_show')", name="ck_appointments_status"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_appointments_customer_id_customers", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_appointments_organization_id_organizations", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["call_sessions.id"], name="fk_appointments_session_id_call_sessions", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
        sa.UniqueConstraint("organization_id", "confirmation_code", name="uq_appointments_org_code"),
    )
    op.create_index("ix_appointments_organization_id", "appointments", ["organization_id"])
    op.create_index("idx_appointments_customer", "appointments", ["customer_id"])
    op.create_index("idx_appointments_org_slot_confirmed", "appointments", ["organization_id", "scheduled_at"], unique=True, postgresql_where=sa.text("status = 'confirmed'"))
    op.execute("CREATE TRIGGER trg_appointments_updated_at BEFORE UPDATE ON appointments FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # 12. tickets table
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("number", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(length=30), server_default="General", nullable=False),
        sa.Column("priority", sa.String(length=20), server_default="normal", nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("category IN ('Complaint', 'Escalation', 'Billing', 'General', 'Technical')", name="ck_tickets_category"),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name="ck_tickets_priority"),
        sa.CheckConstraint("status IN ('open', 'in_progress', 'resolved', 'closed')", name="ck_tickets_status"),
        sa.ForeignKeyConstraint(["assigned_to"], ["profiles.id"], name="fk_tickets_assigned_to_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_tickets_customer_id_customers", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_tickets_organization_id_organizations", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["call_sessions.id"], name="fk_tickets_session_id_call_sessions", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_tickets"),
        sa.UniqueConstraint("number", name="uq_tickets_number"),
    )
    op.create_index("ix_tickets_organization_id", "tickets", ["organization_id"])
    op.create_index("ix_tickets_assigned_to", "tickets", ["assigned_to"])
    op.create_index("idx_tickets_org_status_created", "tickets", ["organization_id", "status", "created_at"])
    op.execute("CREATE TRIGGER trg_tickets_updated_at BEFORE UPDATE ON tickets FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # 13. audit_logs table (append-only)
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["profiles.id"], name="fk_audit_logs_actor_profile_id_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_audit_logs_organization_id_organizations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])

    # 14. kb_documents & kb_chunks
    op.create_table(
        "kb_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("source_path", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_kb_documents_organization_id_organizations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_kb_documents"),
    )
    op.create_index("ix_kb_documents_organization_id", "kb_documents", ["organization_id"])
    op.execute("CREATE TRIGGER trg_kb_documents_updated_at BEFORE UPDATE ON kb_documents FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    op.execute("""
    CREATE TABLE kb_chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        embedding vector(384)
    );
    """)
    op.create_index("ix_kb_chunks_document_id", "kb_chunks", ["document_id"])
    op.create_index("ix_kb_chunks_organization_id", "kb_chunks", ["organization_id"])
    op.execute("CREATE INDEX idx_kb_chunks_embedding ON kb_chunks USING hnsw (embedding vector_cosine_ops);")

    # 15. Enable & Force Row Level Security (RLS) on all 12 tables
    all_tables = [
        "organizations",
        "profiles",
        "memberships",
        "customers",
        "call_sessions",
        "call_transcripts",
        "latency_logs",
        "handoff_events",
        "appointments",
        "tickets",
        "audit_logs",
        "kb_documents",
        "kb_chunks",
    ]
    for tbl in all_tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")

    # 16. Revoke all permissions from anon and authenticated
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;")
    op.execute("REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM anon, authenticated;")


def downgrade() -> None:
    all_tables = [
        "kb_chunks",
        "kb_documents",
        "audit_logs",
        "tickets",
        "appointments",
        "handoff_events",
        "latency_logs",
        "call_transcripts",
        "call_sessions",
        "customers",
        "memberships",
        "profiles",
        "organizations",
    ]
    for tbl in all_tables:
        op.drop_table(tbl)

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
