"""Generate and revise enterprise policies using Microsoft Agent Framework and Agent Skills."""

import json
from pathlib import Path
from typing import Any

from agent_framework import Agent, SkillsProvider
from pydantic import BaseModel, ConfigDict, Field

from app.clients.foundry_client import get_foundry_client
from app.common.logger import get_logger
from app.config.settings import settings
from app.models.domain_instructions import DomainInstructionSet
from app.models.policy import PolicyDraft
from app.models.policy_api import PolicySectionModel
from app.models.requirements import RequirementAnalysis
from app.models.skill_api import ValidatedRequirementInput

logger = get_logger(__name__)


class StructuredPolicyGenerationOutput(BaseModel):
    """Structured output from the policy generation agent."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, description="Formal enterprise policy title.")
    domain: str = Field(min_length=1, default="General", description="Policy domain classification (HR, IT, Finance, etc.).")
    description: str | None = Field(default=None, description="Executive summary or description of the policy.")
    sections: list[PolicySectionModel] = Field(min_length=1, description="Structured policy sections.")
    unresolved_items: list[str] = Field(default_factory=list, description="Unresolved gaps or clarification items.")


ENTERPRISE_POLICY_INSTRUCTIONS = """
You are an Enterprise Policy Drafting Agent.

Your objective is to draft a comprehensive, authoritative, production-ready enterprise policy document
grounded strictly in the validated requirements and guided by any applied Agent Skills.

## Core Rules:
1. Preserve every requirement ID, number, currency, unit of time, and condition exactly as given.
2. Never invent business rules, monetary thresholds, approval hierarchies, or legal obligations.
3. Every section that addresses a requirement MUST include that requirement ID in its `requirement_ids` array.
4. Organize the policy into standard enterprise sections:
   - Purpose and Scope (e.g., section_id="purpose")
   - Definitions and Applicability (e.g., section_id="definitions")
   - Core Policy Rules (e.g., section_id="rules")
   - Responsibilities and Administration (e.g., section_id="roles")
   - Compliance, Violations, and Review (e.g., section_id="compliance")
5. Never use placeholder tokens such as [TODO], [TBD], [INSERT], or [PLACEHOLDER]. If essential details
   are missing from the requirements, record them explicitly in the `unresolved_items` list.
6. The policy must read formally, professionally, and clearly.

Return structured output matching StructuredPolicyGenerationOutput.
"""

SECTION_REVISION_INSTRUCTIONS = """
You are a Policy Revision Agent.

Your objective is to revise a single section of an enterprise policy based on explicit user instructions.

Rules:
1. Apply the user's modifications accurately.
2. Do not remove or alter validated numeric values or units unless explicitly instructed.
3. Preserve all existing requirement IDs mapped to this section.
4. Maintain formal, executive enterprise policy tone.
5. Do not introduce incomplete placeholders like [TODO] or [TBD].

Return the revised section as a PolicySectionModel.
"""


async def generate_policy_from_requirements(
    requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
    applied_skills: list[str] | list[dict[str, Any]] | None = None,
    custom_title: str | None = None,
    domain: str | None = None,
    custom_description: str | None = None,
    skill_instructions: str | None = None,
    client: Any = None,
) -> StructuredPolicyGenerationOutput:
    """Draft an enterprise policy from validated requirements using the LLM agent."""

    llm_client = client or get_foundry_client()

    # Normalize requirements for the prompt
    norm_reqs = []
    for r in requirements:
        if isinstance(r, ValidatedRequirementInput):
            norm_reqs.append(r.model_dump())
        elif isinstance(r, dict):
            norm_reqs.append(r)
        elif hasattr(r, "model_dump"):
            norm_reqs.append(r.model_dump())
        else:
            norm_reqs.append(dict(r))

    system_instructions = ENTERPRISE_POLICY_INSTRUCTIONS
    if skill_instructions:
        system_instructions += f"\n\n## Applied Agent Skill Guidance:\n{skill_instructions}"

    agent = Agent(
        client=llm_client,
        name="EnterprisePolicyGeneratorAgent",
        instructions=system_instructions,
        default_options={"response_format": StructuredPolicyGenerationOutput},
    )

    prompt_data = {
        "title": custom_title or "Enterprise Policy",
        "domain": domain or "General",
        "description": custom_description or "",
        "requirements": norm_reqs,
    }

    prompt = (
        "Generate a complete enterprise policy draft adhering strictly to these requirements:\n\n"
        + json.dumps(prompt_data, indent=2, ensure_ascii=False)
    )

    result = await agent.run(prompt)

    if getattr(result, "value", None) is not None:
        policy_output = StructuredPolicyGenerationOutput.model_validate(result.value)
    else:
        policy_output = StructuredPolicyGenerationOutput.model_validate_json(result.text)

    # Honor custom overrides if provided
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
    client: Any = None,
) -> PolicySectionModel:
    """Revise an existing policy section using the LLM according to user guidance."""

    llm_client = client or get_foundry_client()

    agent = Agent(
        client=llm_client,
        name="PolicySectionRevisionAgent",
        instructions=SECTION_REVISION_INSTRUCTIONS,
        default_options={"response_format": PolicySectionModel},
    )

    prompt_data = {
        "current_section": current_section.model_dump(),
        "revision_instructions": user_instructions,
        "all_requirements": [
            r.model_dump() if hasattr(r, "model_dump") else r
            for r in all_requirements
        ],
    }

    result = await agent.run(
        "Revise this policy section in accordance with user instructions:\n\n"
        + json.dumps(prompt_data, indent=2, ensure_ascii=False)
    )

    if getattr(result, "value", None) is not None:
        revised = PolicySectionModel.model_validate(result.value)
    else:
        revised = PolicySectionModel.model_validate_json(result.text)

    # Preserve section_id and ensure requirement IDs are not accidentally lost
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
5. If the domain instructions contain no usable domains, report the issue
   as an unresolved item instead of inventing a domain.
6. Do not silently resolve conflicting requirements.
7. Put genuinely missing decisions and unresolved conflicts in unresolved_items.
8. Organize the requirements into clear policy sections.
9. Do not add explanatory claims that are not supported by the input.
10. Use relevant Agent Skills when drafting the policy.

Return a structured response matching the PolicyDraft model.
"""


def create_policy_generator() -> Agent:
    """Create a policy agent with filesystem-based skills."""

    skills_root = Path(settings.generated_skills_dir).resolve()

    if not skills_root.is_dir():
        skills_root.mkdir(parents=True, exist_ok=True)

    skills_provider = SkillsProvider.from_paths(
        skill_paths=skills_root,
        disable_load_skill_approval=True,
        disable_read_skill_resource_approval=True,
    )

    return Agent(
        client=get_foundry_client(),
        name="PolicyGeneratorAgent",
        instructions=LEGACY_POLICY_GENERATOR_INSTRUCTIONS,
        context_providers=[skills_provider],
        default_options={"response_format": PolicyDraft},
    )


async def generate_policy(
    analysis: RequirementAnalysis,
    domain_instructions: DomainInstructionSet,
) -> PolicyDraft:
    """Generate a policy using requirements, domains, and available skills."""

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
        policy = PolicyDraft.model_validate_json(result.text)

    expected_domains = list(dict.fromkeys(usable_domains))
    policy.domains = expected_domains

    return policy
