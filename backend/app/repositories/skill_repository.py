"""Database operations for skills and their versions."""

import logging
import uuid
from pathlib import Path

from app.config.settings import settings
from app.models.skill_db import Skill, SkillVersion
from app.models.skills import GeneratedSkillSet
from app.services.skill_file_service import write_skill_file
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


async def save_skill_set(
    session: AsyncSession,
    skill_set: GeneratedSkillSet,
    source_requirement_version_id: str | None = None,
) -> list[Skill]:
    """Save generated skills as initial draft versions.

    Files are written before the database transaction is committed.
    If database persistence fails, the transaction is rolled back and
    files created by this operation are removed on a best-effort basis.

    Filesystem writes and database commits cannot form one atomic
    transaction, so cleanup failures must be logged and handled operationally.
    """
    generated_skills = skill_set.skills

    if not generated_skills:
        return []

    names = [skill.name.strip() for skill in generated_skills]
    normalized_names = [name.casefold() for name in names]

    if any(not name for name in names):
        raise ValueError("Skill names must not be empty.")

    if len(normalized_names) != len(set(normalized_names)):
        raise ValueError(
            "Skill names must be unique within a generated set."
        )

    skills_root = settings.generated_skills_path.resolve()
    created_files: list[Path] = []
    skill_ids: list[uuid.UUID] = []

    try:
        # Detect existing names case-insensitively.
        # The database uniqueness constraint remains necessary to protect
        # against concurrent requests.
        result = await session.execute(
            select(Skill.name).where(
                func.lower(Skill.name).in_(normalized_names)
            )
        )
        existing_names = {
            name.casefold()
            for name in result.scalars().all()
        }

        conflicts = sorted(
            name
            for name in names
            if name.casefold() in existing_names
        )

        if conflicts:
            raise ValueError(f"Skills already exist: {conflicts}")

        # Write each initial skill file and stage its database records.
        for generated_skill in generated_skills:
            skill_id = uuid.uuid4()
            skill_ids.append(skill_id)

            relative_path = write_skill_file(
                generated_skill=generated_skill,
                skill_id=str(skill_id),
                version=1,
            )

            file_path = (skills_root / relative_path).resolve()

            try:
                file_path.relative_to(skills_root)
            except ValueError as exc:
                raise ValueError(
                    "Skill file path escapes the skills directory."
                ) from exc

            # Track only files that actually exist. If the writer creates
            # a file and then raises before returning, that partial-write
            # cleanup must be handled by write_skill_file itself.
            if file_path.is_file():
                created_files.append(file_path)

            skill = Skill(
                id=skill_id,
                name=generated_skill.name.strip(),
                description=generated_skill.description,
            )

            skill.versions.append(
                SkillVersion(
                    version=1,
                    file_path=relative_path,
                    status="draft",
                    source_requirement_version_id=(
                        source_requirement_version_id
                    ),
                )
            )

            session.add(skill)

        await session.flush()

        result = await session.execute(
            select(Skill)
            .options(selectinload(Skill.versions))
            .where(Skill.id.in_(skill_ids))
        )

        skills_by_id = {
            skill.id: skill
            for skill in result.scalars().all()
        }

        saved_skills = [
            skills_by_id[skill_id]
            for skill_id in skill_ids
            if skill_id in skills_by_id
        ]

        if len(saved_skills) != len(skill_ids):
            raise RuntimeError(
                "One or more saved skills could not be reloaded."
            )

        # Ensure the returned relationships are ordered explicitly.
        for skill in saved_skills:
            skill.versions.sort(key=lambda item: item.version)

        await session.commit()

        logger.info("Saved %d generated skill(s).", len(saved_skills))
        return saved_skills

    except IntegrityError as exc:
        await session.rollback()
        _cleanup_created_files(created_files, skills_root)

        logger.warning(
            "Could not save generated skills because of a database "
            "integrity conflict."
        )
        raise ValueError(
            "One or more skills conflict with existing database records."
        ) from exc

    except Exception:
        await session.rollback()
        _cleanup_created_files(created_files, skills_root)
        raise


def _cleanup_created_files(
    created_files: list[Path],
    skills_root: Path,
) -> None:
    """Remove files created by a failed database operation."""
    for file_path in created_files:
        try:
            resolved_path = file_path.resolve()
            resolved_path.relative_to(skills_root)

            if resolved_path.is_file():
                resolved_path.unlink()

        except (OSError, ValueError):
            logger.exception(
                "Could not clean up generated skill file: %s",
                file_path,
            )


async def get_skill_by_id(
    session: AsyncSession,
    skill_id: uuid.UUID,
) -> Skill | None:
    """Fetch a skill by ID, including its version records."""
    result = await session.execute(
        select(Skill)
        .options(selectinload(Skill.versions))
        .where(Skill.id == skill_id)
    )

    return result.scalars().first()


async def get_skill_by_name(
    session: AsyncSession,
    name: str,
) -> Skill | None:
    """Fetch a skill by exact name, including its versions."""
    result = await session.execute(
        select(Skill)
        .options(selectinload(Skill.versions))
        .where(Skill.name == name)
    )

    return result.scalars().first()


async def list_skills(
    session: AsyncSession,
) -> list[Skill]:
    """List all skills with versions, newest skills first."""
    result = await session.execute(
        select(Skill)
        .options(selectinload(Skill.versions))
        .order_by(Skill.created_at.desc())
    )

    skills = list(result.scalars().all())

    for skill in skills:
        skill.versions.sort(key=lambda item: item.version)

    return skills


async def get_skill_versions(
    session: AsyncSession,
    skill_id: uuid.UUID,
) -> list[SkillVersion]:
    """Retrieve skill versions in ascending version order."""
    result = await session.execute(
        select(SkillVersion)
        .where(SkillVersion.skill_id == skill_id)
        .order_by(SkillVersion.version.asc())
    )

    return list(result.scalars().all())


async def get_skill_version(
    session: AsyncSession,
    skill_id: uuid.UUID,
    version: int,
) -> SkillVersion | None:
    """Retrieve one specific version of a skill."""
    if version < 1:
        return None

    result = await session.execute(
        select(SkillVersion).where(
            SkillVersion.skill_id == skill_id,
            SkillVersion.version == version,
        )
    )

    return result.scalars().first()
