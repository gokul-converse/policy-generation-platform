
import json
from functools import lru_cache

from agent_framework import Agent

from app.clients.foundry_client import get_foundry_client
from app.prompts.repair_prompt import REPAIR_SYSTEM_PROMPT

@lru_cache(maxsize=1)
def get_ui_json_repair_agent() -> Agent:
    return Agent(
        client=get_foundry_client(),
        name="UIJsonRepairAgent",
        instructions=REPAIR_SYSTEM_PROMPT,
    )


async def repair_ui_json(
    policy_text: str,
    invalid_output: str,
    errors: list[str],
    schema: dict,
) -> str:
    repair_agent = get_ui_json_repair_agent()

    repair_input = {
        "policy_text": policy_text,
        "invalid_generated_output": invalid_output,
        "validation_errors": errors,
        "json_schema": schema,
    }

    response = await repair_agent.run(
        json.dumps(repair_input, ensure_ascii=False)
    )

    return response.text
