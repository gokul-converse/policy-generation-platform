"""Test loading requirements by session_id from conversational requirement gathering."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.policy_generation.policy_generator import StructuredPolicyGenerationOutput
from app.db.session import Base, get_db
from app.main import app
from app.models.policy_api import PolicySectionModel
from app.models.skills import GeneratedSkill, GeneratedSkillSet
from app.services import policy_service, skill_service


@pytest.fixture
def mock_output():
    skill_set = GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="conversational-leave-skill",
                description="Skill from conversational session",
                instructions=(
                    "# Leave Skill\n\n"
                    "## Purpose\n"
                    "Rules\n\n"
                    "## Instructions\n"
                    "Provide 25 days annual leave.\n\n"
                    "## Source Requirements\n"
                    "- REQ-SESS-001: Staff receive 25 days of paid annual leave."
                ),
                requirement_ids=["REQ-SESS-001"],
            )
        ]
    )
    policy_output = StructuredPolicyGenerationOutput(
        title="Conversational HR Policy",
        domain="Human Resources",
        sections=[
            PolicySectionModel(
                section_id="purpose",
                title="Purpose",
                content="Establishes leave rules.",
                requirement_ids=["REQ-SESS-001"],
            ),
            PolicySectionModel(
                section_id="entitlement",
                title="Entitlement",
                content="Staff receive 25 days of paid annual leave.",
                requirement_ids=["REQ-SESS-001"],
            ),
        ],
        unresolved_items=[],
    )
    return skill_set, policy_output


@pytest.mark.asyncio
async def test_session_id_loads_requirements_automatically(tmp_path, monkeypatch, mock_output):
    """Verify passing only session_id automatically queries DB for requirements."""
    mock_skill_set, mock_policy_output = mock_output

    test_db = tmp_path / "test_session_id.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{test_db.as_posix()}")

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Create teammate's requirement tables in test db
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS requirement_sessions (
                session_id TEXT PRIMARY KEY,
                original_description TEXT NOT NULL,
                domain TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS requirements (
                requirement_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """))
        # Seed conversational requirement gathering session
        await conn.execute(text("""
            INSERT INTO requirement_sessions (session_id, original_description, domain, status, created_at, updated_at)
            VALUES ('SES-HR-777', 'Annual leave conversation with employee', 'Human Resources', 'completed', '2026-10-22', '2026-10-22');
        """))
        await conn.execute(text("""
            INSERT INTO requirements (requirement_id, session_id, topic, description, status, created_at)
            VALUES ('REQ-SESS-001', 'SES-HR-777', 'Leave Entitlement', 'Staff receive 25 days of paid annual leave.', 'validated', '2026-10-22');
        """))

    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(skill_service, "generate_skills", AsyncMock(return_value=mock_skill_set))
    monkeypatch.setattr(policy_service, "generate_policy_from_requirements", AsyncMock(return_value=mock_policy_output))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Skill Generation with ONLY session_id
        skill_payload = {"session_id": "SES-HR-777"}
        res_skill = await client.post("/skills/generate", json=skill_payload)
        assert res_skill.status_code == 201, res_skill.text
        skill_data = res_skill.json()
        assert len(skill_data["skills"]) == 1
        assert skill_data["skills"][0]["source_requirement_version_id"] == "SES-HR-777"

        # 2. Policy Generation with ONLY session_id and skill_command
        policy_payload = {
            "session_id": "SES-HR-777",
            "skill_command": "/company-policy-generator",
        }
        res_policy = await client.post("/policies/generate", json=policy_payload)
        assert res_policy.status_code == 201, res_policy.text
        policy_data = res_policy.json()
        assert policy_data["domain"] == "Human Resources"
        assert policy_data["version"] == 1
        assert policy_data["validation_status"] == "pass"
        assert policy_data["source_requirement_version_id"] == "SES-HR-777"
        assert len(policy_data["sections"]) == 2

        # 3. Non-existent session_id returns 422 / 400 error
        bad_res = await client.post("/policies/generate", json={"session_id": "NON-EXISTENT-SESSION"})
        assert bad_res.status_code in (400, 422, 500)

    app.dependency_overrides.clear()
    await test_engine.dispose()
