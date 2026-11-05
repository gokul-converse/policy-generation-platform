"""Services for generating, saving, and retrieving skills."""

from pathlib import Path
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



def get_builtin_skills() -> list[dict[str, str]]:
    """Discover built-in skills from the backend skills directory."""
    backend_root = Path(settings.BACKEND_ROOT).resolve()
    builtin_directory = backend_root / "skills"

    results: list[dict[str, str]] = []

    if not builtin_directory.is_dir():
        return results

    for skill_directory in sorted(
        builtin_directory.iterdir(),
        key=lambda path: path.name.casefold(),
    ):
        if not skill_directory.is_dir():
            continue

        skill_file = skill_directory / "SKILL.md"

        if not skill_file.is_file():
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")

            name = skill_directory.name
            description = ""

            # Read optional YAML frontmatter.
            if content.startswith("---"):
                parts = content.split("---", 2)

                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1]) or {}

                    if isinstance(frontmatter, dict):
                        frontmatter_name = frontmatter.get("name")
                        frontmatter_description = frontmatter.get(
                            "description", ""
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
                skill_directory.name,
            )

    return results


async def get_slash_commands(
    session: AsyncSession,
) -> list[SlashCommandItem]:
    """Return built-in and generated skills for the slash-command dropdown."""
    items: list[SlashCommandItem] = []
    seen_names: set[str] = set()

    # Add built-in skills.
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

    # Add generated skills from the database.
    database_skills = await list_skills(session)

    for skill in database_skills:
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
    """Generate skills from a confirmed requirement and save them."""

    # Validate the identifiers.
    if not session_id or not session_id.strip():
        raise ValueError("A valid session_id is required.")

    if not requirement_id or not requirement_id.strip():
        raise ValueError("A valid requirement_id is required.")

    session_id = session_id.strip()
    requirement_id = requirement_id.strip()

    # Load the requirement from requirement_versions.requirements_json.
    # The adapter verifies the session, requirement, and snapshot status.
    requirements, domain, _purpose = await load_single_requirement(
        session=session,
        requirement_id=requirement_id,
        session_id=session_id,
        source_requirement_version_id=source_requirement_version_id,
    )

    if not requirements:
        raise ValueError(
            f"No confirmed requirement found for {requirement_id!r}."
        )

    # Keep the exact version used to generate the skills.
    loaded_version_id = requirements[0].source_version_id

    if not loaded_version_id:
        raise ValueError(
            "The confirmed requirement version ID is missing. "
            "Cannot save skills without source version traceability."
        )

    logger.info(
        "Generating skills for requirement_id=%s, session_id=%s, "
        "source_version_id=%s, domain=%s.",
        requirement_id,
        session_id,
        loaded_version_id,
        domain,
    )

    # Generate skills using the complete confirmed requirement JSON.
    try:
        skill_set: GeneratedSkillSet = await generate_skills(requirements)
    except Exception:
        logger.exception(
            "Skill generation failed for requirement_id=%s, session_id=%s.",
            requirement_id,
            session_id,
        )
        raise

    # Save skills with the exact confirmed requirement version.
    try:
        saved_skills = await save_skill_set(
            session=session,
            skill_set=skill_set,
            source_requirement_version_id=loaded_version_id,
        )
    except Exception:
        logger.exception(
            "Saving generated skills failed for requirement_id=%s, "
            "session_id=%s.",
            requirement_id,
            session_id,
        )
        raise

    # Build the API response.
    results: list[dict] = []

    for skill in saved_skills:
        if not skill.versions:
            logger.warning(
                "Saved skill '%s' has no version records.",
                skill.name,
            )
            continue

        latest_version = max(
            skill.versions,
            key=lambda item: item.version,
        )

        results.append(
            {
                "skill_id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "version_id": latest_version.id,
                "version": latest_version.version,
                "status": latest_version.status,
                "source_requirement_version_id": (
                    latest_version.source_requirement_version_id
                ),
            }
        )

    return results


# Keep the previous function name for existing callers.
save_generated_skills = generate_and_save_skills


async def get_skill_detail(
    session: AsyncSession,
    skill_id: UUID,
) -> SkillDetailResponse | None:
    """Retrieve a skill and all its versions from the database."""

    skill = await get_skill_by_id(session, skill_id)

    if not skill:
        return None

    versions_detail = [
        SkillVersionDetail(
            version_id=version.id,
            skill_id=version.skill_id,
            version=version.version,
            status=version.status,
            created_at=version.created_at,
            source_requirement_version_id=(
                version.source_requirement_version_id
            ),
            content=version.content,
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
    """Retrieve all skills with their version metadata."""

    skills = await list_skills(
        session,
        limit=limit,
        offset=offset,
    )

    results: list[SkillDetailResponse] = []

    for skill in skills:
        versions_detail = [
            SkillVersionDetail(
                version_id=version.id,
                skill_id=version.skill_id,
                version=version.version,
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
    """Retrieve a specific skill version with its database content."""

    if version < 1:
        raise ValueError(
            "Skill version must be greater than or equal to 1."
        )

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
        status=skill_version.status,
        created_at=skill_version.created_at,
        source_requirement_version_id=(
            skill_version.source_requirement_version_id
        ),
        content=skill_version.content,
    )