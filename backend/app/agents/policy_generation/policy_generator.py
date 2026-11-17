"""Generate and revise enterprise policies using Microsoft Agent Framework."""

import json
import re
from typing import Any
from uuid import UUID

from agent_framework import Agent, SkillsProvider
from app.clients.foundry_client import get_foundry_client
from app.common.logger import get_logger
from app.context.database_skill_source import DatabaseSkillsSource
from app.models.policy_api import PolicySectionModel
from app.models.skill_api import ValidatedRequirementInput
from app.models.skill_db import SkillVersion
from app.prompts.policy import (
    ENTERPRISE_POLICY_INSTRUCTIONS,
)
from app.services.skill_file_service import split_skill_markdown
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = get_logger(__name__)


# ============================================================================
# Structured policy output
# ============================================================================

class StructuredPolicyGenerationOutput(BaseModel):
    """Structured output from the policy generation agent."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        description="Formal enterprise policy title.",
    )

    domain: str = Field(
        min_length=1,
        default="General",
        description="Policy domain classification.",
    )

    description: str | None = Field(
        default=None,
        description="Executive summary or policy description.",
    )

    sections: list[PolicySectionModel] = Field(
        min_length=1,
        description="Structured policy sections.",
    )

    unresolved_items: list[str] = Field(
        default_factory=list,
        description="Unresolved gaps or clarification items.",
    )




# ============================================================================
# Skill provider construction
# ============================================================================


def create_policy_skills_provider(
    selected_skill_version_ids: list[UUID] | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> SkillsProvider:
    """Load selected generated skill versions from the database."""

    selected_versions = list(
        dict.fromkeys(selected_skill_version_ids or [])
    )

    if not selected_versions:
        logger.warning(
            "No generated skill versions selected for policy generation."
        )

        return SkillsProvider.from_paths(
            skill_paths=[],
            disable_load_skill_approval=True,
            disable_read_skill_resource_approval=True,
            disable_run_skill_script_approval=True,
        )

    if session_factory is None:
        raise ValueError(
            "Database session factory is required to load generated skills."
        )

    database_source = DatabaseSkillsSource(
        session_factory=session_factory,
        skill_version_ids=selected_versions,
    )

    return SkillsProvider(
        database_source,
        disable_load_skill_approval=True,
        disable_read_skill_resource_approval=True,
        disable_run_skill_script_approval=True,
    )



async def load_requirements_from_selected_skills(
    selected_skill_version_ids: list[UUID],
    session_factory: async_sessionmaker[AsyncSession],
) -> list[dict[str, Any]]:
    """
    Load Source Requirements from exact selected skill versions.

    Supports multiline JSON requirement content.
    Returns the standard requirement structure expected by
    _normalize_requirements().
    """

    if not selected_skill_version_ids:
        raise ValueError(
            "At least one skill version must be selected."
        )

    async with session_factory() as session:
        result = await session.scalars(
            select(SkillVersion).where(
                SkillVersion.id.in_(selected_skill_version_ids)
            )
        )
        versions = list(result.all())

    versions_by_id = {
        version.id: version
        for version in versions
    }

    missing_ids = (
        set(selected_skill_version_ids) - set(versions_by_id)
    )

    if missing_ids:
        raise ValueError(
            "Selected skill versions were not found: "
            f"{sorted(str(item) for item in missing_ids)}"
        )

    requirements_by_id: dict[str, dict[str, Any]] = {}

    for version_id in selected_skill_version_ids:
        version = versions_by_id[version_id]

        if not version.content:
            raise ValueError(
                f"Skill version {version_id} has empty content."
            )

        _, _, source_requirements = split_skill_markdown(
            version.content
        )

        if not source_requirements.strip():
            raise ValueError(
                f"Skill version {version_id} has no Source Requirements."
            )

        lines = source_requirements.splitlines()

        if not lines or lines[0].strip() != "## Source Requirements":
            raise ValueError(
                f"Invalid Source Requirements heading in skill version "
                f"{version_id}."
            )

        requirement_blocks: list[str] = []
        current_block: list[str] = []

        for line in lines[1:]:
            if line.strip().startswith("- "):
                if current_block:
                    requirement_blocks.append(
                        "\n".join(current_block).strip()
                    )

                current_block = [line.strip()]

            elif current_block:
                current_block.append(line)

            elif line.strip():
                raise ValueError(
                    f"Invalid Source Requirements format in "
                    f"skill version {version_id}: {line!r}"
                )

        if current_block:
            requirement_blocks.append(
                "\n".join(current_block).strip()
            )

        for block in requirement_blocks:
            requirement_entry = block[2:].strip()

            requirement_id, separator, requirement_text = (
                requirement_entry.partition(":")
            )

            requirement_id = requirement_id.strip()
            requirement_text = requirement_text.strip()

            if not separator or not requirement_id or not requirement_text:
                raise ValueError(
                    f"Invalid requirement entry in skill version "
                    f"{version_id}: {block!r}"
                )

            existing = requirements_by_id.get(requirement_id)

            if existing:
                if existing["text"] != requirement_text:
                    raise ValueError(
                        f"Conflicting text found for requirement "
                        f"{requirement_id!r} across selected skills."
                    )
                continue

          
            requirements_by_id[requirement_id] = {
                "requirement_id": requirement_id,
                "text": requirement_text,
                "status": "skill_source",
                "source_skill_version_id": str(version_id),
            }

    if not requirements_by_id:
        raise ValueError(
            "No requirements could be extracted from selected skills."
        )

    return list(requirements_by_id.values())


# ============================================================================
# Input normalization
# ============================================================================

def _normalize_requirements(
    requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Normalize and validate authoritative requirements.

    Requirements must contain unique IDs and non-empty source text.
    The original requirement wording is preserved.
    """
    if not requirements:
        raise ValueError(
            "At least one validated requirement is required."
        )

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, requirement in enumerate(requirements, start=1):
        if isinstance(requirement, dict):
            item = requirement
        elif hasattr(requirement, "model_dump"):
            item = requirement.model_dump()
        else:
            raise ValueError(
                f"Requirement at position {index} has an unsupported type."
            )

        requirement_id = item.get("requirement_id")
        requirement_text = item.get("text")

        if not isinstance(requirement_id, str) or not requirement_id.strip():
            raise ValueError(
                f"Requirement at position {index} has an invalid requirement_id."
            )

        if not isinstance(requirement_text, str) or not requirement_text.strip():
            raise ValueError(
                f"Requirement {requirement_id!r} has empty requirement text."
            )

        requirement_id = requirement_id.strip()

        if requirement_id in seen_ids:
            raise ValueError(
                f"Duplicate requirement ID supplied: {requirement_id}"
            )

        seen_ids.add(requirement_id)

        normalized_item = dict(item)
        normalized_item["requirement_id"] = requirement_id
        normalized_item["text"] = requirement_text

        normalized.append(normalized_item)

    return normalized

def _normalize_skill_version_ids(
    skill_version_ids: list[UUID] | None,
) -> list[UUID]:
    """
    Normalize and deduplicate selected generated skill-version IDs.
    """
    if not skill_version_ids:
        return []

    normalized: list[UUID] = []
    seen: set[UUID] = set()

    for version_id in skill_version_ids:
        try:
            normalized_id = (
                version_id
                if isinstance(version_id, UUID)
                else UUID(str(version_id))
            )
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid selected skill version ID: {version_id!r}"
            ) from exc

        if normalized_id not in seen:
            seen.add(normalized_id)
            normalized.append(normalized_id)

    return normalized



def _validate_policy_generation_output(
    policy_output: StructuredPolicyGenerationOutput,
    requirements: list[dict[str, Any]],
) -> None:
    """
    Validate generated policy structure, section numbering,
    and requirement traceability.
    """

    if not policy_output.title or not policy_output.title.strip():
        raise ValueError(
            "Generated policy title cannot be empty."
        )

    if not policy_output.domain or not policy_output.domain.strip():
        raise ValueError(
            "Generated policy domain cannot be empty."
        )

    if not policy_output.sections:
        raise ValueError(
            "Generated policy must contain at least one section."
        )

    known_requirement_ids = {
        item["requirement_id"]
        for item in requirements
    }

    seen_section_ids: set[str] = set()
    main_section_numbers: list[int] = []
    subsection_counts: dict[int, int] = {}

    for section in policy_output.sections:

        section_id = section.section_id.strip()

        if not re.fullmatch(r"\d+(?:\.\d+)?", section_id):
            raise ValueError(
                f"Invalid section ID '{section_id}'. "
                "Use handbook numbering such as 1, 1.1, 1.2."
            )

        if section_id in seen_section_ids:
            raise ValueError(
                f"Duplicate policy section ID: {section_id}"
            )

        seen_section_ids.add(section_id)

        if not section.title.strip():
            raise ValueError(
                f"Section {section_id} has an empty title."
            )

        if not section.content.strip():
            raise ValueError(
                f"Section {section_id} has empty content."
            )

        unknown_ids = (
            set(section.requirement_ids)
            - known_requirement_ids
        )

        if unknown_ids:
            raise ValueError(
                f"Section {section_id} contains unknown "
                f"requirement IDs: {sorted(unknown_ids)}"
            )

        # Validate main section numbering.
        if "." not in section_id:
            main_number = int(section_id)

            expected_number = len(main_section_numbers) + 1

            if main_number != expected_number:
                raise ValueError(
                    f"Invalid main section numbering. "
                    f"Expected {expected_number}, got {main_number}."
                )

            main_section_numbers.append(main_number)

        # Validate subsection numbering.
        else:
            main_part, subsection_part = section_id.split(".")

            main_number = int(main_part)
            subsection_number = int(subsection_part)

            if main_number not in main_section_numbers:
                raise ValueError(
                    f"Subsection {section_id} has no preceding "
                    f"main section {main_number}."
                )

            expected_subsection = (
                subsection_counts.get(main_number, 0) + 1
            )

            if subsection_number != expected_subsection:
                raise ValueError(
                    f"Invalid subsection numbering for section "
                    f"{main_number}. Expected "
                    f"{main_number}.{expected_subsection}, "
                    f"got {section_id}."
                )

            subsection_counts[main_number] = subsection_number


# ============================================================================
# Policy generation
# ============================================================================




async def generate_policy_from_skill(
    selected_skill_version_ids: list[UUID],
    custom_title: str | None = None,
    domain: str | None = None,
    custom_description: str | None = None,
    client: Any = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    additional_generation_guidance: str | None = None,
) -> StructuredPolicyGenerationOutput:
    """
    Generate a complete enterprise policy using exact selected
    skill versions and their Source Requirements.

    Dynamically builds a requirement coverage checklist so the
    generator preserves every substantive requirement.
    """

    # 1. Validate database session factory.
    if session_factory is None:
        raise ValueError("Database session factory is required.")

    # 2. Normalize selected skill version IDs.
    selected_skill_version_ids = _normalize_skill_version_ids(
        selected_skill_version_ids
    )

    if not selected_skill_version_ids:
        raise ValueError(
            "At least one skill version must be selected."
        )

    # 3. Extract requirements from exact selected skill versions.
    requirements = await load_requirements_from_selected_skills(
        selected_skill_version_ids=selected_skill_version_ids,
        session_factory=session_factory,
    )

    normalized_requirements = _normalize_requirements(
        requirements
    )

    # 4. Build a dynamic requirement coverage checklist.
    requirement_coverage_checklist: list[dict[str, Any]] = []

    for requirement in normalized_requirements:
        requirement_id = requirement["requirement_id"]
        requirement_text = requirement["text"]

        try:
            parsed_requirement = json.loads(requirement_text)
        except (json.JSONDecodeError, TypeError):
            parsed_requirement = None

        if isinstance(parsed_requirement, dict):
            for field_name, field_value in parsed_requirement.items():
                requirement_coverage_checklist.append(
                    {
                        "requirement_id": requirement_id,
                        "source_field": field_name,
                        "source_content": field_value,
                        "coverage_instruction": (
                            "Preserve every substantive statement "
                            "and condition in this field."
                        ),
                    }
                )
        else:
            requirement_coverage_checklist.append(
                {
                    "requirement_id": requirement_id,
                    "source_field": "requirement_text",
                    "source_content": requirement_text,
                    "coverage_instruction": (
                        "Preserve every substantive statement "
                        "and condition in this requirement."
                    ),
                }
            )

    if not requirement_coverage_checklist:
        raise ValueError(
            "Could not build the requirement coverage checklist."
        )

    # 5. Initialize LLM client and skill provider.
    llm_client = client or get_foundry_client()

    skills_provider = create_policy_skills_provider(
        selected_skill_version_ids=selected_skill_version_ids,
        session_factory=session_factory,
    )

    # 6. Prepare system instructions.
    system_instructions = (
        ENTERPRISE_POLICY_INSTRUCTIONS
        + """

## SELECTED SKILL SOURCE RULES

The selected skill versions provide policy-drafting guidance
and their Source Requirements.

The Source Requirements extracted from the exact selected
skill versions are the requirement input for this generation.

Do not retrieve or assume different requirement text from
an external requirement database.

Source Requirements have authority over skill instructions
when their content conflicts.

Do not describe feedback-derived requirement changes as
independently validated or approved.

Preserve all requirement IDs, scope conditions, numeric values,
responsibilities, timelines, and approval rules.

Do not invent unsupported business rules.

## STRICT NUMERIC PRESERVATION

Preserve every numeric value exactly as specified in the
Source Requirements.

Preserve the original:
- Numeric values
- Units of measurement
- Frequencies
- Durations
- Percentages
- Thresholds
- Timelines
- Conditions and applicability

Never calculate, derive, round, normalize, or convert a
numeric value from another source value.

Do not assume that one numeric value should be mathematically
recalculated based on another value.

For example, if the Source Requirements specify:
- Annual allocation: 15 days per year
- Monthly accrual: 1 day per month

Preserve both values exactly.

Do not calculate the monthly accrual as 1.25 days.

If numeric values appear inconsistent or ambiguous, preserve
the original values and record the ambiguity in unresolved_items.
Do not silently correct the Source Requirements.

## POLICY CONTENT CONSOLIDATION

Represent each business rule in one appropriate,
authoritative policy section.

Consolidate overlapping or repeated content without removing
any unique requirement.

Do not unnecessarily repeat the same:
- Allocation rules
- Accrual rules
- Approval rules
- Carry-forward rules
- Cancellation rules
- Eligibility conditions

Do not remove unique conditions, exceptions, responsibilities,
restrictions, or numeric values during consolidation.

## REQUIREMENT COVERAGE CHECKLIST

The generation input contains a dynamically generated
requirement_coverage_checklist.

Use it to verify every field and substantive statement in
the selected Source Requirements.

A requirement is not covered merely because its ID appears
in a policy section.

Every substantive rule must be represented in policy content.

In particular:

- Preserve all scope statements.
- Preserve numeric limits explicitly.
- Preserve approval conditions explicitly.
- Preserve all independent rules.
- Do not omit requirements contained in JSON fields.

## ADDITIONAL USER FEEDBACK RULES

Consider additional user feedback when generating the policy.

Apply relevant feedback to policy wording, structure,
clarifications, and presentation.

When feedback changes a business requirement, use the
corresponding Source Requirements from the selected skill version.

Do not introduce a business requirement that is absent from
the selected skill versions.

If feedback conflicts with the selected Source Requirements,
do not silently override them. Record the conflict in
unresolved_items.

Additional generation guidance must not override
Source Requirements or introduce unsupported business rules.

"""
    )

    # 7. Initialize policy generation agent.
    agent = Agent(
        client=llm_client,
        name="EnterprisePolicyGeneratorAgent",
        instructions=system_instructions,
        context_providers=[skills_provider],
        default_options={
            "response_format": StructuredPolicyGenerationOutput,
        },
    )

    # 8. Prepare generation input.
    prompt_data = {
        "title": custom_title,
        "domain": domain,
        "description": custom_description or "",
        "source_requirements": normalized_requirements,
        "requirement_coverage_checklist": (
            requirement_coverage_checklist
        ),
        "selected_skill_version_ids": [
            str(version_id)
            for version_id in selected_skill_version_ids
        ],
        "additional_generation_guidance": (
            additional_generation_guidance.strip()
            if additional_generation_guidance
            else None
        ),
        "skill_usage_instruction": (
            "Use the selected skill versions for drafting guidance. "
            "Use the supplied Source Requirements as the authoritative "
            "business-rule source. Follow the requirement coverage "
            "checklist to preserve every substantive requirement. "
            "Preserve all numeric values exactly without recalculation. "
            "Consolidate repeated rules without removing unique "
            "requirements. Do not introduce unsupported requirements."
        ),
    }

    # 9. Prepare generation prompt.
    prompt = (
        "Generate a complete enterprise policy draft using the "
        "selected skill versions and their Source Requirements.\n\n"

        "IMPORTANT: Before drafting, inspect every entry in "
        "requirement_coverage_checklist.\n\n"

        "Preserve every substantive requirement, including "
        "all scope statements, eligibility conditions, numeric "
        "limits, units, timelines, responsibilities, permissions, "
        "obligations, restrictions, exceptions, and approvals.\n\n"

        "Do not omit a condition because it appears in a scope "
        "field instead of a rules list.\n\n"

        "Do not replace a specific numeric limit with vague wording.\n\n"

        "STRICT NUMERIC PRESERVATION:\n"
        "Preserve every annual allocation, monthly accrual, "
        "duration, threshold, percentage, frequency, and timeline "
        "exactly as specified in Source Requirements.\n"
        "Never calculate, derive, round, convert, or normalize a "
        "numeric value from another source value.\n"
        "For example, if the source specifies 15 days per year "
        "and 1 day per month, preserve both values exactly. "
        "Do not change the monthly value to 1.25 days.\n"
        "If values appear inconsistent, preserve the source values "
        "and report the ambiguity in unresolved_items.\n\n"

        "POLICY CONTENT CONSOLIDATION:\n"
        "Represent each business rule in one appropriate "
        "authoritative section.\n"
        "Consolidate overlapping content without removing "
        "any unique requirement, condition, exception, "
        "responsibility, or numeric value.\n"
        "Avoid repeating the same allocation, accrual, "
        "approval, or carry-forward rules in multiple sections.\n\n"

        "For every source requirement, ensure the generated policy "
        "explicitly represents all its substantive statements.\n\n"

        "Map each policy section to the correct source requirement IDs. "
        "Do not claim complete coverage when only part of a requirement "
        "is represented.\n\n"

        "Do not invent unsupported business rules or workflows.\n\n"

        "Apply additional user feedback only when it is consistent "
        "with the selected Source Requirements.\n\n"

        "If feedback conflicts with the selected Source Requirements, "
        "do not silently override them. Record the conflict in "
        "unresolved_items.\n\n"

        "If essential information is missing, record it in "
        "unresolved_items without inventing a decision.\n\n"

        "Generate the complete policy, not individual sections.\n\n"

        "Return only StructuredPolicyGenerationOutput.\n\n"

        + json.dumps(
            prompt_data,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    # 10. Execute policy generation.
    result = await agent.run(prompt)
    
    # Check for pending tool approval requests.
    pending_requests = (
        getattr(result, "user_input_requests", None) or []
    )

    for request in pending_requests:
        function_call = getattr(
            request,
            "function_call",
            None,
        )

        logger.error(
            "Pending tool approval detected: tool=%s arguments=%s",
            getattr(function_call, "name", None),
            getattr(function_call, "arguments", None),
        )

    
    # 11. Parse structured output

    response_value = getattr(result, "value", None)
    result_text = getattr(result, "text", None)

    policy_output = None

    # First: structured response
    if response_value is not None:
        policy_output = (
            StructuredPolicyGenerationOutput.model_validate(
                response_value
            )
        )

    # Second: direct response text
    elif isinstance(result_text, str) and result_text.strip():
        policy_output = (
            StructuredPolicyGenerationOutput.model_validate_json(
                result_text
            )
        )

    # Third: inspect assistant messages
    else:
        messages = getattr(result, "messages", None) or []

        for message in reversed(messages):
            role = getattr(message, "role", None)

            if role and str(role).lower() not in ("assistant", "agent"):
                continue

            message_text = getattr(message, "text", None)

            if isinstance(message_text, str) and message_text.strip():
                policy_output = (
                    StructuredPolicyGenerationOutput.model_validate_json(
                        message_text
                    )
                )
                break

            contents = getattr(message, "contents", None) or []

            for content in contents:
                content_text = getattr(content, "text", None)

                if (
                    isinstance(content_text, str)
                    and content_text.strip()
                ):
                    try:
                        policy_output = (
                            StructuredPolicyGenerationOutput
                            .model_validate_json(content_text)
                        )
                        break
                    except Exception:
                        logger.debug(
                            "Assistant content is not structured policy JSON."
                        )

            if policy_output is not None:
                break

    if policy_output is None:
        messages = getattr(result, "messages", None) or []

        diagnostics = [
            {
                "role": getattr(message, "role", None),
                "message_type": type(message).__name__,
                "content_types": [
                    getattr(content, "type", None)
                    for content in (
                        getattr(message, "contents", None) or []
                    )
                ],
            }
            for message in messages
        ]

        logger.error(
            "Policy generation returned no structured output. "
            "Response type=%s, diagnostics=%s",
            type(result).__name__,
            diagnostics,
        )

        raise ValueError(
            "Policy generation returned no structured output. "
            "Check response diagnostics."
        )


    # 12. Apply explicitly supplied policy metadata.
    if custom_title:
        policy_output.title = custom_title

    if domain:
        policy_output.domain = domain

    if custom_description and not policy_output.description:
        policy_output.description = custom_description

    # 13. Validate structural integrity.
    _validate_policy_generation_output(
        policy_output=policy_output,
        requirements=normalized_requirements,
    )

    # 14. Log generation result.
    logger.info(
        "Policy generated successfully. "
        "Title=%s, sections=%d, requirements=%d, "
        "coverage_checklist_items=%d, selected_skill_versions=%d",
        policy_output.title,
        len(policy_output.sections),
        len(normalized_requirements),
        len(requirement_coverage_checklist),
        len(selected_skill_version_ids),
    )

    return policy_output
