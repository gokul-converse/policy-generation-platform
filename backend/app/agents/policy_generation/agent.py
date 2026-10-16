from agent_framework import Agent
from app.clients.foundry_client import get_foundry_client


async def generate_policy(state: dict) -> str:
    requirements = state.get("requirements", {})
    domain_instructions = state.get("domain_instructions", {})
    skill = state.get("skill_text", "")

    agent = Agent(
        client=get_foundry_client(),
        name="PolicyGenerationAgent",
        instructions=(
            "You are a careful policy writer. Draft a complete, clear, practical policy "
            "using the user's requirements and the provided reusable skill. Use Markdown. "
            "Do not claim legal compliance or invent organization-specific details. "
            "Clearly mark any details that need confirmation as [To be confirmed]."
        ),
    )
    prompt = (
        "USER REQUEST:\n"
        f"{state.get('description', '')}\n\n"
        "BUSINESS CONTEXT:\n"
        f"{state.get('business_context', '') or 'Not provided'}\n\n"
        "REQUIREMENTS ANALYSIS:\n"
        f"{requirements}\n\n"
        "DOMAIN INSTRUCTIONS:\n"
        f"{domain_instructions}\n\n"
        "REUSABLE SKILL (SKILL.md):\n"
        f"{skill}\n\n"
        "Generate the final policy in Markdown with appropriate headings, scope, roles, "
        "procedures, controls, exceptions, review cadence, and ownership where relevant."
    )
    result = await agent.run(prompt)
    policy = (result.text or "").strip()
    if not policy:
        raise ValueError("Policy generation agent returned an empty response.")
    return policy
