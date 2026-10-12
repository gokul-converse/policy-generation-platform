import asyncio
import json

from app.workflows.mock_policy_workflow import (
    build_mock_policy_workflow,
)


async def main():
    workflow = build_mock_policy_workflow()

    mock_request = {
        "request_id": "REQ-001",
        "user_input": "Create an employee leave policy.",
        "selected_skills": [
            {
                "id": "leave_policy",
                "instructions": (
                    "Define leave eligibility and entitlements."
                ),
            },
            {
                "id": "policy_formatting",
                "instructions": (
                    "Organize the policy into clear sections."
                ),
            },
        ],
    }

    events = await workflow.run(mock_request)

    outputs = events.get_outputs()

    print("\n===== FINAL MASTER POLICY =====")
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    asyncio.run(main())     