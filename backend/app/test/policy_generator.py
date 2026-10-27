
"""End-to-end test for the MAF Policy Generation Agent."""

import asyncio

from app.agents.policy_generation.policy_generator import (
    create_policy_generator,
)
from app.models.policy import PolicyDraft
from app.models.requirements import RequirementAnalysis


async def main() -> None:
    analysis = RequirementAnalysis(
        original_text=(
            "Employees receive 20 days of annual leave per year. "
            "Requests must be submitted at least 5 days before leave starts."
        ),
        requirements=[
            "Employees must receive 20 days of annual leave per year.",
            "Annual leave requests must be submitted at least 5 days "
            "before the start date of leave.",
        ],
        identified_domains=["Leave Policy", "Request Procedure"],
        missing_information=[],
        ambiguities=[],
    )

    agent = create_policy_generator()

    try:
        result = await agent.run(
            "Generate a policy draft from this requirements analysis:\n"
            + analysis.model_dump_json(indent=2)
        )

        print("\n--- RAW AGENT RESPONSE ---")
        print("Response type:", type(result).__name__)
        print("Finish reason:", getattr(result, "finish_reason", None))
        print("Response text:", repr(result.text))
        print("Structured value:", repr(result.value))

        # Inspect message content if the response text is empty.
        for i, message in enumerate(result.messages or []):
            for j, content in enumerate(
                getattr(message, "contents", []) or []
            ):
                print(f"\nMessage {i + 1}, content {j + 1}:")
                try:
                    print(content.to_dict())
                except Exception:
                    print("Content type:", type(content).__name__)
                    print("Content:", repr(content))

        if result.value is not None:
            policy = PolicyDraft.model_validate(result.value)
        elif result.text and result.text.strip():
            policy = PolicyDraft.model_validate_json(result.text)
        else:
            raise RuntimeError(
                "Agent returned no usable policy output. "
                "Review the raw response and content items above."
            )

        print("\n--- GENERATED POLICY ---")
        print(policy.model_dump_json(indent=2))

        policy_text = " ".join(
            [
                policy.title,
                *policy.domains,
                *[
                    f"{section.title} {section.content}"
                    for section in policy.sections
                ],
            ]
        ).lower()

        # Validate the two explicit requirements.
        assert "20" in policy_text, (
            "FAIL: The policy is missing the 20-day entitlement."
        )
        assert "5" in policy_text, (
            "FAIL: The policy is missing the 5-day notice requirement."
        )

        # Flag likely invented rules for manual review.
        possible_inventions = [
            "manager approval",
            "carry forward",
            "carry-forward",
            "probation period",
            "maximum consecutive leave",
        ]
        flagged = [
            phrase
            for phrase in possible_inventions
            if phrase in policy_text
        ]

        print("\n--- TEST RESULTS ---")
        print("PASS: PolicyDraft schema validation succeeded.")
        print("PASS: 20-day entitlement is present.")
        print("PASS: 5-day notice requirement is present.")

        if flagged:
            print("REVIEW REQUIRED: Possible unsupported rules:", flagged)
        else:
            print(
                "No common unsupported-rule phrases detected. "
                "Review the policy manually before treating it as compliant."
            )

    finally:
        # Client/session cleanup will be handled separately after
        # confirming the installed MAF cleanup API.
        pass


if __name__ == "__main__":
    asyncio.run(main())
