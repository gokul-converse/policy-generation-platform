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
    create_next_skill_version,
    get_skill_by_id,
    get_skill_by_name,
)
from app.services.requirement_adapter import (
    adapt_requirements,
    load_requirements_from_session,
    load_single_requirement,
)
from app.services.validation_service import validate_policy_draft
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

def normalize_optional_text(value: str | None) -> str | None:
    """Treat blank strings and API placeholder values as missing."""
    if not isinstance(value, str):
        return None

    cleaned = value.strip()

    if not cleaned or cleaned.casefold() in {
        "string",
        "null",
        "none",
        "n/a",
        "undefined",
    }:
        return None

    return cleaned


def derive_policy_title(
    requirements: list[ValidatedRequirementInput],
) -> str:
    """Derive a readable title from the validated requirement."""
    for requirement in requirements:
        category = normalize_optional_text(requirement.category)

        if category and category.casefold() not in {
            "general",
            "other",
            "unknown",
        }:
            if "policy" in category.casefold():
                return category

            return f"{category} Policy"

    if requirements:
        requirement_text = normalize_optional_text(
            requirements[0].text
        )

        if requirement_text:
            words = requirement_text.rstrip(".!?").split()[:7]
            title = " ".join(words)

            return title[0].upper() + title[1:] if title else "Policy Draft"

    return "Policy Draft"


def reject_placeholder_policy_content(
    output: StructuredPolicyGenerationOutput,
) -> None:
    """Reject empty sections and literal placeholder content."""
    if not normalize_optional_text(output.title):
        raise ValueError(
            "Policy generation returned an empty or placeholder title."
        )

    if not output.sections:
        raise ValueError(
            "Policy generation returned no policy sections."
        )

    for section in output.sections:
        content = normalize_optional_text(section.content)

        if content is None or content.casefold() in {
            "string",
            "null",
            "none",
            "undefined",
        }:
            raise ValueError(
                f"Section '{section.title}' contains empty or placeholder "
                "content. Check the policy-generation prompt."
            )


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

    # 1. Validate request identifiers.
    session_id = request.session_id.strip()
    requirement_id = request.requirement_id.strip()

    if not session_id:
        raise ValueError("'session_id' cannot be empty.")

    if not requirement_id:
        raise ValueError("'requirement_id' cannot be empty.")

    # 2. Load the confirmed requirement from the existing database.
    (
        adapted_reqs,
        requirement_domain,
        original_description,
    ) = await load_single_requirement(
        session=session,
        requirement_id=requirement_id,
        session_id=session_id,
    )

    if not adapted_reqs:
        raise ValueError(
            f"No requirement found for requirement_id='{requirement_id}' "
            f"in session_id='{session_id}'."
        )

    # 3. Normalize optional request values.
    requested_title = normalize_optional_text(request.title)
    requested_domain = normalize_optional_text(request.domain)
    requested_description = normalize_optional_text(request.description)

    policy_domain = (
        requested_domain
        or normalize_optional_text(requirement_domain)
        or "General"
    )

    policy_desc = (
        requested_description
        or normalize_optional_text(original_description)
    )

    # A requirement ID is not automatically a version ID.
    source_version = normalize_optional_text(
        request.source_requirement_version_id
    )

    # 4. Resolve explicitly selected skills.
    skill_instructions, applied_identifiers = (
        await load_skill_instructions(
            session=session,
            skill_command=request.skill_command,
            skill_ids=request.selected_skill_ids,
        )
    )

    # 5. Derive a title when the caller omits it or sends "string".
    effective_title = (
        requested_title
        or derive_policy_title(adapted_reqs)
    )

    # 6. Generate the policy from the validated requirement.
    policy_output: StructuredPolicyGenerationOutput = (
        await generate_policy_from_requirements(
            requirements=adapted_reqs,
            applied_skills=applied_identifiers,
            custom_title=effective_title,
            domain=policy_domain,
            custom_description=policy_desc,
            skill_instructions=(
                skill_instructions if skill_instructions else None
            ),
        )
    )

    if not policy_output:
        raise ValueError(
            "The policy-generation agent returned no output."
        )

    # 7. Reject placeholder or empty generated content.
    reject_placeholder_policy_content(policy_output)

    generated_title = normalize_optional_text(policy_output.title)
    generated_domain = normalize_optional_text(policy_output.domain)
    generated_description = normalize_optional_text(
        policy_output.description
    )

    # Do not persist placeholder metadata returned by the model.
    final_title = generated_title or effective_title
    final_domain = generated_domain or policy_domain
    final_description = generated_description or policy_desc

    # 8. Validate the generated policy against the source requirements.
    validation_report = validate_policy_draft(
        sections=policy_output.sections,
        requirements=adapted_reqs,
        unresolved_items=policy_output.unresolved_items,
    )

    # 9. Persist the policy and its first version.
    policy = await policy_repository.create_policy(
        session=session,
        title=final_title,
        domain=final_domain,
        sections=policy_output.sections,
        description=final_description,
        applied_skill_ids=applied_identifiers,
        validation_status=validation_report.overall_status.lower(),
        validation_report=validation_report,
        source_requirement_version_id=source_version,
        change_summary=(
            "Initial policy draft generated from validated requirements."
        ),
    )

    # 10. Format and save the text document.
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



async def _load_requirements_for_policy_source(
    session: AsyncSession,
    source_reference: str | None,
) -> list[ValidatedRequirementInput]:
    """Resolve persisted source references for policy validation when possible.

    Existing policy versions store a single source reference. Depending on how
    the policy was generated, it may be a requirement ID, a session ID, or a
    snapshot/version ID. Resolve only recognized requirement/session IDs; an
    unknown snapshot ID must not be misused as a requirement ID.
    """
    if not source_reference or not source_reference.strip():
        return []

    source_reference = source_reference.strip()

    # Session-based generation stores the session ID as its source reference.
    try:
        loaded, _, _ = await load_requirements_from_session(
            session=session,
            session_id=source_reference,
        )
        return loaded
    except ValueError:
        # It may instead be a requirement ID or an opaque snapshot ID.
        pass
    except SQLAlchemyError:
        # Some supported policy-only workflows have no requirement tables.
        await session.rollback()
        return []

    # Requirement-based generation stores the requirement ID as the fallback
    # source reference. Look up its owning session before calling the adapter.
    try:
        result = await session.execute(
            text(
                "SELECT session_id FROM requirements "
                "WHERE requirement_id = :requirement_id"
            ),
            {"requirement_id": source_reference},
        )
        source_session_id = result.scalar_one_or_none()
    except SQLAlchemyError:
        await session.rollback()
        return []

    if not source_session_id:
        return []

    try:
        loaded, _, _ = await load_single_requirement(
            session=session,
            requirement_id=source_reference,
            session_id=str(source_session_id),
        )
        return loaded
    except ValueError:
        return []



async def modify_policy_section(
    session: AsyncSession,
    policy_id: UUID,
    request: PolicyModificationRequest,
    requirements: list[Any] | None = None,
) -> PolicyResponse:
    """Modify a policy and create matching versions for its linked skills."""

    policy = await policy_repository.get_policy_by_id(session, policy_id)

    if not policy or not policy.versions:
        raise ValueError(f"Policy {policy_id} not found.")

    latest_version = max(policy.versions, key=lambda item: item.version)

    current_sections = [
        PolicySectionModel.model_validate(section)
        for section in json.loads(latest_version.content_json)
    ]

    applied_skills = json.loads(
        latest_version.applied_skill_ids_json or "[]"
    )

    target_sec_id = request.section_id
    updated_sections: list[PolicySectionModel] = []
    found = False

    # Build the updated policy sections.
    for section in current_sections:
        if target_sec_id and section.section_id == target_sec_id:
            found = True

            if request.updated_content:
                revised_section = section.model_copy(
                    update={
                        "content": request.updated_content.strip()
                    }
                )
            else:
                normalized_requirements = adapt_requirements(
                    requirements or []
                )

                revised_section = await revise_policy_section_agent(
                    current_section=section,
                    user_instructions=request.instructions,
                    all_requirements=normalized_requirements,
                    applied_skills=applied_skills,
                )

            updated_sections.append(revised_section)
        else:
            updated_sections.append(section)

    if target_sec_id and not found:
        raise ValueError(
            f"Section {target_sec_id} not found in policy."
        )

    # Load requirements for validation.
    if requirements:
        normalized_requirements = adapt_requirements(requirements)
    else:
        normalized_requirements = (
            await _load_requirements_for_policy_source(
                session=session,
                source_reference=(
                    latest_version.source_requirement_version_id
                ),
            )
        )

    validation_report = validate_policy_draft(
        sections=updated_sections,
        requirements=normalized_requirements,
    )

    skills_root = settings.generated_skills_path.resolve()
    created_skill_files: list[Path] = []

    try:
        # Stage the new policy version. The repository must not commit here.
        new_policy_version = (
            await policy_repository.create_policy_version(
                session=session,
                policy_id=policy.id,
                sections=updated_sections,
                change_summary=request.instructions,
                validation_status=(
                    validation_report.overall_status.lower()
                ),
                validation_report=validation_report,
                source_requirement_version_id=(
                    latest_version.source_requirement_version_id
                ),
                applied_skill_ids=applied_skills,
            )
        )

        # Create a matching version for each linked generated skill.
        # Built-in skill names are not UUIDs, so skip those identifiers.
        processed_skill_ids: set[UUID] = set()

        for skill_identifier in applied_skills:
            try:
                skill_id = UUID(str(skill_identifier))
            except (ValueError, TypeError, AttributeError):
                # Built-in slash-command skills are not database skill IDs.
                continue

            if skill_id in processed_skill_ids:
                continue

            processed_skill_ids.add(skill_id)

            skill = await get_skill_by_id(session, skill_id)

            if skill is None or not skill.versions:
                raise ValueError(
                    f"Linked skill {skill_identifier} was not found "
                    "or has no saved versions. No versions were committed."
                )

            previous_latest = max(
                skill.versions,
                key=lambda item: item.version,
            )

            # Save the expected next file path so we can remove it if the
            # overall database transaction fails.
            next_skill_version = previous_latest.version + 1
            expected_relative_path = (
                Path(str(skill.id))
                / f"v{next_skill_version}"
                / "SKILL.md"
            )
            expected_file = (
                skills_root / expected_relative_path
            ).resolve()

            new_skill_version = await create_next_skill_version(
                session=session,
                skill_id=skill_id,
            )

            # Track only the file created by this operation.
            actual_file = (
                skills_root / new_skill_version.file_path
            ).resolve()

            actual_file.relative_to(skills_root)

            if actual_file != expected_file:
                raise RuntimeError(
                    "Created skill version path did not match "
                    "the expected version path."
                )

            created_skill_files.append(actual_file)

        # Commit policy and skill version rows together.
        await session.commit()

    except Exception:
        await session.rollback()

        # Database rollback does not remove files created on disk.
        for file_path in created_skill_files:
            try:
                resolved_path = file_path.resolve()
                resolved_path.relative_to(skills_root)

                if resolved_path.is_file():
                    resolved_path.unlink()
            except (OSError, ValueError):
                logger.exception(
                    "Could not clean up skill file after failed "
                    "policy modification: %s",
                    file_path,
                )

        raise

    # Save the policy document only after the database commit succeeds.
    text_content = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=new_policy_version.version,
        sections=updated_sections,
        description=policy.description,
        status="draft",
    )

    saved_path = save_policy_document_to_file(
        policy.id,
        new_policy_version.version,
        text_content,
    )

    return _build_policy_response(
        policy,
        new_policy_version,
        policy_text_path=saved_path,
    )

async def approve_policy_version(
    session: AsyncSession,
    policy_id: UUID,
    version: int,
) -> PolicyResponse:
    """Approve a specific policy version."""

    updated_version = (
        await policy_repository.update_policy_version_status(
            session=session,
            policy_id=policy_id,
            version=version,
            new_status="approved",
        )
    )

    if updated_version is None:
        raise ValueError(
            f"Policy {policy_id} version {version} not found."
        )

    policy = await policy_repository.get_policy_by_id(
        session,
        policy_id,
    )

    if policy is None:
        raise ValueError(f"Policy {policy_id} not found.")

    sections = [
        PolicySectionModel.model_validate(item)
        for item in json.loads(updated_version.content_json)
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
        updated_version,
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
    domain: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[PolicyResponse]:
    """List policies with their latest version details.

    domain filters by the policy's domain (e.g. 'hr', 'finance').
    status filters by the *latest* version's status ('draft' or
    'approved') and is applied after pagination, so a page may return
    fewer than `limit` results if some policies' latest version doesn't
    match. Narrow with domain/limit rather than relying on status
    filtering for exact page sizes.
    """

    policies = await policy_repository.list_policies(
        session,
        domain=domain,
        limit=limit,
        offset=offset,
    )
    results: list[PolicyResponse] = []

    for policy_item in policies:
        if policy_item.versions:
            latest_version = max(
                policy_item.versions,
                key=lambda version: version.version,
            )

            if status is not None and latest_version.status != status:
                continue

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
