
"""Requirements Gathering Agent using the Ollama chat client."""

import json

from app.clients.ollama_client import create_ollama_client


SYSTEM_INSTRUCTIONS = """
You are the Requirements Gathering Agent for a policy generation platform.

Responsibilities:
1. Understand the user's policy request.
2. Identify the policy domain and intent.
3. Extract only explicitly stated requirements.
4. Review supplied document evidence for relevant context.
5. Preserve each evidence item's source and approval status.
6. Identify potentially missing information for the validation agent.
7. Never invent company rules or claim that unapproved evidence is approved.

Return ONLY one valid JSON object, without Markdown fences, using
this structure:

{
  "requirement_type": "policy_generation",
  "domain": "hr",
  "policy_name": null,
  "user_intent": "",
  "requirements": {},
  "evidence": [],
  "missing_fields": [],
  "validation_handoff": {
    "status": "needs_validation",
    "questions_to_consider": []
  }
}

Domain must be one of: hr, finance, it_security, general, unknown.
Use null or empty arrays when information is unknown.
Include only evidence records supplied in the input.
The validation agent is responsible for final completeness validation.
"""


def parse_json_response(response_text: str) -> dict:
    """Parse and validate the model's JSON object."""
    response_text = response_text.strip()

    if response_text.startswith("```"):
        lines = response_text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        response_text = "\n".join(lines).strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Ollama returned invalid JSON. Check the model output."
        ) from exc

    if not isinstance(result, dict):
        raise ValueError("The model response must be a JSON object.")

    required_keys = {
        "requirement_type",
        "domain",
        "policy_name",
        "user_intent",
        "requirements",
        "evidence",
        "missing_fields",
        "validation_handoff",
    }

    missing_keys = required_keys - result.keys()

    if missing_keys:
        raise ValueError(
            f"Model JSON is missing required keys: {sorted(missing_keys)}"
        )

    return result


async def gather_requirements(
    user_input: str,
    evidence: list[dict],
) -> dict:
    """Understand user input and produce structured requirements JSON."""
    client = create_ollama_client()

    prompt = f"""
{SYSTEM_INSTRUCTIONS}

USER REQUEST:
{user_input}

RETRIEVED DOCUMENT EVIDENCE:
{json.dumps(evidence, ensure_ascii=False, indent=2)}

Analyze the request and evidence.
Return the required JSON object only.
"""

    # Use the chat client's public API directly.
    response = await client.get_response(prompt)

    response_text = getattr(response, "text", None)

    if not response_text:
        raise ValueError(
            "Ollama returned an empty response. "
            "Check the configured model and Ollama server."
        )

    result = parse_json_response(response_text)

    # Keep the source evidence supplied by the application.
    # Do not trust the model to invent or modify source references.
    result["evidence"] = evidence

    return result
