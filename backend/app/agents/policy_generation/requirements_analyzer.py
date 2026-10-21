
"""Analyze policy requirements using Microsoft Agent Framework and Ollama."""

from agent_framework import Agent
from app.clients.ollama_client import create_ollama_client
from app.models.requirements import RequirementAnalysis

REQUIREMENTS_INSTRUCTIONS = """
You are a requirements analyst for a policy-generation system.

Analyze the original policy description supplied by the user.

Your responsibilities:
1. Extract each distinct, explicit business requirement.
2. Preserve the meaning, numbers, units, deadlines, conditions, and exceptions.
3. Do not turn suggestions into mandatory requirements.
4. Discover meaningful policy domains from the actual input.
5. Identify missing information only when it materially affects
   interpretation or drafting.
6. Identify conflicting statements and materially ambiguous requirements.
7. Never invent company rules, approval procedures, eligibility conditions,
   penalties, or other business requirements.
8. Keep each requirement complete and understandable.
9. Preserve the original_text exactly as supplied.

Return a JSON object with exactly these fields:
{
  "original_text": "The exact original input",
  "requirements": [],
  "identified_domains": [],
  "missing_information": [],
  "ambiguities": []
}

All fields except original_text must be arrays of strings.
Use empty arrays when there are no items.
Do not include Markdown or explanations outside the JSON object.
"""


def clean_analysis(
    analysis: RequirementAnalysis,
    original_text: str,
) -> RequirementAnalysis:
    """Normalize model output and preserve the authoritative user input."""

    # The user's input, not the LLM, is the source of truth.
    analysis.original_text = original_text

    # Remove blank values and duplicates from each collection.
    for field_name in (
        "requirements",
        "identified_domains",
        "missing_information",
        "ambiguities",
    ):
        values = getattr(analysis, field_name)

        cleaned = [
            value.strip()
            for value in values
            if isinstance(value, str) and value.strip()
        ]

        setattr(analysis, field_name, list(dict.fromkeys(cleaned)))

    # An empty requirement list is a failed analysis, not a valid result.
    if not analysis.requirements:
        raise ValueError(
            "Requirements analysis returned no usable requirements. "
            "Clarify the input or retry the analysis."
        )

    return analysis


async def analyze_requirements(
    description: str,
) -> RequirementAnalysis:
    """Convert runtime input into a validated requirements analysis."""

    # Validate input before creating a client or making a model call.
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Policy requirements cannot be empty.")

    client = create_ollama_client()

    agent = Agent(
        client=client,
        name="RequirementsAnalyzerAgent",
        instructions=REQUIREMENTS_INSTRUCTIONS,
        default_options={
            "response_format": RequirementAnalysis.model_json_schema()
        },
    )

    result = await agent.run(
        "Analyze the following policy requirements.\n\n"
        f"Original input:\n{description}"
    )

    # Validate the structured model response.
    if getattr(result, "value", None) is not None:
        analysis = RequirementAnalysis.model_validate(result.value)
    else:
        analysis = RequirementAnalysis.model_validate_json(result.text)

    return clean_analysis(analysis, description)
