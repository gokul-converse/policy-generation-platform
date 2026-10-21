
"""API routes for skill generation."""

from app.common.logger import get_logger
from app.db.session import get_db
from app.models.skill_api import (
    SkillGenerationRequest,
    SkillGenerationResponse,
)
from app.services.skill_service import generate_and_save_skills
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/skills", tags=["Skills"])
logger = get_logger(__name__)


@router.post("/generate", response_model=SkillGenerationResponse)
async def generate_skills_endpoint(
    request: SkillGenerationRequest,
    session: AsyncSession = Depends(get_db),
) -> SkillGenerationResponse:
    """Generate skills from validated requirements and save them as drafts."""

    logger.info(
        "Received skill generation request with %d requirements.",
        len(request.requirements),
    )
    validated_requirements = {
        "requirements": [
            requirement.model_dump()
            for requirement in request.requirements
        ]
    }

    saved_skills = await generate_and_save_skills(
        session=session,
        validated_requirements=validated_requirements,
    )

    logger.info("Returning %d generated skills.", len(saved_skills))
    return SkillGenerationResponse(skills=saved_skills)
