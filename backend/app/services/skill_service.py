
"""Application service for generating and saving draft skills."""

from app.common.logger import get_logger
from app.agents.policy_generation.skill_generation import generate_skills
from app.models.skills import GeneratedSkillSet
from app.repositories.skill_repository import save_skill_set
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


async def generate_and_save_skills(
    session: AsyncSession,
    validated_requirements: dict,
) -> list[dict]:
    """Generate draft skills and persist them with versioned Markdown files."""

    requirement_count = len(validated_requirements.get("requirements", []))
    logger.info(
        "Starting skill generation for %d validated requirements.",
        requirement_count,
    )

    # 1. Generate skills using the existing agent.
    skill_set: GeneratedSkillSet = await generate_skills(
        validated_requirements
    )
    logger.info("Generated %d draft skills.", len(skill_set.skills))

    # 2. Persist the complete generated set.
    saved_skills = await save_skill_set(session, skill_set)
    logger.info("Persisted %d draft skills.", len(saved_skills))

    # 3. Return stable IDs and version IDs to the caller.
    return [
        {
            "skill_id": skill.id,
            "name": skill.name,
            "version_id": skill.versions[0].id,
            "version": skill.versions[0].version,
            "status": skill.versions[0].status,
        }
        for skill in saved_skills
    ]
