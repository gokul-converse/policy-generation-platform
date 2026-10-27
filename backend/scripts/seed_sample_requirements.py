"""Seed the dev database with sample requirement data for manual testing.

Creates one confirmed requirement session ('SES-DEMO-001') with two
validated requirements ('REQ-DEMO-001', 'REQ-DEMO-002'). This lets you
exercise both entry points into skill/policy generation without waiting
on the teammate's requirement-gathering agent:

  - Single requirement:  POST /skills/generate   {"requirement_id": "REQ-DEMO-001"}
                          POST /policies/generate {"requirement_id": "REQ-DEMO-001"}

  - Whole session:       POST /skills/generate   {"session_id": "SES-DEMO-001"}
                          POST /policies/generate {"session_id": "SES-DEMO-001"}

Safe to re-run: existing rows with the same IDs are left untouched.

Usage:
    python -m scripts.seed_sample_requirements
"""

import asyncio

from sqlalchemy import text

from app.db.session import AsyncSessionLocal, create_db_tables

SESSION_ID = "SES-DEMO-001"


async def seed() -> None:
    """Insert the demo session and its two requirements if not present."""

    # Make sure every table (including the requirement tables) exists,
    # the same bootstrap the app itself runs on startup.
    await create_db_tables()

    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            text(
                "SELECT 1 FROM requirement_sessions WHERE session_id = :sid"
            ),
            {"sid": SESSION_ID},
        )

        if existing.first() is not None:
            print(f"Session {SESSION_ID!r} already exists — nothing to do.")
            return

        await session.execute(
            text(
                """
                INSERT INTO requirement_sessions
                    (session_id, original_description, domain, status,
                     created_at, updated_at)
                VALUES
                    (:sid, :description, 'hr', 'confirmed',
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "sid": SESSION_ID,
                "description": (
                    "Employees receive 20 days of annual leave per year, "
                    "and leave requests must be submitted at least 5 "
                    "days before the leave starts."
                ),
            },
        )

        requirements_insert = text(
            """
            INSERT INTO requirements
                (requirement_id, session_id, topic, description,
                 status, created_at)
            VALUES
                (:requirement_id, :sid, :topic, :description,
                 'validated', CURRENT_TIMESTAMP)
            """
        )

        await session.execute(
            requirements_insert,
            {
                "requirement_id": "REQ-DEMO-001",
                "sid": SESSION_ID,
                "topic": "Leave Entitlement",
                "description": (
                    "Employees receive 20 days of annual leave per year."
                ),
            },
        )

        await session.execute(
            requirements_insert,
            {
                "requirement_id": "REQ-DEMO-002",
                "sid": SESSION_ID,
                "topic": "Notice Period",
                "description": (
                    "Leave requests must be submitted at least 5 days "
                    "before the leave starts."
                ),
            },
        )

        await session.commit()

    print(f"Seeded session {SESSION_ID!r} with requirements:")
    print("  - REQ-DEMO-001: Employees receive 20 days of annual leave per year.")
    print("  - REQ-DEMO-002: Leave requests must be submitted at least 5 days before leave starts.")


if __name__ == "__main__":
    asyncio.run(seed())
