"""Test the requirements analysis agent."""

import asyncio
from pprint import pprint

from app.agents.policy_generation.requirements_analyzer import analyze_requirements


async def main() -> None:
    description = (
        "Employees receive 20 days of annual leave per year. "
        "Requests must be submitted at least 5 days before leave starts."
    )

    analysis = await analyze_requirements(description)

    # Display the validated structured result.
    pprint(analysis.model_dump())

    # Verify the original text and explicit numbers are preserved.
    assert analysis.original_text == description

    combined_requirements = " ".join(analysis.requirements)

    assert "20" in combined_requirements
    assert "5" in combined_requirements

    print("\nRequirements analysis test passed.")


if __name__ == "__main__":
    asyncio.run(main())
