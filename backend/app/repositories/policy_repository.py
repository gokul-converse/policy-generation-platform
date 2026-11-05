"""Database operations for policies and their versions."""

import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.policy_api import (
    PolicySectionModel,
    PolicyValidationReport,
)
from app.models.policy_db import Policy, PolicyVersion


async def create_policy(
    session: AsyncSession,
    title: str,
    domain: str,
    sections: list[PolicySectionModel],
    content_text: str,
    description: str | None = None,
    applied_skill_ids: list[str] | None = None,
    applied_skill_version_ids: list[str] | None = None,
    validation_status: str = "pending",
    validation_report: PolicyValidationReport | None = None,
    source_requirement_version_id: str | None = None,
    change_summary: str | None = (
        "Initial policy draft generated from validated requirements."
    ),
) -> Policy:
    """Create a policy and its first version in the current transaction."""

    policy = Policy(
        id=uuid.uuid4(),
        title=title,
        description=description,
        domain=domain,
        status="draft",
    )

    version_record = PolicyVersion(
        policy_id=policy.id,
        version=1,
        status="draft",
        content_json=json.dumps(
            [section.model_dump() for section in sections],
            ensure_ascii=False,
        ),
        content_text=content_text,
        validation_status=validation_status,
        validation_report_json=(
            validation_report.model_dump_json()
            if validation_report
            else "{}"
        ),
        source_requirement_version_id=source_requirement_version_id,
        applied_skill_ids_json=json.dumps(
            applied_skill_ids or [],
            ensure_ascii=False,
        ),
        applied_skill_version_ids_json=json.dumps(
            applied_skill_version_ids or [],
            ensure_ascii=False,
        ),
        change_summary=change_summary,
    )

    policy.versions.append(version_record)

    session.add(policy)
    await session.flush()

    return policy


async def create_policy_version(
    session: AsyncSession,
    policy_id: uuid.UUID,
    sections: list[PolicySectionModel],
    content_text: str,
    change_summary: str,
    validation_status: str = "pending",
    validation_report: PolicyValidationReport | None = None,
    source_requirement_version_id: str | None = None,
    applied_skill_ids: list[str] | None = None,
    applied_skill_version_ids: list[str] | None = None,
) -> PolicyVersion:
    """Create a new policy version in the current transaction."""

    result = await session.execute(
        select(func.max(PolicyVersion.version)).where(
            PolicyVersion.policy_id == policy_id
        )
    )

    highest_version = result.scalar_one_or_none() or 0
    next_version = highest_version + 1

    new_version = PolicyVersion(
        policy_id=policy_id,
        version=next_version,
        status="draft",
        content_json=json.dumps(
            [section.model_dump() for section in sections],
            ensure_ascii=False,
        ),
        content_text=content_text,
        validation_status=validation_status,
        validation_report_json=(
            validation_report.model_dump_json()
            if validation_report
            else "{}"
        ),
        source_requirement_version_id=source_requirement_version_id,
        applied_skill_ids_json=json.dumps(
            applied_skill_ids or [],
            ensure_ascii=False,
        ),
        applied_skill_version_ids_json=json.dumps(
            applied_skill_version_ids or [],
            ensure_ascii=False,
        ),
        change_summary=change_summary,
    )

    session.add(new_version)
    await session.flush()

    return new_version


async def get_policy_by_id(
    session: AsyncSession,
    policy_id: uuid.UUID,
) -> Policy | None:
    """Fetch a policy with its complete version history."""

    result = await session.execute(
        select(Policy)
        .options(selectinload(Policy.versions))
        .where(Policy.id == policy_id)
        .execution_options(populate_existing=True)
    )

    return result.scalars().first()


async def list_policies(
    session: AsyncSession,
    domain: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Policy]:
    """List policies with their complete version history."""

    query = (
        select(Policy)
        .options(selectinload(Policy.versions))
        .order_by(Policy.created_at.desc())
        .offset(offset)
        .execution_options(populate_existing=True)
    )

    if domain is not None:
        query = query.where(Policy.domain == domain)

    if limit is not None:
        query = query.limit(limit)

    result = await session.execute(query)

    return list(result.scalars().all())


async def get_policy_version(
    session: AsyncSession,
    policy_id: uuid.UUID,
    version: int,
) -> PolicyVersion | None:
    """Fetch a specific policy version."""

    result = await session.execute(
        select(PolicyVersion).where(
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.version == version,
        )
    )

    return result.scalars().first()


async def update_policy_version_status(
    session: AsyncSession,
    policy_id: uuid.UUID,
    version: int,
    new_status: str,
) -> PolicyVersion | None:
    """Update a policy version status within the current transaction."""

    version_record = await get_policy_version(
        session,
        policy_id,
        version,
    )

    if version_record is None:
        return None

    version_record.status = new_status

    await session.flush()

    return version_record


async def update_policy_status(
    session: AsyncSession,
    policy_id: uuid.UUID,
    new_status: str,
) -> Policy | None:
    """Update the overall policy lifecycle status."""

    policy = await get_policy_by_id(session, policy_id)

    if policy is None:
        return None

    policy.status = new_status

    await session.flush()

    return policy
