
"""End-to-end WebSocket test for the generic requirement workflow."""

import asyncio
import json
import os

import websockets


WS_URL = os.getenv(
    "REQUIREMENT_WS_URL",
    "ws://127.0.0.1:8000/ws/requirements",
)

MAX_QUESTIONS = 5

INITIAL_REQUIREMENT = (
    "I want to create an employee leave policy. It should define "
    "leave eligibility, annual leave limits, approval workflow, "
    "and rules for applying for leave."
)


def answer_question(question: str) -> str:
    """Choose a test answer based on the actual question asked."""
    q = question.casefold()

    if any(word in q for word in ("probation", "tenure")):
        return (
            "For testing only, assume probation lasts 3 months. "
            "Annual leave accrual begins after probation ends. "
            "This is a test assumption and is not approved policy."
        )

    if any(
        word in q
        for word in (
            "eligibility",
            "eligible",
            "employee types",
            "employment type",
            "full-time",
            "part-time",
            "contractor",
            "intern",
        )
    ):
        return (
            "The policy covers full-time and part-time employees. "
            "Contractors and interns are excluded. Eligibility for "
            "annual leave begins after probation."
        )

    if any(
        word in q
        for word in (
            "carryover",
            "carry over",
            "expiry",
            "expire",
            "unused leave",
        )
    ):
        return (
            "Carryover limits and expiry rules are undecided. "
            "Keep them as unresolved details for review."
        )

    if any(
        word in q
        for word in (
            "accrual",
            "accrue",
            "annual leave",
            "entitlement",
            "leave limit",
            "leave balance",
            "pro-rata",
            "proportionally",
        )
    ):
        return (
            "For testing only, assume full-time employees accrue "
            "15 days of annual leave per year and part-time employees "
            "accrue proportionally to their working hours. This is an "
            "unapproved test assumption. Carryover and expiry remain "
            "undecided."
        )

    if any(
        word in q
        for word in (
            "approval",
            "approver",
            "manager",
            "escalation",
            "timeline",
            "service level",
            "sla",
        )
    ):
        return (
            "The reporting manager reviews leave requests first. "
            "HR handles exceptions. Approval timelines and escalation "
            "levels remain undecided."
        )

    if any(
        word in q
        for word in (
            "submit",
            "submission",
            "apply",
            "application",
            "notice period",
            "documentation",
            "supporting document",
            "blackout",
        )
    ):
        return (
            "Employees submit leave requests through the company leave "
            "management system. Notice periods, blackout dates, and "
            "supporting-document requirements remain undecided."
        )

    if any(
        word in q
        for word in (
            "policy name",
            "policy title",
            "formal designation",
            "name of the policy",
        )
    ):
        return "Use the name Employee Leave Policy."

    if any(
        word in q
        for word in (
            "leave types",
            "types of leave",
            "leave categories",
            "sick leave",
            "casual leave",
        )
    ):
        return (
            "The policy should cover annual leave. Sick, casual, and "
            "emergency leave applicability still needs review."
        )

    if any(
        word in q
        for word in (
            "jurisdiction",
            "location",
            "country",
            "legal",
            "compliance",
            "geographic",
        )
    ):
        return (
            "The applicable country and location-specific requirements "
            "have not been decided. Record them as unresolved."
        )

    # Generic fallback: do not invent a business rule just to answer.
    return (
        "This detail has not been decided yet. Please retain it as "
        "unresolved rather than assuming a value."
    )


def normalize_question(question: str) -> str:
    """Normalize question wording for test reporting."""
    return " ".join(question.casefold().split()).rstrip(" ?.!:")


async def receive_json(websocket) -> dict:
    """Receive and parse one JSON response."""
    raw = await websocket.recv()
    response = json.loads(raw)

    print("\nServer response:")
    print(json.dumps(response, indent=2, ensure_ascii=False))

    if response.get("event") == "error":
        raise RuntimeError(
            f"Backend returned an error: {response.get('message')}"
        )

    return response


async def send_event(websocket, payload: dict) -> dict:
    """Send a WebSocket event and receive its response."""
    print("\nSending:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    await websocket.send(json.dumps(payload))
    return await receive_json(websocket)


async def main() -> None:
    questions = []
    session_id = None
    requirement_id = None
    draft_response = None

    print(f"Connecting to {WS_URL}")

    async with websockets.connect(
        WS_URL,
        open_timeout=15,
        close_timeout=5,
        max_size=2_000_000,
    ) as websocket:
        response = await send_event(
            websocket,
            {
                "event": "start",
                "message": INITIAL_REQUIREMENT,
            },
        )

        session_id = response.get("session_id")
        requirement_id = response.get("requirement_id")

        if not session_id:
            raise RuntimeError(
                "The start response did not contain session_id."
            )

        while response.get("event") == "clarification_question":
            question = response.get("question", "").strip()

            if not question:
                raise RuntimeError(
                    "Clarification response has no question."
                )

            normalized = normalize_question(question)

            if normalized in [
                normalize_question(previous)
                for previous in questions
            ]:
                print(
                    "\nTEST FAILURE: Exact duplicate question detected."
                )
                break

            questions.append(question)

            if len(questions) > MAX_QUESTIONS:
                print(
                    "\nTEST FAILURE: Backend exceeded the five-question limit."
                )
                break

            print(
                f"\nClarification {len(questions)}/{MAX_QUESTIONS}: "
                f"{question}"
            )

            answer = answer_question(question)

            response = await send_event(
                websocket,
                {
                    "event": "answer",
                    "session_id": session_id,
                    "message": answer,
                },
            )

            requirement_id = (
                response.get("requirement_id") or requirement_id
            )

        if response.get("event") == "requirement_draft":
            draft_response = response
            requirement_id = (
                response.get("requirement_id") or requirement_id
            )

            print("\nDraft is ready for review.")
            print(
                "Questions asked:",
                response.get("questions_asked"),
            )
            print(
                "Unresolved details:",
                json.dumps(
                    response.get("unresolved_details", []),
                    indent=2,
                    ensure_ascii=False,
                ),
            )

            # This is a test confirmation. Only run against test data.
            confirmation = await send_event(
                websocket,
                {
                    "event": "confirm",
                    "session_id": session_id,
                    "message": "confirm",
                },
            )

            if confirmation.get("event") == "requirements_finalized":
                print("\nTEST PASSED: Requirements finalized.")
                print("Requirement ID:", confirmation.get("requirement_id"))
                print(
                    "Version ID:",
                    confirmation.get("requirement_version_id"),
                )
                print(
                    "Version number:",
                    confirmation.get("version_number"),
                )
            else:
                print(
                    "\nTEST WARNING: Draft returned, but confirmation "
                    "did not finalize successfully."
                )

        elif response.get("event") == "clarification_question":
            print(
                "\nTEST WARNING: Workflow is still asking questions "
                "after the test loop."
            )
        else:
            print(
                "\nTEST WARNING: Workflow ended with event:",
                response.get("event"),
            )

    print("\n========== TEST SUMMARY ==========")
    print("Session ID:", session_id)
    print("Requirement ID:", requirement_id)
    print("Questions asked:", len(questions))
    print("Within maximum limit:", len(questions) <= MAX_QUESTIONS)
    print("Draft received:", draft_response is not None)

    if len(questions) < 3:
        print(
            "NOTE: Fewer than three questions were asked. "
            "Check whether material gaps remained; the agent should "
            "not ask unnecessary questions just to reach three."
        )

    print("==================================")


if __name__ == "__main__":
    asyncio.run(main())
