"""Database operations for policies and their versions."""

import json
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.policy_api import PolicySectionModel, PolicyValidationReport
from app.models.policy_db import Policy, PolicyVersion


async def create_policy(
    session: AsyncSession,
    title: str,
    domain: str,
    sections: list[PolicySectionModel],
    description: str | None = None,
    applied_skill_ids: list[str] | None = None,
    validation_status: str = "pending",
    validation_report: PolicyValidationReport | None = None,
    source_requirement_version_id: str | None = None,
    change_summary: str | None = "Initial policy draft generated from validated requirements.",
) -> Policy:
    """Create a new policy and its version 1 draft record."""

    policy_id = uuid.uuid4()
    policy = Policy(
        id=policy_id,
        title=title,
        description=description,
        domain=domain,
    )

    sections_json = json.dumps([s.model_dump() for s in sections], ensure_ascii=False)
    report_json = (
        validation_report.model_dump_json()
        if validation_report
        else "{}"
    )
    skills_json = json.dumps(applied_skill_ids or [], ensure_ascii=False)

    version_record = PolicyVersion(
        policy_id=policy_id,
        version=1,
        status="draft",
        content_json=sections_json,
        validation_status=validation_status,
        validation_report_json=report_json,
        source_requirement_version_id=source_requirement_version_id,
        applied_skill_ids_json=skills_json,
        change_summary=change_summary,
    )

    policy.versions.append(version_record)
    session.add(policy)
    await session.commit()

    return await get_policy_by_id(session, policy_id)  # type: ignore


async def create_policy_version(
    session: AsyncSession,
    policy_id: uuid.UUID,
    sections: list[PolicySectionModel],
    change_summary: str,
    validation_status: str = "pending",
    validation_report: PolicyValidationReport | None = None,
    source_requirement_version_id: str | None = None,
    applied_skill_ids: list[str] | None = None,
) -> PolicyVersion:
    """Create a new version record for an existing policy."""

    # Find highest existing version
    res = await session.execute(
        select(func.max(PolicyVersion.version)).where(PolicyVersion.policy_id == policy_id)
    )
    highest_v = res.scalar_one_or_none() or 0
    new_version_num = highest_v + 1

    sections_json = json.dumps([s.model_dump() for s in sections], ensure_ascii=False)
    report_json = (
        validation_report.model_dump_json()
        if validation_report
        else "{}"
    )
    skills_json = json.dumps(applied_skill_ids or [], ensure_ascii=False)

    new_version = PolicyVersion(
        policy_id=policy_id,
        version=new_version_num,
        status="draft",
        content_json=sections_json,
        validation_status=validation_status,
        validation_report_json=report_json,
        source_requirement_version_id=source_requirement_version_id,
        applied_skill_ids_json=skills_json,
        change_summary=change_summary,
    )

    session.add(new_version)
    await session.commit()
    await session.refresh(new_version)

    # Invalidate cached versions relationship on parent policy
    parent = await session.get(Policy, policy_id)
    if parent:
        session.expire(parent, ["versions"])

    return new_version


async def get_policy_by_id(
    session: AsyncSession,
    policy_id: uuid.UUID,
) -> Policy | None:
    """Fetch policy by ID with all version records."""
    res = await session.execute(
        select(Policy)
        .options(selectinload(Policy.versions))
        .where(Policy.id == policy_id)
        .execution_options(populate_existing=True)
    )
    return res.scalars().first()


async def list_policies(
    session: AsyncSession,
) -> list[Policy]:
    """List all policies with versions ordered by created date."""
    res = await session.execute(
        select(Policy)
        .options(selectinload(Policy.versions))
        .order_by(Policy.created_at.desc())
        .execution_options(populate_existing=True)
    )
    return list(res.scalars().all())


async def get_policy_version(
    session: AsyncSession,
    policy_id: uuid.UUID,
    version: int,
) -> PolicyVersion | None:
    """Fetch a specific version record for a policy."""
    res = await session.execute(
        select(PolicyVersion).where(
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.version == version,
        )
    )
    return res.scalars().first()


async def update_policy_version_status(
    session: AsyncSession,
    policy_id: uuid.UUID,
    version: int,
    new_status: str,
) -> PolicyVersion | None:
    """Update approval or review status of a policy version."""
    v = await get_policy_version(session, policy_id, version)
    if not v:
        return None

    v.status = new_status
    await session.commit()
    await session.refresh(v)
    return v
