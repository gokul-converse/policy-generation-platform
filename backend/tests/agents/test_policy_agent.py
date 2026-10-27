import asyncio
import json

from app.agents.policy_generation.agent import (
    initial_policy_agent,
)
from app.models.policy import PolicyDraft

async def main():
    request = "Create an employee leave policy."

    result = await initial_policy_agent.run(request)

    print("\nGenerated policy:\n")
    print(result.text)

    print("RAW RESPONSE:", repr(result.text))
    print("RESPONSE LENGTH:", len(result.text or ""))

    # # # Verify that the model returned valid JSON.
    # # policy = json.loads(result.text)

    # print("\nPolicy title:", policy["title"])
    # print("Number of sections:", len(policy["sections"]))


if __name__ == "__main__":
    asyncio.run(main())