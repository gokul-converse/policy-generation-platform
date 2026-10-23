"""FastAPI routes for enterprise policy generation, review, and approval."""

from uuid import UUID

from app.common.logger import get_logger
from app.db.session import get_db
from app.models.policy_api import (
    PolicyGenerationRequest,
    PolicyModificationRequest,
    PolicyResponse,
    PolicyVersionSummary,
)
from app.services import policy_service
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post(
    "/generate",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate enterprise policy draft",
    description=(
        "Generates a structured policy from validated requirements and "
        "selected Agent Skills, validates the draft, and saves a version."
    ),
)
async def generate_policy_endpoint(
    request: PolicyGenerationRequest,
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Generate and persist a new enterprise policy draft."""

    try:
        return await policy_service.generate_and_save_policy(
            session=session,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        logger.exception("Policy generation failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Policy generation failed due to an internal server error.",
        ) from None


@router.get(
    "",
    response_model=list[PolicyResponse],
    summary="List all policies",
    description="Returns all enterprise policies with their latest versions.",
)
async def list_policies_endpoint(
    session: AsyncSession = Depends(get_db),
) -> list[PolicyResponse]:
    """Retrieve all enterprise policies."""

    return await policy_service.list_all_policies(session)


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Get policy details",
    description=(
        "Returns the latest version of a policy or a requested historical version."
    ),
)
async def get_policy_endpoint(
    policy_id: UUID,
    version: int | None = Query(
        default=None,
        ge=1,
        description="Optional positive policy version number.",
    ),
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Fetch policy details."""

    policy = await policy_service.get_policy_detail(
        session=session,
        policy_id=policy_id,
        version=version,
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy or requested version not found.",
        )

    return policy


@router.post(
    "/{policy_id}/modify",
    response_model=PolicyResponse,
    summary="Modify policy",
    description=(
        "Edits policy content or revises a section, validates the result, "
        "and creates a new policy version."
    ),
)
async def modify_policy_endpoint(
    policy_id: UUID,
    request: PolicyModificationRequest,
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Revise or directly edit policy content."""

    try:
        return await policy_service.modify_policy_section(
            session=session,
            policy_id=policy_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        logger.exception(
            "Policy modification failed for policy %s.",
            policy_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Policy modification failed due to an internal server error.",
        ) from None


@router.get(
    "/{policy_id}/versions",
    response_model=list[PolicyVersionSummary],
    summary="List policy versions",
    description="Returns the version history for a policy.",
)
async def list_policy_versions_endpoint(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> list[PolicyVersionSummary]:
    """Retrieve policy version history."""

    policy = await policy_service.get_policy_detail(
        session=session,
        policy_id=policy_id,
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found.",
        )

    return await policy_service.get_policy_versions_list(
        session=session,
        policy_id=policy_id,
    )


@router.get(
    "/{policy_id}/versions/{version}",
    response_model=PolicyResponse,
    summary="Get specific policy version",
    description="Returns a particular historical version of a policy.",
)
async def get_policy_version_endpoint(
    policy_id: UUID,
    version: int,
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Fetch a specific policy version."""

    if version < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Version must be a positive integer.",
        )

    policy = await policy_service.get_policy_detail(
        session=session,
        policy_id=policy_id,
        version=version,
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy or requested version not found.",
        )

    return policy


@router.post(
    "/{policy_id}/versions/{version}/approve",
    response_model=PolicyResponse,
    summary="Approve policy version",
    description="Approves a specific policy version.",
)
async def approve_policy_version_endpoint(
    policy_id: UUID,
    version: int,
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Approve a specific policy version."""

    if version < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Version must be a positive integer.",
        )

    try:
        return await policy_service.approve_policy_version(
            session=session,
            policy_id=policy_id,
            version=version,
        )
    except ValueError as exc:
        # The service uses ValueError for a missing policy/version.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        logger.exception(
            "Approval failed for policy %s version %s.",
            policy_id,
            version,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Policy approval failed due to an internal server error.",
        ) from None


@router.get(
    "/{policy_id}/text",
    response_class=PlainTextResponse,
    summary="Get policy document text",
    description="Returns the formatted text for a policy version.",
)
async def get_policy_text_endpoint(
    policy_id: UUID,
    version: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_db),
) -> str:
    """Return the requested policy's formatted text."""

    # Verify that the requested policy exists before returning its text.
    policy = await policy_service.get_policy_detail(
        session=session,
        policy_id=policy_id,
        version=version,
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy or requested version not found.",
        )

    content = policy_service.get_policy_text_content(
        policy_id=policy_id,
        version=version or policy.version,
    )

    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy document text not found.",
        )

    return content
