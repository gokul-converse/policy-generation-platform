
"""Update skill name indexes.

Revision ID: 89cd1e7c9d15
Revises: 697ad2067455
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "89cd1e7c9d15"
down_revision: Union[str, Sequence[str], None] = "697ad2067455"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace the case-sensitive name index with a case-insensitive one."""

    # Remove the previous non-unique index if it exists.
    with op.batch_alter_table("skills") as batch_op:
        batch_op.drop_index("ix_skills_name")

    # Prevent duplicate names regardless of capitalization.
    op.create_index(
        "uq_skills_name_lower",
        "skills",
        [sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    """Restore the previous case-sensitive name index."""

    op.drop_index(
        "uq_skills_name_lower",
        table_name="skills",
    )

    op.create_index(
        "ix_skills_name",
        "skills",
        ["name"],
        unique=False,
    )
