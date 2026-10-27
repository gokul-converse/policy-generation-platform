"""Test skill generation using Azure AI Foundry."""

from pprint import pprint

from agent_framework import Agent
from app.agents.policy_generation.skill_generation import (
    SKILL_GENERATOR_INSTRUCTIONS,
)
from app.clients.foundry_client import (
    get_foundry_client,
    get_foundry_credential,
)
from app.models.domain_instructions import (
    DomainInstruction,
    DomainInstructionSet,
)
from app.models.skills import GeneratedSkillSet


async def main():
    try:
        domain_instructions = DomainInstructionSet(
            domains=[
                DomainInstruction(
                    domain="Leave Policy",
                    instructions=(
                        "Employees receive 20 days of annual leave per year. "
                        "Requests must be submitted at least 5 days before "
                        "leave starts."
                    ),
                    unresolved_questions=[],
                ),
                DomainInstruction(
                    domain="Request Procedure",
                    instructions=(
                        "Annual leave requests must be submitted at least "
                        "5 days before leave starts."
                    ),
                    unresolved_questions=[],
                ),
            ]
        )

        async with Agent(
            client=get_foundry_client(),
            name="SkillGeneratorAgent",
            instructions=SKILL_GENERATOR_INSTRUCTIONS,
            default_options={
                "response_format": GeneratedSkillSet
            },
        ) as agent:
            result = await agent.run(
                "Generate skills for these domain instructions:\n"
                + domain_instructions.model_dump_json(indent=2)
            )

            if getattr(result, "value", None) is not None:
                skills = GeneratedSkillSet.model_validate(result.value)
            else:
                skills = GeneratedSkillSet.model_validate_json(result.text)

            pprint(skills.model_dump())

    finally:
        pass
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())