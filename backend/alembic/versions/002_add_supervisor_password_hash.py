"""002_add_supervisor_password_hash

Revision ID: 002_add_supervisor_password_hash
Revises: 001_initial_schema
Create Date: 2026-10-25 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_add_supervisor_password_hash'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        'supervisor_profiles',
        sa.Column('password_hash', sa.String(length=255), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('supervisor_profiles', 'password_hash')
