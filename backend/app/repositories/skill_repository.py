"""Database operations for skills and their versions."""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.skill_db import Skill, SkillVersion
from app.models.skills import GeneratedSkillSet
from app.services.skill_file_service import build_skill_markdown

logger = logging.getLogger(__name__)


async def save_skill_set(
    session: AsyncSession,
    skill_set: GeneratedSkillSet,
    source_requirement_version_id: str | None = None,
) -> list[Skill]:
    """Save generated skills and their initial draft versions."""

    generated_skills = skill_set.skills

    if not generated_skills:
        raise ValueError(
            "Cannot save an empty generated skill set."
        )

    names = [skill.name.strip() for skill in generated_skills]
    normalized_names = [name.casefold() for name in names]

    if any(not name for name in names):
        raise ValueError("Skill names must not be empty.")

    if len(normalized_names) != len(set(normalized_names)):
        raise ValueError(
            "Skill names must be unique within a generated set."
        )

    try:
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

        skill_ids: list[uuid.UUID] = []

        for generated_skill in generated_skills:
            skill_id = uuid.uuid4()
            skill_ids.append(skill_id)

            content = build_skill_markdown(generated_skill)

            skill = Skill(
                id=skill_id,
                name=generated_skill.name.strip(),
                description=generated_skill.description,
            )

            skill.versions.append(
                SkillVersion(
                    version=1,
                    content=content,
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

        for skill in saved_skills:
            skill.versions.sort(key=lambda item: item.version)

            if not skill.versions:
                raise RuntimeError(
                    f"Saved skill '{skill.name}' has no version records."
                )

        await session.commit()

        logger.info(
            "Saved %d generated skill(s) in the database.",
            len(saved_skills),
        )

        return saved_skills

    except IntegrityError as exc:
        await session.rollback()

        logger.warning(
            "Could not save generated skills because of a database "
            "integrity conflict."
        )

        raise ValueError(
            "One or more skills conflict with existing database records."
        ) from exc

    except Exception:
        await session.rollback()
        raise

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
    """Fetch a skill by name, ignoring capitalization."""

    result = await session.execute(
        select(Skill)
        .options(selectinload(Skill.versions))
        .where(func.lower(Skill.name) == name.strip().lower())
    )

    return result.scalars().first()


async def list_skills(
    session: AsyncSession,
    limit: int | None = None,
    offset: int = 0,
) -> list[Skill]:
    """List skills with their complete version history."""

    query = (
        select(Skill)
        .options(selectinload(Skill.versions))
        .order_by(Skill.created_at.desc())
        .offset(offset)
    )

    if limit is not None:
        query = query.limit(limit)

    result = await session.execute(query)

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


async def create_next_skill_version(
    session: AsyncSession,
    skill_id: uuid.UUID,
) -> SkillVersion:
    """Create a new draft version using the previous version's content."""

    result = await session.execute(
        select(Skill)
        .options(selectinload(Skill.versions))
        .where(Skill.id == skill_id)
    )

    skill = result.scalar_one_or_none()

    if skill is None or not skill.versions:
        raise ValueError(
            f"Skill {skill_id} not found or has no versions."
        )

    latest = max(skill.versions, key=lambda item: item.version)

    if not latest.content:
        raise ValueError(
            "The latest skill version has no stored content."
        )

    next_version = latest.version + 1

    new_version = SkillVersion(
        skill_id=skill.id,
        version=next_version,
        content=latest.content,
        status="draft",
        source_requirement_version_id=(
            latest.source_requirement_version_id
        ),
    )

    session.add(new_version)
    await session.flush()

    return new_version
