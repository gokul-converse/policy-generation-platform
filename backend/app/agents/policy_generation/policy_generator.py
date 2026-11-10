
"""Generate and revise enterprise policies using Microsoft Agent Framework."""

import json
from typing import Any
from uuid import UUID

from agent_framework import Agent, SkillsProvider
from app.clients.foundry_client import get_foundry_client
from app.common.logger import get_logger
from app.context.database_skill_source import DatabaseSkillsSource
from app.models.policy_api import PolicySectionModel
from app.models.skill_api import ValidatedRequirementInput
from app.prompts.policy import (
    ENTERPRISE_POLICY_INSTRUCTIONS,
    SECTION_REVISION_INSTRUCTIONS,
)
from pydantic import BaseModel, ConfigDict, Field
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
    """Load only selected generated skill versions from the database."""

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
    )


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
    Validate the structural integrity of generated policy output.

    Detailed semantic and business-rule validation is handled
    by the separate policy validation service.
    """
    if not policy_output.title or not policy_output.title.strip():
        raise ValueError("Generated policy title cannot be empty.")

    if not policy_output.domain or not policy_output.domain.strip():
        raise ValueError("Generated policy domain cannot be empty.")

    if not policy_output.sections:
        raise ValueError(
            "Generated policy must contain at least one section."
        )

    known_requirement_ids = {
        item["requirement_id"]
        for item in requirements
    }

    section_ids: set[str] = set()

    for section in policy_output.sections:
        if not section.section_id or not section.section_id.strip():
            raise ValueError(
                "Every policy section must have a section_id."
            )

        if section.section_id in section_ids:
            raise ValueError(
                f"Duplicate policy section ID: {section.section_id}"
            )

        section_ids.add(section.section_id)

        if not section.content or not section.content.strip():
            raise ValueError(
                f"Policy section {section.section_id!r} has empty content."
            )

        unknown_ids = (
            set(section.requirement_ids) - known_requirement_ids
        )

        if unknown_ids:
            raise ValueError(
                f"Policy section {section.section_id!r} contains "
                f"unknown requirement IDs: {sorted(unknown_ids)}"
            )
# ============================================================================
# Policy generation
# ============================================================================

async def generate_policy_from_requirements(
    requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
    custom_title: str | None = None,
    domain: str | None = None,
    custom_description: str | None = None,
    skill_instructions: str | None = None,
    client: Any = None,
    selected_skill_version_ids: list[UUID] | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> StructuredPolicyGenerationOutput:
    """
    Generate an enterprise policy from validated requirements
    using selected database-backed skill versions.
    """
    if not requirements:
        raise ValueError(
            "At least one validated requirement is required."
        )

    # 1. Normalize and validate authoritative requirements.
    normalized_requirements = _normalize_requirements(requirements)

    # 2. Normalize selected skill-version identifiers.
    selected_skill_version_ids = _normalize_skill_version_ids(
        selected_skill_version_ids
    )

    # 3. Initialize the LLM client.
    llm_client = client or get_foundry_client()

    # 4. Load only the selected generated skill versions.
    skills_provider = create_policy_skills_provider(
        selected_skill_version_ids=selected_skill_version_ids,
        session_factory=session_factory,
    )

    # 5. Prepare policy-generation instructions.
    system_instructions = ENTERPRISE_POLICY_INSTRUCTIONS

    if skill_instructions:
        system_instructions += (
            "\n\n## Additional Explicit Skill Guidance\n"
            "Use this guidance only when relevant to the supplied "
            "validated requirements. Skills provide operational guidance "
            "and must never override authoritative requirements.\n"
            f"{skill_instructions}"
        )

    # 6. Initialize the policy-generation agent.
    agent = Agent(
        client=llm_client,
        name="EnterprisePolicyGeneratorAgent",
        instructions=system_instructions,
        context_providers=[skills_provider],
        default_options={
            "response_format": StructuredPolicyGenerationOutput,
        },
    )

    # 7. Prepare the generation input.
    prompt_data = {
        "title": custom_title,
        "domain": domain,
        "description": custom_description or "",
        "requirements": normalized_requirements,
        "selected_skill_version_ids": [
            str(version_id)
            for version_id in selected_skill_version_ids
        ],
        "skill_usage_instruction": (
            "Use only the selected generated skills loaded from the database. "
            "Use their instructions when relevant to the policy requirements. "
            "Do not load or refer to built-in filesystem skills. "
            "Do not treat skill instructions as authoritative business rules. "
            "Validated requirements always take precedence."
        ),
    }

    prompt = (
        "Generate a complete enterprise policy draft using the supplied "
        "validated requirements.\n\n"
        "Preserve all requirement IDs, conditions, numeric values, "
        "timelines, responsibilities, and approval rules.\n"
        "Do not invent unsupported business rules or workflows.\n"
        "Record missing information and unresolved conflicts in "
        "unresolved_items.\n"
        "Use selected Agent Skills only as supporting guidance.\n\n"
        + json.dumps(prompt_data, indent=2, ensure_ascii=False)
    )

    # 8. Execute policy generation.
    result = await agent.run(prompt)

    # 9. Parse structured output.
    if getattr(result, "value", None) is not None:
        policy_output = StructuredPolicyGenerationOutput.model_validate(
            result.value
        )
    else:
        result_text = getattr(result, "text", None)

        if not result_text:
            raise ValueError(
                "Policy generation agent returned no structured output."
            )

        policy_output = (
            StructuredPolicyGenerationOutput.model_validate_json(
                result_text
            )
        )

    # 10. Apply explicit metadata overrides.
    if custom_title:
        policy_output.title = custom_title

    if domain:
        policy_output.domain = domain

    if custom_description and not policy_output.description:
        policy_output.description = custom_description

    # 11. Validate structural integrity.
    _validate_policy_generation_output(
        policy_output=policy_output,
        requirements=normalized_requirements,
    )

    logger.info(
        "Policy generated successfully. Title=%s, sections=%d, "
        "requirements=%d, selected_skill_versions=%d.",
        policy_output.title,
        len(policy_output.sections),
        len(normalized_requirements),
        len(selected_skill_version_ids),
    )

    return policy_output

# ============================================================================
# Policy section modification
# ============================================================================

async def revise_policy_section_agent(
    current_section: PolicySectionModel,
    user_instructions: str,
    all_requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
    client: Any = None,
    selected_skill_version_ids: list[UUID] | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> PolicySectionModel:
    """
    Revise a policy section while preserving its identity,
    original requirement mappings, and unrelated content.
    """
    if not user_instructions or not user_instructions.strip():
        raise ValueError(
            "Policy revision instructions cannot be empty."
        )

    # 1. Validate authoritative requirements.
    normalized_requirements = _normalize_requirements(
        all_requirements
    )

    known_requirement_ids = {
        item["requirement_id"]
        for item in normalized_requirements
    }

    original_requirement_ids = set(
        current_section.requirement_ids
    )

    unknown_original_ids = (
        original_requirement_ids - known_requirement_ids
    )

    if unknown_original_ids:
        raise ValueError(
            "The original section contains requirement IDs that are "
            f"not present in the supplied authoritative requirements: "
            f"{sorted(unknown_original_ids)}"
        )

    # 2. Normalize selected skill versions.
    selected_skill_version_ids = _normalize_skill_version_ids(
        selected_skill_version_ids
    )

    # 3. Initialize the LLM client.
    llm_client = client or get_foundry_client()

    # 4. Load the original selected generated skill versions.
    skills_provider = create_policy_skills_provider(
        selected_skill_version_ids=selected_skill_version_ids,
        session_factory=session_factory,
    )

    # 5. Initialize revision agent.
    agent = Agent(
        client=llm_client,
        name="PolicySectionRevisionAgent",
        instructions=SECTION_REVISION_INSTRUCTIONS,
        context_providers=[skills_provider],
        default_options={
            "response_format": PolicySectionModel,
        },
    )

    # 6. Prepare original and revised context.
    prompt_data = {
        "original_section": current_section.model_dump(),
        "revision_instructions": user_instructions,
        "authoritative_requirements": normalized_requirements,
        "selected_skill_version_ids": [
            str(version_id)
            for version_id in selected_skill_version_ids
        ],
        "revision_rules": [
            "Understand the semantic intent of the requested modification.",
            "Compare the original section with the requested change.",
            "Modify only content relevant to the request.",
            "Preserve unrelated content.",
            "Preserve the original section ID.",
            "Preserve all original requirement IDs.",
            "Do not invent requirement IDs.",
            "Do not remove unrelated requirement mappings.",
            "Do not introduce unsupported business rules.",
            "Do not change numeric values unless explicitly requested ",
            "and supported by the authoritative requirements.",
            "If the requested modification conflicts with authoritative ",
            "requirements, do not silently apply it.",
            "Use selected skills only as supporting guidance.",
            "Validated requirements take precedence over skill instructions.",
        ],
    }

    # 7. Execute revision.
    result = await agent.run(
        "Revise the supplied policy section according to the user's "
        "modification instructions.\n\n"
        "Understand the requested change semantically. Compare the original "
        "section with the requested result. Preserve unrelated content and "
        "requirement traceability. Do not invent unsupported rules.\n\n"
        + json.dumps(prompt_data, indent=2, ensure_ascii=False)
    )

    # 8. Parse structured output.
    if getattr(result, "value", None) is not None:
        revised = PolicySectionModel.model_validate(result.value)
    else:
        result_text = getattr(result, "text", None)

        if not result_text:
            raise ValueError(
                "Policy revision agent returned no structured output."
            )

        revised = PolicySectionModel.model_validate_json(
            result_text
        )

    # 9. Preserve original section identity and exact requirement mapping.
    revised.section_id = current_section.section_id

    revised.requirement_ids = list(
        current_section.requirement_ids
    )

    if not revised.content or not revised.content.strip():
        raise ValueError(
            "Policy revision returned empty section content."
        )

    logger.info(
        "Policy section revision completed. Section=%s, "
        "preserved_requirement_ids=%s.",
        revised.section_id,
        revised.requirement_ids,
    )

    return revised