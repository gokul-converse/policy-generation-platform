
"""Integration test for skill generation using Azure AI Foundry."""

import asyncio
from pprint import pprint

from app.agents.policy_generation.skill_generation import generate_skills


async def main() -> None:
    """Generate draft skills from sample validated requirements."""

    requirements = {
        "requirements": [
            {
                "requirement_id": "REQ-001",
                "text": "Employees receive 20 days of annual leave per year.",
            },
            {
                "requirement_id": "REQ-002",
                "text": (
                    "Leave requests must be submitted at least "
                    "5 days before leave starts."
                ),
            },
        ]
    }

    skills = await generate_skills(requirements)

    print("\nGenerated draft skills:")
    pprint(skills.model_dump())

    for skill in skills.skills:
        assert skill.name
        assert skill.description
        assert skill.instructions
        assert skill.requirement_ids

        assert set(skill.requirement_ids).issubset(
            {"REQ-001", "REQ-002"}
        )

    print("\nSkill generation and output validation passed.")


if __name__ == "__main__":
    asyncio.run(main())
