"""add applied skill version references

Revision ID: 1f7ebfd30eeb
Revises: da120d30911c
Create Date: 2026-11-02 23:45:36.804327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f7ebfd30eeb'
down_revision: Union[str, Sequence[str], None] = 'da120d30911c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "policy_versions",
        sa.Column(
            "applied_skill_version_ids_json",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment="JSON list of exact generated skill version UUIDs used by this policy version",
        ),
    )


def downgrade():
    op.drop_column(
        "policy_versions",
        "applied_skill_version_ids_json",
    )