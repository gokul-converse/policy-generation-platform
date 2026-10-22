"""add source requirement version to skills

Revision ID: 343110985a18
Revises: e53b2cb8a85b
Create Date: 2026-10-21 16:00:40.666941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '343110985a18'
down_revision: Union[str, Sequence[str], None] = 'e53b2cb8a85b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Safely add source_requirement_version_id column to skill_versions without dropping teammate tables."""
    op.add_column('skill_versions', sa.Column('source_requirement_version_id', sa.String(length=128), nullable=True))


def downgrade() -> None:
    """Safely remove source_requirement_version_id column from skill_versions."""
    op.drop_column('skill_versions', 'source_requirement_version_id')
