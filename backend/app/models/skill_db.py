
"""SQLAlchemy models for skills and their versions."""

import uuid
from datetime import datetime, timezone

from app.db.session import Base
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Skill(Base):
    """Stable identity for a reusable skill."""

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    versions: Mapped[list["SkillVersion"]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan",
    )


class SkillVersion(Base):
    """Metadata for a version whose content is stored in a Markdown file."""

    __tablename__ = "skill_versions"

    __table_args__ = (
        UniqueConstraint(
            "skill_id",
            "version",
            name="uq_skill_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    skill: Mapped["Skill"] = relationship(back_populates="versions")
