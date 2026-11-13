import json
from functools import lru_cache
from pathlib import Path

from agent_framework import Agent

from app.clients.foundry_client import get_foundry_client
from app.prompts.json_generation_prompt import UI_JSON_GENERATION_SYSTEM_PROMPT

BACKEND_DIR = Path(__file__).resolve().parents[3]
SCHEMA_PATH = BACKEND_DIR / "ui_contracts" / "policy-ui-contract.schema.json"


@lru_cache(maxsize=1)
def load_ui_schema() -> str:
    """Load the authoritative JSON Schema contract."""
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(
            f"Policy UI JSON Schema not found: {SCHEMA_PATH}"
        )

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return json.dumps(schema, ensure_ascii=False, indent=2)


@lru_cache(maxsize=1)
def get_ui_json_agent() -> Agent:
    """Create and reuse the Foundry UI generation agent."""
    schema_text = load_ui_schema()

    instructions = (
        UI_JSON_GENERATION_SYSTEM_PROMPT
        + "\n\nAUTHORITATIVE JSON SCHEMA:\n"
        + schema_text
    )

    return Agent(
        client=get_foundry_client(),
        name="UIJsonGenerationAgent",
        instructions=instructions,
    )