
"""Generate domain instructions using Microsoft Agent Framework and Ollama."""

from agent_framework import Agent
from app.clients.ollama_client import create_ollama_client
from app.models.domain_instructions import (
    DomainInstruction,
    DomainInstructionSet,
)
from app.models.requirements import RequirementAnalysis

DOMAIN_INSTRUCTION_PROMPT = """
You are a domain-instruction designer for a policy-generation system.

Use the supplied original text and requirements analysis to produce
instructions for the relevant policy domains.

Rules:
1. Discover domain names from the actual supplied requirements.
2. Do not use a fixed list of policy domains.
3. Use only the original text and extracted requirements as sources
   of business rules.
4. Preserve every explicit number, unit, deadline, condition, and exception.
5. Do not invent company procedures, approval rules, eligibility rules,
   deadlines, limits, or documentation requirements.
6. Do not treat common industry practices as user requirements.
7. Do not ask generic questions merely because a detail was not supplied.
8. Add an unresolved question only when missing information materially
   affects interpreting or implementing an explicit requirement.
9. Do not answer unresolved questions by guessing.
10. Each domain's instructions must explain how to preserve and organize
    the requirements relevant to that domain.
11. Do not create duplicate domains for the same subject.
12. If the input contains conflicting statements, preserve the conflict
    and describe it as unresolved.

Return structured output matching DomainInstructionSet:
{
  "domains": [
    {
      "domain": "A domain discovered from the input",
      "instructions": "Grounded instructions for this domain",
      "unresolved_questions": []
    }
  ]
}

Do not include Markdown outside the structured response.
"""


async def generate_domain_instructions(
    analysis: RequirementAnalysis,
) -> DomainInstructionSet:
    """Generate and validate instructions for a policy request."""

    if not analysis.requirements:
        raise ValueError(
            "Cannot generate domain instructions without requirements."
        )

    client = create_ollama_client()

    agent = Agent(
        client=client,
        name="DomainInstructionGeneratorAgent",
        instructions=DOMAIN_INSTRUCTION_PROMPT,
        default_options={
            "response_format": DomainInstructionSet.model_json_schema()
        },
    )

    result = await agent.run(
        "Generate domain instructions for the following analysis.\n\n"
        + analysis.model_dump_json(indent=2)
    )

    if getattr(result, "value", None) is not None:
        domain_set = DomainInstructionSet.model_validate(result.value)
    else:
        domain_set = DomainInstructionSet.model_validate_json(result.text)

    # Prevent a blank or malformed domain result from reaching skill generation.
    if not domain_set.domains:
        raise ValueError(
            "The domain-instruction generator returned no domains."
        )

    return domain_set
