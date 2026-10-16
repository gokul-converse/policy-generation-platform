import re
from pathlib import Path
from agent_framework import Agent
from app.clients.foundry_client import get_foundry_client

SKILLS_DIR = Path(__file__).resolve().parents[1] / "generated_skills"


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return value or "general-policy"


def _ensure_frontmatter(content: str, name: str, description: str) -> str:
    content = (content or "").strip()
    if not content:
        raise ValueError("Foundry returned an empty skill document.")
    if content.startswith("---"):
        return content + "\n"
    return (
        "---\n"
        f"name: {_slug(name)}\n"
        f"description: {description.replace(chr(10), ' ').strip()}\n"
        "---\n\n"
        + content
        + "\n"
    )


async def generate_or_reuse_skill(domain_instructions: dict) -> dict:
    domain = _slug(str(domain_instructions.get("domain", "general")))
    skill_name = _slug(str(domain_instructions.get("skill_name", "policy-writing")))
    skill_dir = SKILLS_DIR / domain / skill_name
    skill_path = skill_dir / "SKILL.md"

    if skill_path.exists():
        return {
            "domain": domain,
            "skill_name": skill_name,
            "skill_path": str(skill_path),
            "skill_text": skill_path.read_text(encoding="utf-8"),
            "reused": True,
        }

    client = get_foundry_client()
    agent = Agent(
        client=client,
        name="SkillGenerator",
        instructions=(
            "Write a reusable SKILL.md file for an AI policy-writing agent. "
            "Make it specific to the supplied domain and instructions. Include "
            "purpose, when to use, workflow, quality checks, and boundaries. "
            "Do not write a particular organization's final policy. Output Markdown only."
        ),
    )
    prompt = (
        f"Domain: {domain_instructions.get('domain', 'general')}\n"
        f"Policy type: {domain_instructions.get('policy_type', 'policy')}\n"
        f"Skill name: {domain_instructions.get('skill_name', skill_name)}\n"
        f"Domain instructions:\n{domain_instructions.get('instructions', '')}\n"
    )
    result = await agent.run(prompt)
    skill_text = _ensure_frontmatter(
        result.text,
        skill_name,
        f"Reusable policy-writing guidance for the {domain} domain.",
    )
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(skill_text, encoding="utf-8")
    return {
        "domain": domain,
        "skill_name": skill_name,
        "skill_path": str(skill_path),
        "skill_text": skill_text,
        "reused": False,
    }
