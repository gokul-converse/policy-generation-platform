"""Generate and revise enterprise policies using Microsoft Agent Framework and Agent Skills."""

import json
from pathlib import Path
from typing import Any

import yaml
from agent_framework import Agent, SkillsProvider
from app.clients.foundry_client import get_foundry_client
from app.common.logger import get_logger
from app.config.settings import settings
from app.models.domain_instructions import DomainInstructionSet
from app.models.policy import PolicyDraft
from app.models.policy_api import PolicySectionModel
from app.models.skill_api import ValidatedRequirementInput
from app.prompts.policy import (
    ENTERPRISE_POLICY_INSTRUCTIONS,
    SECTION_REVISION_INSTRUCTIONS,
)
from pydantic import BaseModel, ConfigDict, Field

logger = get_logger(__name__)


class StructuredPolicyGenerationOutput(BaseModel):
    """Structured output from the policy-generation agent."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        description="Formal enterprise policy title.",
    )
    domain: str = Field(
        min_length=1,
        default="General",
        description="Policy domain classification (HR, IT, Finance, etc.).",
    )
    description: str | None = Field(
        default=None,
        description="Executive summary or description of the policy.",
    )
    sections: list[PolicySectionModel] = Field(
        min_length=1,
        description="Structured policy sections.",
    )
    unresolved_items: list[str] = Field(
        default_factory=list,
        description="Unresolved gaps or clarification items.",
    )



def create_policy_skills_provider(
    selected_skill_ids: list[str] | None = None,
) -> SkillsProvider:
    """
    Discover available skills or restrict discovery to explicit selections.

    Built-in skills are identified by their frontmatter name or directory
    name. Generated skills are identified by their database UUID directory.

    An empty selection enables automatic discovery of all available skills.
    """

    backend_root = Path(settings.BACKEND_ROOT).resolve()
    builtin_skills_root = backend_root / "skills"
    generated_skills_root = settings.generated_skills_path

    selected = {
        identifier.strip().lstrip("/")
        for identifier in (selected_skill_ids or [])
        if isinstance(identifier, str) and identifier.strip()
    }

    # An empty selection means automatic discovery.
    filter_selected = bool(selected)
    skill_paths: list[Path] = []

    # Discover built-in skills.
    if builtin_skills_root.is_dir():
        for skill_file in builtin_skills_root.glob("*/SKILL.md"):
            if not skill_file.is_file():
                continue

            skill_dir = skill_file.parent

            if filter_selected:
                skill_name = skill_dir.name

                try:
                    content = skill_file.read_text(encoding="utf-8")

                    if content.startswith("---"):
                        parts = content.split("---", 2)

                        if len(parts) >= 3:
                            metadata = yaml.safe_load(parts[1]) or {}

                            if isinstance(metadata, dict):
                                skill_name = str(
                                    metadata.get("name", skill_name)
                                )

                except (OSError, yaml.YAMLError):
                    logger.warning(
                        "Could not read skill metadata from %s.",
                        skill_file,
                    )
                    continue

                if (
                    skill_name not in selected
                    and skill_dir.name not in selected
                ):
                    continue

            skill_paths.append(skill_dir)

    # Generated skills use <skill_uuid>/vN/SKILL.md.
    if generated_skills_root.is_dir():
        for skill_file in generated_skills_root.glob("*/v*/SKILL.md"):
            if not skill_file.is_file():
                continue

            skill_dir = skill_file.parent
            skill_id = skill_dir.parent.name

            if filter_selected and skill_id not in selected:
                continue

            skill_paths.append(skill_dir)

    unique_paths = sorted(
        {path.resolve() for path in skill_paths},
        key=lambda path: str(path).lower(),
    )

    if filter_selected and not unique_paths:
        raise ValueError(
            "None of the selected skills could be resolved. "
            f"Selected identifiers: {sorted(selected)}"
        )

    if not unique_paths:
        logger.warning(
            "No Agent Skills were discovered. Checked built-in path %s "
            "and generated path %s.",
            builtin_skills_root,
            generated_skills_root,
        )

    return SkillsProvider.from_paths(
        skill_paths=unique_paths,
        disable_load_skill_approval=True,
        disable_read_skill_resource_approval=True,
    )


async def generate_policy_from_requirements(
    requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
    applied_skills: list[str] | list[dict[str, Any]] | None = None,
    custom_title: str | None = None,
    domain: str | None = None,
    custom_description: str | None = None,
    skill_instructions: str | None = None,
    client: Any = None,
) -> StructuredPolicyGenerationOutput:
    """Draft an enterprise policy from validated requirements."""

    llm_client = client or get_foundry_client()

    norm_reqs: list[dict[str, Any]] = []

    for requirement in requirements:
        if isinstance(requirement, dict):
            norm_reqs.append(requirement)
        elif hasattr(requirement, "model_dump"):
            norm_reqs.append(requirement.model_dump())
        else:
            norm_reqs.append(dict(requirement))

    system_instructions = ENTERPRISE_POLICY_INSTRUCTIONS

    # Preserve explicit skill guidance for compatibility.
    if skill_instructions:
        system_instructions += (
            "\n\n## Explicitly Applied Skill Guidance\n"
            "Follow the following supplied guidance when applicable. "
            "Validated requirements remain the source of truth.\n"
            f"{skill_instructions}"
        )

    selected_skill_ids: list[str] = []
    for item in (applied_skills or []):
        if isinstance(item, str):
            identifier = item.strip()
        elif isinstance(item, dict):
            identifier = str(
                item.get("skill_id") or item.get("id") or item.get("name") or ""
            ).strip()
        else:
            identifier = str(item).strip()
        if identifier and identifier not in selected_skill_ids:
            selected_skill_ids.append(identifier)

    skills_provider = create_policy_skills_provider(
        selected_skill_ids=selected_skill_ids,
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
        "title": custom_title or "Enterprise Policy",
        "domain": domain or "General",
        "description": custom_description or "",
        "requirements": norm_reqs,
        "applied_skills": applied_skills or [],
        "skill_usage_instruction": (
            "Use the explicitly selected skills when relevant. "
            "Load their instructions through the available SkillsProvider. "
            "If a selected skill cannot be loaded, do not pretend it was used. "
            "Validated requirements always take precedence."
        ),
    }

    prompt = (
        "Generate a complete enterprise policy draft adhering strictly "
        "to the supplied validated requirements. Use the explicitly "
        "selected Agent Skills when provided. Do not assume a skill applies "
        "merely because it exists. Validated requirements take precedence.\n\n"
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

    # Deterministic traceability check: the model may omit source IDs even
    # when it has drafted content for those requirements. Do not silently
    # claim complete coverage; report omissions for review.
    source_ids = {
        str(item.get("requirement_id", "")).strip()
        for item in norm_reqs
        if isinstance(item, dict) and str(item.get("requirement_id", "")).strip()
    }
    mapped_ids = {
        requirement_id
        for section in policy_output.sections
        for requirement_id in section.requirement_ids
    }
    missing_ids = sorted(source_ids - mapped_ids)
    unknown_ids = sorted(mapped_ids - source_ids) if source_ids else []
    if missing_ids:
        note = "Requirement IDs not mapped to any policy section: " + ", ".join(missing_ids)
        if note not in policy_output.unresolved_items:
            policy_output.unresolved_items.append(note)
        logger.warning("Policy generation omitted requirement mappings: %s", missing_ids)
    if unknown_ids:
        note = "Policy sections reference IDs not present in the supplied requirements: " + ", ".join(unknown_ids)
        if note not in policy_output.unresolved_items:
            policy_output.unresolved_items.append(note)
        logger.warning("Policy generation returned unknown requirement IDs: %s", unknown_ids)

    # Honor custom overrides when provided.
    if custom_title:
        policy_output.title = custom_title

    if domain:
        policy_output.domain = domain

    if custom_description and not policy_output.description:
        policy_output.description = custom_description

    return policy_output


async def revise_policy_section_agent(
    current_section: PolicySectionModel,
    user_instructions: str,
    all_requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
    applied_skills: list[str] | None = None,
    client: Any = None,
) -> PolicySectionModel:
    """Revise a policy section using the policy's selected skills."""

    llm_client = client or get_foundry_client()

    skills_provider = create_policy_skills_provider(
        selected_skill_ids=applied_skills or [],
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

    normalized_requirements = [
        requirement.model_dump()
        if hasattr(requirement, "model_dump")
        else requirement
        for requirement in all_requirements
    ]

    prompt_data = {
        "current_section": current_section.model_dump(),
        "revision_instructions": user_instructions,
        "all_requirements": normalized_requirements,
        "applied_skills": applied_skills or [],
    }

    result = await agent.run(
        "Revise this policy section according to the user's instructions. "
        "Use the selected Agent Skills when relevant, preserve requirement "
        "traceability, and do not invent rules.\n\n"
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

    # Preserve section identity and requirement traceability.
    revised.section_id = current_section.section_id

    if not revised.requirement_ids:
        revised.requirement_ids = current_section.requirement_ids

    return revised


# =========================================================================
# Legacy compatibility functions for existing callers
# =========================================================================

LEGACY_POLICY_GENERATOR_INSTRUCTIONS = """
You are a policy-drafting agent.

Use the original requirements, generated domain instructions, and available
Agent Skills to draft a structured policy.

Rules:
1. Preserve every explicit requirement, number, condition, and exception.
2. Never invent business rules, approvals, eligibility conditions, or deadlines.
3. Use the domain names from the supplied domain instructions.
4. Never return blank, whitespace-only, or invented domain names.
5. If domain instructions contain no usable domains, report the issue as
   an unresolved item instead of inventing a domain.
6. Do not silently resolve conflicting requirements.
7. Put missing decisions and unresolved conflicts in unresolved_items.
8. Organize requirements into clear policy sections.
9. Do not add explanatory claims unsupported by the input.
10. Use relevant available Agent Skills when drafting the policy.

Return a structured response matching the PolicyDraft model.
"""


def create_policy_generator() -> Agent:
    """Create the legacy policy agent with built-in and generated skills."""

    skills_provider = create_policy_skills_provider()

    return Agent(
        client=get_foundry_client(),
        name="PolicyGeneratorAgent",
        instructions=LEGACY_POLICY_GENERATOR_INSTRUCTIONS,
        context_providers=[skills_provider],
        default_options={"response_format": PolicyDraft},
    )


async def generate_policy(
    analysis: Any,
    domain_instructions: DomainInstructionSet,
) -> PolicyDraft:
    """Generate a legacy policy draft from a model-like input and domain instructions.

    The input is accepted generically to avoid coupling this module to a
    particular requirement-analysis model. The active API workflow should use
    generate_policy_from_requirements with validated requirement records.
    """

    usable_domains = [
        item.domain.strip()
        for item in domain_instructions.domains
        if item.domain.strip()
    ]

    if not usable_domains:
        raise ValueError(
            "Cannot generate a policy without valid domain instructions. "
            "Review the domain-instruction generation result first."
        )

    agent = create_policy_generator()

    payload = {
        "requirements_analysis": analysis.model_dump(),
        "domain_instructions": domain_instructions.model_dump(),
    }

    result = await agent.run(
        "Generate a policy draft using this input:\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
    )

    if getattr(result, "value", None) is not None:
        policy = PolicyDraft.model_validate(result.value)
    else:
        result_text = getattr(result, "text", None)

        if not result_text:
            raise ValueError(
                "Legacy policy generator returned no structured output."
            )

        policy = PolicyDraft.model_validate_json(result_text)

    policy.domains = list(dict.fromkeys(usable_domains))

    return policy
