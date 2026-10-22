"""Application service for generating, validating, persisting, and modifying enterprise policies."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.repositories import policy_repository
from app.repositories.skill_repository import get_skill_by_id, get_skill_by_name
from app.services.requirement_adapter import adapt_requirements, load_requirements_from_session
from app.services.validation_service import validate_policy_draft

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
        lines.extend([
            "## Executive Summary",
            description.strip(),
            "",
        ])

    lines.extend([
        "## Table of Contents",
    ])
    for i, sec in enumerate(sections, start=1):
        lines.append(f"{i}. {sec.title}")
    lines.append("")

    for i, sec in enumerate(sections, start=1):
        lines.extend([
            "-" * 80,
            f"Section {i}: {sec.title} [{sec.section_id}]",
            "-" * 80,
            sec.content.strip(),
            "",
        ])
        if sec.requirement_ids:
            lines.append(f"Traceable Requirements: {', '.join(sec.requirement_ids)}")
            lines.append("")

    lines.append("=" * 80)
    lines.append("END OF POLICY DOCUMENT")
    lines.append("=" * 80)

    return "\n".join(lines)


def save_policy_document_to_file(
    policy_id: UUID,
    version: int,
    content_text: str,
) -> str:
    """Write the policy document to data/policy.txt and an archived version file."""

    data_dir = settings.BACKEND_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    policies_dir = data_dir / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)

    # 1. Primary requested file: data/policy.txt
    primary_file = data_dir / "policy.txt"
    primary_file.write_text(content_text, encoding="utf-8")

    # 2. Versioned archive file: data/policies/{policy_id}_v{version}.txt
    versioned_file = policies_dir / f"{policy_id}_v{version}.txt"
    versioned_file.write_text(content_text, encoding="utf-8")

    logger.info("Saved policy to %s and %s", primary_file, versioned_file)
    return "data/policy.txt"


async def load_skill_instructions(
    session: AsyncSession,
    skill_command: str | None,
    skill_ids: list[UUID],
) -> tuple[str, list[str]]:
    """Load instructions from built-in or database-persisted Agent Skills."""

    combined_instructions: list[str] = []
    applied_identifiers: list[str] = []

    # 1. Check slash-command trigger (e.g. /company-policy-generator or /skill-creator)
    if skill_command:
        cmd_clean = skill_command.strip().lstrip("/")
        applied_identifiers.append(cmd_clean)

        builtin_dir = settings.BACKEND_ROOT / "skills" / cmd_clean
        if builtin_dir.is_dir():
            skill_md = builtin_dir / "SKILL.md"
            if skill_md.is_file():
                combined_instructions.append(f"--- Skill: {cmd_clean} ---\n" + skill_md.read_text(encoding="utf-8"))

            # Include references if present (progressive disclosure)
            ref_dir = builtin_dir / "references"
            if ref_dir.is_dir():
                for ref_file in ref_dir.glob("*.md"):
                    combined_instructions.append(
                        f"--- Reference ({ref_file.name}) ---\n" + ref_file.read_text(encoding="utf-8")
                    )
        else:
            # Check if skill exists in database by name
            db_skill = await get_skill_by_name(session, cmd_clean)
            if db_skill and db_skill.versions:
                latest_v = db_skill.versions[-1]
                skills_root = Path(settings.generated_skills_dir).resolve()
                fpath = skills_root / latest_v.file_path
                if fpath.is_file():
                    combined_instructions.append(
                        f"--- Skill: {db_skill.name} (v{latest_v.version}) ---\n"
                        + fpath.read_text(encoding="utf-8")
                    )

    # 2. Check explicitly selected skill UUIDs
    for sid in skill_ids:
        applied_identifiers.append(str(sid))
        db_skill = await get_skill_by_id(session, sid)
        if db_skill and db_skill.versions:
            latest_v = db_skill.versions[-1]
            skills_root = Path(settings.generated_skills_dir).resolve()
            fpath = skills_root / latest_v.file_path
            if fpath.is_file():
                combined_instructions.append(
                    f"--- Skill: {db_skill.name} (v{latest_v.version}) ---\n"
                    + fpath.read_text(encoding="utf-8")
                )

    return "\n\n".join(combined_instructions), applied_identifiers


def _build_policy_response(
    policy: Policy,
    version_record: PolicyVersion,
    policy_text_path: str = "data/policy.txt",
) -> PolicyResponse:
    """Helper to convert Policy and PolicyVersion DB models to PolicyResponse."""

    raw_sections = json.loads(version_record.content_json)
    sections = [PolicySectionModel.model_validate(s) for s in raw_sections]

    validation_report = None
    if version_record.validation_report_json and version_record.validation_report_json != "{}":
        try:
            validation_report = PolicyValidationReport.model_validate_json(
                version_record.validation_report_json
            )
        except Exception:
            pass

    applied_skills = json.loads(version_record.applied_skill_ids_json or "[]")

    return PolicyResponse(
        policy_id=policy.id,
        version=version_record.version,
        title=policy.title,
        description=policy.description,
        domain=policy.domain,
        status=version_record.status,
        sections=sections,
        applied_skill_ids=applied_skills,
        source_requirement_version_id=version_record.source_requirement_version_id,
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
    """Generate an enterprise policy draft, validate it deterministically, and save to DB and disk."""

    # 1. Normalize requirements: check if session_id is provided to load from conversational gathering
    if request.session_id and not request.requirements:
        adapted_reqs, sess_domain, sess_desc = await load_requirements_from_session(
            session=session,
            session_id=request.session_id,
        )
        policy_domain = request.domain or sess_domain or "General"
        policy_desc = request.description or sess_desc
        source_version = request.source_requirement_version_id or request.session_id
    elif request.requirements:
        adapted_reqs = adapt_requirements(request.requirements)
        policy_domain = request.domain or "General"
        policy_desc = request.description
        source_version = request.source_requirement_version_id or request.session_id
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
        source_version = request.source_requirement_version_id or request.session_id
    else:
        raise ValueError("Either 'session_id' or 'requirements' must be provided.")

    # 2. Resolve skill instructions (e.g. from /company-policy-generator)
    skill_instructions, applied_identifiers = await load_skill_instructions(
        session=session,
        skill_command=request.skill_command,
        skill_ids=request.selected_skill_ids,
    )

    # 3. Generate policy using LLM agent
    policy_output: StructuredPolicyGenerationOutput = await generate_policy_from_requirements(
        requirements=adapted_reqs,
        applied_skills=applied_identifiers,
        custom_title=request.title,
        domain=policy_domain,
        custom_description=policy_desc,
        skill_instructions=skill_instructions if skill_instructions else None,
    )

    # 4. Deterministic quality and preservation validation
    validation_report = validate_policy_draft(
        sections=policy_output.sections,
        requirements=adapted_reqs,
        unresolved_items=policy_output.unresolved_items,
    )

    # 5. Persist policy and version 1 in DB
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
        change_summary="Initial policy draft generated from validated requirements.",
    )

    # 6. Format and save to data/policy.txt
    text_content = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=1,
        sections=policy_output.sections,
        description=policy.description,
        status="draft",
    )
    saved_path = save_policy_document_to_file(policy.id, 1, text_content)

    v1_record = policy.versions[0]
    return _build_policy_response(policy, v1_record, policy_text_path=saved_path)


async def modify_policy_section(
    session: AsyncSession,
    policy_id: UUID,
    request: PolicyModificationRequest,
    requirements: list[Any] | None = None,
) -> PolicyResponse:
    """Revise a policy section, create a new sequential version, validate, and update data/policy.txt."""

    policy = await policy_repository.get_policy_by_id(session, policy_id)
    if not policy or not policy.versions:
        raise ValueError(f"Policy {policy_id} not found.")

    latest_version = max(policy.versions, key=lambda v: v.version)
    current_sections = [
        PolicySectionModel.model_validate(s)
        for s in json.loads(latest_version.content_json)
    ]

    target_sec_id = request.section_id
    updated_sections: list[PolicySectionModel] = []
    found = False

    for sec in current_sections:
        if target_sec_id and sec.section_id == target_sec_id:
            found = True
            if request.updated_content:
                # Direct user edit
                revised_sec = sec.model_copy(update={"content": request.updated_content.strip()})
            else:
                # AI-assisted revision
                norm_reqs = adapt_requirements(requirements or [])
                revised_sec = await revise_policy_section_agent(
                    current_section=sec,
                    user_instructions=request.instructions,
                    all_requirements=norm_reqs,
                )
            updated_sections.append(revised_sec)
        else:
            updated_sections.append(sec)

    if target_sec_id and not found:
        raise ValueError(f"Section {target_sec_id} not found in policy.")

    # Validate revised draft
    norm_reqs = adapt_requirements(requirements or []) if requirements else []
    validation_report = validate_policy_draft(
        sections=updated_sections,
        requirements=norm_reqs,
    )

    applied_skills = json.loads(latest_version.applied_skill_ids_json or "[]")

    new_version_record = await policy_repository.create_policy_version(
        session=session,
        policy_id=policy.id,
        sections=updated_sections,
        change_summary=request.instructions,
        validation_status=validation_report.overall_status.lower(),
        validation_report=validation_report,
        source_requirement_version_id=latest_version.source_requirement_version_id,
        applied_skill_ids=applied_skills,
    )

    # Format and update data/policy.txt
    text_content = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=new_version_record.version,
        sections=updated_sections,
        description=policy.description,
        status="draft",
    )
    saved_path = save_policy_document_to_file(policy.id, new_version_record.version, text_content)

    return _build_policy_response(policy, new_version_record, policy_text_path=saved_path)


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
        raise ValueError(f"Policy {policy_id} version {version} not found.")

    policy = await policy_repository.get_policy_by_id(session, policy_id)
    if not policy:
        raise ValueError(f"Policy {policy_id} not found.")

    # Re-write document text with APPROVED status
    raw_sections = json.loads(updated_v.content_json)
    sections = [PolicySectionModel.model_validate(s) for s in raw_sections]
    text_content = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=version,
        sections=sections,
        description=policy.description,
        status="approved",
    )
    saved_path = save_policy_document_to_file(policy.id, version, text_content)

    return _build_policy_response(policy, updated_v, policy_text_path=saved_path)


async def get_policy_detail(
    session: AsyncSession,
    policy_id: UUID,
    version: int | None = None,
) -> PolicyResponse | None:
    """Retrieve details of a policy for a specific version or its latest version."""

    policy = await policy_repository.get_policy_by_id(session, policy_id)
    if not policy or not policy.versions:
        return None

    if version is not None:
        target_v = next((v for v in policy.versions if v.version == version), None)
        if not target_v:
            return None
    else:
        target_v = max(policy.versions, key=lambda v: v.version)

    return _build_policy_response(policy, target_v)


async def list_all_policies(
    session: AsyncSession,
) -> list[PolicyResponse]:
    """List all enterprise policies with their latest version details."""

    policies = await policy_repository.list_policies(session)
    results = []
    for p in policies:
        if p.versions:
            latest_v = max(p.versions, key=lambda v: v.version)
            results.append(_build_policy_response(p, latest_v))
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
            version_id=v.id,
            policy_id=v.policy_id,
            version=v.version,
            status=v.status,
            validation_status=v.validation_status,
            change_summary=v.change_summary,
            created_at=v.created_at,
        )
        for v in sorted(policy.versions, key=lambda x: x.version)
    ]


def get_policy_text_content(
    policy_id: UUID | None = None,
    version: int | None = None,
) -> str | None:
    """Read the policy text document."""

    if policy_id and version:
        versioned_file = settings.BACKEND_ROOT / "data" / "policies" / f"{policy_id}_v{version}.txt"
        if versioned_file.is_file():
            return versioned_file.read_text(encoding="utf-8")

    primary_file = settings.BACKEND_ROOT / "data" / "policy.txt"
    if primary_file.is_file():
        return primary_file.read_text(encoding="utf-8")

    return None
