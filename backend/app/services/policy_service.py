"""Application service for generating, validating, persisting, and modifying enterprise policies."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.agents.policy_generation.policy_generator import (
    StructuredPolicyGenerationOutput,
    generate_policy_from_requirements,
    revise_policy_section_agent,
)
from app.common.logger import get_logger
from app.config.settings import settings
from app.models.policy_api import (
    PolicyGenerationRequest,
    PolicyModificationRequest,
    PolicyResponse,
    PolicySectionModel,
    PolicyValidationReport,
    PolicyVersionSummary,
)
from app.models.policy_db import Policy, PolicyVersion
from app.models.skill_api import ValidatedRequirementInput
from app.repositories import policy_repository
from app.repositories.skill_repository import (
    get_skill_by_id,
    get_skill_by_name,
)
from app.services.requirement_adapter import (
    adapt_requirements,
    load_requirements_from_session,
    load_single_requirement,
)
from app.services.validation_service import validate_policy_draft
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


def format_policy_document_text(
    title: str,
    domain: str,
    version: int,
    sections: list[PolicySectionModel],
    description: str | None = None,
    status: str = "draft",
) -> str:
    """Format structured policy sections into an enterprise text document."""

    lines: list[str] = [
        "=" * 80,
        f"ENTERPRISE POLICY: {title.upper()}",
        f"Domain: {domain} | Version: {version} | Status: {status.upper()}",
        "=" * 80,
        "",
    ]

    if description:
        lines.extend(
            [
                "## Executive Summary",
                description.strip(),
                "",
            ]
        )

    lines.append("## Table of Contents")

    for i, sec in enumerate(sections, start=1):
        lines.append(f"{i}. {sec.title}")

    lines.append("")

    for i, sec in enumerate(sections, start=1):
        lines.extend(
            [
                "-" * 80,
                f"Section {i}: {sec.title} [{sec.section_id}]",
                "-" * 80,
                sec.content.strip(),
                "",
            ]
        )

        if sec.requirement_ids:
            lines.append(
                f"Traceable Requirements: {', '.join(sec.requirement_ids)}"
            )
            lines.append("")

    lines.extend(
        [
            "=" * 80,
            "END OF POLICY DOCUMENT",
            "=" * 80,
        ]
    )

    return "\n".join(lines)


def save_policy_document_to_file(
    policy_id: UUID,
    version: int,
    content_text: str,
) -> str:
    """Write the current policy and a versioned archive to disk."""

    data_dir = settings.BACKEND_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    policies_dir = data_dir / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)

    primary_file = data_dir / "policy.txt"
    primary_file.write_text(content_text, encoding="utf-8")

    versioned_file = policies_dir / f"{policy_id}_v{version}.txt"
    versioned_file.write_text(content_text, encoding="utf-8")

    logger.info(
        "Saved policy to %s and %s",
        primary_file,
        versioned_file,
    )

    return "data/policy.txt"


async def load_skill_instructions(
    session: AsyncSession,
    skill_command: str | None,
    skill_ids: list[UUID],
) -> tuple[str, list[str]]:
    """Resolve explicitly selected built-in and generated skills."""

    applied_identifiers: list[str] = []

    # Resolve an explicitly requested slash command.
    if skill_command:
        cmd_clean = skill_command.strip().lstrip("/")

        if not cmd_clean:
            raise ValueError("The skill command cannot be empty.")

        builtin_dir = settings.BACKEND_ROOT / "skills" / cmd_clean

        if builtin_dir.is_dir():
            skill_file = builtin_dir / "SKILL.md"

            if not skill_file.is_file():
                raise ValueError(
                    f"Built-in skill '{cmd_clean}' has no SKILL.md file."
                )

            applied_identifiers.append(cmd_clean)

        else:
            db_skill = await get_skill_by_name(session, cmd_clean)

            if not db_skill or not db_skill.versions:
                raise ValueError(f"Skill '{cmd_clean}' was not found.")

            applied_identifiers.append(str(db_skill.id))

    # Resolve explicitly selected generated skill IDs.
    for skill_id in skill_ids:
        db_skill = await get_skill_by_id(session, skill_id)

        if not db_skill or not db_skill.versions:
            raise ValueError(
                f"Selected skill '{skill_id}' was not found "
                "or has no saved versions."
            )

        identifier = str(db_skill.id)

        if identifier not in applied_identifiers:
            applied_identifiers.append(identifier)

    # SkillsProvider loads skill instructions separately.
    return "", applied_identifiers


def _build_policy_response(
    policy: Policy,
    version_record: PolicyVersion,
    policy_text_path: str = "data/policy.txt",
) -> PolicyResponse:
    """Convert policy database models into a PolicyResponse."""

    raw_sections = json.loads(version_record.content_json)
    sections = [
        PolicySectionModel.model_validate(section)
        for section in raw_sections
    ]

    validation_report = None

    if (
        version_record.validation_report_json
        and version_record.validation_report_json != "{}"
    ):
        try:
            validation_report = (
                PolicyValidationReport.model_validate_json(
                    version_record.validation_report_json
                )
            )
        except Exception:
            logger.exception(
                "Could not parse validation report for policy %s version %s",
                policy.id,
                version_record.version,
            )

    applied_skills = json.loads(
        version_record.applied_skill_ids_json or "[]"
    )

    return PolicyResponse(
        policy_id=policy.id,
        version=version_record.version,
        title=policy.title,
        description=policy.description,
        domain=policy.domain,
        status=version_record.status,
        sections=sections,
        applied_skill_ids=applied_skills,
        source_requirement_version_id=(
            version_record.source_requirement_version_id
        ),
        validation_status=version_record.validation_status,
        validation_report=validation_report,
        change_summary=version_record.change_summary,
        policy_text_path=policy_text_path,
        created_at=version_record.created_at,
    )


async def generate_and_save_policy(
    session: AsyncSession,
    request: PolicyGenerationRequest,
) -> PolicyResponse:
    """Generate, validate, and persist an enterprise policy draft."""

    # 1. Normalize requirements.
    if request.requirement_id:
        (
            adapted_reqs,
            requirement_domain,
            original_description,
        ) = await load_single_requirement(
            session=session,
            requirement_id=request.requirement_id,
        )

        policy_domain = (
            request.domain or requirement_domain or "General"
        )
        policy_desc = request.description or original_description
        source_version = (
            request.source_requirement_version_id
            or request.requirement_id
        )

    elif request.session_id and not request.requirements:
        adapted_reqs, sess_domain, sess_desc = (
            await load_requirements_from_session(
                session=session,
                session_id=request.session_id,
            )
        )

        policy_domain = request.domain or sess_domain or "General"
        policy_desc = request.description or sess_desc
        source_version = (
            request.source_requirement_version_id or request.session_id
        )

    elif request.requirements:
        adapted_reqs = adapt_requirements(request.requirements)

        policy_domain = request.domain or "General"
        policy_desc = request.description
        source_version = (
            request.source_requirement_version_id or request.session_id
        )

    elif request.requirements_description:
        adapted_reqs = [
            ValidatedRequirementInput(
                requirement_id="REQ-001",
                text=request.requirements_description.strip(),
                session_id=request.session_id,
            )
        ]

        policy_domain = request.domain or "General"
        policy_desc = request.description
        source_version = (
            request.source_requirement_version_id or request.session_id
        )

    else:
        raise ValueError(
            "Provide 'requirement_id', 'session_id', "
            "'requirements', or 'requirements_description'."
        )

    # 2. Resolve selected skill identifiers.
    skill_instructions, applied_identifiers = (
        await load_skill_instructions(
            session=session,
            skill_command=request.skill_command,
            skill_ids=request.selected_skill_ids,
        )
    )

    # 3. Generate the policy.
    policy_output: StructuredPolicyGenerationOutput = (
        await generate_policy_from_requirements(
            requirements=adapted_reqs,
            applied_skills=applied_identifiers,
            custom_title=request.title,
            domain=policy_domain,
            custom_description=policy_desc,
            skill_instructions=(
                skill_instructions if skill_instructions else None
            ),
        )
    )

    # 4. Validate requirement preservation and policy quality.
    validation_report = validate_policy_draft(
        sections=policy_output.sections,
        requirements=adapted_reqs,
        unresolved_items=policy_output.unresolved_items,
    )

    # 5. Persist the policy and initial version.
    policy = await policy_repository.create_policy(
        session=session,
        title=policy_output.title,
        domain=policy_output.domain,
        sections=policy_output.sections,
        description=policy_output.description or policy_desc,
        applied_skill_ids=applied_identifiers,
        validation_status=validation_report.overall_status.lower(),
        validation_report=validation_report,
        source_requirement_version_id=source_version,
        change_summary=(
            "Initial policy draft generated from validated requirements."
        ),
    )

    # 6. Format and save the policy document.
    text_content = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=1,
        sections=policy_output.sections,
        description=policy.description,
        status="draft",
    )

    saved_path = save_policy_document_to_file(
        policy.id,
        1,
        text_content,
    )

    v1_record = policy.versions[0]

    return _build_policy_response(
        policy,
        v1_record,
        policy_text_path=saved_path,
    )


async def modify_policy_section(
    session: AsyncSession,
    policy_id: UUID,
    request: PolicyModificationRequest,
    requirements: list[Any] | None = None,
) -> PolicyResponse:
    """Revise a policy section, validate it, and create a new version."""

    policy = await policy_repository.get_policy_by_id(session, policy_id)

    if not policy or not policy.versions:
        raise ValueError(f"Policy {policy_id} not found.")

    latest_version = max(policy.versions, key=lambda v: v.version)

    current_sections = [
        PolicySectionModel.model_validate(section)
        for section in json.loads(latest_version.content_json)
    ]

    # Reuse the skill selections saved with this policy version.
    applied_skills = json.loads(
        latest_version.applied_skill_ids_json or "[]"
    )

    target_sec_id = request.section_id
    updated_sections: list[PolicySectionModel] = []
    found = False

    for sec in current_sections:
        if target_sec_id and sec.section_id == target_sec_id:
            found = True

            if request.updated_content:
                # Direct user edit.
                revised_sec = sec.model_copy(
                    update={"content": request.updated_content.strip()}
                )
            else:
                # AI-assisted revision with the original selected skills.
                norm_reqs = adapt_requirements(requirements or [])

                revised_sec = await revise_policy_section_agent(
                    current_section=sec,
                    user_instructions=request.instructions,
                    all_requirements=norm_reqs,
                    applied_skills=applied_skills,
                )

            updated_sections.append(revised_sec)

        else:
            updated_sections.append(sec)

    if target_sec_id and not found:
        raise ValueError(
            f"Section {target_sec_id} not found in policy."
        )

    # Load requirements for deterministic validation.
    if requirements:
        norm_reqs = adapt_requirements(requirements)
    else:
        source_requirement_id = (
            latest_version.source_requirement_version_id
        )

        if source_requirement_id:
            try:
                norm_reqs, _, _ = await load_single_requirement(
                    session=session,
                    requirement_id=source_requirement_id,
                )
            except ValueError:
                # Older policies may store a session ID or another
                # source reference rather than an individual requirement ID.
                norm_reqs = []
        else:
            norm_reqs = []

    validation_report = validate_policy_draft(
        sections=updated_sections,
        requirements=norm_reqs,
    )

    # 5. Persist the new version, retaining selected skill IDs.
    new_version_record = await policy_repository.create_policy_version(
        session=session,
        policy_id=policy.id,
        sections=updated_sections,
        change_summary=request.instructions,
        validation_status=validation_report.overall_status.lower(),
        validation_report=validation_report,
        source_requirement_version_id=(
            latest_version.source_requirement_version_id
        ),
        applied_skill_ids=applied_skills,
    )

    # 6. Format and update the policy document.
    text_content = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=new_version_record.version,
        sections=updated_sections,
        description=policy.description,
        status="draft",
    )

    saved_path = save_policy_document_to_file(
        policy.id,
        new_version_record.version,
        text_content,
    )

    return _build_policy_response(
        policy,
        new_version_record,
        policy_text_path=saved_path,
    )


async def approve_policy_version(
    session: AsyncSession,
    policy_id: UUID,
    version: int,
) -> PolicyResponse:
    """Approve a specific version of a policy."""

    updated_v = await policy_repository.update_policy_version_status(
        session=session,
        policy_id=policy_id,
        version=version,
        new_status="approved",
    )

    if not updated_v:
        raise ValueError(
            f"Policy {policy_id} version {version} not found."
        )

    policy = await policy_repository.get_policy_by_id(session, policy_id)

    if not policy:
        raise ValueError(f"Policy {policy_id} not found.")

    raw_sections = json.loads(updated_v.content_json)
    sections = [
        PolicySectionModel.model_validate(section)
        for section in raw_sections
    ]

    text_content = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=version,
        sections=sections,
        description=policy.description,
        status="approved",
    )

    saved_path = save_policy_document_to_file(
        policy.id,
        version,
        text_content,
    )

    return _build_policy_response(
        policy,
        updated_v,
        policy_text_path=saved_path,
    )


async def get_policy_detail(
    session: AsyncSession,
    policy_id: UUID,
    version: int | None = None,
) -> PolicyResponse | None:
    """Retrieve a specific policy version or the latest version."""

    policy = await policy_repository.get_policy_by_id(session, policy_id)

    if not policy or not policy.versions:
        return None

    if version is not None:
        target_v = next(
            (v for v in policy.versions if v.version == version),
            None,
        )

        if not target_v:
            return None
    else:
        target_v = max(policy.versions, key=lambda v: v.version)

    return _build_policy_response(policy, target_v)


async def list_all_policies(
    session: AsyncSession,
) -> list[PolicyResponse]:
    """List all policies with their latest version details."""

    policies = await policy_repository.list_policies(session)
    results: list[PolicyResponse] = []

    for policy_item in policies:
        if policy_item.versions:
            latest_version = max(
                policy_item.versions,
                key=lambda version: version.version,
            )
            results.append(
                _build_policy_response(policy_item, latest_version)
            )

    return results


async def get_policy_versions_list(
    session: AsyncSession,
    policy_id: UUID,
) -> list[PolicyVersionSummary]:
    """Retrieve version history summaries for a policy."""

    policy = await policy_repository.get_policy_by_id(session, policy_id)

    if not policy:
        return []

    return [
        PolicyVersionSummary(
            version_id=version_record.id,
            policy_id=version_record.policy_id,
            version=version_record.version,
            status=version_record.status,
            validation_status=version_record.validation_status,
            change_summary=version_record.change_summary,
            created_at=version_record.created_at,
        )
        for version_record in sorted(
            policy.versions,
            key=lambda version: version.version,
        )
    ]


def get_policy_text_content(
    policy_id: UUID | None = None,
    version: int | None = None,
) -> str | None:
    """Read the policy text document."""

    if policy_id and version:
        versioned_file = (
            settings.BACKEND_ROOT
            / "data"
            / "policies"
            / f"{policy_id}_v{version}.txt"
        )

        if versioned_file.is_file():
            return versioned_file.read_text(encoding="utf-8")

    primary_file = settings.BACKEND_ROOT / "data" / "policy.txt"

    if primary_file.is_file():
        return primary_file.read_text(encoding="utf-8")

    return None
