"""Application service for generating, validating, persisting, and modifying enterprise policies."""

import json
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from app.agents.policy_generation.policy_generator import (
    StructuredPolicyGenerationOutput,
    generate_policy_from_skill,
    load_requirements_from_selected_skills,
)
from app.agents.policy_generation.policy_modification import (
    analyze_policy_feedback,
    modify_skill_content,
    validate_skill_modification_output,
)
from app.agents.policy_generation.policy_validation import validate_policy_semantics
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
from app.models.skill_db import SkillVersion
from app.repositories import policy_repository
from app.repositories.skill_repository import (
    activate_skill_version,
    create_skill_version_from_content,
    get_skill_by_id,
    get_skill_by_name,
)
from app.services.skill_file_service import (
    rebuild_skill_markdown,
    split_skill_markdown,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


def _build_semantic_validation_report(
    semantic_report: Any,
    total_requirements: int,
) -> PolicyValidationReport:
    """Adapt semantic validation output to the persisted API report model."""
    missing_requirements = list(
        dict.fromkeys(semantic_report.missing_requirements or [])
    )

    # Semantic output currently has no coverage_score field. Until that
    # field is added to the semantic output model, derive a conservative
    # coverage estimate from the requirements explicitly marked missing.
    if total_requirements > 0:
        missing_count = min(len(missing_requirements), total_requirements)
        coverage_score = round(
            (total_requirements - missing_count) / total_requirements,
            4,
        )
    else:
        coverage_score = 1.0

    return PolicyValidationReport(
        overall_status=semantic_report.overall_status,
        coverage_score=coverage_score,
        missing_requirements=missing_requirements,
        findings=semantic_report.findings or [],
        clarification_items=semantic_report.clarification_items or [],
    )


def _log_validation_summary(
    workflow_id: str,
    stage: str,
    report: Any,
    duration_seconds: float,
) -> None:
    """Log validation status and counts without exposing policy content."""
    status_counts = {
        status: sum(
            finding.status == status
            for finding in report.findings
        )
        for status in ("PASS", "FAIL", "NEEDS_CLARIFICATION")
    }

    logger.info(
        "[%s] %s validation completed: status=%s coverage=%s "
        "findings=%s missing_requirements=%d clarification_items=%d "
        "duration_seconds=%.2f.",
        workflow_id,
        stage,
        report.overall_status,
        getattr(report, "coverage_score", None),
        status_counts,
        len(report.missing_requirements),
        len(report.clarification_items),
        duration_seconds,
    )


VALIDATION_STATUS_MAP = {
    "PASS": "pass",
    "FAIL": "fail",
    "NEEDS_CLARIFICATION": "needs_clarification",
}
#Error raised when a policy modification fails validation.
class PolicyModificationRejected(ValueError):
    """Raised when a policy modification fails validation."""

    def __init__(
        self,
        message: str,
        comparison: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.comparison = comparison
        
#Error raised when initial policy generation fails validation.
class PolicyGenerationRejected(ValueError):
    """Raised when initial policy generation fails validation."""

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
    """
    Format structured policy sections into handbook-style policy text.

    Uses hierarchical section numbering:
        1. MAIN SECTION
        1.1 Subsection
        1.2 Subsection
        2. NEXT MAIN SECTION

    Requirement IDs are excluded from readable policy text.
    They remain available in structured data for traceability.
    """

    lines: list[str] = [
        title.strip().upper(),
        "",
        f"Domain: {domain}",
        f"Version: {version}",
        f"Status: {status.upper()}",
        "",
    ]

    if description and description.strip():
        lines.extend([
            description.strip(),
            "",
        ])

    # Table of contents
    if sections:
        lines.extend([
            "TABLE OF CONTENTS",
            "",
        ])

        for section in sections:
            section_id = section.section_id.strip()
            section_title = section.title.strip()

            lines.append(f"{section_id}. {section_title}")

        lines.append("")

    # Complete policy content
    for section in sections:
        section_id = section.section_id.strip()
        section_title = section.title.strip()
        section_content = section.content.strip()

        # Main section heading
        if "." not in section_id:
            heading = (
                f"{section_id}. {section_title.upper()}"
            )
        else:
            # Subsection heading
            heading = (
                f"{section_id} {section_title}"
            )

        lines.extend([
            heading,
            "",
            section_content,
            "",
        ])

    return "\n".join(lines).strip() + "\n"



def get_current_skill_version(skill: Any) -> SkillVersion:
    """Return the active skill version, or latest version if none is active."""

    if not skill.versions:
        raise ValueError(
            f"Skill '{skill.name}' has no saved versions."
        )

    active_versions = [
        version
        for version in skill.versions
        if version.status == "active"
    ]

    if active_versions:
        return max(active_versions, key=lambda item: item.version)

    return max(skill.versions, key=lambda item: item.version)


async def load_skill_instructions(
    session: AsyncSession,
    skill_command: str | None,
    skill_ids: list[UUID] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Resolve generated skills and their current versions."""

    applied_skill_ids: list[str] = []
    applied_skill_version_ids: list[str] = []

    selected_ids = list(dict.fromkeys(skill_ids or []))
    command_name = normalize_optional_text(skill_command)

    if command_name:
        command_name = command_name.lstrip("/").strip()

        if not command_name:
            raise ValueError("The skill command cannot be empty.")

        database_skill = await get_skill_by_name(
            session,
            command_name,
        )

        if database_skill is None:
            raise ValueError(
                f"Generated skill '{command_name}' was not found."
            )

        latest_version = get_current_skill_version(database_skill)

        if not normalize_optional_text(latest_version.content):
            raise ValueError(
                f"Generated skill '{command_name}' has no stored content."
            )

        applied_skill_ids.append(str(database_skill.id))
        applied_skill_version_ids.append(str(latest_version.id))

    for skill_id in selected_ids:
        database_skill = await get_skill_by_id(
            session,
            skill_id,
        )

        if database_skill is None:
            raise ValueError(
                f"Generated skill '{skill_id}' was not found."
            )

        latest_version = get_current_skill_version(database_skill)

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

    logger.debug(
        "Resolved generated skill references: skill_count=%d "
        "version_count=%d.",
        len(applied_skill_ids),
        len(applied_skill_version_ids),
    )

    return (
        [],
        applied_skill_ids,
        applied_skill_version_ids,
    )
    
    
async def load_selected_skill_instructions(
    session: AsyncSession,
    skill_ids: list[str],
    skill_version_ids: list[str],
) -> list[dict[str, Any]]:
    """
    Load the exact selected generated skill-version contents.

    The policy validation agent receives the same skill versions
    that were used by the policy generation agent.
    """

    if len(skill_ids) != len(skill_version_ids):
        raise ValueError(
            "Skill IDs and skill-version IDs do not match."
        )

    selected_instructions: list[dict[str, Any]] = []

    for skill_id, version_id in zip(
        skill_ids,
        skill_version_ids,
    ):
        database_skill = await get_skill_by_id(
            session,
            UUID(skill_id),
        )

        if database_skill is None:
            raise ValueError(
                f"Generated skill '{skill_id}' was not found."
            )

        selected_version = next(
            (
                item
                for item in database_skill.versions
                if str(item.id) == str(version_id)
            ),
            None,
        )

        if selected_version is None:
            raise ValueError(
                f"Skill version '{version_id}' does not belong "
                f"to skill '{database_skill.name}'."
            )

        content = normalize_optional_text(
            selected_version.content
        )

        if not content:
            raise ValueError(
                f"Skill '{database_skill.name}' version "
                f"{selected_version.version} has no content."
            )

        selected_instructions.append(
            {
                "skill_id": str(database_skill.id),
                "skill_name": database_skill.name,
                "skill_version_id": str(selected_version.id),
                "content": content,
            }
        )

    return selected_instructions




async def resolve_modification_skill_baseline(
    session: AsyncSession,
    skill_id: UUID,
    policy_linked_skill_version_id: UUID,
    workflow_id: str,
) -> SkillVersion:
    """
    Resolve the SkillVersion used as the baseline for modification.

    Reuse a newer draft version if a previous modification created
    one but failed before a new PolicyVersion was saved.

    Otherwise, use the exact SkillVersion linked to the latest
    PolicyVersion.
    """
    skill = await get_skill_by_id(
        session=session,
        skill_id=skill_id,
    )

    if skill is None:
        raise ValueError(f"Skill '{skill_id}' was not found.")

    if not skill.versions:
        raise ValueError(
            f"Skill '{skill_id}' has no saved versions."
        )

    policy_linked_version = next(
        (
            version
            for version in skill.versions
            if version.id == policy_linked_skill_version_id
        ),
        None,
    )

    if policy_linked_version is None:
        raise ValueError(
            "The SkillVersion referenced by the latest "
            "PolicyVersion does not belong to the selected skill."
        )

    newer_draft_versions = [
        version
        for version in skill.versions
        if (
            version.version > policy_linked_version.version
            and str(version.status).casefold() == "draft"
        )
    ]

    if newer_draft_versions:
        selected_version = max(
            newer_draft_versions,
            key=lambda item: item.version,
        )

        logger.info(
            "[%s] Reusing previous unlinked draft SkillVersion: "
            "skill_id=%s selected_version_id=%s version=%s.",
            workflow_id,
            skill_id,
            selected_version.id,
            selected_version.version,
        )

    else:
        selected_version = policy_linked_version

        logger.info(
            "[%s] Using PolicyVersion-linked SkillVersion: "
            "skill_id=%s version_id=%s version=%s.",
            workflow_id,
            skill_id,
            selected_version.id,
            selected_version.version,
        )

    return selected_version


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
    policy_record: Policy,
    version_record: PolicyVersion,
) -> PolicyResponse:
    """Build the complete API response from policy and version records."""

    sections_data = json.loads(
        version_record.content_json or "[]"
    )

    sections = [
        PolicySectionModel.model_validate(section)
        for section in sections_data
    ]

    applied_skills = json.loads(
        version_record.applied_skill_ids_json or "[]"
    )

    applied_skill_versions = json.loads(
        version_record.applied_skill_version_ids_json or "[]"
    )

    validation_report = None

    if version_record.validation_report_json:
        validation_report_data = json.loads(
            version_record.validation_report_json
        )

        validation_report = PolicyValidationReport.model_validate(
            validation_report_data
        )

    return PolicyResponse(
        policy_id=policy_record.id,
        version=version_record.version,
        title=policy_record.title,

        
        description=policy_record.description,

        domain=policy_record.domain,
        policy_status=policy_record.status,
        status=version_record.status,
        sections=sections,
        policy_text=version_record.content_text,
        applied_skill_ids=applied_skills,
        applied_skill_version_ids=applied_skill_versions,
        source_requirement_version_id=(
            str(version_record.source_requirement_version_id)
            if version_record.source_requirement_version_id
            else None
        ),
        validation_status=version_record.validation_status,
        validation_report=validation_report,
        change_summary=version_record.change_summary,
        created_at=version_record.created_at,
    )



def extract_policy_metadata_from_skill_requirements(
    requirements: list[dict[str, Any]],
) -> dict[str, str]:
    """Extract shared policy metadata from skill Source Requirements."""

    if not requirements:
        raise ValueError(
            "Selected skill contains no Source Requirements."
        )

    required_fields = ("policy_name", "domain", "purpose")
    metadata: dict[str, str] = {}

    for requirement in requirements:
        # Match the key returned by the requirements loader.
        requirement_text = requirement.get(
            "requirement_text",
            requirement.get("text"),
        )

        if not isinstance(requirement_text, str):
            raise ValueError(
                f"Invalid Source Requirements content for "
                f"requirement {requirement.get('requirement_id')}."
            )

        try:
            requirement_data = json.loads(requirement_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Requirement {requirement.get('requirement_id')} "
                "does not contain valid JSON."
            ) from exc

        if not isinstance(requirement_data, dict):
            raise ValueError(
                "Each Source Requirement must contain a JSON object."
            )

        for field in required_fields:
            value = normalize_optional_text(
                requirement_data.get(field)
            )

            if not value:
                raise ValueError(
                    f"Required policy metadata '{field}' is missing "
                    "from Source Requirements."
                )

            existing_value = metadata.get(field)

            if (
                existing_value
                and existing_value.casefold() != value.casefold()
            ):
                raise ValueError(
                    f"Conflicting '{field}' values found in "
                    "Source Requirements."
                )

            metadata[field] = value

    return metadata



async def generate_and_save_policy(
    session: AsyncSession,
    request: PolicyGenerationRequest,
) -> PolicyResponse:
    """Generate, validate, and persist a policy from a generated skill."""

    workflow_id = uuid4().hex[:12]
    workflow_started = perf_counter()

    # 1. Resolve the generated skill.
    skill_command = normalize_optional_text(request.skill_command)

    if not skill_command:
        logger.warning(
            "[%s] Policy generation rejected: skill_command is empty.",
            workflow_id,
        )
        raise ValueError("Skill command cannot be empty.")

    logger.info("[%s] Policy generation started.", workflow_id)

    skill_resolution_started = perf_counter()
    try:
        (
            _,
            applied_skill_ids,
            applied_skill_version_ids,
        ) = await load_skill_instructions(
            session=session,
            skill_command=skill_command,
            skill_ids=[],
        )
    except Exception:
        logger.exception(
            "[%s] Failed to resolve the requested generated skill.",
            workflow_id,
        )
        raise

    if len(applied_skill_ids) != 1 or len(applied_skill_version_ids) != 1:
        logger.warning(
            "[%s] Policy generation requires exactly one generated skill; "
            "resolved skills=%d versions=%d.",
            workflow_id,
            len(applied_skill_ids),
            len(applied_skill_version_ids),
        )
        raise ValueError(
            "Policy generation requires exactly one generated skill."
        )

    skill_id = UUID(applied_skill_ids[0])
    skill_version_id = UUID(applied_skill_version_ids[0])
    logger.info(
        "[%s] Generated skill resolved: skill_id=%s "
        "skill_version_id=%s duration_seconds=%.2f.",
        workflow_id,
        skill_id,
        skill_version_id,
        perf_counter() - skill_resolution_started,
    )

    # 2. Load the exact selected skill version.
    skill_load_started = perf_counter()
    try:
        selected_skill_instructions = (
            await load_selected_skill_instructions(
                session=session,
                skill_ids=applied_skill_ids,
                skill_version_ids=applied_skill_version_ids,
            )
        )

        if len(selected_skill_instructions) != 1:
            raise ValueError("Could not load the selected skill version.")

        database_skill = await get_skill_by_id(session, skill_id)

        if database_skill is None:
            raise ValueError(f"Generated skill '{skill_id}' was not found.")

        skill_version = await session.get(
            SkillVersion,
            skill_version_id,
        )

        if skill_version is None or skill_version.skill_id != skill_id:
            raise ValueError(
                "Selected skill version does not belong to the skill."
            )
    except Exception:
        logger.exception(
            "[%s] Failed to load the exact selected skill version: "
            "skill_id=%s skill_version_id=%s.",
            workflow_id,
            skill_id,
            skill_version_id,
        )
        raise

    logger.info(
        "[%s] Exact skill version loaded: skill_id=%s "
        "skill_version_id=%s duration_seconds=%.2f.",
        workflow_id,
        skill_id,
        skill_version_id,
        perf_counter() - skill_load_started,
    )

    # 3. Extract policy metadata from Source Requirements.
    source_load_started = perf_counter()
    try:
        source_requirements = await load_requirements_from_selected_skills(
            selected_skill_version_ids=[skill_version_id],
            session_factory=AsyncSessionLocal,
        )

        metadata = extract_policy_metadata_from_skill_requirements(
            source_requirements
        )
    except Exception:
        logger.exception(
            "[%s] Failed to load policy Source Requirements or metadata: "
            "skill_version_id=%s.",
            workflow_id,
            skill_version_id,
        )
        raise

    policy_title = metadata["policy_name"]
    policy_domain = metadata["domain"]
    purpose = metadata["purpose"]
    logger.info(
        "[%s] Policy source loaded: requirement_count=%d "
        "skill_version_id=%s duration_seconds=%.2f.",
        workflow_id,
        len(source_requirements),
        skill_version_id,
        perf_counter() - source_load_started,
    )

    # 4. Generate the policy using the exact skill version.
    generation_started = perf_counter()
    try:
        policy_output = await generate_policy_from_skill(
            selected_skill_version_ids=[skill_version_id],
            session_factory=AsyncSessionLocal,
            custom_title=policy_title,
            domain=policy_domain,
            custom_description=purpose,
        )
    except Exception:
        logger.exception(
            "[%s] Policy generation agent failed: skill_version_id=%s.",
            workflow_id,
            skill_version_id,
        )
        raise

    if not policy_output:
        logger.error(
            "[%s] Policy generation agent returned no output: "
            "skill_version_id=%s.",
            workflow_id,
            skill_version_id,
        )
        raise ValueError(
            "The policy-generation agent returned no output."
        )

    logger.info(
        "[%s] Policy draft generated: sections=%d unresolved_items=%d "
        "duration_seconds=%.2f.",
        workflow_id,
        len(policy_output.sections),
        len(policy_output.unresolved_items),
        perf_counter() - generation_started,
    )

    try:
        reject_placeholder_policy_content(policy_output)
    except ValueError:
        logger.warning(
            "[%s] Generated policy contains empty or placeholder content.",
            workflow_id,
        )
        raise

    final_description = (
        normalize_optional_text(policy_output.description) or purpose
    )

    # 5. Run semantic policy validation only.
    semantic_started = perf_counter()
    try:
        semantic_report = await validate_policy_semantics(
            sections=policy_output.sections,
            selected_skill_version_ids=[skill_version_id],
            session_factory=AsyncSessionLocal,
            operation="generation",
            skill_instructions=selected_skill_instructions,
            policy_metadata={
                "title": policy_title,
                "domain": policy_domain,
            },
        )
    except Exception:
        logger.exception(
            "[%s] Semantic policy validation failed: skill_version_id=%s.",
            workflow_id,
            skill_version_id,
        )
        raise

    validation_report = _build_semantic_validation_report(
        semantic_report=semantic_report,
        total_requirements=len(source_requirements),
    )

    _log_validation_summary(
        workflow_id,
        "Semantic policy",
        validation_report,
        perf_counter() - semantic_started,
    )

    # 8.Reject failed validation before policy persistence.
    if validation_report.overall_status.upper() == "FAIL":

        details = "\n".join(
            f"- {finding.rule_name}: {finding.message}"
            for finding in validation_report.findings
            if finding.status.upper() == "FAIL"
        )

        failed_rules = [
            finding.rule_name
            for finding in validation_report.findings
            if finding.status.upper() == "FAIL"
        ]
        logger.error(
            "[%s] Policy generation rejected by validation: "
            "skill_id=%s skill_version_id=%s failed_rules=%s.",
            workflow_id,
            skill_id,
            skill_version_id,
            failed_rules,
        )

        raise PolicyGenerationRejected(
            "Policy generation failed validation. "
            "No policy record or version was created:\n" + details,
            comparison=validation_report.model_dump(),
        )

    # 9. Prepare the policy document.
    text_content = format_policy_document_text(
        title=policy_title,
        domain=policy_domain,
        version=1,
        sections=policy_output.sections,
        description=final_description,
        status="draft",
    )

    # 10. Preserve original requirement lineage.
    source_version_id = skill_version.source_requirement_version_id

    # 11. Map validation status.
    validation_status = VALIDATION_STATUS_MAP[
        validation_report.overall_status.upper()
    ]

    # 12. Persist the policy and first version.
    persistence_started = perf_counter()
    try:
        policy = await policy_repository.create_policy(
            session=session,
            title=policy_title,
            domain=policy_domain,
            sections=policy_output.sections,
            content_text=text_content,
            description=final_description,
            applied_skill_ids=applied_skill_ids,
            applied_skill_version_ids=applied_skill_version_ids,
            validation_status=validation_status,
            validation_report=validation_report,
            source_requirement_version_id=source_version_id,
            change_summary=(
                "Initial policy draft generated from the selected skill."
            ),
        )

        await session.commit()
    except Exception:
        logger.exception(
            "[%s] Failed to persist generated policy: "
            "skill_id=%s skill_version_id=%s.",
            workflow_id,
            skill_id,
            skill_version_id,
        )
        raise

    if not policy.versions:
        raise RuntimeError(
            "Policy was created but its first version was not returned."
        )

    first_version = max(
        policy.versions,
        key=lambda item: item.version,
    )

    if validation_status == "needs_clarification":
        logger.warning(
            "[%s] Policy draft saved with unresolved clarification items: "
            "policy_id=%s version=%d clarification_count=%d.",
            workflow_id,
            policy.id,
            first_version.version,
            len(validation_report.clarification_items),
        )

    logger.info(
        "[%s] Policy generation completed: policy_id=%s version=%d "
        "validation_status=%s duration_seconds=%.2f "
        "persistence_seconds=%.2f.",
        workflow_id,
        policy.id,
        first_version.version,
        validation_status,
        perf_counter() - workflow_started,
        perf_counter() - persistence_started,
    )

    return _build_policy_response(policy, first_version)




async def modify_policy(
    session: AsyncSession,
    policy_id: UUID,
    request: PolicyModificationRequest,
) -> PolicyResponse:
    """
    Apply user feedback and regenerate the complete policy.

    The latest PolicyVersion provides the original SkillVersion
    reference.

    If a previous modification created a newer draft SkillVersion
    but failed before saving a PolicyVersion, reuse that draft.

    Original SkillVersions and requirement database records
    remain unchanged.
    """

    workflow_id = uuid4().hex[:12]
    workflow_started = perf_counter()

    # ---------------------------------------------------------
    # 1. Validate feedback
    # ---------------------------------------------------------
    feedback = normalize_optional_text(request.feedback)

    if not feedback:
        logger.warning(
            "[%s] Policy modification rejected: feedback is empty "
            "for policy_id=%s.",
            workflow_id,
            policy_id,
        )
        raise ValueError("Policy feedback cannot be empty.")

    logger.info(
        "[%s] Policy modification started: policy_id=%s.",
        workflow_id,
        policy_id,
    )

    # ---------------------------------------------------------
    # 2. Load policy and latest version
    # ---------------------------------------------------------
    policy = await policy_repository.get_policy_by_id(
        session=session,
        policy_id=policy_id,
    )

    if policy is None or not policy.versions:
        logger.warning(
            "[%s] Policy modification target not found: policy_id=%s.",
            workflow_id,
            policy_id,
        )
        raise ValueError(f"Policy '{policy_id}' not found.")

    latest_version = max(
        policy.versions,
        key=lambda item: item.version,
    )

    logger.info(
        "[%s] Baseline policy loaded: policy_id=%s version=%d.",
        workflow_id,
        policy_id,
        latest_version.version,
    )

    # ---------------------------------------------------------
    # 3. Resolve skill references
    # ---------------------------------------------------------
    try:
        skill_ids = json.loads(
            latest_version.applied_skill_ids_json or "[]"
        )

        skill_version_ids = json.loads(
            latest_version.applied_skill_version_ids_json or "[]"
        )

    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "The policy contains invalid skill-version metadata."
        ) from exc

    if not isinstance(skill_ids, list) or not isinstance(
        skill_version_ids, list
    ):
        raise ValueError(
            "Invalid skill references in the policy version."
        )

    if not skill_ids or not skill_version_ids:
        raise ValueError(
            "The policy does not contain the skill references "
            "required for modification."
        )

    if len(skill_ids) != len(skill_version_ids):
        raise ValueError(
            "Skill IDs and skill-version IDs do not match."
        )

    # Current workflow supports one generated skill per policy.
    if len(skill_ids) != 1:
        raise ValueError(
            "Policy modification currently supports exactly "
            "one generated skill per policy."
        )

    # ---------------------------------------------------------
    # 4. Validate identifiers and resolve modification baseline
    # ---------------------------------------------------------
    try:
        skill_id = UUID(str(skill_ids[0]))

        policy_linked_skill_version_id = UUID(
            str(skill_version_ids[0])
        )

    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(
            "The policy contains an invalid skill or skill-version ID."
        ) from exc

    baseline_skill_version = await resolve_modification_skill_baseline(
        session=session,
        skill_id=skill_id,
        policy_linked_skill_version_id=policy_linked_skill_version_id,
        workflow_id=workflow_id,
    )

    base_skill_version_id = baseline_skill_version.id

    logger.info(
        "[%s] Modification baseline selected: "
        "skill_id=%s policy_linked_version_id=%s "
        "selected_baseline_version_id=%s version_number=%s.",
        workflow_id,
        skill_id,
        policy_linked_skill_version_id,
        base_skill_version_id,
        baseline_skill_version.version,
    )

    # ---------------------------------------------------------
    # 5. Load exact baseline skill version
    # ---------------------------------------------------------
    selected_skill_instructions = await load_selected_skill_instructions(
        session=session,
        skill_ids=[str(skill_id)],
        skill_version_ids=[str(base_skill_version_id)],
    )

    if len(selected_skill_instructions) != 1:
        logger.error(
            "[%s] Could not load the baseline skill version: "
            "policy_id=%s skill_id=%s skill_version_id=%s.",
            workflow_id,
            policy_id,
            skill_id,
            base_skill_version_id,
        )
        raise ValueError(
            "Could not load the exact skill version used by the policy."
        )

    original_skill_content = selected_skill_instructions[0]["content"]

    # ---------------------------------------------------------
    # 6. Extract skill instructions and Source Requirements
    # ---------------------------------------------------------
    (
        _,
        existing_instructions,
        existing_source_requirements,
    ) = split_skill_markdown(original_skill_content)

    if not existing_instructions.strip():
        raise ValueError(
            "The selected skill has no instructions."
        )

    if not existing_source_requirements.strip():
        raise ValueError(
            "The selected skill has no Source Requirements."
        )

    # ---------------------------------------------------------
    # 7. Analyze user feedback
    # ---------------------------------------------------------
    feedback_analysis_started = perf_counter()

    try:
        feedback_analysis = await analyze_policy_feedback(
            feedback=feedback,
            existing_skill_instructions=existing_instructions,
            existing_source_requirements=existing_source_requirements,
        )

    except Exception:
        logger.exception(
            "[%s] Policy feedback analysis failed: policy_id=%s "
            "baseline_version=%d.",
            workflow_id,
            policy_id,
            baseline_skill_version.version,
        )
        raise

    change_scope = feedback_analysis.change_scope

    allowed_scopes = {
        "none",
        "instructions",
        "source_requirements",
        "both",
    }

    if change_scope not in allowed_scopes:
        raise ValueError(
            f"Unsupported skill modification scope: {change_scope}"
        )

    requires_skill_modification = (
        feedback_analysis.requires_skill_modification
    )

    logger.info(
        "[%s] Policy feedback analyzed: skill_change_required=%s "
        "change_scope=%s duration_seconds=%.2f.",
        workflow_id,
        requires_skill_modification,
        change_scope,
        perf_counter() - feedback_analysis_started,
    )

    if requires_skill_modification and change_scope == "none":
        raise ValueError(
            "Feedback analysis requested skill modification "
            "but returned scope 'none'."
        )

    if not requires_skill_modification and change_scope != "none":
        raise ValueError(
            "Feedback analysis returned an inconsistent "
            "skill modification decision."
        )

    # ---------------------------------------------------------
    # 8. Initialize selected skill version
    # ---------------------------------------------------------
    selected_skill_version_id = base_skill_version_id
    modification_summary = None

    if requires_skill_modification:

        # 8.1 Modify the existing skill content.
        skill_modification_started = perf_counter()

        try:
            skill_modification = await modify_skill_content(
                feedback=feedback,
                existing_instructions=existing_instructions,
                existing_source_requirements=existing_source_requirements,
                change_scope=change_scope,
                change_reason=feedback_analysis.reason,
            )

        except Exception:
            logger.exception(
                "[%s] Skill modification agent failed: "
                "skill_id=%s base_skill_version_id=%s scope=%s.",
                workflow_id,
                skill_id,
                base_skill_version_id,
                change_scope,
            )
            raise

        logger.info(
            "[%s] Skill modification generated: skill_id=%s "
            "base_skill_version_id=%s scope=%s duration_seconds=%.2f.",
            workflow_id,
            skill_id,
            base_skill_version_id,
            change_scope,
            perf_counter() - skill_modification_started,
        )

        # 8.2 Resolve optional output according to scope.
        revised_instructions = skill_modification.instructions

        revised_source_requirements = (
            skill_modification.source_requirements
        )

        if revised_instructions is None:
            if change_scope == "source_requirements":
                revised_instructions = existing_instructions
            else:
                raise ValueError(
                    "Skill Modification Agent did not return "
                    "the required instructions."
                )

        if revised_source_requirements is None:
            if change_scope == "instructions":
                revised_source_requirements = (
                    existing_source_requirements
                )
            else:
                raise ValueError(
                    "Skill Modification Agent did not return "
                    "the required Source Requirements."
                )

        # 8.3 Validate output types.
        if not isinstance(revised_instructions, str):
            raise ValueError(
                "Skill Modification Agent returned invalid instructions."
            )

        if not isinstance(revised_source_requirements, str):
            raise ValueError(
                "Skill Modification Agent returned invalid "
                "Source Requirements."
            )

        if not revised_instructions.strip():
            raise ValueError(
                "Skill Modification Agent returned empty instructions."
            )

        if not revised_source_requirements.strip():
            raise ValueError(
                "Skill Modification Agent returned empty "
                "Source Requirements."
            )

        # 8.4 Validate skill modification consistency.
        validate_skill_modification_output(
            original_instructions=existing_instructions,
            original_source_requirements=existing_source_requirements,
            revised_instructions=revised_instructions,
            revised_source_requirements=revised_source_requirements,
            change_scope=change_scope,
        )

        # 8.5 Rebuild skill Markdown while preserving frontmatter.
        revised_skill_content = rebuild_skill_markdown(
            existing_content=original_skill_content,
            revised_instructions=revised_instructions,
            revised_source_requirements=revised_source_requirements,
        )

        # 8.6 Create a new skill version.
        skill_persistence_started = perf_counter()

        try:
            new_skill_version = await create_skill_version_from_content(
                session=session,
                skill_id=skill_id,
                base_skill_version_id=base_skill_version_id,
                content=revised_skill_content,
            )

            # The policy generator reads through a separate DB session.
            await session.commit()

        except Exception:
            logger.exception(
                "[%s] Failed to create or commit revised skill version: "
                "skill_id=%s base_skill_version_id=%s.",
                workflow_id,
                skill_id,
                base_skill_version_id,
            )
            raise

        selected_skill_version_id = new_skill_version.id
        modification_summary = skill_modification.change_summary

        logger.info(
            "[%s] Revised skill version committed: skill_id=%s "
            "base_version_id=%s new_version_id=%s scope=%s "
            "duration_seconds=%.2f.",
            workflow_id,
            skill_id,
            base_skill_version_id,
            selected_skill_version_id,
            change_scope,
            perf_counter() - skill_persistence_started,
        )

    # ---------------------------------------------------------
    # 9. Prepare exact selected skill references
    # ---------------------------------------------------------
    selected_skill_version_ids = [
        selected_skill_version_id
    ]

    selected_skill_ids = [
        str(skill_id)
    ]

    selected_skill_version_id_strings = [
        str(selected_skill_version_id)
    ]

    logger.info(
        "[%s] Policy regeneration source selected: policy_id=%s "
        "skill_id=%s skill_version_id=%s.",
        workflow_id,
        policy_id,
        skill_id,
        selected_skill_version_id,
    )

    # ---------------------------------------------------------
    # 10. Regenerate the complete policy
    # ---------------------------------------------------------
    generation_started = perf_counter()

    try:
        policy_output: StructuredPolicyGenerationOutput = (
            await generate_policy_from_skill(
                selected_skill_version_ids=selected_skill_version_ids,
                session_factory=AsyncSessionLocal,
                custom_title=policy.title,
                domain=policy.domain,
                custom_description=policy.description,
                additional_generation_guidance=(
                    feedback_analysis.policy_generation_guidance
                ),
            )
        )

    except Exception:
        logger.exception(
            "[%s] Policy regeneration failed: policy_id=%s "
            "base_version=%d skill_version_id=%s.",
            workflow_id,
            policy_id,
            latest_version.version,
            selected_skill_version_id,
        )
        raise

    if not policy_output:
        logger.error(
            "[%s] Policy generator returned no output: policy_id=%s.",
            workflow_id,
            policy_id,
        )
        raise ValueError(
            "The policy-generation agent returned no output."
        )

    logger.info(
        "[%s] Complete policy regenerated: policy_id=%s "
        "sections=%d unresolved_items=%d duration_seconds=%.2f.",
        workflow_id,
        policy_id,
        len(policy_output.sections),
        len(policy_output.unresolved_items),
        perf_counter() - generation_started,
    )

    try:
        reject_placeholder_policy_content(policy_output)

    except ValueError:
        logger.warning(
            "[%s] Regenerated policy contains empty or placeholder content: "
            "policy_id=%s.",
            workflow_id,
            policy_id,
        )
        raise

    # ---------------------------------------------------------
    # 11. Load requirements from the exact selected skill version
    # ---------------------------------------------------------
    requirement_load_started = perf_counter()

    try:
        skill_requirements = await load_requirements_from_selected_skills(
            selected_skill_version_ids=selected_skill_version_ids,
            session_factory=AsyncSessionLocal,
        )

    except Exception:
        logger.exception(
            "[%s] Failed to load Source Requirements for validation: "
            "skill_version_id=%s.",
            workflow_id,
            selected_skill_version_id,
        )
        raise

    logger.info(
        "[%s] Source Requirements loaded for validation: count=%d "
        "skill_version_id=%s duration_seconds=%.2f.",
        workflow_id,
        len(skill_requirements),
        selected_skill_version_id,
        perf_counter() - requirement_load_started,
    )

    if not skill_requirements:
        raise ValueError(
            "The selected skill version contains no Source Requirements."
        )

    # ---------------------------------------------------------
    # 12. Load exact selected skill version for validation
    # ---------------------------------------------------------
    selected_skill_instructions = await load_selected_skill_instructions(
        session=session,
        skill_ids=selected_skill_ids,
        skill_version_ids=selected_skill_version_id_strings,
    )

    if len(selected_skill_instructions) != 1:
        raise ValueError(
            "Could not load the exact selected skill version "
            "for policy validation."
        )

    # ---------------------------------------------------------
    # 13. Semantic policy validation only
    # ---------------------------------------------------------
    semantic_started = perf_counter()

    try:
        semantic_report = await validate_policy_semantics(
            sections=policy_output.sections,
            selected_skill_version_ids=selected_skill_version_ids,
            session_factory=AsyncSessionLocal,
            operation="generation",
            skill_instructions=selected_skill_instructions,
            policy_metadata={
                "title": policy.title,
                "domain": policy.domain,
            },
        )

    except Exception:
        logger.exception(
            "[%s] Semantic policy validation failed: policy_id=%s "
            "skill_version_id=%s.",
            workflow_id,
            policy_id,
            selected_skill_version_id,
        )
        raise

    validation_report = _build_semantic_validation_report(
        semantic_report=semantic_report,
        total_requirements=len(skill_requirements),
    )

    _log_validation_summary(
        workflow_id,
        "Semantic policy modification",
        validation_report,
        perf_counter() - semantic_started,
    )

    logger.info(
        "[%s] Policy modification validation finished: "
        "policy_id=%s base_version=%d candidate_version=%d.",
        workflow_id,
        policy.id,
        latest_version.version,
        latest_version.version + 1,
    )

    # ---------------------------------------------------------
    # 14. Reject failed validation
    # ---------------------------------------------------------
    if validation_report.overall_status.upper() == "FAIL":

        details = "\n".join(
            f"- {finding.rule_name}: {finding.message}"
            for finding in validation_report.findings
            if finding.status.upper() == "FAIL"
        )

        failed_rules = [
            finding.rule_name
            for finding in validation_report.findings
            if finding.status.upper() == "FAIL"
        ]

        logger.error(
            "[%s] Policy modification rejected by validation: "
            "policy_id=%s base_version=%d failed_rules=%s.",
            workflow_id,
            policy_id,
            latest_version.version,
            failed_rules,
        )

        raise PolicyModificationRejected(
            "Policy regeneration failed validation. "
            "No new policy version was created:\n" + details,
            comparison=validation_report.model_dump(),
        )

    # ---------------------------------------------------------
    # 15. Prepare new policy version
    # ---------------------------------------------------------
    next_version = latest_version.version + 1

    final_description = (
        normalize_optional_text(policy_output.description)
        or policy.description
    )

    text_content = format_policy_document_text(
        title=policy.title,
        domain=policy.domain,
        version=next_version,
        sections=policy_output.sections,
        description=final_description,
        status="draft",
    )

    # Build change summary.
    change_summary_parts = [feedback]

    if modification_summary:
        change_summary_parts.append(
            f"Skill modification: {modification_summary}"
        )

    change_summary = "\n".join(change_summary_parts)

    validation_status = VALIDATION_STATUS_MAP[
        validation_report.overall_status.upper()
    ]

    # ---------------------------------------------------------
    # 16. Save new policy version with exact lineage
    # ---------------------------------------------------------
    persistence_started = perf_counter()

    try:
        new_policy_version = await policy_repository.create_policy_version(
            session=session,
            policy_id=policy.id,
            sections=policy_output.sections,
            content_text=text_content,
            change_summary=change_summary,
            validation_status=validation_status,
            validation_report=validation_report,

            # Preserve the original source requirement lineage.
            # Feedback-derived Source Requirements are stored in
            # the newly created SkillVersion.
            source_requirement_version_id=(
                latest_version.source_requirement_version_id
            ),

            # Store the exact skill version used for regeneration.
            applied_skill_ids=selected_skill_ids,
            applied_skill_version_ids=selected_skill_version_id_strings,
        )

        await session.commit()

    except Exception:
        logger.exception(
            "[%s] Failed to persist regenerated policy: "
            "policy_id=%s candidate_version=%d "
            "skill_version_id=%s.",
            workflow_id,
            policy_id,
            next_version,
            selected_skill_version_id,
        )
        raise

    if validation_status == "needs_clarification":
        logger.warning(
            "[%s] Policy version saved with unresolved clarification items: "
            "policy_id=%s version=%d clarification_count=%d.",
            workflow_id,
            policy.id,
            next_version,
            len(validation_report.clarification_items),
        )

    logger.info(
        "[%s] Policy modification completed: policy_id=%s "
        "version=%d validation_status=%s skill_version_id=%s "
        "duration_seconds=%.2f persistence_seconds=%.2f.",
        workflow_id,
        policy.id,
        next_version,
        validation_status,
        selected_skill_version_id,
        perf_counter() - workflow_started,
        perf_counter() - persistence_started,
    )

    return _build_policy_response(
        policy,
        new_policy_version,
    )


async def approve_policy_version(
    session: AsyncSession,
    policy_id: UUID,
    version: int,
) -> PolicyResponse:
    """Approve a policy version and activate its exact skill versions."""

    # 1. Activate the selected policy version.
    updated_version = (
        await policy_repository.update_policy_version_status(
            session=session,
            policy_id=policy_id,
            version=version,
            new_status="active",
        )
    )

    if updated_version is None:
        raise ValueError(
            f"Policy {policy_id} version {version} not found."
        )

    # 2. Load the updated policy.
    policy = await policy_repository.get_policy_by_id(
        session=session,
        policy_id=policy_id,
    )

    if policy is None:
        raise ValueError(f"Policy {policy_id} not found.")

    # 3. Resolve exact skill lineage from the approved policy version.
    try:
        skill_ids = json.loads(
            updated_version.applied_skill_ids_json or "[]"
        )
        skill_version_ids = json.loads(
            updated_version.applied_skill_version_ids_json or "[]"
        )
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "The policy version contains invalid skill metadata."
        ) from exc

    if (
        not isinstance(skill_ids, list)
        or not isinstance(skill_version_ids, list)
        or not skill_ids
        or len(skill_ids) != len(skill_version_ids)
    ):
        raise ValueError(
            "The approved policy version has invalid skill references."
        )

    # 4. Activate the exact skill versions used by this policy version.
    for skill_id, skill_version_id in zip(
        skill_ids,
        skill_version_ids,
    ):
        try:
            parsed_skill_id = UUID(str(skill_id))
            parsed_version_id = UUID(str(skill_version_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(
                "The policy version contains an invalid skill ID "
                "or skill-version ID."
            ) from exc

        activated_skill_version = await activate_skill_version(
            session=session,
            skill_id=parsed_skill_id,
            skill_version_id=parsed_version_id,
        )

        if activated_skill_version is None:
            raise ValueError(
                f"Could not activate skill version {skill_version_id} "
                f"for skill {skill_id}."
            )

    # 5. Rebuild the policy document.
    sections = [
        PolicySectionModel.model_validate(item)
        for item in json.loads(
            updated_version.content_json or "[]"
        )
    ]

    updated_version.content_text = format_policy_document_text(
    title=policy.title,
    domain=policy.domain,
    version=version,
    sections=sections,
    description=policy.description,
    status="active",
        )

    # 6. Commit policy and skill lifecycle changes together.
    await session.commit()

    # 7. Return the updated policy.
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