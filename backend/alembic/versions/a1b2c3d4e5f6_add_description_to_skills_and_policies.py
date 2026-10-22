"""add description to skills and policies

Revision ID: a1b2c3d4e5f6
Revises: 47d6e855c3a1
Create Date: 2026-10-21 21:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '47d6e855c3a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Safely add description columns to skills and policies."""
    op.add_column('skills', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('policies', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    """Safely remove description columns."""
    op.drop_column('policies', 'description')
    op.drop_column('skills', 'description')
