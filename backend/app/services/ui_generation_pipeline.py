
import logging
import time

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from app.agents.foundry.agent import get_ui_json_agent
from app.agents.repair.agent import repair_ui_json

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BACKEND_DIR / "json_schema" / "policy-ui-contract.schema.json"

MAX_REPAIR_ATTEMPTS = 2

@lru_cache(maxsize=1)
def load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as file:
        schema = json.load(file)

    Draft202012Validator.check_schema(schema)
    return schema


def validate_output(output: Any, validator) -> list[str]:
    if not isinstance(output, dict):
        return ["<root>: output must be a JSON object"]

    errors = sorted(
        validator.iter_errors(output),
        key=lambda err: list(map(str, err.absolute_path)),
    )

    return [
        f"{'.'.join(map(str, err.absolute_path)) or '<root>'}: "
        f"{err.message}"
        for err in errors
    ]


def parse_json(raw_output: str) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(raw_output), []
    except (json.JSONDecodeError, TypeError) as exc:
        return None, [f"JSON parsing error: {exc}"]


async def generate_validated_ui(
    policy_text: str,
    request_id: str = "unknown",
) -> dict:
    pipeline_started = time.perf_counter()

    logger.info("[%s] Pipeline started", request_id)

    try:
        schema = load_schema()
        validator = Draft202012Validator(schema)
        logger.info("[%s] Schema loaded", request_id)

        generation_agent = get_ui_json_agent()

        generation_started = time.perf_counter()
        logger.info("[%s] Generation agent started", request_id)

        response = await generation_agent.run(policy_text)
        raw_output = response.text

        logger.info(
            "[%s] Generation agent completed | duration=%.2fs | "
            "response_chars=%d",
            request_id,
            time.perf_counter() - generation_started,
            len(raw_output),
        )

        for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
            logger.info(
                "[%s] Output processing started | repair_attempt=%d",
                request_id,
                attempt,
            )

            ui_definition, parse_errors = parse_json(raw_output)

            if parse_errors:
                validation_errors = parse_errors
                logger.warning(
                    "[%s] JSON parsing failed | repair_attempt=%d",
                    request_id,
                    attempt,
                )
            else:
                logger.info(
                    "[%s] JSON parsing passed | repair_attempt=%d",
                    request_id,
                    attempt,
                )

                validation_errors = validate_output(
                    ui_definition, validator
                )

            if not validation_errors:
                logger.info(
                    "[%s] Schema validation passed | repair_attempt=%d",
                    request_id,
                    attempt,
                )
                logger.info(
                    "[%s] Pipeline succeeded | total_duration=%.2fs",
                    request_id,
                    time.perf_counter() - pipeline_started,
                )
                return ui_definition

            logger.warning(
                "[%s] Validation failed | repair_attempt=%d | "
                "error_count=%d | errors=%s",
                request_id,
                attempt,
                len(validation_errors),
                validation_errors,
            )

            if attempt == MAX_REPAIR_ATTEMPTS:
                logger.error(
                    "[%s] Repair limit reached | attempts=%d",
                    request_id,
                    MAX_REPAIR_ATTEMPTS,
                )
                raise ValueError(
                    "UI output remained invalid after "
                    f"{MAX_REPAIR_ATTEMPTS} repair attempts."
                )

            repair_started = time.perf_counter()

            logger.info(
                "[%s] Repair agent started | attempt=%d",
                request_id,
                attempt + 1,
            )

            try:
                raw_output = await repair_ui_json(
                    policy_text=policy_text,
                    invalid_output=raw_output,
                    errors=validation_errors,
                    schema=schema,
                )
            except Exception:
                logger.exception(
                    "[%s] Repair agent failed | attempt=%d",
                    request_id,
                    attempt + 1,
                )
                raise

            logger.info(
                "[%s] Repair agent completed | attempt=%d | "
                "duration=%.2fs | response_chars=%d",
                request_id,
                attempt + 1,
                time.perf_counter() - repair_started,
                len(raw_output),
            )

    except Exception:
        logger.exception("[%s] Pipeline failed", request_id)
        raise

    raise RuntimeError("Unexpected end of UI generation pipeline.")
