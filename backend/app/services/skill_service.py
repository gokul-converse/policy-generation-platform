"""Application service for generating, saving, and retrieving draft skills."""

from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from app.agents.policy_generation.skill_generation import generate_skills
from app.common.logger import get_logger
from app.config.settings import settings
from app.models.skill_api import (
    SkillDetailResponse,
    SkillVersionDetail,
    SlashCommandItem,
)
from app.models.skills import GeneratedSkillSet
from app.repositories.skill_repository import (
    get_skill_by_id,
    get_skill_version,
    list_skills,
    save_skill_set,
)
from app.services.requirement_adapter import load_single_requirement
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


def read_skill_file_content(relative_path: str) -> str | None:
    """Safely read a skill Markdown file from the generated skills directory."""
    skills_root = settings.generated_skills_path.resolve()
    file_path = (skills_root / relative_path).resolve()

    # Prevent path traversal outside the generated skills directory.
    try:
        file_path.relative_to(skills_root)
    except ValueError:
        logger.warning(
            "Rejected skill path outside generated skills directory."
        )
        return None

    if not file_path.is_file():
        return None

    try:
        return file_path.read_text(encoding="utf-8")
    except OSError:
        logger.exception(
            "Could not read generated skill file: %s",
            relative_path,
        )
        return None


def get_builtin_skills() -> list[dict[str, str]]:
    """Scan backend/skills for built-in Agent Skills."""
    backend_root = Path(settings.BACKEND_ROOT).resolve()
    builtin_dir = backend_root / "skills"
    results: list[dict[str, str]] = []

    if not builtin_dir.is_dir():
        return results

    for item in sorted(
        builtin_dir.iterdir(),
        key=lambda path: path.name.casefold(),
    ):
        if not item.is_dir():
            continue

        skill_file = item / "SKILL.md"
        if not skill_file.is_file():
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")
            name = item.name
            description = ""

            if content.startswith("---"):
                parts = content.split("---", 2)

                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1]) or {}

                    if isinstance(frontmatter, dict):
                        frontmatter_name = frontmatter.get("name")
                        frontmatter_description = frontmatter.get(
                            "description",
                            "",
                        )

                        if (
                            isinstance(frontmatter_name, str)
                            and frontmatter_name.strip()
                        ):
                            name = frontmatter_name.strip()

                        if isinstance(frontmatter_description, str):
                            description = frontmatter_description.strip()

            results.append(
                {
                    "name": name,
                    "description": description,
                    "file_path": skill_file.relative_to(
                        backend_root
                    ).as_posix(),
                }
            )

        except (OSError, yaml.YAMLError, ValueError):
            logger.exception(
                "Could not read or parse built-in skill '%s'.",
                item.name,
            )

    return results


async def get_slash_commands(
    session: AsyncSession,
) -> list[SlashCommandItem]:
    """Return built-in and generated skills for the slash-command dropdown."""
    items: list[SlashCommandItem] = []
    seen_names: set[str] = set()

    # Built-in skills are discovered from the backend skills directory.
    for builtin in get_builtin_skills():
        name = builtin["name"]
        normalized_name = name.casefold()

        if normalized_name in seen_names:
            logger.warning(
                "Skipping duplicate built-in skill name '%s'.",
                name,
            )
            continue

        items.append(
            SlashCommandItem(
                command=f"/{name}",
                name=name,
                description=builtin["description"],
                skill_id=None,
                source="builtin",
            )
        )
        seen_names.add(normalized_name)

    # Generated skills are discovered from the database.
    db_skills = await list_skills(session)

    for skill in db_skills:
        normalized_name = skill.name.casefold()

        if normalized_name in seen_names:
            logger.warning(
                "Skipping duplicate slash-command name '%s'.",
                skill.name,
            )
            continue

        items.append(
            SlashCommandItem(
                command=f"/{skill.name}",
                name=skill.name,
                description=(
                    skill.description or f"Generated skill: {skill.name}"
                ),
                skill_id=skill.id,
                source="generated",
            )
        )
        seen_names.add(normalized_name)

    return items



async def generate_and_save_skills(
    session: AsyncSession,
    session_id: str,
    requirement_id: str,
    source_requirement_version_id: str | None = None,
) -> list[dict]:
    """Generate and save skills from one requirement in a session."""

    if not session_id or not session_id.strip():
        raise ValueError("A valid session_id is required.")

    if not requirement_id or not requirement_id.strip():
        raise ValueError("A valid requirement_id is required.")

    session_id = session_id.strip()
    requirement_id = requirement_id.strip()

    adapted, domain, original_description = await load_single_requirement(
        session=session,
        requirement_id=requirement_id,
        session_id=session_id,
    )

    if not adapted:
        raise ValueError(
            f"No valid requirement found for {requirement_id!r}."
        )

    logger.info(
        "Generating skills for requirement_id=%s in session_id=%s; "
        "domain=%s.",
        requirement_id,
        session_id,
        domain,
    )

    skill_set: GeneratedSkillSet = await generate_skills(adapted)

    saved_skills = await save_skill_set(
        session=session,
        skill_set=skill_set,
        source_requirement_version_id=source_requirement_version_id,
    )

    results: list[dict] = []

    for skill in saved_skills:
        if not skill.versions:
            logger.warning(
                "Saved skill '%s' has no version records.",
                skill.name,
            )
            continue

        version = max(
            skill.versions,
            key=lambda item: item.version,
        )

        results.append(
            {
                "skill_id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "version_id": version.id,
                "version": version.version,
                "status": version.status,
                "source_requirement_version_id": (
                    version.source_requirement_version_id
                ),
            }
        )

    return results


# Alias retained for compatibility with older callers.
save_generated_skills = generate_and_save_skills


async def get_skill_detail(
    session: AsyncSession,
    skill_id: UUID,
) -> SkillDetailResponse | None:
    """Retrieve a skill and its versions, including readable file content."""
    skill = await get_skill_by_id(session, skill_id)

    if not skill:
        return None

    versions_detail = [
        SkillVersionDetail(
            version_id=version.id,
            skill_id=version.skill_id,
            version=version.version,
            file_path=version.file_path,
            status=version.status,
            created_at=version.created_at,
            source_requirement_version_id=(
                version.source_requirement_version_id
            ),
            content=read_skill_file_content(version.file_path),
        )
        for version in sorted(
            skill.versions,
            key=lambda item: item.version,
            reverse=True,
        )
    ]

    return SkillDetailResponse(
        skill_id=skill.id,
        name=skill.name,
        description=skill.description,
        created_at=skill.created_at,
        versions=versions_detail,
    )


async def list_all_skills(
    session: AsyncSession,
    limit: int | None = None,
    offset: int = 0,
) -> list[SkillDetailResponse]:
    """Retrieve skills and their version metadata."""
    skills = await list_skills(session, limit=limit, offset=offset)
    results: list[SkillDetailResponse] = []

    for skill in skills:
        versions_detail = [
            SkillVersionDetail(
                version_id=version.id,
                skill_id=version.skill_id,
                version=version.version,
                file_path=version.file_path,
                status=version.status,
                created_at=version.created_at,
                source_requirement_version_id=(
                    version.source_requirement_version_id
                ),
                content=None,
            )
            for version in sorted(
                skill.versions,
                key=lambda item: item.version,
                reverse=True,
            )
        ]

        results.append(
            SkillDetailResponse(
                skill_id=skill.id,
                name=skill.name,
                description=skill.description,
                created_at=skill.created_at,
                versions=versions_detail,
            )
        )

    return results


async def get_skill_version_detail(
    session: AsyncSession,
    skill_id: UUID,
    version: int,
) -> SkillVersionDetail | None:
    """Retrieve one skill version, including its Markdown content."""
    if version < 1:
        raise ValueError("Skill version must be greater than or equal to 1.")

    skill_version = await get_skill_version(
        session,
        skill_id,
        version,
    )

    if not skill_version:
        return None

    return SkillVersionDetail(
        version_id=skill_version.id,
        skill_id=skill_version.skill_id,
        version=skill_version.version,
        file_path=skill_version.file_path,
        status=skill_version.status,
        created_at=skill_version.created_at,
        source_requirement_version_id=(
            skill_version.source_requirement_version_id
        ),
        content=read_skill_file_content(skill_version.file_path),
    )
