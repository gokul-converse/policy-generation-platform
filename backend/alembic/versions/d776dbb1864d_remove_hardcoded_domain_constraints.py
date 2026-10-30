
"""Remove hardcoded domain constraints."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d776dbb1864d"
down_revision: Union[str, Sequence[str], None] = "89cd1e7c9d15"
branch_labels = None
depends_on = None


DOMAIN_CHECK = "domain IN ('hr', 'finance', 'it_security', 'general')"


def documents_table(include_domain_check: bool) -> sa.Table:
    metadata = sa.MetaData()

    constraints = [
        sa.UniqueConstraint("file_path", "version"),
        sa.CheckConstraint(
            "approval_status IN "
            "('approved', 'pending_review', 'rejected', "
            "'sample_not_approved', 'unknown')"
        ),
        sa.CheckConstraint(
            "ingestion_status IN "
            "('pending', 'processing', 'completed', 'failed')"
        ),
    ]

    if include_domain_check:
        constraints.append(
            sa.CheckConstraint(
                DOMAIN_CHECK,
                name="ck_documents_domain",
            )
        )

    return sa.Table(
        "documents",
        metadata,
        sa.Column(
            "document_id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("document_name", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column(
            "version",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'1'"),
        ),
        sa.Column(
            "approval_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'sample_not_approved'"),
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column(
            "ingestion_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        *constraints,
    )


def approval_rules_table(include_domain_check: bool) -> sa.Table:
    metadata = sa.MetaData()

    constraints = [
        sa.CheckConstraint(
            "data_status IN ('sample', 'verified', 'unknown')"
        ),
    ]

    if include_domain_check:
        constraints.append(
            sa.CheckConstraint(
                DOMAIN_CHECK,
                name="ck_approval_rules_domain",
            )
        )

    return sa.Table(
        "approval_rules",
        metadata,
        sa.Column(
            "rule_id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("rule_name", sa.Text(), nullable=False),
        sa.Column("condition_description", sa.Text(), nullable=False),
        sa.Column("approver_role", sa.Text(), nullable=False),
        sa.Column(
            "source_document_id",
            sa.Integer(),
            sa.ForeignKey(
                "documents.document_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column(
            "data_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'sample'"),
        ),
        *constraints,
    )


def requirement_sessions_table(
    include_domain_check: bool,
) -> sa.Table:
    metadata = sa.MetaData()

    constraints = [
        sa.CheckConstraint(
            "status IN ('gathering', 'awaiting_clarification', "
            "'validating', 'ready_for_confirmation', "
            "'confirmed', 'cancelled')"
        ),
    ]

    if include_domain_check:
        constraints.append(
            sa.CheckConstraint(
                DOMAIN_CHECK,
                name="ck_requirement_sessions_domain",
            )
        )

    return sa.Table(
        "requirement_sessions",
        metadata,
        sa.Column(
            "session_id",
            sa.Text(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("original_description", sa.Text(), nullable=False),
        sa.Column(
            "domain",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'general'"),
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'gathering'"),
        ),
        sa.Column(
            "created_at",
            sa.Text(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.Text(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        *constraints,
    )


def upgrade() -> None:
    # Remove only the domain CHECK from documents.
    with op.batch_alter_table(
        "documents",
        copy_from=documents_table(include_domain_check=True),
    ) as batch_op:
        batch_op.drop_constraint(
            "ck_documents_domain",
            type_="check",
        )

    # Remove only the domain CHECK from approval_rules.
    with op.batch_alter_table(
        "approval_rules",
        copy_from=approval_rules_table(include_domain_check=True),
    ) as batch_op:
        batch_op.drop_constraint(
            "ck_approval_rules_domain",
            type_="check",
        )

    # Remove only the domain CHECK from requirement_sessions.
    with op.batch_alter_table(
        "requirement_sessions",
        copy_from=requirement_sessions_table(
            include_domain_check=True
        ),
    ) as batch_op:
        batch_op.drop_constraint(
            "ck_requirement_sessions_domain",
            type_="check",
        )


def downgrade() -> None:
    # Restore the original documents domain CHECK.
    with op.batch_alter_table(
        "documents",
        copy_from=documents_table(include_domain_check=False),
    ) as batch_op:
        batch_op.create_check_constraint(
            "ck_documents_domain",
            DOMAIN_CHECK,
        )

    # Restore the original approval_rules domain CHECK.
    with op.batch_alter_table(
        "approval_rules",
        copy_from=approval_rules_table(include_domain_check=False),
    ) as batch_op:
        batch_op.create_check_constraint(
            "ck_approval_rules_domain",
            DOMAIN_CHECK,
        )

    # Restore the original requirement_sessions domain CHECK.
    with op.batch_alter_table(
        "requirement_sessions",
        copy_from=requirement_sessions_table(
            include_domain_check=False
        ),
    ) as batch_op:
        batch_op.create_check_constraint(
            "ck_requirement_sessions_domain",
            DOMAIN_CHECK,
        )
