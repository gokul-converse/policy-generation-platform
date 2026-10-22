"""Test dynamic domain instruction generation."""

import asyncio
from pprint import pprint

from app.agents.policy_generation.domain_instruction_generator import (
    generate_domain_instructions,
)
from app.models.requirements import RequirementAnalysis


async def main():
    analysis = RequirementAnalysis(
        original_text=(
            "Employees receive 20 days of annual leave per year. "
            "Requests must be submitted at least 5 days before leave starts."
        ),
        requirements=[
            "Employees must receive 20 days of annual leave per year.",
            "Annual leave requests must be submitted at least 5 days "
            "before leave starts.",
        ],
        identified_domains=["Leave Policy", "Request Procedure"],
        missing_information=[],
        ambiguities=[],
    )

    result = await generate_domain_instructions(analysis)

    pprint(result.model_dump())

    assert result.domains, "No domain instructions were generated."

    for domain in result.domains:
        assert domain.domain.strip()
        assert domain.instructions.strip()

    print("\nDomain instruction generation test passed.")


if __name__ == "__main__":
    asyncio.run(main())