"""create policy tables

Revision ID: 47d6e855c3a1
Revises: 343110985a18
Create Date: 2026-10-21 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47d6e855c3a1'
down_revision: Union[str, Sequence[str], None] = '343110985a18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Safely create policies and policy_versions tables without touching teammate tables."""
    op.create_table(
        'policies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('domain', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_policies_title'), 'policies', ['title'], unique=False)
    op.create_index(op.f('ix_policies_domain'), 'policies', ['domain'], unique=False)

    op.create_table(
        'policy_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('policy_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('content_json', sa.Text(), nullable=False),
        sa.Column('validation_status', sa.String(length=32), nullable=False),
        sa.Column('validation_report_json', sa.Text(), nullable=False),
        sa.Column('source_requirement_version_id', sa.String(length=128), nullable=True),
        sa.Column('applied_skill_ids_json', sa.Text(), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'version', name='uq_policy_version'),
    )
    op.create_index(op.f('ix_policy_versions_policy_id'), 'policy_versions', ['policy_id'], unique=False)


def downgrade() -> None:
    """Safely drop policy tables."""
    op.drop_index(op.f('ix_policy_versions_policy_id'), table_name='policy_versions')
    op.drop_table('policy_versions')
    op.drop_index(op.f('ix_policies_domain'), table_name='policies')
    op.drop_index(op.f('ix_policies_title'), table_name='policies')
    op.drop_table('policies')
