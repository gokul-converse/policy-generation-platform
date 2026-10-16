import json
import re

from agent_framework import Agent
from app.clients.ollama_client import get_ollama_client


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(f"Invalid JSON response:\n{text}")

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse domain instructions JSON: {exc}\n"
            f"Model response:\n{text}"
        ) from exc


async def generate_domain_instructions(
    requirements: dict,
    description: str = "",
    business_context: str = "",
) -> dict:
    client = get_ollama_client()

    agent = Agent(
        client=client,
        name="DomainInstructionGenerator",
        instructions="""
You are a policy writing instruction generator.

Use the policy requirements to create practical writing instructions
for another AI agent that will generate the final policy.

Support any business domain and policy type.
Use the current request to determine the appropriate domain.
Keep instructions simple, useful, and reusable.
Include important requirements and relevant responsibilities.
Avoid inventing company-specific rules or legal requirements.
Mention details that need confirmation when appropriate.

Return one concise JSON object containing:
domain, policy_type, skill_name, instructions.
""",
    )

    prompt = f"""
Create writing instructions for the following policy.

Analyzed requirements:
{json.dumps(requirements, ensure_ascii=False)}

Policy description:
{description}

Business context:
{business_context or "Not provided"}

Keep the response short and return only JSON.
"""

    result = await agent.run(prompt)
    data = _parse_json(result.text)

    # Use analyzed values as fallbacks if the model omits a field
    data.setdefault("domain", requirements.get("domain", "general"))
    data.setdefault(
        "policy_type",
        requirements.get("policy_type", "general policy"),
    )
    data.setdefault("skill_name", "policy-writing")
    data.setdefault(
        "instructions",
        "Write a clear, practical policy based on the supplied requirements.",
    )

    print(
        f"Domain instructions generated: "
        f"{data['policy_type']} | Domain: {data['domain']}"
    )

    return data
