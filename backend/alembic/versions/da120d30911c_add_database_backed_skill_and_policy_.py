"""Add database-backed skill and policy content

Revision ID: da120d30911c
Revises: d776dbb1864d
Create Date: 2026-11-02 22:59:18.502750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da120d30911c'
down_revision: Union[str, Sequence[str], None] = 'd776dbb1864d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    """Upgrade schema for database-backed skill and policy content."""

    # Add policy status and initialize existing records as draft.
    with op.batch_alter_table("policies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'draft'"),
            )
        )

    # Add readable policy content and initialize existing records.
    with op.batch_alter_table("policy_versions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "content_text",
                sa.Text(),
                nullable=False,
                server_default=sa.text("''"),
                comment="Complete rendered policy text",
            )
        )

    # Move generated skill storage to the database.
    # Existing legacy skill content will remain NULL.
    with op.batch_alter_table("skill_versions") as batch_op:
        batch_op.add_column(
            sa.Column("content", sa.Text(), nullable=True)
        )
        batch_op.drop_column("file_path")


def downgrade() -> None:
    """Downgrade schema."""

    # Original file paths cannot be recovered.
    # Recreate the legacy column as nullable.
    with op.batch_alter_table("skill_versions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "file_path",
                sa.String(length=512),
                nullable=True,
            )
        )
        batch_op.drop_column("content")

    with op.batch_alter_table("policy_versions") as batch_op:
        batch_op.drop_column("content_text")

    with op.batch_alter_table("policies") as batch_op:
        batch_op.drop_column("status")
