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
# Agent instructions
# ============================================================================

ENTERPRISE_POLICY_INSTRUCTIONS = """
You are an Enterprise Policy Drafting Agent.

Your objective is to draft a comprehensive enterprise policy document
grounded strictly in validated requirements and guided by relevant
Agent Skills.

## Core Rules

1. Preserve every requirement ID, number, currency, unit of time,
   date, and condition exactly as given.

2. Never invent business rules, monetary thresholds, approval
   hierarchies, penalties, or legal obligations.

3. Every section that addresses a requirement MUST include that
   requirement ID in its requirement_ids array.

4. Organize the policy into appropriate enterprise sections:
   - Purpose and Scope
   - Definitions and Applicability
   - Core Policy Rules
   - Responsibilities and Administration
   - Procedures and Exceptions, when supported
   - Compliance, Violations, and Review

5. Never use placeholder tokens such as [TODO], [TBD], [INSERT],
   or [PLACEHOLDER].

6. If essential information is missing, record it in unresolved_items.
   Do not silently invent missing decisions.

7. Use the selected Agent Skills when relevant.
   Follow their instructions when applicable to the requirements.

8. Validated requirements always take precedence over generic
   skill guidance.

9. Every policy rule must be traceable to the supplied requirements
   or explicitly identified as an unresolved decision.

10. The policy must read formally, professionally, and clearly.

Return structured output matching StructuredPolicyGenerationOutput.
"""


SECTION_REVISION_INSTRUCTIONS = """
You are an Enterprise Policy Revision Agent.

Your objective is to revise one existing policy section based on
the user's explicit modification instructions.

## Required Process

1. Understand the original section and the requested change.
2. Identify the exact policy content affected by the request.
3. Compare the original section against the requested modification.
4. Apply the requested change without unnecessarily rewriting
   unrelated content.
5. Preserve existing requirement mappings.
6. Check the revised content against authoritative requirements.
7. Preserve numeric values, dates, units, conditions, and exceptions
   unless an explicit modification is supported by the authoritative
   requirements.
8. Never invent business rules, approval authorities, deadlines,
   penalties, or legal obligations.
9. Use the selected Agent Skills when relevant.
10. Do not introduce unresolved placeholders.

If the requested change conflicts with authoritative requirements,
do not silently resolve the conflict. Return the best compliant
revision and identify the conflict for validation.

Return the revised section as a PolicySectionModel.
"""


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
    """Normalize requirement models into dictionaries."""

    normalized: list[dict[str, Any]] = []

    for requirement in requirements:
        if isinstance(requirement, dict):
            normalized.append(requirement)

        elif hasattr(requirement, "model_dump"):
            normalized.append(requirement.model_dump())

        else:
            normalized.append(dict(requirement))

    return normalized


def _normalize_skill_names(
    applied_skills: list[str] | list[dict[str, Any]] | None,
) -> list[str]:
    """
    Normalize legacy skill identifiers.

    New generated skill references must be supplied separately as
    exact SkillVersion UUIDs.
    """

    names: list[str] = []

    for item in applied_skills or []:
        identifier = (
            item if isinstance(item, str) else str(item)
        ).strip()

        if not identifier:
            continue

        try:
            UUID(identifier)

            # UUIDs are not built-in skill names.
            # Generated skills must be passed using exact version IDs.
            continue

        except ValueError:
            pass

        name = identifier.lstrip("/")

        if name not in names:
            names.append(name)

    return names


def _build_policy_skills_provider(
    applied_skills: list[str] | list[dict[str, Any]] | None,
    selected_builtin_skill_names: list[str] | None,
    selected_skill_version_ids: list[UUID] | None,
    session_factory: async_sessionmaker[AsyncSession] | None,
) -> SkillsProvider:
    """
    Resolve the skill selection for policy generation or revision.

    Explicit new arguments take precedence over legacy applied_skills.
    """

    if selected_builtin_skill_names is None:
        builtin_names = _normalize_skill_names(applied_skills)
    else:
        builtin_names = selected_builtin_skill_names

    return create_policy_skills_provider(
        selected_builtin_skill_names=builtin_names,
        selected_skill_version_ids=selected_skill_version_ids,
        session_factory=session_factory,
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
    """Generate an enterprise policy from validated requirements."""

    llm_client = client or get_foundry_client()

    normalized_requirements = _normalize_requirements(requirements)

    skills_provider = create_policy_skills_provider(
    selected_skill_version_ids=selected_skill_version_ids,
    session_factory=session_factory,
    )

    system_instructions = ENTERPRISE_POLICY_INSTRUCTIONS

    if skill_instructions:
        system_instructions += (
            "\n\n## Additional Explicit Skill Guidance\n"
            "Follow this guidance when applicable. "
            "Validated requirements remain authoritative.\n"
            f"{skill_instructions}"
        )

    agent = Agent(
        client=llm_client,
        name="EnterprisePolicyGeneratorAgent",
        instructions=system_instructions,
        context_providers=[skills_provider],
        default_options={
            "response_format": StructuredPolicyGenerationOutput,
        },
    )

    prompt_data = {
    "title": custom_title ,
    "domain": domain ,
    "description": custom_description or "",
    "requirements": normalized_requirements,
    "selected_skill_version_ids": [
        str(version_id)
        for version_id in (selected_skill_version_ids or [])
    ],
    "skill_usage_instruction": (
        "Use only the selected generated skills loaded from the database. "
        "Follow their instructions when relevant. "
        "Do not load or refer to built-in filesystem skills. "
        "Validated requirements always take precedence."
    ),
}
    prompt = (
        "Generate a complete enterprise policy draft adhering strictly "
        "to the supplied validated requirements. Use selected Agent "
        "Skills when relevant.\n\n"
        + json.dumps(prompt_data, indent=2, ensure_ascii=False)
    )

    result = await agent.run(prompt)

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

    if custom_title:
        policy_output.title = custom_title

    if domain:
        policy_output.domain = domain

    if custom_description and not policy_output.description:
        policy_output.description = custom_description

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
    """Revise a policy section using its original selected skills."""

    llm_client = client or get_foundry_client()

    skills_provider = create_policy_skills_provider(
    selected_skill_version_ids=selected_skill_version_ids,
    session_factory=session_factory,
    )

    agent = Agent(
        client=llm_client,
        name="PolicySectionRevisionAgent",
        instructions=SECTION_REVISION_INSTRUCTIONS,
        context_providers=[skills_provider],
        default_options={
            "response_format": PolicySectionModel,
        },
    )

    normalized_requirements = _normalize_requirements(all_requirements)

    prompt_data = {
        "original_section": current_section.model_dump(),
        "revision_instructions": user_instructions,
        "authoritative_requirements": normalized_requirements,
        "revision_rules": [
            "Understand the semantic intent of the requested modification.",
            "Compare the original section with the requested change.",
            "Modify only content relevant to the request.",
            "Preserve unrelated content.",
            "Preserve all existing requirement IDs.",
            "Do not introduce unsupported requirements.",
            "Do not invent business rules.",
            "Use selected Agent Skills when relevant.",
        ],
    }

    result = await agent.run(
        "Revise the policy section according to the user's instructions. "
        "Compare the original section with the requested modification, "
        "preserve traceability, and follow authoritative requirements.\n\n"
        + json.dumps(prompt_data, indent=2, ensure_ascii=False)
    )

    if getattr(result, "value", None) is not None:
        revised = PolicySectionModel.model_validate(result.value)

    else:
        result_text = getattr(result, "text", None)

        if not result_text:
            raise ValueError(
                "Policy revision agent returned no structured output."
            )

        revised = PolicySectionModel.model_validate_json(result_text)

    # Preserve section identity.
    revised.section_id = current_section.section_id

    # Preserve every original requirement mapping.
    revised.requirement_ids = list(
        dict.fromkeys(
            [
                *current_section.requirement_ids,
                *revised.requirement_ids,
            ]
        )
    )

    return revised


