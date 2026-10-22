
"""Run the complete policy-generation pipeline with runtime input."""

import asyncio

from app.agents.policy_generation.domain_instruction_generator import (
    generate_domain_instructions,
)
from app.agents.policy_generation.policy_generator import generate_policy
from app.agents.policy_generation.requirements_analyzer import (
    analyze_requirements,
)
from app.agents.policy_generation.skill_generation import generate_skills
from app.services.skill_service import save_generated_skills


async def run_pipeline(description: str) -> None:
    """Run every stage using requirements supplied at runtime."""

    if not description.strip():
        raise ValueError("Policy requirements cannot be empty.")

    print("\n[1/5] Analyzing requirements...")
    analysis = await analyze_requirements(description)
    print(analysis.model_dump_json(indent=2))

    if not analysis.requirements:
        raise ValueError(
            "The analyzer returned no requirements. "
            "Please clarify the policy request and try again."
        )

    print("\n[2/5] Generating domain instructions...")
    domain_instructions = await generate_domain_instructions(analysis)
    print(domain_instructions.model_dump_json(indent=2))

    if not domain_instructions.domains:
        raise ValueError(
            "No policy domains were discovered. "
            "Review the domain-instruction generator output."
        )

    print("\n[3/5] Generating skills...")
    skill_set = await generate_skills(domain_instructions)
    print(skill_set.model_dump_json(indent=2))

    if not skill_set.skills:
        raise ValueError("Skill generation returned no skills.")

    # Preserve the original request and the structured analysis as references.
    reference_content = (
        "## Original user input\n\n"
        f"{description.strip()}\n\n"
        "## Extracted requirements\n\n"
        + "\n".join(f"- {item}" for item in analysis.requirements)
        + "\n\n## Domain instructions\n\n"
        + domain_instructions.model_dump_json(indent=2)
    )

    print("\n[4/5] Saving generated skills...")
    saved_paths = save_generated_skills(
        skill_set,
        reference_content=reference_content,
    )

    for path in saved_paths:
        print(f"Saved: {path}")

    print("\n[5/5] Generating the policy...")
    policy = await generate_policy(analysis, domain_instructions)
    print(policy.model_dump_json(indent=2))

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED")
    print(f"Title: {policy.title}")
    print(f"Domains: {policy.domains}")
    print(f"Sections: {len(policy.sections)}")
    print(f"Unresolved items: {policy.unresolved_items}")
    print(f"Skills saved: {len(saved_paths)}")
    print("=" * 60)


def main() -> None:
    """Collect a new policy request from the terminal."""

    print("Policy Generation Agent")
    print("Enter the requirements for the policy you want to create.")
    print("Example: Employees receive 20 days of annual leave per year.")

    description = input("\nPolicy requirements: ").strip()

    if not description:
        print("No requirements supplied. Nothing to process.")
        return

    asyncio.run(run_pipeline(description))


if __name__ == "__main__":
    main()
