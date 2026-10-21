
"""Generate policy drafts using Microsoft Agent Framework Agent Skills."""

import json
from pathlib import Path

from agent_framework import Agent, SkillsProvider
from app.clients.foundry_client import get_foundry_client
from app.config.settings import settings
from app.models.domain_instructions import DomainInstructionSet
from app.models.policy import PolicyDraft
from app.models.requirements import RequirementAnalysis

POLICY_GENERATOR_INSTRUCTIONS = """
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
        raise FileNotFoundError(
            f"Generated skills directory not found: {skills_root}"
        )

    skills_provider = SkillsProvider.from_paths(
        skill_paths=skills_root,
        disable_load_skill_approval=True,
        disable_read_skill_resource_approval=True,
    )

    return Agent(
        client=get_foundry_client(),
        name="PolicyGeneratorAgent",
        instructions=POLICY_GENERATOR_INSTRUCTIONS,
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

    # Enforce the domains established by the domain-instruction stage.
    expected_domains = list(dict.fromkeys(usable_domains))
    generated_domains = set(policy.domains)

    if not generated_domains.issubset(set(expected_domains)):
        raise ValueError(
            "Policy generator returned domains not present in the "
            f"domain instructions. Expected: {expected_domains}; "
            f"received: {policy.domains}"
        )

    # Avoid returning an incomplete list of domains.
    policy.domains = expected_domains

    return policy
