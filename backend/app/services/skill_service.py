"""Application service for generating, saving, and retrieving draft skills."""

from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.policy_generation.skill_generation import generate_skills
from app.common.logger import get_logger
from app.config.settings import settings
from app.models.skill_api import SkillDetailResponse, SkillVersionDetail, SlashCommandItem
from app.models.skills import GeneratedSkillSet
from app.repositories.skill_repository import (
    get_skill_by_id,
    get_skill_by_name,
    get_skill_version,
    get_skill_versions,
    list_skills,
    save_skill_set,
)
from app.services.requirement_adapter import adapt_requirements, load_requirements_from_session

logger = get_logger(__name__)


def read_skill_file_content(relative_path: str) -> str | None:
    """Safely read skill markdown file content."""
    skills_root = Path(settings.generated_skills_dir).resolve()
    file_path = (skills_root / relative_path).resolve()
    if file_path.is_relative_to(skills_root) and file_path.is_file():
        return file_path.read_text(encoding="utf-8")
    return None


def get_builtin_skills() -> list[dict[str, str]]:
    """Scan backend/skills directory for pre-installed Agent Skills."""
    builtin_dir = settings.BACKEND_ROOT / "skills"
    results = []

    if not builtin_dir.is_dir():
        return results

    for item in builtin_dir.iterdir():
        skill_file = item / "SKILL.md"
        if item.is_dir() and skill_file.is_file():
            try:
                text = skill_file.read_text(encoding="utf-8")
                name = item.name
                desc = ""
                if text.startswith("---"):
                    parts = text.split("---", 2)
                    if len(parts) >= 3:
                        fm = yaml.safe_load(parts[1]) or {}
                        name = fm.get("name", name)
                        desc = fm.get("description", "")
                results.append({
                    "name": name,
                    "description": desc,
                    "file_path": str(skill_file.relative_to(settings.BACKEND_ROOT).as_posix()),
                })
            except Exception as exc:
                logger.warning("Could not parse builtin skill %s: %s", item.name, exc)

    return results


async def get_slash_commands(
    session: AsyncSession,
) -> list[SlashCommandItem]:
    """Return all available skills formatted for the Claude-like slash-command (/) dropdown."""

    items: list[SlashCommandItem] = []
    seen_names: set[str] = set()

    # 1. Built-in skills (e.g. company-policy-generator, skill-creator)
    for builtin in get_builtin_skills():
        name = builtin["name"]
        cmd = f"/{name}"
        items.append(
            SlashCommandItem(
                command=cmd,
                name=name,
                description=builtin["description"],
                skill_id=None,
                source="builtin",
            )
        )
        seen_names.add(name)

    # 2. Persisted / dynamically generated skills in database
    db_skills = await list_skills(session)
    for skill in db_skills:
        if skill.name not in seen_names:
            items.append(
                SlashCommandItem(
                    command=f"/{skill.name}",
                    name=skill.name,
                    description=skill.description or f"Generated skill: {skill.name}",
                    skill_id=skill.id,
                    source="generated",
                )
            )
            seen_names.add(skill.name)

    return items


async def generate_and_save_skills(
    session: AsyncSession,
    validated_requirements: dict | list | Any = None,
    session_id: str | None = None,
    source_requirement_version_id: str | None = None,
) -> list[dict]:
    """Generate draft skills and persist them with versioned Markdown files."""

    if session_id and not validated_requirements:
        adapted, domain, orig_desc = await load_requirements_from_session(session, session_id)
        source_version = source_requirement_version_id or session_id
    elif validated_requirements:
        adapted = adapt_requirements(validated_requirements)
        source_version = source_requirement_version_id
    else:
        raise ValueError("Either 'requirements' or 'session_id' must be provided.")

    logger.info(
        "Starting skill generation for %d validated requirements (source_version=%s).",
        len(adapted),
        source_version,
    )

    # 1. Generate skills using the agent.
    skill_set: GeneratedSkillSet = await generate_skills(adapted)
    logger.info("Generated %d draft skills.", len(skill_set.skills))

    # 2. Persist the complete generated set with provenance.
    saved_skills = await save_skill_set(
        session,
        skill_set,
        source_requirement_version_id=source_version,
    )
    logger.info("Persisted %d draft skills.", len(saved_skills))

    # 3. Return stable IDs, names, descriptions, and version IDs to the caller.
    return [
        {
            "skill_id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "version_id": skill.versions[0].id,
            "version": skill.versions[0].version,
            "status": skill.versions[0].status,
            "source_requirement_version_id": skill.versions[0].source_requirement_version_id,
        }
        for skill in saved_skills
    ]


# Alias for legacy compatibility
save_generated_skills = generate_and_save_skills


async def get_skill_detail(
    session: AsyncSession,
    skill_id: UUID,
) -> SkillDetailResponse | None:
    """Retrieve full detail of a skill including versions and file content."""
    skill = await get_skill_by_id(session, skill_id)
    if not skill:
        return None

    versions_detail = [
        SkillVersionDetail(
            version_id=v.id,
            skill_id=v.skill_id,
            version=v.version,
            file_path=v.file_path,
            status=v.status,
            created_at=v.created_at,
            source_requirement_version_id=v.source_requirement_version_id,
            content=read_skill_file_content(v.file_path),
        )
        for v in skill.versions
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
) -> list[SkillDetailResponse]:
    """Retrieve all skills with their versions."""
    skills = await list_skills(session)
    result = []
    for skill in skills:
        versions_detail = [
            SkillVersionDetail(
                version_id=v.id,
                skill_id=v.skill_id,
                version=v.version,
                file_path=v.file_path,
                status=v.status,
                created_at=v.created_at,
                source_requirement_version_id=v.source_requirement_version_id,
                content=None,
            )
            for v in skill.versions
        ]
        result.append(
            SkillDetailResponse(
                skill_id=skill.id,
                name=skill.name,
                description=skill.description,
                created_at=skill.created_at,
                versions=versions_detail,
            )
        )
    return result


async def get_skill_version_detail(
    session: AsyncSession,
    skill_id: UUID,
    version: int,
) -> SkillVersionDetail | None:
    """Retrieve a specific version of a skill with content."""
    v = await get_skill_version(session, skill_id, version)
    if not v:
        return None

    return SkillVersionDetail(
        version_id=v.id,
        skill_id=v.skill_id,
        version=v.version,
        file_path=v.file_path,
        status=v.status,
        created_at=v.created_at,
        source_requirement_version_id=v.source_requirement_version_id,
        content=read_skill_file_content(v.file_path),
    )
