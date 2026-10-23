from functools import lru_cache
from pathlib import Path

from agent_framework import Agent

from app.clients.foundry_client import get_foundry_client
from app.prompts.json_generation_prompt import UI_JSON_GENERATION_SYSTEM_PROMPT

# agent.py is at backend/app/agents/foundry/agent.py, so parents[3] is backend/
BACKEND_DIR = Path(__file__).resolve().parents[3]
CLOUD_MODEL_GUIDE = BACKEND_DIR / "md_files" / "render-schema-reference.md"


@lru_cache(maxsize=1)
def load_renderer_instructions() -> str:
    """Load and cache the renderer specification."""
    if not CLOUD_MODEL_GUIDE.is_file():
        raise FileNotFoundError(
            f"Renderer specification not found: {CLOUD_MODEL_GUIDE}"
        )

    return CLOUD_MODEL_GUIDE.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def get_ui_json_agent() -> Agent:
    """Create and reuse the Foundry UI JSON generation agent."""
    renderer_instructions = load_renderer_instructions()

    instructions = (
        UI_JSON_GENERATION_SYSTEM_PROMPT
        + "\n\n"
        + "RENDERER SPECIFICATION:\n"
        + renderer_instructions
    )

    return Agent(
        client=get_foundry_client(),
        name="UIJsonGenerationAgent",
        instructions=instructions,
    )
