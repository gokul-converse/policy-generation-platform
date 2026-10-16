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
            f"Could not parse requirements JSON: {exc}\n"
            f"Model response:\n{text}"
        ) from exc


async def analyze_requirements(
    description: str,
    business_context: str = "",
) -> dict:
    client = get_ollama_client()

    agent = Agent(
        client=client,
        name="RequirementsAnalyzer",
        instructions="""
You are a policy requirements analyzer.

Analyze the user's current policy description and identify:
- Policy type
- Business domain
- Objective
- Scope
- Main requirements
- Constraints
- Missing information

Support any policy type or business domain.
Keep the output concise and relevant to the request.
Use reasonable general assumptions where appropriate.
Do not reuse details from previous requests.

Return one JSON object with these fields:
policy_type, domain, objective, scope,
requirements, constraints, missing_information.
""",
    )

    prompt = f"""
Analyze the following policy request.

Policy description:
{description}

Business context:
{business_context or "Not provided"}

Return the extracted requirements as JSON.
"""

    result = await agent.run(prompt)
    data = _parse_json(result.text)

    print(
        f"Requirements analyzed: "
        f"{data.get('policy_type', 'Policy')} | "
        f"Domain: {data.get('domain', 'General')}"
    )

    return data


# Keeps compatibility with existing workflow code
async def generate_requirements(
    description: str,
    business_context: str = "",
) -> dict:
    return await analyze_requirements(description, business_context)
