"""API routes for skill generation, management, and slash-command flow."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logger import get_logger
from app.db.session import get_db
from app.models.skill_api import (
    SkillDetailResponse,
    SkillGenerationRequest,
    SkillGenerationResponse,
    SkillVersionDetail,
    SlashCommandItem,
)
from app.services.skill_service import (
    generate_and_save_skills,
    get_skill_detail,
    get_skill_version_detail,
    get_slash_commands,
    list_all_skills,
)

router = APIRouter(prefix="/skills", tags=["Skills"])
logger = get_logger(__name__)


@router.get(
    "/slash-commands",
    response_model=list[SlashCommandItem],
    summary="List available skills for the Claude-like slash-command (/) dropdown",
)
async def list_slash_commands_endpoint(
    session: AsyncSession = Depends(get_db),
) -> list[SlashCommandItem]:
    """Return all skills available for chat / forward-slash autocomplete."""
    return await get_slash_commands(session)


@router.post(
    "/generate",
    response_model=SkillGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_skills_endpoint(
    request: SkillGenerationRequest,
    session: AsyncSession = Depends(get_db),
) -> SkillGenerationResponse:
    """Generate skills from validated requirements and save them as drafts."""

    req_count = len(request.requirements) if request.requirements else 0
    logger.info(
        "Received skill generation request with %d requirements (session_id=%s).",
        req_count,
        request.session_id,
    )

    try:
        saved_skills = await generate_and_save_skills(
            session=session,
            validated_requirements=request.requirements,
            session_id=request.session_id,
            source_requirement_version_id=request.source_requirement_version_id,
        )

        logger.info("Returning %d generated skills.", len(saved_skills))
        return SkillGenerationResponse(skills=saved_skills)

    except ValueError as exc:
        logger.warning("Skill generation failed validation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error during skill generation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Skill generation failed due to an internal error.",
        )


@router.get(
    "",
    response_model=list[SkillDetailResponse],
)
async def list_skills_endpoint(
    session: AsyncSession = Depends(get_db),
) -> list[SkillDetailResponse]:
    """List all persisted skills and their versions."""
    return await list_all_skills(session)


@router.get(
    "/{skill_id}",
    response_model=SkillDetailResponse,
)
async def get_skill_endpoint(
    skill_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> SkillDetailResponse:
    """Retrieve full details of a specific skill."""
    skill = await get_skill_detail(session, skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill with ID {skill_id} not found.",
        )
    return skill


@router.get(
    "/{skill_id}/versions",
    response_model=list[SkillVersionDetail],
)
async def get_skill_versions_endpoint(
    skill_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> list[SkillVersionDetail]:
    """Retrieve all versions of a specific skill."""
    skill = await get_skill_detail(session, skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill with ID {skill_id} not found.",
        )
    return skill.versions


@router.get(
    "/{skill_id}/versions/{version}",
    response_model=SkillVersionDetail,
)
async def get_skill_version_endpoint(
    skill_id: UUID,
    version: int,
    session: AsyncSession = Depends(get_db),
) -> SkillVersionDetail:
    """Retrieve a specific version of a skill including file content."""
    version_detail = await get_skill_version_detail(session, skill_id, version)
    if not version_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} for skill ID {skill_id} not found.",
        )
    return version_detail
