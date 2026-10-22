"""FastAPI route definitions for enterprise policy generation, review, and approval."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.policy_api import (
    PolicyGenerationRequest,
    PolicyModificationRequest,
    PolicyResponse,
    PolicyVersionSummary,
)
from app.services import policy_service

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post(
    "/generate",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate enterprise policy draft",
    description="Drafts a structured policy from validated requirements and Agent Skills, validates deterministically, and saves to database and data/policy.txt.",
)
async def generate_policy_endpoint(
    request: PolicyGenerationRequest,
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Generate a new enterprise policy draft."""
    try:
        return await policy_service.generate_and_save_policy(
            session=session,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy generation failed: {exc}",
        )


@router.get(
    "",
    response_model=list[PolicyResponse],
    summary="List all policies",
    description="Returns all enterprise policies with their current version details.",
)
async def list_policies_endpoint(
    session: AsyncSession = Depends(get_db),
) -> list[PolicyResponse]:
    """Retrieve all enterprise policies."""
    return await policy_service.list_all_policies(session)


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Get policy detail",
    description="Fetch a policy by ID, returning its latest version or specified version.",
)
async def get_policy_endpoint(
    policy_id: UUID,
    version: int | None = Query(default=None, description="Optional version number to retrieve"),
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
            detail=f"Policy {policy_id} not found.",
        )
    return policy


@router.post(
    "/{policy_id}/modify",
    response_model=PolicyResponse,
    summary="Modify policy section",
    description="Modifies an existing policy section, validates the change, creates a new version record, and updates data/policy.txt.",
)
async def modify_policy_endpoint(
    policy_id: UUID,
    request: PolicyModificationRequest,
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Revise or edit a policy section."""
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
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy modification failed: {exc}",
        )


@router.get(
    "/{policy_id}/versions",
    response_model=list[PolicyVersionSummary],
    summary="List policy versions",
    description="Retrieve the complete version history for a policy.",
)
async def list_policy_versions_endpoint(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> list[PolicyVersionSummary]:
    """Get policy version history."""
    return await policy_service.get_policy_versions_list(
        session=session,
        policy_id=policy_id,
    )


@router.get(
    "/{policy_id}/versions/{version}",
    response_model=PolicyResponse,
    summary="Get specific policy version",
    description="Retrieve a historical version of a policy.",
)
async def get_policy_version_endpoint(
    policy_id: UUID,
    version: int,
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Fetch specific policy version."""
    policy = await policy_service.get_policy_detail(
        session=session,
        policy_id=policy_id,
        version=version,
    )
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} of policy {policy_id} not found.",
        )
    return policy


@router.post(
    "/{policy_id}/versions/{version}/approve",
    response_model=PolicyResponse,
    summary="Approve policy version",
    description="Approves a policy draft version, updating its status to 'approved' and marking data/policy.txt as approved.",
)
async def approve_policy_version_endpoint(
    policy_id: UUID,
    version: int,
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Approve a policy version."""
    try:
        return await policy_service.approve_policy_version(
            session=session,
            policy_id=policy_id,
            version=version,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{policy_id}/text",
    response_class=PlainTextResponse,
    summary="Get raw policy document text",
    description="Returns the full formatted plain text of data/policy.txt for download or UI display.",
)
async def get_policy_text_endpoint(
    policy_id: UUID,
    version: int | None = Query(default=None),
) -> str:
    """Return raw text document content."""
    content = policy_service.get_policy_text_content(policy_id=policy_id, version=version)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy document text not found.",
        )
    return content
