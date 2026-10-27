
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BACKEND_DIR / "schemas" / "policy-ui-contract.schema.json"


@lru_cache(maxsize=1)
def get_validator():
    with SCHEMA_PATH.open(encoding="utf-8") as file:
        schema = json.load(file)

    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_ui_definition(ui_definition: dict) -> list[str]:
    """Return schema validation errors; an empty list means valid."""
    validator = get_validator()

    errors = sorted(
        validator.iter_errors(ui_definition),
        key=lambda error: list(map(str, error.absolute_path)),
    )

    return [
        f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: "
        f"{error.message}"
        for error in errors
    ]
