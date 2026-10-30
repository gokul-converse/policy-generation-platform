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
from app.services.validation_service import (
    validate_policy_draft,
    validate_policy_modification,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class PolicyModificationRejected(ValueError):
    """Raised when a modification fails validation after revision.

    Carries the structured validation comparison (as `.comparison`)
    so the API layer can return it to the frontend in a 409 response,
    instead of just a plain error string. Subclasses ValueError so
    any caller still matching on ValueError keeps working unchanged.
    """

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
    session_domain: str | None,
) -> tuple[str, str]:
    """
    Extract policy name and domain from authoritative requirement data.

    Priority:
    1. policy_name from requirement JSON.
    2. Requirement topic/category as policy name.
    3. Domain from requirement JSON.
    4. Domain from the linked requirement session.

    Do not infer policy names from arbitrary requirement text.
    Do not filter domain values such as General, Other or Unknown.
    """

    if not requirements:
        raise ValueError(
            "At least one source requirement is required."
        )

    policy_names: list[str] = []
    topics: list[str] = []
    domains: list[str] = []

    for requirement in requirements:
        payload: dict[str, Any] = {}

        requirement_text = getattr(requirement, "text", None)

        # Extract structured metadata from requirement JSON.
        if isinstance(requirement_text, str):
            try:
                parsed = json.loads(requirement_text)
            except (TypeError, json.JSONDecodeError):
                parsed = None

            if isinstance(parsed, dict):
                payload = parsed

        # Extract policy name.
        policy_name = normalize_optional_text(
            payload.get("policy_name")
        )

        if policy_name:
            policy_names.append(policy_name)

        # Extract requirement topic.
        topic = normalize_optional_text(
            getattr(requirement, "category", None)
        )

        if topic:
            topics.append(topic)

        # Extract domain.
        domain = normalize_optional_text(
            payload.get("domain")
        )

        if domain:
            domains.append(domain)

    # Resolve policy name.
    unique_policy_names = list(dict.fromkeys(policy_names))

    if len(unique_policy_names) > 1:
        raise ValueError(
            "Conflicting policy_name values found in requirements: "
            + ", ".join(unique_policy_names)
        )

    if unique_policy_names:
        policy_title = unique_policy_names[0]

    else:
        unique_topics = list(dict.fromkeys(topics))

        if len(unique_topics) > 1:
            raise ValueError(
                "Multiple requirement topics were found without "
                "a single policy_name."
            )

        if not unique_topics:
            raise ValueError(
                "No policy_name or requirement topic was found."
            )

        # Use the requirement topic exactly as provided.
        policy_title = unique_topics[0]

    # Resolve domain.
    unique_domains = list(dict.fromkeys(domains))

    if len(unique_domains) > 1:
        raise ValueError(
            "Conflicting domain values found in requirements: "
            + ", ".join(unique_domains)
        )

    if unique_domains:
        policy_domain = unique_domains[0]
    else:
        policy_domain = normalize_optional_text(session_domain)

    if not policy_domain:
        raise ValueError(
            "No domain was found in the requirement or its linked session."
        )

    return policy_title, policy_domain


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


def _stored_clarification_items(version_record: PolicyVersion) -> list[str]:
    """Read deduplicated unresolved clarification items from a saved version."""
    raw_report = getattr(version_record, "validation_report_json", None)
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
    """Generate, validate and persist a policy from authoritative requirements."""

    # ---------------------------------------------------------
    # 1. Validate request identifiers
    # ---------------------------------------------------------

    session_id = (
        request.session_id.strip()
        if request.session_id
        else ""
    )

    requirement_id = (
        request.requirement_id.strip()
        if request.requirement_id
        else ""
    )

    if not session_id:
        raise ValueError("'session_id' cannot be empty.")

    if not requirement_id:
        raise ValueError("'requirement_id' cannot be empty.")

    # ---------------------------------------------------------
    # 2. Load authoritative requirement
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 3. Extract policy name and domain from requirement
    # ---------------------------------------------------------

    effective_title, policy_domain = (
        extract_policy_metadata_from_requirements(
            requirements=adapted_reqs,
            session_domain=requirement_domain,
        )
    )

    # Description comes from the original requirement session.
    policy_description = normalize_optional_text(
        original_description
    )

    if not policy_description:
        policy_description = (
            "Enterprise policy generated from validated requirements."
        )

    logger.info(
        "Policy metadata resolved: title=%s, domain=%s, "
        "requirement_id=%s",
        effective_title,
        policy_domain,
        requirement_id,
    )

    # ---------------------------------------------------------
    # 4. Resolve authoritative source version
    # ---------------------------------------------------------

    source_version = (
        normalize_optional_text(
            request.source_requirement_version_id
        )
        or await _resolve_confirmed_requirement_version_id(
            session=session,
            session_id=session_id,
        )
        or requirement_id
    )

    # ---------------------------------------------------------
    # 5. Resolve selected skill
    # ---------------------------------------------------------

    skill_command = (
        normalize_optional_text(request.skill_command)
        or "/policy"
    )

    skill_instructions, applied_identifiers = (
        await load_skill_instructions(
            session=session,
            skill_command=skill_command,
            skill_ids=[],
        )
    )

    # ---------------------------------------------------------
    # 6. Generate policy using extracted metadata
    # ---------------------------------------------------------

    policy_output: StructuredPolicyGenerationOutput = (
        await generate_policy_from_requirements(
            requirements=adapted_reqs,
            applied_skills=applied_identifiers,
            custom_title=effective_title,
            domain=policy_domain,
            custom_description=policy_description,
            skill_instructions=(
                skill_instructions
                if skill_instructions
                else None
            ),
        )
    )

    if not policy_output:
        raise ValueError(
            "The policy-generation agent returned no output."
        )

    # ---------------------------------------------------------
    # 7. Validate generated output
    # ---------------------------------------------------------

    reject_placeholder_policy_content(policy_output)

    # Do not allow LLM to overwrite requirement metadata.
    final_title = effective_title
    final_domain = policy_domain

    generated_description = normalize_optional_text(
        policy_output.description
    )

    final_description = (
        generated_description or policy_description
    )

    # ---------------------------------------------------------
    # 8. Validate policy against authoritative requirements
    # ---------------------------------------------------------

    validation_report = validate_policy_draft(
        sections=policy_output.sections,
        requirements=adapted_reqs,
        unresolved_items=policy_output.unresolved_items,
    )

    # ---------------------------------------------------------
    # 9. Save policy and initial version
    # ---------------------------------------------------------

    policy = await policy_repository.create_policy(
        session=session,
        title=final_title,
        domain=final_domain,
        sections=policy_output.sections,
        description=final_description,
        applied_skill_ids=applied_identifiers,
        validation_status=(
            validation_report.overall_status.lower()
        ),
        validation_report=validation_report,
        source_requirement_version_id=source_version,
        change_summary=(
            "Initial policy draft generated from validated requirements."
        ),
    )

    # ---------------------------------------------------------
    # 10. Format policy document
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 11. Return policy response
    # ---------------------------------------------------------

    v1_record = policy.versions[0]

    return _build_policy_response(
        policy,
        v1_record,
        policy_text_path=saved_path,
    )


async def _resolve_confirmed_requirement_version_id(
    session: AsyncSession,
    session_id: str,
) -> str | None:
    """Look up the latest confirmed/valid requirement_versions snapshot.

    This is the ID that modify_policy_section's resolver checks first,
    so injecting it at generation time avoids falling through the
    fragile requirement_id / session-id fallback chain later.
    """
    try:
        result = await session.execute(
            text(
                """
                SELECT requirement_version_id
                FROM requirement_versions
                WHERE session_id = :sid
                  AND validation_status IN ('valid', 'confirmed')
                ORDER BY version_number DESC
                LIMIT 1
                """
            ),
            {"sid": session_id},
        )
        row = result.first()
    except SQLAlchemyError:
        await session.rollback()
        raise

    if row and row.requirement_version_id:
        return str(row.requirement_version_id)

    logger.warning(
        "No confirmed requirement_versions snapshot found for session "
        "%s at policy-generation time. Falling back to requirement_id "
        "as the source reference; later section modification may fail "
        "to resolve requirements if that requirement is ever removed.",
        session_id,
    )
    return None




async def _load_requirements_for_policy_source(
    session: AsyncSession,
    source_reference: str | None,
    fallback_requirement_ids: list[str] | None = None,
) -> list[ValidatedRequirementInput]:
    """Resolve authoritative requirements from a version, session, or requirement."""

    source_reference = normalize_optional_text(source_reference)

    # 1. Resolve an exact requirement-version/snapshot ID.
    if source_reference:
        try:
            result = await session.execute(
                text(
                    """
                    SELECT session_id, requirements_json, validation_status
                    FROM requirement_versions
                    WHERE requirement_version_id = :reference
                    """
                ),
                {"reference": source_reference},
            )
            snapshot = result.mappings().first()

            if snapshot is not None:
                validation_status = str(
                    snapshot["validation_status"] or ""
                ).strip().lower()

                if validation_status not in {"valid", "confirmed"}:
                    raise ValueError(
                        "The referenced requirement version is not "
                        "validated or confirmed."
                    )

                try:
                    payload = json.loads(snapshot["requirements_json"])
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValueError(
                        "The referenced requirement version contains "
                        "invalid JSON."
                    ) from exc

                # Support a list, a wrapped list, or one requirement object.
                if isinstance(payload, list):
                    requirements_payload = payload

                elif isinstance(payload, dict):
                    nested = payload.get("requirements")

                    if isinstance(nested, list):
                        requirements_payload = nested

                    elif any(
                        key in payload
                        for key in (
                            "purpose",
                            "scope",
                            "rules",
                            "policy_name",
                        )
                    ):
                        requirements_payload = [payload]

                    else:
                        requirements_payload = []

                else:
                    requirements_payload = []

                if not requirements_payload:
                    raise ValueError(
                        "The referenced requirement version contains "
                        "no requirements."
                    )

                snapshot_session_id = normalize_optional_text(
                    str(snapshot["session_id"])
                    if snapshot["session_id"] is not None
                    else None
                )

                if not snapshot_session_id:
                    raise ValueError(
                        "The requirement version has no associated session."
                    )

                # Resolve authoritative records using real IDs from the
                # existing policy section mappings.
                loaded_requirements: list[ValidatedRequirementInput] = []
                seen_requirement_ids: set[str] = set()

                for raw_requirement_id in dict.fromkeys(
                    fallback_requirement_ids or []
                ):
                    requirement_id = normalize_optional_text(
                        raw_requirement_id
                    )
                    if not requirement_id:
                        continue

                    result = await session.execute(
                        text(
                            """
                            SELECT requirement_id
                            FROM requirements
                            WHERE requirement_id = :requirement_id
                              AND session_id = :session_id
                            """
                        ),
                        {
                            "requirement_id": requirement_id,
                            "session_id": snapshot_session_id,
                        },
                    )

                    matched_id = result.scalar_one_or_none()
                    if not matched_id:
                        continue

                    matched_id = str(matched_id)
                    if matched_id in seen_requirement_ids:
                        continue

                    loaded, _, _ = await load_single_requirement(
                        session=session,
                        requirement_id=matched_id,
                        session_id=snapshot_session_id,
                    )

                    for item in loaded:
                        item_id = normalize_optional_text(
                            str(item.requirement_id)
                            if getattr(item, "requirement_id", None)
                            else None
                        )

                        if item_id and item_id not in seen_requirement_ids:
                            loaded_requirements.append(item)
                            seen_requirement_ids.add(item_id)

                if loaded_requirements:
                    return loaded_requirements

                # Direct snapshot adaptation is safe only when every
                # object already contains a real requirement ID.
                if all(
                    isinstance(item, dict)
                    and normalize_optional_text(item.get("requirement_id"))
                    for item in requirements_payload
                ):
                    normalized = adapt_requirements(requirements_payload)
                    if normalized:
                        return normalized

                raise ValueError(
                    "The requirement version contains content, but its "
                    "requirement IDs could not be resolved to validated "
                    "records in the snapshot's session."
                )

        except SQLAlchemyError:
            await session.rollback()
            raise

        # 2. Resolve a session ID.
        try:
            loaded, _, _ = await load_requirements_from_session(
                session=session,
                session_id=source_reference,
            )
            if loaded:
                return loaded
        except ValueError:
            pass
        except SQLAlchemyError:
            await session.rollback()
            raise

        # 3. Resolve a requirement ID and its owning session.
        try:
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
            source_session_id = result.scalar_one_or_none()

            if source_session_id:
                loaded, _, _ = await load_single_requirement(
                    session=session,
                    requirement_id=source_reference,
                    session_id=str(source_session_id),
                )
                if loaded:
                    return loaded

        except ValueError:
            pass
        except SQLAlchemyError:
            await session.rollback()
            raise

    # 4. Recover requirements using IDs mapped to existing policy sections.
    for raw_requirement_id in dict.fromkeys(
        fallback_requirement_ids or []
    ):
        requirement_id = normalize_optional_text(raw_requirement_id)
        if not requirement_id:
            continue

        try:
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
            source_session_id = result.scalar_one_or_none()

            if source_session_id:
                loaded, _, _ = await load_single_requirement(
                    session=session,
                    requirement_id=requirement_id,
                    session_id=str(source_session_id),
                )
                if loaded:
                    return loaded

        except ValueError:
            continue
        except SQLAlchemyError:
            await session.rollback()
            raise

    return []




async def modify_policy_section(
    session: AsyncSession,
    policy_id: UUID,
    request: PolicyModificationRequest,
    requirements: list[Any] | None = None,
) -> PolicyResponse:
    """
    Revise one policy section using section_id and instructions.

    - Ignores request.updated_content.
    - Uses supplied validated requirements when available.
    - Otherwise resolves requirements using the policy's existing
      source reference and section requirement IDs.
    - Preserves existing requirement mappings.
    - Creates a new policy version without overwriting the old version.
    - Creates new versions for linked generated skills.
    """

    # ---------------------------------------------------------------
    # 1. Validate the modification request.
    # ---------------------------------------------------------------
    target_section_id = normalize_optional_text(request.section_id)
    instructions = normalize_optional_text(request.instructions)

    if not target_section_id:
        raise ValueError(
            "A valid section_id is required for policy modification."
        )

    if not instructions:
        raise ValueError(
            "Modification instructions cannot be empty."
        )

    # Do not read request.updated_content.

    # ---------------------------------------------------------------
    # 2. Load the policy and its latest version.
    # ---------------------------------------------------------------
    policy = await policy_repository.get_policy_by_id(
        session,
        policy_id,
    )

    if policy is None or not policy.versions:
        raise ValueError(f"Policy {policy_id} not found.")

    latest_version = max(
        policy.versions,
        key=lambda item: item.version,
    )

    try:
        raw_sections = json.loads(latest_version.content_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "The stored policy content is invalid JSON."
        ) from exc

    if not isinstance(raw_sections, list):
        raise ValueError(
            "The stored policy content must contain a list of sections."
        )

    current_sections = [
        PolicySectionModel.model_validate(section)
        for section in raw_sections
    ]

    # ---------------------------------------------------------------
    # 3. Find the target section.
    # ---------------------------------------------------------------
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

    # Collect requirement IDs already mapped to the policy.
    # These are fallback identifiers, not requirement content.
    fallback_requirement_ids = list(
        dict.fromkeys(
            str(requirement_id).strip()
            for section in current_sections
            for requirement_id in section.requirement_ids
            if requirement_id and str(requirement_id).strip()
        )
    )

    # ---------------------------------------------------------------
    # 4. Resolve authoritative requirements.
    # ---------------------------------------------------------------
    if requirements is not None:
        normalized_requirements = adapt_requirements(requirements)

    else:
        # First attempt: resolve the stored source reference.
        # The resolver must recognize session IDs and requirement IDs.
        # An unrecognized snapshot/version ID must not be treated
        # automatically as a requirement ID.
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

    # ---------------------------------------------------------------
    # 5. Build the authoritative requirement ID set.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # 6. Load the policy's applied skills.
    # ---------------------------------------------------------------
    try:
        applied_skills = json.loads(
            latest_version.applied_skill_ids_json or "[]"
        )
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "The policy's applied-skill metadata is invalid JSON."
        ) from exc

    if not isinstance(applied_skills, list):
        raise ValueError(
            "The policy's applied-skill metadata must be a list."
        )

    # ---------------------------------------------------------------
    # 7. Ask the revision agent to modify the target section.
    # ---------------------------------------------------------------
    revised_section = await revise_policy_section_agent(
        current_section=current_section,
        user_instructions=instructions,
        all_requirements=normalized_requirements,
        applied_skills=applied_skills,
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

    # ---------------------------------------------------------------
    # 8. Validate requirement traceability.
    # ---------------------------------------------------------------
    revised_requirement_ids = {
        str(requirement_id).strip()
        for requirement_id in revised_section.requirement_ids
        if requirement_id and str(requirement_id).strip()
    }

    unknown_ids = (
        revised_requirement_ids - source_requirement_ids
    )

    if unknown_ids:
        raise ValueError(
            "The revised section contains unknown requirement IDs: "
            + ", ".join(sorted(unknown_ids))
        )

    # Do not silently remove previously valid mappings.
    missing_existing_ids = (
        existing_requirement_ids - revised_requirement_ids
    )

    if missing_existing_ids:
        raise ValueError(
            "The revision removed existing requirement mappings: "
            + ", ".join(sorted(missing_existing_ids))
        )

    # ---------------------------------------------------------------
    # 8A. Validate the requested modification before persistence.
    # ---------------------------------------------------------------
    modification_report = validate_policy_modification(
        original_section=current_section,
        revised_section=revised_section,
        instructions=instructions,
        requirements=normalized_requirements,
    )

    if modification_report.overall_status.upper() != "PASS":
        details = "\n".join(
            f"- {finding.rule_name}: {finding.message}"
            + (f" Details: {'; '.join(finding.details)}" if finding.details else "")
            for finding in modification_report.findings
            if finding.status in {"FAIL", "NEEDS_CLARIFICATION"}
        )
        raise PolicyModificationRejected(
            "Policy modification rejected before creating a new version:\n"
            + details,
            comparison=modification_report.model_dump(),
        )

    # ---------------------------------------------------------------
    # 9. Replace only the requested section.
    # ---------------------------------------------------------------
    updated_sections = [
        revised_section
        if section.section_id == target_section_id
        else section
        for section in current_sections
    ]

    # ---------------------------------------------------------------
    # 10. Validate the complete revised policy.
    # A wording change does not mean that the user has answered prior
    # clarification questions, so carry them forward until source requirements
    # are updated and the policy is revalidated.
    inherited_clarifications = _stored_clarification_items(latest_version)
    validation_report = validate_policy_draft(
        sections=updated_sections,
        requirements=normalized_requirements,
        unresolved_items=inherited_clarifications,
    )

    # FAIL blocks persistence. NEEDS_CLARIFICATION is still a valid draft state;
    # the new version can be saved but cannot be approved.
    if validation_report.overall_status.upper() == "FAIL":
        details = "\n".join(
            f"- {finding.rule_name}: {finding.message}"
            + (
                f" Details: {'; '.join(finding.details)}"
                if finding.details else ""
            )
            for finding in validation_report.findings
            if finding.status == "FAIL"
        )
        raise PolicyModificationRejected(
            "Policy modification rejected because whole-policy validation "
            "failed. No new policy version was created:\n" + details,
            comparison=validation_report.model_dump(),
        )

    # 11. Create a new policy version and linked skill versions.
    # ---------------------------------------------------------------
    skills_root = Path(
        settings.generated_skills_path
    ).resolve()

    created_skill_files: list[Path] = []

    try:
        new_policy_version = (
            await policy_repository.create_policy_version(
                session=session,
                policy_id=policy.id,
                sections=updated_sections,
                change_summary=instructions,
                validation_status=(
                    validation_report.overall_status.lower()
                ),
                validation_report=validation_report,

                # Preserve the existing metadata for backward
                # compatibility. It is not used as the sole
                # requirement-resolution mechanism.
                source_requirement_version_id=(
                    latest_version.source_requirement_version_id
                ),
                applied_skill_ids=applied_skills,
            )
        )

        processed_skill_ids: set[UUID] = set()

        for skill_identifier in applied_skills:
            # Built-in skill names are not generated-skill UUIDs.
            try:
                skill_id = UUID(str(skill_identifier))
            except (ValueError, TypeError, AttributeError):
                continue

            if skill_id in processed_skill_ids:
                continue

            processed_skill_ids.add(skill_id)

            skill = await get_skill_by_id(
                session,
                skill_id,
            )

            if skill is None or not skill.versions:
                raise ValueError(
                    f"Linked skill '{skill_identifier}' was not found "
                    "or has no saved versions."
                )

            previous_latest = max(
                skill.versions,
                key=lambda item: item.version,
            )

            expected_version = previous_latest.version + 1

            new_skill_version = await create_next_skill_version(
                session=session,
                skill_id=skill_id,
            )

            actual_file = (
                skills_root / new_skill_version.file_path
            ).resolve()

            # Prevent paths from escaping the generated skills directory.
            actual_file.relative_to(skills_root)

            expected_file = (
                skills_root
                / str(skill_id)
                / f"v{expected_version}"
                / "SKILL.md"
            ).resolve()

            if actual_file != expected_file:
                raise RuntimeError(
                    "The generated skill version path did not match "
                    "the expected version."
                )

            created_skill_files.append(actual_file)

        await session.commit()

    except Exception:
        await session.rollback()

        # Remove files created by this operation if the database
        # transaction fails.
        for file_path in created_skill_files:
            try:
                resolved_path = file_path.resolve()
                resolved_path.relative_to(skills_root)

                if resolved_path.is_file():
                    resolved_path.unlink()

            except (OSError, ValueError):
                logger.exception(
                    "Failed to clean up generated skill file: %s",
                    file_path,
                )

        raise

    # ---------------------------------------------------------------
    # 12. Save the new policy document.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # 13. Return the new policy version.
    # ---------------------------------------------------------------
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
    """Approve a specific version of a policy without validation checks."""

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