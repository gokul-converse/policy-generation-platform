"""SQLAlchemy models for policies and their version history."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Policy(Base):
    """Stable identity for an enterprise policy."""

    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    domain: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="general",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    versions: Mapped[list["PolicyVersion"]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="PolicyVersion.version.asc()",
    )


class PolicyVersion(Base):
    """Versioned draft or approved content of a policy."""

    __tablename__ = "policy_versions"

    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "version",
            name="uq_policy_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        nullable=False,
    )
    content_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON serialization of structured policy sections",
    )
    validation_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )
    validation_report_json: Mapped[str] = mapped_column(
        Text,
        default="{}",
        nullable=False,
        comment="JSON serialization of deterministic validation findings",
    )
    source_requirement_version_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    applied_skill_ids_json: Mapped[str] = mapped_column(
        Text,
        default="[]",
        nullable=False,
    )
    change_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    policy: Mapped["Policy"] = relationship(back_populates="versions")
