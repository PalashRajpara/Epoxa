"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-25 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)
    op.create_index('ix_organizations_created_at', 'organizations', ['created_at'])

    # 2. Businesses
    op.create_table(
        'businesses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_businesses_organization_id', 'businesses', ['organization_id'])

    # 3. Business Locations
    op.create_table(
        'business_locations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('timezone', sa.String(length=100), nullable=False, server_default='UTC'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_business_locations_business_id', 'business_locations', ['business_id'])

    # 4. Supervisor Profiles
    op.create_table(
        'supervisor_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_supervisor_profiles_email', 'supervisor_profiles', ['email'], unique=True)

    # 5. Organization Memberships
    op.create_table(
        'organization_memberships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('supervisor_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='supervisor'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supervisor_id'], ['supervisor_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'supervisor_id', name='uq_org_membership')
    )
    op.create_index('ix_organization_memberships_org_id', 'organization_memberships', ['organization_id'])
    op.create_index('ix_organization_memberships_sup_id', 'organization_memberships', ['supervisor_id'])

    # 6. Business Memberships
    op.create_table(
        'business_memberships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('supervisor_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='supervisor'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supervisor_id'], ['supervisor_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id', 'supervisor_id', name='uq_biz_membership')
    )

    # 7. Customers
    op.create_table(
        'customers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_customers_org_id', 'customers', ['organization_id'])
    op.create_index('ix_customers_phone_number', 'customers', ['phone_number'])
    op.create_index('ix_customers_email', 'customers', ['email'])

    # 8. Call Sessions
    op.create_table(
        'call_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=True),
        sa.Column('customer_id', sa.UUID(), nullable=True),
        sa.Column('room_name', sa.String(length=120), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='initiating'),
        sa.Column('handoff_state', sa.String(length=50), nullable=False, server_default='none'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('termination_reason', sa.String(length=100), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_call_sessions_org_id', 'call_sessions', ['organization_id'])
    op.create_index('ix_call_sessions_room_name', 'call_sessions', ['room_name'], unique=True)
    op.create_index('ix_call_sessions_status', 'call_sessions', ['status'])

    # 9. Call Events
    op.create_table(
        'call_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('call_session_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('actor', sa.String(length=50), nullable=False, server_default='system'),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['call_session_id'], ['call_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_call_events_session_id', 'call_events', ['call_session_id'])

    # 10. Transcripts
    op.create_table(
        'transcripts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('call_session_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('speaker', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('is_purged', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('purged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['call_session_id'], ['call_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transcripts_session_id', 'transcripts', ['call_session_id'])
    op.create_index('ix_transcripts_org_id', 'transcripts', ['organization_id'])
    op.create_index('ix_transcripts_created_at', 'transcripts', ['created_at'])
    op.create_index('ix_transcripts_is_purged', 'transcripts', ['is_purged'])

    # 11. Call Summaries
    op.create_table(
        'call_summaries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('call_session_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('primary_intent', sa.String(length=100), nullable=True),
        sa.Column('detected_sentiment', sa.String(length=50), nullable=True),
        sa.Column('follow_up_required', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['call_session_id'], ['call_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_session_id')
    )
    op.create_index('ix_call_summaries_org_id', 'call_summaries', ['organization_id'])

    # 12. Support Tickets
    op.create_table(
        'support_tickets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=True),
        sa.Column('customer_id', sa.UUID(), nullable=True),
        sa.Column('call_session_id', sa.UUID(), nullable=True),
        sa.Column('assigned_supervisor_id', sa.UUID(), nullable=True),
        sa.Column('ticket_number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='general'),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_supervisor_id'], ['supervisor_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['call_session_id'], ['call_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_number')
    )
    op.create_index('ix_support_tickets_org_id', 'support_tickets', ['organization_id'])
    op.create_index('ix_support_tickets_status', 'support_tickets', ['status'])

    # 13. Escalations
    op.create_table(
        'escalations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('call_session_id', sa.UUID(), nullable=False),
        sa.Column('support_ticket_id', sa.UUID(), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['call_session_id'], ['call_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['support_ticket_id'], ['support_tickets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_escalations_org_id', 'escalations', ['organization_id'])

    # 14. Takeover Events
    op.create_table(
        'takeover_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('call_session_id', sa.UUID(), nullable=False),
        sa.Column('supervisor_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['call_session_id'], ['call_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supervisor_id'], ['supervisor_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_takeover_events_org_id', 'takeover_events', ['organization_id'])

    # 15. Knowledge Documents
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False, server_default='faq'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_documents_org_id', 'knowledge_documents', ['organization_id'])

    # 16. Knowledge Chunks
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('chunk_content', sa.Text(), nullable=False),
        sa.Column('chunk_hash', sa.String(length=64), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['knowledge_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_chunks_document_id', 'knowledge_chunks', ['document_id'])
    op.create_index('ix_knowledge_chunks_org_id', 'knowledge_chunks', ['organization_id'])

    # 17. Agent Configs
    op.create_table(
        'agent_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('voice_model', sa.String(length=100), nullable=False, server_default='aura-asteria-en'),
        sa.Column('llm_model', sa.String(length=100), nullable=False, server_default='llama-3.3-70b-versatile'),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_configs_org_id', 'agent_configs', ['organization_id'])

def downgrade() -> None:
    op.drop_table('agent_configs')
    op.drop_table('knowledge_chunks')
    op.drop_table('knowledge_documents')
    op.drop_table('takeover_events')
    op.drop_table('escalations')
    op.drop_table('support_tickets')
    op.drop_table('call_summaries')
    op.drop_table('transcripts')
    op.drop_table('call_events')
    op.drop_table('call_sessions')
    op.drop_table('customers')
    op.drop_table('business_memberships')
    op.drop_table('organization_memberships')
    op.drop_table('supervisor_profiles')
    op.drop_table('business_locations')
    op.drop_table('businesses')
    op.drop_table('organizations')
