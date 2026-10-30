"""API routes for skill generation, management, and slash commands."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
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
from app.repositories.skill_repository import get_skill_by_id
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
    summary="List available skills for slash-command autocomplete",
    description=(
        "Returns built-in and persisted generated skills available "
        "through the forward-slash command interface."
    ),
)
async def list_slash_commands_endpoint(
    session: AsyncSession = Depends(get_db),
) -> list[SlashCommandItem]:
    """Return available skills for slash-command autocomplete."""
    try:
        return await get_slash_commands(session)
    except Exception:
        logger.exception("Failed to load slash commands.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load available skills.",
        ) from None


@router.post(
    "/generate",
    response_model=SkillGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate skills from one confirmed requirement",
)
async def generate_skills_endpoint(
    request: SkillGenerationRequest,
    session: AsyncSession = Depends(get_db),
) -> SkillGenerationResponse:
    """Generate skills from one requirement in a specified session."""

    logger.info(
        "Received skill generation request for requirement_id=%s, "
        "session_id=%s.",
        request.requirement_id,
        request.session_id,
    )

    try:
        saved_skills = await generate_and_save_skills(
            session=session,
            requirement_id=request.requirement_id,
            session_id=request.session_id,
            source_requirement_version_id=(
                request.source_requirement_version_id
            ),
        )

        return SkillGenerationResponse(skills=saved_skills)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Skill generation failed for requirement_id=%s.",
            request.requirement_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Skill generation failed due to an internal error.",
        ) from None

@router.get(
    "",
    response_model=list[SkillDetailResponse],
    summary="List generated skills",
)
async def list_skills_endpoint(
    session: AsyncSession = Depends(get_db),
    limit: int = Query(
    default=50,
    ge=1,
    le=200,
    description=(
        "Maximum number of skills to return. "
        "Optional; defaults to 50. Allowed range: 1–200."
    ),
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description=(
            "Number of skills to skip before returning results. "
            "Optional; defaults to 0."
        ),
    ),
) -> list[SkillDetailResponse]:
    """List persisted skills and their version metadata."""
    try:
        return await list_all_skills(session, limit=limit, offset=offset)
    except Exception:
        logger.exception("Failed to list generated skills.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve skills.",
        ) from None


@router.get(
    "/{skill_id}",
    response_model=SkillDetailResponse,
    summary="Get skill details",
)
async def get_skill_endpoint(
    skill_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> SkillDetailResponse:
    """Retrieve details of a specific skill."""
    try:
        skill = await get_skill_detail(session, skill_id)
    except Exception:
        logger.exception("Failed to retrieve skill %s.", skill_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve the requested skill.",
        ) from None

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill with ID {skill_id} not found.",
        )

    return skill


@router.get(
    "/{skill_id}/versions",
    response_model=list[SkillVersionDetail],
    summary="List skill versions",
)
async def get_skill_versions_endpoint(
    skill_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> list[SkillVersionDetail]:
    """Retrieve version metadata for a specific skill."""
    try:
        skill = await get_skill_by_id(session, skill_id)
    except Exception:
        logger.exception(
            "Failed to retrieve versions for skill %s.",
            skill_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve skill versions.",
        ) from None

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill with ID {skill_id} not found.",
        )

    return [
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


@router.get(
    "/{skill_id}/versions/{version}",
    response_model=SkillVersionDetail,
    summary="Get a specific skill version",
)
async def get_skill_version_endpoint(
    skill_id: UUID,
    version: int = Path(
    ge=1,
    description="Positive, one-based skill version number.",
    ),
    session: AsyncSession = Depends(get_db),
) -> SkillVersionDetail:
    """Retrieve one skill version, including its Markdown content."""
    try:
        version_detail = await get_skill_version_detail(
            session=session,
            skill_id=skill_id,
            version=version,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception:
        logger.exception(
            "Failed to retrieve skill %s version %s.",
            skill_id,
            version,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve the requested skill version.",
        ) from None

    if version_detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Version {version} for skill ID {skill_id} not found."
            ),
        )

    return version_detail
