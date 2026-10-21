
"""Database operations for skills and their versions."""

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.settings import settings
from app.models.skill_db import Skill, SkillVersion
from app.models.skills import GeneratedSkillSet
from app.services.skill_file_service import write_skill_file


async def save_skill_set(
    session: AsyncSession,
    skill_set: GeneratedSkillSet,
) -> list[Skill]:
    """Save generated skills as draft versions with Markdown files."""

    names = [skill.name for skill in skill_set.skills]

    if len(names) != len(set(names)):
        raise ValueError(
            "Skill names must be unique within a generated set."
        )

    if not skill_set.skills:
        return []

    skills_root = Path(settings.generated_skills_dir).resolve()
    created_files: list[Path] = []

    try:
        # Reject names that already exist in the database.
        result = await session.execute(
            select(Skill.name).where(Skill.name.in_(names))
        )
        existing_names = set(result.scalars().all())

        if existing_names:
            raise ValueError(
                f"Skills already exist: {sorted(existing_names)}"
            )

        # Write Markdown files and create matching database records.
        for generated_skill in skill_set.skills:
            skill_id = uuid.uuid4()

            relative_path = write_skill_file(
                generated_skill=generated_skill,
                skill_id=str(skill_id),
                version=1,
            )

            file_path = (skills_root / relative_path).resolve()

            if not file_path.is_relative_to(skills_root):
                raise ValueError(
                    "Skill file path escapes the skills directory."
                )

            created_files.append(file_path)

            skill = Skill(
                id=skill_id,
                name=generated_skill.name,
            )

            skill.versions.append(
                SkillVersion(
                    version=1,
                    file_path=relative_path,
                    status="draft",
                )
            )

            session.add(skill)

        await session.flush()

        # Reload persisted records with their versions.
        result = await session.execute(
            select(Skill)
            .options(selectinload(Skill.versions))
            .where(Skill.name.in_(names))
        )

        saved_skills = list(result.scalars().all())

        await session.commit()

        return saved_skills

    except Exception:
        await session.rollback()

        # Clean up files created by this failed operation.
        for file_path in created_files:
            try:
                if (
                    file_path.is_relative_to(skills_root)
                    and file_path.is_file()
                ):
                    file_path.unlink()
            except OSError:
                # Preserve the original exception.
                pass

        raise
