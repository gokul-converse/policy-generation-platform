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



async def create_skill_version_from_content(
    session: AsyncSession,
    skill_id: uuid.UUID,
    base_skill_version_id: uuid.UUID,
    content: str,
) -> SkillVersion:
    """
    Create a new skill version using modified content.

    The original skill version remains unchanged.
    Requirement-version lineage is preserved from the selected base version.
    """

    if not content or not content.strip():
        raise ValueError("Modified skill content cannot be empty.")

    # 1. Retrieve the exact base skill version.
    base_version = await session.scalar(
        select(SkillVersion).where(
            SkillVersion.id == base_skill_version_id,
            SkillVersion.skill_id == skill_id,
        )
    )

    if base_version is None:
        raise ValueError(
            "The selected base skill version does not exist "
            "for the supplied skill."
        )

    # 2. Find the latest version number for this skill.
    latest_version = await session.scalar(
        select(func.max(SkillVersion.version)).where(
            SkillVersion.skill_id == skill_id
        )
    )

    next_version_number = (latest_version or 0) + 1

    # 3. Create a new version without modifying the original.
    new_version = SkillVersion(
        skill_id=skill_id,
        version=next_version_number,
        content=content,
        status="draft",
        source_requirement_version_id=(
            base_version.source_requirement_version_id
        ),
    )

    session.add(new_version)

    # 4. Persist the new row within the current transaction.
    await session.flush()

    logger.info(
        "Created skill version. Skill ID=%s, "
        "Base version ID=%s, New version ID=%s, Version=%s",
        skill_id,
        base_skill_version_id,
        new_version.id,
        new_version.version,
    )

    return new_version


async def activate_skill_version(
    session: AsyncSession,
    skill_id: uuid.UUID,
    skill_version_id: uuid.UUID,
) -> SkillVersion | None:
    """Activate a skill version and supersede the previously active version."""

    result = await session.execute(
        select(Skill)
        .options(selectinload(Skill.versions))
        .where(Skill.id == skill_id)
    )

    skill = result.scalar_one_or_none()

    if skill is None:
        return None

    target_version = next(
        (
            item
            for item in skill.versions
            if item.id == skill_version_id
        ),
        None,
    )

    if target_version is None:
        return None

    for version_record in skill.versions:
        if (
            version_record.id != target_version.id
            and version_record.status == "active"
        ):
            version_record.status = "superseded"

    target_version.status = "active"

    await session.flush()

    return target_version
