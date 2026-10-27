
import json
from pathlib import Path

from jsonschema import Draft202012Validator

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BACKEND_DIR / "schemas" / "policy-ui-contract.schema.json"
OUTPUT_DIR = BACKEND_DIR / "test_outputs"


def main():
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)

    # Check that the schema itself is valid.
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    files = [
        OUTPUT_DIR / "annual_leave.json",
        OUTPUT_DIR / "expense_policy.json",
    ]

    for path in files:
        print(f"\nChecking: {path.name}")

        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"FAIL — Invalid JSON: {exc}")
            continue

        errors = sorted(
            validator.iter_errors(data),
            key=lambda error: list(map(str, error.absolute_path)),
        )

        if not errors:
            print("PASS — Valid JSON and schema compliant.")
        else:
            print(f"FAIL — {len(errors)} schema error(s):")
            for error in errors:
                location = ".".join(map(str, error.absolute_path)) or "<root>"
                print(f"  - {location}: {error.message}")


if __name__ == "__main__":
    main()
