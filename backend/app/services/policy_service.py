"""Application service for generating, validating, persisting, and modifying enterprise policies."""

import json
from typing import Any
from uuid import UUID

from app.agents.policy_generation.policy_generator import (
    StructuredPolicyGenerationOutput,
    generate_policy_from_requirements,
    revise_policy_section_agent,
)
from app.common.logger import get_logger
from app.db.session import AsyncSessionLocal
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
from app.services.validation_service import (
    validate_policy_draft,
    validate_policy_modification,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class PolicyModificationRejected(ValueError):
    """Raised when a policy modification fails validation."""

    def __init__(
        self,
        message: str,
        comparison: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.comparison = comparison


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


def extract_policy_metadata_from_requirements(
    requirements: list[ValidatedRequirementInput],
) -> tuple[str, str]:
    """Extract policy name and domain from confirmed requirement JSON."""

    if not requirements:
        raise ValueError(
            "At least one source requirement is required."
        )

    policy_names: list[str] = []
    topics: list[str] = []
    domains: list[str] = []

    for requirement in requirements:
        try:
            requirement_json = json.loads(requirement.text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Requirement {requirement.requirement_id!r} "
                "does not contain valid JSON."
            ) from exc

        if not isinstance(requirement_json, dict):
            raise ValueError(
                f"Requirement {requirement.requirement_id!r} "
                "must contain a JSON object."
            )

        policy_name = normalize_optional_text(
            requirement_json.get("policy_name")
        )
        domain = normalize_optional_text(
            requirement_json.get("domain")
        )
        topic = normalize_optional_text(
            requirement.category
        )

        if policy_name:
            policy_names.append(policy_name)

        if domain:
            domains.append(domain)

        if topic:
            topics.append(topic)

    # Resolve the policy title.
    unique_policy_names = list(dict.fromkeys(policy_names))

    if len(unique_policy_names) > 1:
        raise ValueError(
            "Conflicting policy_name values found in requirements."
        )

    if unique_policy_names:
        policy_title = unique_policy_names[0]
    else:
        unique_topics = list(dict.fromkeys(topics))

        if len(unique_topics) != 1:
            raise ValueError(
                "A single policy_name or requirement topic is required."
            )

        policy_title = unique_topics[0]

    # Domain must come from the confirmed requirement JSON.
    unique_domains = list(dict.fromkeys(domains))

    if len(unique_domains) != 1:
        raise ValueError(
            "A single domain must be present in the confirmed "
            "requirement JSON."
        )

    return policy_title, unique_domains[0]


def reject_placeholder_policy_content(
    output: StructuredPolicyGenerationOutput,
) -> None:
    """Reject empty or placeholder policy sections."""

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
                f"Section '{section.title}' contains empty or "
                "placeholder content. Check the policy-generation prompt."
            )



def format_policy_document_text(
    title: str,
    domain: str,
    version: int,
    sections: list[PolicySectionModel],
    description: str | None = None,
    status: str = "draft",
) -> str:
    """Format policy sections into a clean enterprise text document.

    Requirement IDs are intentionally excluded from the generated
    policy document. They remain available in the structured policy
    data for internal traceability and validation.
    """

    lines: list[str] = [
        f"ENTERPRISE POLICY: {title.upper()}",
        f"Domain: {domain} | Version: {version} | Status: {status.upper()}",
        "",
    ]

    if description:
        lines.extend(
            [
                "## Executive Summary",
                "",
                description.strip(),
                "",
            ]
        )

    if sections:
        lines.append("## Table of Contents")
        lines.append("")

        for index, section in enumerate(sections, start=1):
            lines.append(f"{index}. {section.title}")

        lines.append("")

    for index, section in enumerate(sections, start=1):
        lines.extend(
            [
                f"## Section {index}: {section.title}",
                "",
                section.content.strip(),
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"




async def load_skill_instructions(
    session: AsyncSession,
    skill_command: str | None,
    skill_ids: list[UUID] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """
    Resolve generated skills and their latest database versions.

    Built-in filesystem skills are not loaded here.
    Only generated skills stored in the database are supported.

    Returns:
        (
            builtin_skill_names,       # Always empty
            applied_skill_ids,         # Stable generated skill IDs
            applied_skill_version_ids, # Exact generated skill version IDs
        )
    """

    applied_skill_ids: list[str] = []
    applied_skill_version_ids: list[str] = []

    selected_ids = list(dict.fromkeys(skill_ids or []))

    # Resolve the skill command against the generated skills table.
    command_name = normalize_optional_text(skill_command)

    if command_name:
        command_name = command_name.lstrip("/").strip()

        if not command_name:
            raise ValueError(
                "The skill command cannot be empty."
            )

        database_skill = await get_skill_by_name(
            session,
            command_name,
        )

        if database_skill is None:
            raise ValueError(
                f"Generated skill '{command_name}' was not found in the database."
            )

        if not database_skill.versions:
            raise ValueError(
                f"Generated skill '{command_name}' has no saved versions."
            )

        latest_version = max(
            database_skill.versions,
            key=lambda item: item.version,
        )

        if not normalize_optional_text(latest_version.content):
            raise ValueError(
                f"Generated skill '{command_name}' has no stored content."
            )

        applied_skill_ids.append(
            str(database_skill.id)
        )

        applied_skill_version_ids.append(
            str(latest_version.id)
        )

    # Resolve explicitly selected generated skill IDs.
    for skill_id in selected_ids:

        database_skill = await get_skill_by_id(
            session,
            skill_id,
        )

        if database_skill is None:
            raise ValueError(
                f"Generated skill '{skill_id}' was not found in the database."
            )

        if not database_skill.versions:
            raise ValueError(
                f"Generated skill '{database_skill.name}' "
                "has no saved versions."
            )

        latest_version = max(
            database_skill.versions,
            key=lambda item: item.version,
        )

        if not normalize_optional_text(latest_version.content):
            raise ValueError(
                f"Generated skill '{database_skill.name}' "
                "has no stored content."
            )

        stable_id = str(database_skill.id)
        version_id = str(latest_version.id)

        if stable_id not in applied_skill_ids:
            applied_skill_ids.append(stable_id)

        if version_id not in applied_skill_version_ids:
            applied_skill_version_ids.append(version_id)

    logger.info(
        "Resolved generated skills: skill_ids=%s version_ids=%s",
        applied_skill_ids,
        applied_skill_version_ids,
    )

    # No built-in skills are used by the Policy Generation Agent.
    return (
        [],
        applied_skill_ids,
        applied_skill_version_ids,
    )

def _stored_clarification_items(
    version_record: PolicyVersion,
) -> list[str]:
    """Read unique unresolved clarification items from a saved version."""

    raw_report = getattr(
        version_record,
        "validation_report_json",
        None,
    )

    if not raw_report or raw_report == "{}":
        return []

    try:
        report = json.loads(raw_report)
    except (TypeError, json.JSONDecodeError):
        logger.warning(
            "Could not parse validation report for policy version %s",
            getattr(version_record, "version", "unknown"),
        )
        return []

    if not isinstance(report, dict):
        return []

    items = report.get("clarification_items") or []

    if not isinstance(items, list):
        return []

    cleaned: list[str] = []
    seen: set[str] = set()

    for item in items:
        if isinstance(item, str) and item.strip():
            value = item.strip()

            if value.casefold() not in seen:
                cleaned.append(value)
                seen.add(value.casefold())

    return cleaned


def _build_policy_response(
    policy: Policy,
    version_record: PolicyVersion,
) -> PolicyResponse:
    """Convert database policy records into the frontend response."""

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
            validation_report = PolicyValidationReport.model_validate_json(
                version_record.validation_report_json
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
        policy_status=policy.status,
        status=version_record.status,
        sections=sections,
        policy_text=version_record.content_text or "",
        applied_skill_ids=applied_skills,
        source_requirement_version_id=(
            version_record.source_requirement_version_id
        ),
        validation_status=version_record.validation_status,
        validation_report=validation_report,
        change_summary=version_record.change_summary,
        created_at=version_record.created_at,
    )

async def generate_and_save_policy(
    session: AsyncSession,
    request: PolicyGenerationRequest,
) -> PolicyResponse:
    """Generate, validate, and persist a policy using DB-backed skill versions."""

    # 1. Validate request identifiers.
    session_id = normalize_optional_text(request.session_id)
    requirement_id = normalize_optional_text(request.requirement_id)

    if not session_id:
        raise ValueError("'session_id' cannot be empty.")

    if not requirement_id:
        raise ValueError("'requirement_id' cannot be empty.")

    # 2. Load confirmed requirements.
    # Preserve the existing requirement workflow and exact source version.
    requirements, _, purpose = await load_single_requirement(
        session=session,
        requirement_id=requirement_id,
        session_id=session_id,
        source_requirement_version_id=(
            request.source_requirement_version_id
        ),
    )

    if not requirements:
        raise ValueError(
            f"No confirmed requirement found for {requirement_id!r}."
        )

    # 3. Extract policy metadata.
    policy_title, policy_domain = (
        extract_policy_metadata_from_requirements(requirements)
    )

    # 4. Validate source requirement version.
    source_version_id = requirements[0].source_version_id

    if not source_version_id:
        raise ValueError(
            "The confirmed requirement version ID is missing."
        )

    if any(
        item.source_version_id != source_version_id
        for item in requirements
    ):
        raise ValueError(
            "Requirements were loaded from different source versions."
        )

    # 5. Resolve generated skills from the database.
    skill_command = normalize_optional_text(
        request.skill_command
    )

    if skill_command:
        (
            _,
            applied_skill_ids,
            applied_skill_version_ids,
        ) = await load_skill_instructions(
            session=session,
            skill_command=skill_command,
            skill_ids=[],
        )
    else:
        applied_skill_ids = []
        applied_skill_version_ids = []

    selected_version_uuids = [
        UUID(version_id)
        for version_id in applied_skill_version_ids
    ]

    logger.info(
        "Generating policy: title=%s, domain=%s, "
        "source_version=%s, generated_skill_ids=%s, "
        "generated_skill_versions=%s",
        policy_title,
        policy_domain,
        source_version_id,
        applied_skill_ids,
        applied_skill_version_ids,
    )

    # 6. Generate policy using only selected DB-backed skill versions.
    policy_output: StructuredPolicyGenerationOutput = (
        await generate_policy_from_requirements(
            requirements=requirements,
            selected_skill_version_ids=selected_version_uuids,
            session_factory=AsyncSessionLocal,
            custom_title=policy_title,
            domain=policy_domain,
            custom_description=purpose,
        )
    )

    if not policy_output:
        raise ValueError(
            "The policy-generation agent returned no output."
        )

    # 7. Reject placeholder content.
    reject_placeholder_policy_content(policy_output)

    generated_description = normalize_optional_text(
        policy_output.description
    )

    final_description = generated_description or purpose

    # 8. Validate generated policy against authoritative requirements.
    validation_report = validate_policy_draft(
        sections=policy_output.sections,
        requirements=requirements,
        unresolved_items=policy_output.unresolved_items,
    )

    # 9. Format policy text.
    text_content = format_policy_document_text(
        title=policy_title,
        domain=policy_domain,
        version=1,
        sections=policy_output.sections,
        description=final_description,
        status="draft",
    )

    # 10. Persist policy and exact generated skill references.
    policy = await policy_repository.create_policy(
        session=session,
        title=policy_title,
        domain=policy_domain,
        sections=policy_output.sections,
        content_text=text_content,
        description=final_description,
        applied_skill_ids=applied_skill_ids,
        applied_skill_version_ids=applied_skill_version_ids,
        validation_status=validation_report.overall_status.lower(),
        validation_report=validation_report,
        source_requirement_version_id=source_version_id,
        change_summary=(
            "Initial policy draft generated from confirmed requirements."
        ),
    )

    # 11. Commit database transaction.
    await session.commit()

    # 12. Return persisted policy.
    first_version = max(
        policy.versions,
        key=lambda item: item.version,
    )

    return _build_policy_response(
        policy,
        first_version,
    )


async def _load_requirements_for_policy_source(
    session: AsyncSession,
    source_reference: str | None,
    fallback_requirement_ids: list[str] | None = None,
) -> list[ValidatedRequirementInput]:
    """Resolve requirements from the exact confirmed source version."""

    source_reference = normalize_optional_text(source_reference)

    # 1. Resolve a requirement-version ID.
    if source_reference:
        result = await session.execute(
            text(
                """
                SELECT
                    requirement_version_id,
                    session_id,
                    validation_status
                FROM requirement_versions
                WHERE requirement_version_id = :reference
                """
            ),
            {"reference": source_reference},
        )

        version_row = result.mappings().first()

        if version_row is not None:
            version_status = str(
                version_row["validation_status"] or ""
            ).strip().lower()

            if version_status not in {
                "valid",
                "validated",
                "confirmed",
            }:
                raise ValueError(
                    "The referenced requirement version is not confirmed."
                )

            snapshot_session_id = str(version_row["session_id"])

            # Get all requirement IDs belonging to the snapshot session.
            result = await session.execute(
                text(
                    """
                    SELECT requirement_id
                    FROM requirements
                    WHERE session_id = :session_id
                    ORDER BY created_at ASC
                    """
                ),
                {"session_id": snapshot_session_id},
            )

            requirement_rows = result.mappings().all()

            if not requirement_rows:
                raise ValueError(
                    "No requirements were found for the referenced "
                    "requirement version."
                )

            loaded_requirements = []

            # Always pass the exact version ID to the adapter.
            for row in requirement_rows:
                requirement_id = str(row["requirement_id"])

                loaded, _, _ = await load_single_requirement(
                    session=session,
                    requirement_id=requirement_id,
                    session_id=snapshot_session_id,
                    source_requirement_version_id=source_reference,
                )

                loaded_requirements.extend(loaded)

            return loaded_requirements

    # 2. Resolve a requirement-session ID.
    if source_reference:
        result = await session.execute(
            text(
                """
                SELECT session_id
                FROM requirement_sessions
                WHERE session_id = :session_id
                """
            ),
            {"session_id": source_reference},
        )

        session_id = result.scalar_one_or_none()

        if session_id:
            loaded, _, _ = await load_requirements_from_session(
                session=session,
                session_id=str(session_id),
            )

            return loaded

    # 3. Resolve a requirement ID.
    if source_reference:
        result = await session.execute(
            text(
                """
                SELECT session_id
                FROM requirements
                WHERE requirement_id = :requirement_id
                """
            ),
            {"requirement_id": source_reference},
        )

        session_id = result.scalar_one_or_none()

        if session_id:
            loaded, _, _ = await load_single_requirement(
                session=session,
                requirement_id=source_reference,
                session_id=str(session_id),
            )

            return loaded

    # 4. Try existing policy requirement mappings.
    loaded_requirements = []

    for requirement_id in dict.fromkeys(
        fallback_requirement_ids or []
    ):
        requirement_id = normalize_optional_text(requirement_id)

        if not requirement_id:
            continue

        result = await session.execute(
            text(
                """
                SELECT session_id
                FROM requirements
                WHERE requirement_id = :requirement_id
                """
            ),
            {"requirement_id": requirement_id},
        )

        session_id = result.scalar_one_or_none()

        if not session_id:
            continue

        loaded, _, _ = await load_single_requirement(
            session=session,
            requirement_id=requirement_id,
            session_id=str(session_id),
        )

        loaded_requirements.extend(loaded)

    return loaded_requirements

async def modify_policy_section(
    session: AsyncSession,
    policy_id: UUID,
    request: PolicyModificationRequest,
    requirements: list[Any] | None = None,
) -> PolicyResponse:
    """
    Modify one policy section using semantic comparison and validation.

    Flow:
        1. Load the original policy and latest version.
        2. Identify the requested section.
        3. Load authoritative requirements.
        4. Validate requirement mappings.
        5. Resolve the exact generated skill versions used originally.
        6. Ask the revision agent to modify the section.
        7. Validate the modification against the original section
           and authoritative requirements.
        8. Replace only the requested section.
        9. Validate the complete policy.
        10. Save a new policy version.

    Generated skills are database-only.
    No built-in filesystem skills are loaded.
    """

    # ---------------------------------------------------------
    # 1. Validate modification request
    # ---------------------------------------------------------

    target_section_id = normalize_optional_text(
        request.section_id
    )

    instructions = normalize_optional_text(
        request.instructions
    )

    if not target_section_id:
        raise ValueError(
            "A valid section_id is required."
        )

    if not instructions:
        raise ValueError(
            "Modification instructions cannot be empty."
        )

    # ---------------------------------------------------------
    # 2. Load original policy and latest version
    # ---------------------------------------------------------

    policy = await policy_repository.get_policy_by_id(
        session,
        policy_id,
    )

    if policy is None or not policy.versions:
        raise ValueError(
            f"Policy {policy_id} not found."
        )

    latest_version = max(
        policy.versions,
        key=lambda item: item.version,
    )

    try:
        raw_sections = json.loads(
            latest_version.content_json
        )

    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "The stored policy content is invalid JSON."
        ) from exc

    if not isinstance(raw_sections, list):
        raise ValueError(
            "The stored policy content must contain a list of sections."
        )

    current_sections = [
        PolicySectionModel.model_validate(item)
        for item in raw_sections
    ]

    # ---------------------------------------------------------
    # 3. Find the requested section
    # ---------------------------------------------------------

    matching_sections = [
        section
        for section in current_sections
        if section.section_id == target_section_id
    ]

    if len(matching_sections) != 1:
        raise ValueError(
            f"Expected exactly one section with ID "
            f"'{target_section_id}', found {len(matching_sections)}."
        )

    current_section = matching_sections[0]

    # ---------------------------------------------------------
    # 4. Collect requirement IDs from the original policy
    # ---------------------------------------------------------

    fallback_requirement_ids = list(
        dict.fromkeys(
            str(requirement_id).strip()
            for section in current_sections
            for requirement_id in section.requirement_ids
            if requirement_id
            and str(requirement_id).strip()
        )
    )

    # ---------------------------------------------------------
    # 5. Load authoritative requirements
    # ---------------------------------------------------------

    if requirements is not None:

        normalized_requirements = adapt_requirements(
            requirements
        )

    else:

        normalized_requirements = (
            await _load_requirements_for_policy_source(
                session=session,
                source_reference=(
                    latest_version.source_requirement_version_id
                ),
                fallback_requirement_ids=fallback_requirement_ids,
            )
        )

    if not normalized_requirements:
        raise ValueError(
            "Cannot modify this policy because its authoritative "
            "requirements could not be loaded. Supply validated "
            "requirements or resolve the existing requirement IDs."
        )

    # ---------------------------------------------------------
    # 6. Validate authoritative requirement mappings
    # ---------------------------------------------------------

    source_requirement_ids = {
        str(requirement.requirement_id).strip()
        for requirement in normalized_requirements
        if getattr(requirement, "requirement_id", None)
        and str(requirement.requirement_id).strip()
    }

    if not source_requirement_ids:
        raise ValueError(
            "The resolved requirements contain no valid requirement IDs."
        )

    existing_requirement_ids = set(
        current_section.requirement_ids
    )

    invalid_existing_ids = (
        existing_requirement_ids - source_requirement_ids
    )

    if invalid_existing_ids:
        raise ValueError(
            "The existing section contains requirement IDs that "
            "are absent from the authoritative requirements: "
            + ", ".join(sorted(invalid_existing_ids))
        )

    # ---------------------------------------------------------
    # 7. Load exact generated skill references
    #    from the original policy version
    # ---------------------------------------------------------

    try:
        stored_skill_ids = json.loads(
            latest_version.applied_skill_ids_json or "[]"
        )

        stored_skill_version_ids = json.loads(
            latest_version.applied_skill_version_ids_json or "[]"
        )

    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "The policy's applied-skill metadata is invalid JSON."
        ) from exc

    if not isinstance(stored_skill_ids, list):
        raise ValueError(
            "The policy's applied-skill IDs must be a list."
        )

    if not isinstance(stored_skill_version_ids, list):
        raise ValueError(
            "The policy's applied skill-version IDs must be a list."
        )

    valid_skill_ids: list[str] = []
    valid_skill_version_ids: list[str] = []

    # Keep a mapping of stable skill IDs to their saved versions.
    skill_versions_by_id: dict[str, set[str]] = {}

    # Resolve only generated skills from the database.
    for raw_skill_id in stored_skill_ids:

        skill_id_value = normalize_optional_text(
            str(raw_skill_id)
            if raw_skill_id is not None
            else None
        )

        if not skill_id_value:
            continue

        try:
            skill_uuid = UUID(skill_id_value)

        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(
                f"Invalid generated skill ID stored in policy: "
                f"{skill_id_value}. Built-in skill references are "
                "not supported by the Policy Generation Agent."
            ) from exc

        stable_skill_id = str(skill_uuid)

        if stable_skill_id in valid_skill_ids:
            continue

        database_skill = await get_skill_by_id(
            session,
            skill_uuid,
        )

        if database_skill is None:
            raise ValueError(
                f"Referenced generated skill '{stable_skill_id}' "
                "no longer exists in the database."
            )

        valid_skill_ids.append(
            str(database_skill.id)
        )

        skill_versions_by_id[
            str(database_skill.id)
        ] = {
            str(version.id)
            for version in database_skill.versions
        }

    # ---------------------------------------------------------
    # 8. Preserve exact skill versions
    # ---------------------------------------------------------

    for raw_version_id in stored_skill_version_ids:

        version_id_value = normalize_optional_text(
            str(raw_version_id)
            if raw_version_id is not None
            else None
        )

        if not version_id_value:
            continue

        try:
            version_uuid = UUID(version_id_value)

        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(
                f"Invalid stored skill version ID: "
                f"{version_id_value}"
            ) from exc

        normalized_version_id = str(version_uuid)

        if normalized_version_id in valid_skill_version_ids:
            continue

        # A stored version must belong to one of the policy's
        # referenced generated skills.
        belongs_to_policy_skill = any(
            normalized_version_id in version_ids
            for version_ids in skill_versions_by_id.values()
        )

        if not belongs_to_policy_skill:
            raise ValueError(
                f"Skill version '{normalized_version_id}' "
                "does not belong to any generated skill referenced "
                "by this policy."
            )

        valid_skill_version_ids.append(
            normalized_version_id
        )

    # ---------------------------------------------------------
    # 9. Backward compatibility for older policies
    #    without exact skill-version references
    # ---------------------------------------------------------

    if valid_skill_ids and not valid_skill_version_ids:

        logger.warning(
            "Policy %s version %s has generated skill IDs "
            "but no pinned skill versions. Resolving latest versions.",
            policy.id,
            latest_version.version,
        )

        for stable_skill_id in valid_skill_ids:

            database_skill = await get_skill_by_id(
                session,
                UUID(stable_skill_id),
            )

            if database_skill is None or not database_skill.versions:
                raise ValueError(
                    f"Could not resolve saved versions for "
                    f"generated skill '{stable_skill_id}'."
                )

            latest_skill_version = max(
                database_skill.versions,
                key=lambda item: item.version,
            )

            if not normalize_optional_text(
                latest_skill_version.content
            ):
                raise ValueError(
                    f"Latest version of generated skill "
                    f"'{database_skill.name}' has no stored content."
                )

            valid_skill_version_ids.append(
                str(latest_skill_version.id)
            )

    logger.info(
        "Policy modification skill references: "
        "generated_skill_ids=%s generated_skill_version_ids=%s",
        valid_skill_ids,
        valid_skill_version_ids,
    )

    # ---------------------------------------------------------
    # 10. Ask revision agent to modify the section
    # ---------------------------------------------------------

    revised_section = await revise_policy_section_agent(
        current_section=current_section,
        user_instructions=instructions,
        all_requirements=normalized_requirements,
        selected_skill_version_ids=[
            UUID(version_id)
            for version_id in valid_skill_version_ids
        ],
        session_factory=AsyncSessionLocal,
    )

    if revised_section.section_id != target_section_id:
        raise ValueError(
            "The revision agent returned an unexpected section ID."
        )

    revised_content = normalize_optional_text(
        revised_section.content
    )

    if not revised_content:
        raise ValueError(
            "The revision agent returned empty or placeholder content."
        )

    if revised_content.casefold() in {
        "string",
        "null",
        "none",
        "undefined",
        "todo",
        "tbd",
    }:
        raise ValueError(
            "The revision agent returned placeholder content."
        )

    # ---------------------------------------------------------
    # 11. Validate revised requirement traceability
    # ---------------------------------------------------------

    revised_requirement_ids = {
        str(requirement_id).strip()
        for requirement_id in revised_section.requirement_ids
        if requirement_id
        and str(requirement_id).strip()
    }

    unknown_ids = (
        revised_requirement_ids - source_requirement_ids
    )

    if unknown_ids:
        raise ValueError(
            "The revised section contains unknown requirement IDs: "
            + ", ".join(sorted(unknown_ids))
        )

    missing_existing_ids = (
        existing_requirement_ids - revised_requirement_ids
    )

    if missing_existing_ids:
        raise ValueError(
            "The revision removed existing requirement mappings: "
            + ", ".join(sorted(missing_existing_ids))
        )

    # ---------------------------------------------------------
    # 12. Validate the requested modification semantically
    # ---------------------------------------------------------

    modification_report = validate_policy_modification(
        original_section=current_section,
        revised_section=revised_section,
        instructions=instructions,
        requirements=normalized_requirements,
    )

    if modification_report.overall_status.upper() != "PASS":

        details = "\n".join(
            f"- {finding.rule_name}: {finding.message}"
            + (
                f" Details: {'; '.join(finding.details)}"
                if finding.details
                else ""
            )
            for finding in modification_report.findings
            if finding.status in {
                "FAIL",
                "NEEDS_CLARIFICATION",
            }
        )

        raise PolicyModificationRejected(
            "Policy modification rejected before creating a new version:\n"
            + details,
            comparison=modification_report.model_dump(),
        )

    # ---------------------------------------------------------
    # 13. Replace only the requested section
    # ---------------------------------------------------------

    updated_sections = [
        revised_section
        if section.section_id == target_section_id
        else section
        for section in current_sections
    ]

    # ---------------------------------------------------------
    # 14. Validate the complete policy
    # ---------------------------------------------------------

    inherited_clarifications = _stored_clarification_items(
        latest_version
    )

    validation_report = validate_policy_draft(
        sections=updated_sections,
        requirements=normalized_requirements,
        unresolved_items=inherited_clarifications,
    )

    if validation_report.overall_status.upper() == "FAIL":

        details = "\n".join(
            f"- {finding.rule_name}: {finding.message}"
            + (
                f" Details: {'; '.join(finding.details)}"
                if finding.details
                else ""
            )
            for finding in validation_report.findings
            if finding.status == "FAIL"
        )

        raise PolicyModificationRejected(
            "Policy modification rejected because whole-policy "
            "validation failed. No new policy version was created:\n"
            + details,
            comparison=validation_report.model_dump(),
        )

    # ---------------------------------------------------------
    # 15. Determine next policy version
    # ---------------------------------------------------------

    next_version = latest_version.version + 1

    # ---------------------------------------------------------
    # 16. Format revised policy document
    # ---------------------------------------------------------

    text_content = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=next_version,
        sections=updated_sections,
        description=policy.description,
        status="draft",
    )

    # ---------------------------------------------------------
    # 17. Persist new policy version
    # ---------------------------------------------------------

    new_policy_version = (
        await policy_repository.create_policy_version(
            session=session,
            policy_id=policy.id,
            sections=updated_sections,
            content_text=text_content,
            change_summary=instructions,
            validation_status=(
                validation_report.overall_status.lower()
            ),
            validation_report=validation_report,
            source_requirement_version_id=(
                latest_version.source_requirement_version_id
            ),
            applied_skill_ids=valid_skill_ids,
            applied_skill_version_ids=valid_skill_version_ids,
        )
    )

    # ---------------------------------------------------------
    # 18. Commit and return
    # ---------------------------------------------------------

    await session.commit()

    return _build_policy_response(
        policy,
        new_policy_version,
    )
async def approve_policy_version(
    session: AsyncSession,
    policy_id: UUID,
    version: int,
) -> PolicyResponse:
    """Approve a specific policy version and update its stored text."""

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

    updated_version.content_text = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=version,
        sections=sections,
        description=policy.description,
        status="approved",
    )

    await session.commit()

    return _build_policy_response(
        policy,
        updated_version,
    )


async def get_policy_detail(
    session: AsyncSession,
    policy_id: UUID,
    version: int | None = None,
) -> PolicyResponse | None:
    """Retrieve a specific policy version or the latest version."""

    policy = await policy_repository.get_policy_by_id(
        session,
        policy_id,
    )

    if not policy or not policy.versions:
        return None

    if version is not None:
        target_version = next(
            (
                item
                for item in policy.versions
                if item.version == version
            ),
            None,
        )

        if target_version is None:
            return None
    else:
        target_version = max(
            policy.versions,
            key=lambda item: item.version,
        )

    return _build_policy_response(policy, target_version)


async def list_all_policies(
    session: AsyncSession,
    domain: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[PolicyResponse]:
    """List policies with their latest version details.

    `domain` filters by the policy's domain.
    `status` filters by the latest version's status and is applied
    after pagination, so a page may return fewer than `limit` results.
    """

    policies = await policy_repository.list_policies(
        session,
        domain=domain,
        limit=limit,
        offset=offset,
    )

    results: list[PolicyResponse] = []

    for policy_item in policies:
        if not policy_item.versions:
            continue

        latest_version = max(
            policy_item.versions,
            key=lambda item: item.version,
        )

        if status is not None and latest_version.status != status:
            continue

        results.append(
            _build_policy_response(
                policy_item,
                latest_version,
            )
        )

    return results


async def get_policy_versions_list(
    session: AsyncSession,
    policy_id: UUID,
) -> list[PolicyVersionSummary]:
    """Retrieve version history summaries for a policy."""

    policy = await policy_repository.get_policy_by_id(
        session,
        policy_id,
    )

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
            key=lambda item: item.version,
        )
    ]


async def get_policy_text_content(
    session: AsyncSession,
    policy_id: UUID,
    version: int | None = None,
) -> str | None:
    """Retrieve policy text from the database."""

    policy = await policy_repository.get_policy_by_id(
        session,
        policy_id,
    )

    if not policy or not policy.versions:
        return None

    if version is not None:
        target_version = next(
            (
                item
                for item in policy.versions
                if item.version == version
            ),
            None,
        )

        if target_version is None:
            return None
    else:
        target_version = max(
            policy.versions,
            key=lambda item: item.version,
        )

    return target_version.content_text